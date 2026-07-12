"""Background pipeline + `POST /runs/:id/approve` orchestration.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §8 (pipeline), §4 (job state),
§6 (approve contract). Issue #50.

`approve()` is the synchronous front door: it validates the body, gates the
low-signal flow, transitions the row `preflight_ready → running`, registers an
in-memory job, and hands the heavy work to FastAPI `BackgroundTasks`.

`run_pipeline()` is the background coroutine. It fans out across the approved
competitors concurrently (`asyncio.gather`), caps concurrent OpenAI calls with a
semaphore, pools the per-source quotes + pain items, synthesises grounded gaps,
optionally runs the idea-match step, redacts PII at the persist boundary, and
writes `idea_runs` + `gaps`. `status='done'` is set last.

**Source resilience (slice 2 §5.1, US-S3, issue #60).** Each source is wrapped
in retry-once-with-backoff and isolated: a source that exhausts its retries is
recorded as a `_SourceFailure`, not raised, so it can't cancel its siblings.
After fan-out, `succeeded / total` is gated against `PARTIAL_SOURCE_THRESHOLD` —
above it the run completes `done` with a `partial_sources` banner naming the
failures; below it the run is `failed` (`sources_below_threshold`). Errors
*outside* the per-source fan-out map to `internal_error` (§5.3). A server restart
mid-run still leaves the row `running` — the on-read reconciliation that fixes
that is a separate slice-2 item (§5.2).

**Idea-blinding (spec §13).** `_process_source` does not receive `idea` or
`target_gap`; `idea` is only in scope at the synthesis / idea-match call sites.
A future edit cannot leak the idea into per-source prompts through this module.
"""
from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, HTTPException, status

from app.clients.supabase import (
    get_idea_run,
    insert_gaps,
    update_idea_run_done,
    update_idea_run_failed,
    update_idea_run_running,
)
from app.config.constants import (
    APP_REVIEW_PAGES,
    LOW_SIGNAL_CANDIDATE_THRESHOLD,
    PARTIAL_SOURCE_THRESHOLD,
    SOURCE_RETRY_ATTEMPTS,
    SOURCE_RETRY_BACKOFF_BASE_SECONDS,
)
from app.ingestion.appStoreReviews import getAppReviews
from app.ingestion.youtubeComments import getYoutubeComments
from app.llm import synthesis as synthesis_stage
from app.llm.idea_match import match_idea
from app.preprocessing.redact import redact
from app.schemas.runs import (
    Competitor,
    ExtractionYield,
    FailedSource,
    FailureReason,
    GapItem,
    PainItem,
    PartialSources,
    QualitySignals,
    Quote,
    RunApprove,
    SourceMetadata,
)
from app.services.per_source_extraction_service import extract_per_source

logger = logging.getLogger(__name__)

# Debug trace for this stage only: mirrors the per-source extraction debug log,
# into its own file so per-run pipeline detail can be inspected after the fact
# regardless of the process-wide LOG_LEVEL.
_DEBUG_LOG_PATH = Path("logs/run_pipeline_debug.log")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(_DEBUG_LOG_PATH)
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(_file_handler)
    logger.setLevel(logging.DEBUG)

# Spec §8: cap concurrent OpenAI calls while all sources fan out in parallel.
_OPENAI_CONCURRENCY = 5

# In-memory job registry (spec §4). Lost on restart by design — slice 2 adds the
# restart → failed transition. Keyed by run_id; values:
#   { "status", "stage", "started_at", "future" }
_jobs: dict[str, dict] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set_stage(run_id: str, stage: str) -> None:
    job = _jobs.get(run_id)
    if job is not None:
        job["stage"] = stage


def is_pipeline_live(run_id: str) -> bool:
    """True when a background pipeline for `run_id` is currently running here.

    Restart reconciliation (spec §5.2, US-S4) keys off this: `_jobs` is in-memory
    and lost on restart, so the *absence* of a live entry for a row the DB still
    calls `running` is the signal that the row was orphaned by a server restart.
    Done/failed jobs linger in `_jobs` as an audit trail but are not live.
    """
    job = _jobs.get(run_id)
    return job is not None and job.get("status") == "running"


