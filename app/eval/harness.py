"""Eval runner: drive the real pipeline on a seed idea, score it, write a report.

Spec: planning/specs/v2-slice-3-eval-and-v1-removal_spec.md §4.

    python -m app.eval.harness <seed_name>

`<seed_name>` is the stem of a file in [app/eval/seed/](seed/) (e.g.
`consumer_app`). The harness:

1. runs the real pre-flight (`preflight_service.run`) for the seed idea,
2. drives the real background pipeline (`run_pipeline_service.run_pipeline`) over
   the pre-flight candidates,
3. captures the synthesised `RunResult` + `quality_signals`,
4. scores the four §7.9 metrics ([metrics.py](metrics.py)) against the seed
   labels, and
5. writes a structured JSON report to the gitignored [reports/](reports/).

It reuses the production services so eval scores the same code a real run does —
there is no parallel pipeline here. It bypasses HTTP, the per-IP rate limit, and
the daily budget cap (all enforced above the service layer), but every LLM call
still routes through `resolve(stage)`, so model routing matches production.

Persistence is the one place it diverges: the real pipeline's Supabase writes
(`insert_gaps` / `update_idea_run_done` / `update_idea_run_failed`) are
intercepted in-process and captured rather than written, so eval runs never land
in the production `idea_runs` feed. Everything upstream — pre-flight search,
ingestion, extraction, synthesis, idea-match, `quality_signals` — runs for real.

Requires the same environment as the app (OpenAI / YouTube / App Store / Supabase
config must be importable), since it imports and drives the real services.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import patch
from uuid import uuid4

from pydantic import BaseModel, Field

from app.eval import metrics
from app.schemas.runs import Coverage, GapItem, QualitySignals, RunResult

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent / "seed"
REPORTS_DIR = Path(__file__).parent / "reports"


# --- seed-set schema (§4) ---------------------------------------------------


class ExpectedGap(BaseModel):
    """One hand-labelled expected gap: the pain text + its expected severity band."""

    gap: str = Field(min_length=1)
    severity_range: tuple[int, int]


class SeedIdea(BaseModel):
    """A hand-labelled seed idea (§4 seed-set authoring).

    `category` is the seed-set bucket (consumer-app, mobile-game, …), not the
    LLM-derived pre-flight category — it is operator metadata for the report.
    """

    idea: str = Field(min_length=1)
    target_gap: Optional[str] = None
    category: str = Field(min_length=1)
    expected_gaps: list[ExpectedGap] = Field(default_factory=list)


def load_seed(name: str) -> SeedIdea:
    path = SEED_DIR / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in SEED_DIR.glob("*.json"))
        raise FileNotFoundError(
            f"No seed file {path.name!r} in {SEED_DIR}. Available: {available}"
        )
    return SeedIdea.model_validate_json(path.read_text())


# --- pipeline capture -------------------------------------------------------


def _gap_item_from_row(row: dict) -> GapItem:
    """Rebuild a `GapItem` from the persisted gap-row shape the pipeline emits.

    Inverse of `run_pipeline_service._gap_rows` — the harness captures the rows
    the pipeline would have written and reconstructs the domain objects so the
    scorers see exactly what production would have stored.
    """
    return GapItem(
        gap_id=row["gap_id"],
        gap=row["gap"],
        severity=row["severity"],
        frequency=row["frequency"],
        spread=row["spread"],
        competitors_present=row.get("competitors_present_json") or [],
        evidence_quote_ids=row.get("evidence_quote_ids_json") or [],
    )


class _Capture:
    """Intercepts the pipeline's terminal Supabase writes (see module docstring)."""

    def __init__(self) -> None:
        self.gap_rows: list[dict] = []
        self.done: Optional[dict] = None
        self.failure_reason: Optional[str] = None

    def insert_gaps(self, gap_rows: list[dict]) -> list[dict]:
        self.gap_rows = gap_rows
        return gap_rows

    def update_idea_run_done(self, run_id, quotes, coverage, idea_match,
                             partial_sources=None, quality_signals=None) -> dict:
        self.done = {
            "quotes": quotes,
            "coverage": coverage,
            "idea_match": idea_match,
            "partial_sources": partial_sources,
            "quality_signals": quality_signals,
        }
        return {"id": run_id}

    def update_idea_run_failed(self, run_id, failure_reason) -> dict:
        self.failure_reason = failure_reason
        return {"id": run_id, "failure_reason": failure_reason}


