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

**Happy path only (slice 1).** Any source failure fails the whole run
(`status='failed'`, freeform `failure_reason`). No retries, no partial-source
threshold, no rate limiting. A server restart mid-run leaves the row `running`
forever — that's loud, not silent, and slice 2 fixes it.

**Idea-blinding (spec §13).** `_process_source` does not receive `idea` or
`target_gap`; `idea` is only in scope at the synthesis / idea-match call sites.
A future edit cannot leak the idea into per-source prompts through this module.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import BackgroundTasks, HTTPException, status

from app.clients.supabase import (
    get_idea_run,
    insert_gaps,
    update_idea_run_done,
    update_idea_run_failed,
    update_idea_run_running,
)
from app.config.constants import APP_REVIEW_PAGES
from app.ingestion.appStoreReviews import getAppReviews
from app.ingestion.youtubeComments import getYoutubeComments
from app.llm import synthesis as synthesis_stage
from app.llm.idea_match import match_idea
from app.preprocessing.redact import redact
from app.schemas.runs import (
    Competitor,
    GapItem,
    PainItem,
    Quote,
    RunApprove,
    SourceMetadata,
)
from app.services.per_source_extraction_service import extract_per_source

logger = logging.getLogger(__name__)

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
    - 400 if pre-flight was `low` and `acknowledged_low_signal` isn't true
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
    if row.get("signal_strength") == "low" and request.acknowledged_low_signal is not True:
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
        "mostRecent",
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
) -> tuple[list[PainItem], list[Quote]]:
    """Ingest → extract (idea-blinded) → redact for one source.

    No `idea` / `target_gap` in scope — the confirmation-bias guard (spec §13).
    The OpenAI call inside `extract_per_source` is bounded by `semaphore`; the
    blocking ingestion + extraction run in worker threads so the gather is real
    concurrency rather than serialised blocking calls.
    """
    comments = await asyncio.to_thread(_ingest, competitor)
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
    return pain_items, redacted


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
        results = await asyncio.gather(
            *(_process_source(c, category, semaphore) for c in competitors)
        )

        all_pain: list[PainItem] = []
        all_quotes: list[Quote] = []
        for pain_items, quotes in results:
            all_pain.extend(pain_items)
            all_quotes.extend(quotes)

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
        )

        job = _jobs.get(run_id)
        if job is not None:
            job["status"] = "done"
            job["stage"] = "done"
        logger.info(
            "run_done run_id=%s gaps=%d quotes=%d", run_id, len(gaps), len(all_quotes)
        )
    except Exception as exc:  # noqa: BLE001 — slice 1: any failure fails the run.
        reason = f"{type(exc).__name__}: {exc}"
        logger.exception("run_failed run_id=%s reason=%s", run_id, reason)
        try:
            update_idea_run_failed(run_id, reason)
        finally:
            job = _jobs.get(run_id)
            if job is not None:
                job["status"] = "failed"
                job["stage"] = "failed"