def has_running_pipeline() -> bool:
    """True when a background pipeline is currently `running` on this instance.

    The concurrency guard (spec §6, issue #59 Q2) reuses this registry: it counts
    active *pipelines* (post-approve), not in-flight synchronous pre-flights, so
    a second POST /runs while a pipeline runs returns `429 busy`. Done/failed jobs
    stay in `_jobs` as a thin audit trail but don't count as active.
    """
    return any(job.get("status") == "running" for job in _jobs.values())


# --- approve front door -----------------------------------------------------


def approve(
    run_id: str,
    request: RunApprove,
    background_tasks: BackgroundTasks,
) -> dict:
    """Validate, gate low-signal, transition to running, enqueue the pipeline.

    Returns ``{run_id, status: 'running'}`` (spec §6). Raises:
    - 404 if the run does not exist
    - 409 if the run is not in `preflight_ready`
    - 400 if pre-flight produced fewer than `LOW_SIGNAL_CANDIDATE_THRESHOLD`
      candidates and `acknowledged_low_signal` isn't true
    """
    row = get_idea_run(run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )
    if row["status"] != "preflight_ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is '{row['status']}', expected 'preflight_ready'",
        )
    # Makes sure there are enough competitors to proceed
    candidate_count = len(row.get("competitors_json") or [])
    if (
        candidate_count < LOW_SIGNAL_CANDIDATE_THRESHOLD
        and request.acknowledged_low_signal is not True
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Low-signal run requires acknowledged_low_signal=true",
        )

    competitors = [c.model_dump() for c in request.competitors]
    # The conditional update is the real gate: if a concurrent approve already
    # moved the row out of `preflight_ready`, it returns None and we 409 here —
    # so the pipeline is enqueued exactly once even under a race.
    if update_idea_run_running(run_id, competitors) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run is no longer 'preflight_ready' (already approved?)",
        )
    _jobs[run_id] = {
        "status": "running",
        "stage": "queued",
        "started_at": _now(),
        "future": None,
    }

    # `idea` / `target_gap` enter scope here only for synthesis + idea_match —
    # never threaded into _process_source (spec §13 idea-blinding).
    background_tasks.add_task(
        run_pipeline,
        run_id=run_id,
        idea=row["idea"],
        target_gap=row.get("target_gap"),
        category=row.get("category") or "other",
        competitors=request.competitors,
    )

    logger.info("run_approved run_id=%s sources=%d", run_id, len(competitors))
    return {"run_id": run_id, "status": "running"}


# --- background pipeline ----------------------------------------------------


def _ingest(competitor: Competitor) -> list[dict]:
    """Fetch raw source rows for one competitor (blocking; runs in a thread)."""
    if competitor.source == "youtube":
        return getYoutubeComments(competitor.identifier, "relevance", competitor.name)
    return getAppReviews(
        _appstore_review_id(competitor),
        "mostHelpful", #changed from mostRecent
        APP_REVIEW_PAGES,
        competitor.name,
    )


def _appstore_review_id(competitor: Competitor) -> str:
    """Resolve the numeric track id the iTunes RSS reviews feed needs.

    Pre-flight stores `bundle_id` as the competitor identifier, but the
    customerreviews RSS endpoint keys on the numeric track id — which lives in
    the App Store URL as `/id<digits>`. Fall back to the identifier when it is
    already numeric.
    """
    import re

    match = re.search(r"/id(\d+)", competitor.url)
    if match:
        return match.group(1)
    if competitor.identifier.isdigit():
        return competitor.identifier
    raise ValueError(
        f"Cannot resolve App Store numeric id from url {competitor.url!r}"
    )


def _redact_quote(quote: Quote) -> Quote:
    """Scrub PII from a quote's text at the persist boundary (spec §8, #48)."""
    return quote.model_copy(update={"text_redacted": redact(quote.text_redacted)})