async def _drive_pipeline(seed: SeedIdea) -> tuple[Optional[RunResult], Optional[str]]:
    """Run pre-flight + the background pipeline, capturing the result in-process.

    Returns `(RunResult, None)` on a `done` run, `(None, failure_reason)` when the
    pipeline failed or pre-flight found no candidates to run.
    """
    # Imported lazily: these modules import the Supabase client at module load,
    # which the pure metrics path (and its unit tests) must never require.
    from app.services import preflight_service, run_pipeline_service

    run_id = uuid4().hex
    logger.info("eval_preflight idea=%r", seed.idea)
    preflight = preflight_service.run(seed.idea)

    if not preflight.candidates:
        logger.warning("eval_no_candidates idea=%r — skipping pipeline", seed.idea)
        return None, "no_candidates"

    capture = _Capture()
    # Intercept only the terminal writes; pre-flight, ingestion, extraction, and
    # synthesis all run for real through the same services production uses.
    with patch.object(run_pipeline_service, "insert_gaps", capture.insert_gaps), \
            patch.object(run_pipeline_service, "update_idea_run_done", capture.update_idea_run_done), \
            patch.object(run_pipeline_service, "update_idea_run_failed", capture.update_idea_run_failed):
        await run_pipeline_service.run_pipeline(
            run_id=run_id,
            idea=seed.idea,
            target_gap=seed.target_gap,
            category=preflight.category,
            competitors=preflight.candidates,
        )

    if capture.done is None:
        return None, capture.failure_reason or "internal_error"

    done = capture.done
    result = RunResult(
        run_id=run_id,
        idea=seed.idea,
        target_gap=seed.target_gap,
        created_at=datetime.now(timezone.utc),
        category=preflight.category,
        signal_strength=preflight.signal_strength,
        signal_reasoning=preflight.signal_reasoning,
        competitors=preflight.candidates,
        gaps=[_gap_item_from_row(r) for r in capture.gap_rows],
        quotes=done["quotes"],
        coverage=Coverage.model_validate(done["coverage"]),
        idea_match=done["idea_match"],
        partial_sources=done["partial_sources"],
        quality_signals=(
            QualitySignals.model_validate(done["quality_signals"])
            if done["quality_signals"] is not None
            else None
        ),
    )
    return result, None


# --- scoring + report -------------------------------------------------------


def score(seed: SeedIdea, result: RunResult) -> dict:
    """Score one `RunResult` against the seed labels → the §4 report dict."""
    expected_texts = [g.gap for g in seed.expected_gaps]
    recall = metrics.gap_recall(expected_texts, [g.gap for g in result.gaps])
    quote_pool_ids = set(result.quotes.keys())
    severity_distribution = (
        result.quality_signals.severity_distribution
        if result.quality_signals is not None
        else [0, 0, 0, 0, 0]
    )

    return {
        "idea": seed.idea,
        "category": seed.category,
        "expected_gaps": [g.model_dump() for g in seed.expected_gaps],
        "output_gaps": [
            {
                "gap_id": g.gap_id,
                "gap": g.gap,
                "severity": g.severity,
                "frequency": g.frequency,
                "spread": g.spread,
            }
            for g in result.gaps
        ],
        "gap_recall": {
            "hit": recall.hit,
            "miss": recall.miss,
            "per_gap": [vars(p) for p in recall.per_gap],
        },
        "hallucination_count": metrics.hallucination_count(result.gaps, quote_pool_ids),
        "citation_ratio": metrics.citation_ratio(result.coverage),
        "severity_flag": metrics.severity_flag(severity_distribution),
        "quality_signals": (
            result.quality_signals.model_dump()
            if result.quality_signals is not None
            else None
        ),
    }


def _failure_report(seed: SeedIdea, reason: str) -> dict:
    """Report shape for a run that never reached `done` (no scorable output)."""
    return {
        "idea": seed.idea,
        "category": seed.category,
        "expected_gaps": [g.model_dump() for g in seed.expected_gaps],
        "output_gaps": [],
        "gap_recall": {"hit": 0, "miss": len(seed.expected_gaps), "per_gap": []},
        "hallucination_count": 0,
        "citation_ratio": 0.0,
        "severity_flag": None,
        "quality_signals": None,
        "failure_reason": reason,
    }


def write_report(name: str, report: dict) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{name}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    return path


async def run_seed(name: str) -> dict:
    seed = load_seed(name)
    result, failure_reason = await _drive_pipeline(seed)
    if result is None:
        logger.warning("eval_run_unscored name=%s reason=%s", name, failure_reason)
        return _failure_report(seed, failure_reason or "internal_error")
    return score(seed, result)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    parser = argparse.ArgumentParser(
        prog="python -m app.eval.harness",
        description="Drive the real pipeline on a seed idea and write a scored JSON report.",
    )
    parser.add_argument(
        "seed",
        help="Seed file stem under app/eval/seed/ (e.g. 'consumer_app').",
    )
    args = parser.parse_args(argv)

    report = asyncio.run(run_seed(args.seed))
    path = write_report(args.seed, report)

    recall = report["gap_recall"]
    print(f"\nReport written → {path}")
    print(
        f"  gap_recall: {recall['hit']} hit / {recall['miss']} miss"
        f"  hallucinations: {report['hallucination_count']}"
        f"  citation_ratio: {report['citation_ratio']}"
        f"  severity_flag: {report['severity_flag']}"
    )
    if "failure_reason" in report:
        print(f"  run did not complete: {report['failure_reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
