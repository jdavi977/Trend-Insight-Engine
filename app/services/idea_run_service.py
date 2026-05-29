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
    insert_idea_run,
    list_done_idea_runs,
    update_idea_run_preflight,
)
from app.schemas.runs import (
    RunCreate,
    RunCreateResponse,
    RunFeedItem,
    RunStateResponse,
)
from app.services import preflight_service

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
    return _row_to_state(row)


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
        coverage=row.get("coverage_json"),
        idea_match=row.get("idea_match_json"),
        failure_reason=row.get("failure_reason"),
    )