async def _process_source(
    competitor: Competitor,
    category: str,
    semaphore: asyncio.Semaphore,
) -> tuple[int, list[PainItem], list[Quote]]:
    """Ingest → extract (idea-blinded) → redact for one source.

    No `idea` / `target_gap` in scope — the confirmation-bias guard (spec §13).
    The OpenAI call inside `extract_per_source` is bounded by `semaphore`; the
    blocking ingestion + extraction run in worker threads so the gather is real
    concurrency rather than serialised blocking calls.

    Returns the raw comment count alongside the extracted pain items + quotes so
    the orchestrator can fold per-source extraction yield into `quality_signals`
    (slice 3 §5) without re-ingesting.
    """
    comments = await asyncio.to_thread(_ingest, competitor)
    logger.debug(
        "source_comment_count source=%s name=%s count=%d",
        competitor.source, competitor.name, len(comments),
    )
    metadata = SourceMetadata(
        source=competitor.source,
        source_id=competitor.identifier,
        category=category,
        title=competitor.name,
    )
    async with semaphore:
        pain_items, quotes = await asyncio.to_thread(
            extract_per_source, comments, metadata
        )
    redacted = [_redact_quote(q) for q in quotes]
    return len(comments), pain_items, redacted


# --- per-source resilience (slice 2 §5.1, US-S3) ----------------------------


@dataclass
class _SourceSuccess:
    """One source that survived (possibly after a retry); feeds the quote pool.

    `comment_count` is the raw row count ingested before extraction — it feeds
    the per-source `extraction_yield` in `quality_signals` (slice 3 §5).
    """

    competitor: Competitor
    comment_count: int
    pain_items: list[PainItem]
    quotes: list[Quote]


@dataclass
class _SourceFailure:
    """One source that exhausted its retries; named in `partial_sources`."""

    competitor: Competitor
    reason: str


def _backoff_delay(attempt: int) -> float:
    """Seconds to wait before retry *attempt* (0-indexed): exponential backoff.

    Isolated so tests can patch the wait to zero without faking time (PRD §8).
    """
    return SOURCE_RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)


async def _process_source_resilient(
    competitor: Competitor,
    category: str,
    semaphore: asyncio.Semaphore,
) -> _SourceSuccess | _SourceFailure:
    """Run `_process_source` with retry-once-with-backoff, never raising.

    Slice 2 §5.1: a source is attempted ``SOURCE_RETRY_ATTEMPTS`` times; a
    transient failure on the first attempt is retried after an exponential
    backoff. A source that exhausts every attempt is captured as a
    `_SourceFailure` instead of bubbling up — so one flaky source can't cancel
    its siblings or fail the whole run below the §5.1 threshold.
    """
    last_exc: Exception | None = None
    for attempt in range(SOURCE_RETRY_ATTEMPTS):
        try:
            comment_count, pain_items, quotes = await _process_source(
                competitor, category, semaphore
            )
            return _SourceSuccess(
                competitor=competitor,
                comment_count=comment_count,
                pain_items=pain_items,
                quotes=quotes,
            )
        except Exception as exc:  # noqa: BLE001 — source-level isolation is the point.
            last_exc = exc
            if attempt < SOURCE_RETRY_ATTEMPTS - 1:
                logger.warning(
                    "source_retry source=%s name=%s attempt=%d reason=%s",
                    competitor.source, competitor.name, attempt + 1, exc,
                )
                await asyncio.sleep(_backoff_delay(attempt))

    reason = f"{type(last_exc).__name__}: {last_exc}"
    logger.warning(
        "source_failed source=%s name=%s reason=%s",
        competitor.source, competitor.name, reason,
    )
    return _SourceFailure(competitor=competitor, reason=reason)


