"""Orchestrates the idea-run lifecycle for the `/runs` HTTP surface.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §6.
Layer rule (PRD §10): router → idea_run_service → pipeline stages. The router
must not import preflight/synthesis/persistence directly.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.clients.supabase import (
    get_idea_run,
    insert_feedback_event,
    insert_idea_run,
    list_done_idea_runs,
    list_gaps_for_run,
    update_idea_run_failed_if_running,
    update_idea_run_preflight,
)
from app.schemas.runs import (
    FailureReason,
    RunCreate,
    RunCreateResponse,
    RunFeedback,
    RunFeedItem,
    RunStateResponse,
)
from app.services import preflight_service, run_pipeline_service

logger = logging.getLogger(__name__)


def create_run(request: RunCreate) -> RunCreateResponse:
    row = insert_idea_run(request.idea, request.target_gap)
    run_id = row["id"]

    preflight = preflight_service.run(request.idea)

    update_idea_run_preflight(
        run_id=run_id,
        category=preflight.category,
        signal_strength=preflight.signal_strength,
        signal_reasoning=preflight.signal_reasoning,
        candidates=[c.model_dump() for c in preflight.candidates],
    )

    logger.info(
        "run_created run_id=%s signal=%s candidates=%d",
        run_id, preflight.signal_strength, len(preflight.candidates),
    )

    return RunCreateResponse(
        run_id=run_id,
        status="preflight_ready",
        preflight=preflight,
    )


def get_run(run_id: str) -> Optional[RunStateResponse]:
    row = get_idea_run(run_id)
    if row is None:
        return None
    row = _reconcile_orphaned_running(row)
    return _row_to_state(row)


def _reconcile_orphaned_running(row: dict) -> dict:
    """Read-time restart reconciliation (spec §5.2, US-S4).

    `_jobs` is in-memory and lost on restart, so a row the DB still calls
    `running` with no live pipeline here was orphaned by a server restart.
    Transition it to `failed` + `failure_reason: server_restart` before
    returning. The write is conditional on `status='running'` (the supabase
    guard), so a genuinely-live run on another code path is never clobbered;
    if that guard finds no row we keep the row we already read.
    """
    if row["status"] != "running":
        return row
    if run_pipeline_service.is_pipeline_live(row["id"]):
        return row

    updated = update_idea_run_failed_if_running(
        row["id"], FailureReason.server_restart.value
    )
    if updated is None:
        return row
    logger.warning(
        "run_reconciled_server_restart run_id=%s (orphaned running row)", row["id"]
    )
    return updated


def submit_feedback(run_id: str, feedback: RunFeedback) -> dict:
    """Append a feedback row for a run (spec §7, PRD §9).

    APPEND-ONLY: each submission inserts a new `feedback_events` row — never an
    upsert. Endpoint-level gating (run must be `done`, gap ids must exist) lands
    with POST /runs/:id/feedback in a later slice-2 PR; this is the write path
    the foundation slice exposes.
    """
    row = insert_feedback_event(
        run_id=run_id,
        new_to_me_gap_ids=feedback.new_to_me_gap_ids,
        direction=feedback.direction,
        time_saved_estimate_minutes=feedback.time_saved_estimate_minutes,
    )
    logger.info("feedback_recorded run_id=%s direction=%s", run_id, feedback.direction)
    return row


def list_done_runs(limit: int, before: Optional[datetime]) -> list[RunFeedItem]:
    rows = list_done_idea_runs(limit=limit, before=before)
    return [
        RunFeedItem(
            run_id=r["id"],
            idea=r["idea"],
            completed_at=r["updated_at"],
        )
        for r in rows
    ]


def _row_to_state(row: dict) -> RunStateResponse:
    # Gaps live in their own table; only fetch them for the terminal `done` view
    # (spec §6 — GET /runs/:id returns the full result once complete).
    gaps = _gaps_for(row) if row["status"] == "done" else []
    return RunStateResponse(
        run_id=row["id"],
        idea=row["idea"],
        target_gap=row.get("target_gap"),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        category=row.get("category"),
        signal_strength=row.get("signal_strength"),
        signal_reasoning=row.get("signal_reasoning"),
        competitors=row.get("competitors_json") or [],
        quotes=row.get("quotes_json") or {},
        gaps=gaps,
        coverage=row.get("coverage_json"),
        idea_match=row.get("idea_match_json"),
        partial_sources=row.get("partial_sources_json"),
        failure_reason=row.get("failure_reason"),
    )


def _gaps_for(row: dict) -> list[dict]:
    """Map persisted `gaps` rows to the GapItem-shaped dicts the schema expects."""
    return [
        {
            "gap_id": g["gap_id"],
            "gap": g["gap"],
            "severity": g["severity"],
            "frequency": g["frequency"],
            "spread": g["spread"],
            "competitors_present": g.get("competitors_present_json") or [],
            "evidence_quote_ids": g.get("evidence_quote_ids_json") or [],
        }
        for g in list_gaps_for_run(row["id"])
    ]