def _gap_rows(run_id: str, gaps: list[GapItem]) -> list[dict]:
    """Map ordered GapItems to `gaps` table rows (spec §4)."""
    return [
        {
            "gap_id": gap.gap_id,
            "run_id": run_id,
            "gap": gap.gap,
            "severity": gap.severity,
            "frequency": gap.frequency,
            "spread": gap.spread,
            "competitors_present_json": gap.competitors_present,
            "evidence_quote_ids_json": gap.evidence_quote_ids,
            "ordinal": ordinal,
        }
        for ordinal, gap in enumerate(gaps, start=1)
    ]


# --- quality signals (slice 3 §5 / PRD §7.9) --------------------------------


def _compute_quality_signals(
    gaps: list[GapItem],
    quotes: list[Quote],
    extraction_yield: list[ExtractionYield],
) -> QualitySignals:
    """Derive the per-run observability signals from the synthesised result.

    - `quote_source_diversity` (OQ3): `1 - max_source_share` over the source
      distribution of *cited* quotes (those referenced by some gap's
      `evidence_quote_ids`). 0 when one source supplies every cited quote (or
      there are no citations); approaches 1 as citations spread across sources.
    - `severity_distribution`: length-5 count of gaps at severity [1..5].
    - `single_source_gap_count`: gaps confined to one competitor (`spread == 1`).
    - `extraction_yield`: passed through from the per-source fan-out.
    """
    source_by_quote = {q.quote_id: q.source for q in quotes}
    cited_ids = {qid for gap in gaps for qid in gap.evidence_quote_ids}
    source_counts = Counter(
        source_by_quote[qid] for qid in cited_ids if qid in source_by_quote
    )
    total_cited = sum(source_counts.values())
    diversity = 0.0 if total_cited == 0 else 1.0 - max(source_counts.values()) / total_cited

    severity_distribution = [0, 0, 0, 0, 0]
    for gap in gaps:
        if 1 <= gap.severity <= 5:
            severity_distribution[gap.severity - 1] += 1

    return QualitySignals(
        quote_source_diversity=round(diversity, 4),
        severity_distribution=severity_distribution,
        single_source_gap_count=sum(1 for gap in gaps if gap.spread == 1),
        extraction_yield=extraction_yield,
    )


def _safe_quality_signals(
    run_id: str,
    gaps: list[GapItem],
    quotes: list[Quote],
    extraction_yield: list[ExtractionYield],
) -> QualitySignals | None:
    """Compute `quality_signals` defensively (slice 3 §5).

    The field is observability, never load-bearing for completion: a computation
    error is logged and persisted as `null` rather than failing an otherwise
    successful run.
    """
    try:
        return _compute_quality_signals(gaps, quotes, extraction_yield)
    except Exception as exc:  # noqa: BLE001 — quality_signals must never fail a run.
        logger.warning(
            "quality_signals_failed run_id=%s reason=%s: %s",
            run_id, type(exc).__name__, exc,
        )
        return None


async def run_pipeline(
    run_id: str,
    idea: str,
    target_gap: str | None,
    category: str,
    competitors: list[Competitor],
) -> None:
    """Background task: fan out, synthesise, persist. Sets terminal status last."""
    try:
        _set_stage(run_id, "extracting")
        semaphore = asyncio.Semaphore(_OPENAI_CONCURRENCY)
        # Each task swallows its own failure into a `_SourceFailure`, so the
        # fan-out never cancels siblings — no `return_exceptions` needed because
        # `_process_source_resilient` is contractually non-raising (slice 2 §5.1).
        outcomes = await asyncio.gather(
            *(_process_source_resilient(c, category, semaphore) for c in competitors)
        )

        succeeded = [o for o in outcomes if isinstance(o, _SourceSuccess)]
        failed = [o for o in outcomes if isinstance(o, _SourceFailure)]
        total_count = len(outcomes)

        # Partial-completion gate (US-S3): below the threshold the surviving
        # signal is too thin to synthesise honestly — fail loud rather than ship
        # a misleadingly-confident result from a fraction of the sources.
        if total_count and len(succeeded) / total_count < PARTIAL_SOURCE_THRESHOLD:
            names = ", ".join(o.competitor.name for o in failed)
            reason = (
                f"Only {len(succeeded)}/{total_count} sources succeeded "
                f"(< {int(PARTIAL_SOURCE_THRESHOLD * 100)}% threshold). Failed: {names}"
            )
            logger.warning("run_below_threshold run_id=%s reason=%s", run_id, reason)
            update_idea_run_failed(run_id, FailureReason.sources_below_threshold.value)
            job = _jobs.get(run_id)
            if job is not None:
                job["status"] = "failed"
                job["stage"] = "failed"
            return

        # Some sources may have failed but the threshold held — record the
        # survivors' names for the Result-page banner (slice 2 §5.1).
        partial_sources = None
        if failed:
            partial_sources = PartialSources(
                failed=[
                    FailedSource(
                        source=o.competitor.source,
                        name=o.competitor.name,
                        reason=o.reason,
                    )
                    for o in failed
                ],
                succeeded_count=len(succeeded),
                total_count=total_count,
            )

        all_pain: list[PainItem] = []
        all_quotes: list[Quote] = []
        for outcome in succeeded:
            all_pain.extend(outcome.pain_items)
            all_quotes.extend(outcome.quotes)

        _set_stage(run_id, "synthesis")
        gaps, coverage = await asyncio.to_thread(
            synthesis_stage.synthesize, idea, target_gap, all_quotes, all_pain
        )

        idea_match = None
        if target_gap:
            _set_stage(run_id, "idea_match")
            idea_match = await asyncio.to_thread(
                match_idea, idea, target_gap, gaps, all_quotes
            )

        # Per-run observability (slice 3 §5 / PRD §7.9): yield per surviving
        # source, then derive the post-synthesis signals. Logged, not rendered,
        # and never load-bearing — a computation error persists `null`.
        extraction_yield = [
            ExtractionYield(
                source=o.competitor.source,
                comment_count=o.comment_count,
                pain_item_count=len(o.pain_items),
            )
            for o in succeeded
        ]
        quality_signals = _safe_quality_signals(
            run_id, gaps, all_quotes, extraction_yield
        )
        if quality_signals is not None:
            logger.info(
                "quality_signals run_id=%s diversity=%.4f severity=%s "
                "single_source_gaps=%d",
                run_id, quality_signals.quote_source_diversity,
                quality_signals.severity_distribution,
                quality_signals.single_source_gap_count,
            )

        _set_stage(run_id, "persisting")
        quotes_map = {q.quote_id: q.model_dump() for q in all_quotes}
        # Gaps land BEFORE the status flip so `status='done'` is genuinely the
        # last write (spec §8). The done view reads gaps only once status is
        # 'done', so persisting them first closes the window where a polling
        # client could see a completed run with no gaps.
        insert_gaps(_gap_rows(run_id, gaps))
        update_idea_run_done(
            run_id,
            quotes=quotes_map,
            coverage=coverage.model_dump(),
            idea_match=idea_match.model_dump() if idea_match else None,
            partial_sources=partial_sources.model_dump() if partial_sources else None,
            quality_signals=quality_signals.model_dump() if quality_signals else None,
        )

        job = _jobs.get(run_id)
        if job is not None:
            job["status"] = "done"
            job["stage"] = "done"
        logger.info(
            "run_done run_id=%s gaps=%d quotes=%d", run_id, len(gaps), len(all_quotes)
        )
    except Exception as exc:  # noqa: BLE001 — unexpected pipeline failure.
        # Source-level failures are handled above (§5.1); reaching here means an
        # error outside the per-source fan-out (synthesis, persistence, …), which
        # maps to the catch-all `internal_error` reason (slice 2 §5.3).
        logger.exception(
            "run_failed run_id=%s reason=%s: %s", run_id, type(exc).__name__, exc
        )
        try:
            update_idea_run_failed(run_id, FailureReason.internal_error.value)
        finally:
            job = _jobs.get(run_id)
            if job is not None:
                job["status"] = "failed"
                job["stage"] = "failed"
