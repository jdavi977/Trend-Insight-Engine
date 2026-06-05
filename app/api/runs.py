"""Idea-run HTTP surface — spec §6 (v2 slice 1).

POST /runs, GET /runs/:id, GET /runs, and POST /runs/:id/approve. The approve
endpoint kicks off the background pipeline via FastAPI `BackgroundTasks`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, status

from app.schemas.runs import (
    RunApprove,
    RunCreate,
    RunCreateResponse,
    RunFeedback,
    RunFeedItem,
    RunReport,
    RunStateResponse,
)
from app.services import idea_run_service, rate_limit_service, run_pipeline_service

router = APIRouter(prefix="/runs")


@router.post("", response_model=RunCreateResponse)
def create_run(request: RunCreate, http_request: Request) -> RunCreateResponse:
    # Abuse/cost guards run before any work (spec §6, issue #59): concurrency →
    # rate limit → budget. `check_can_create_run` raises 429 on rejection;
    # `record_run` counts the accepted run against this IP only once it's created
    # (so a budget rejection doesn't burn a rate-limit slot).
    ip = rate_limit_service.client_ip(http_request)
    rate_limit_service.check_can_create_run(ip)
    response = idea_run_service.create_run(request)
    rate_limit_service.record_run(ip)
    return response


@router.get("", response_model=list[RunFeedItem])
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    before: Optional[datetime] = Query(default=None),
) -> list[RunFeedItem]:
    return idea_run_service.list_done_runs(limit=limit, before=before)


@router.get("/{run_id}", response_model=RunStateResponse)
def get_run(run_id: str) -> RunStateResponse:
    run = idea_run_service.get_run(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    return run


@router.post("/{run_id}/approve")
def approve_run(
    run_id: str,
    request: RunApprove,
    background_tasks: BackgroundTasks,
) -> dict:
    return run_pipeline_service.approve(run_id, request, background_tasks)


@router.post("/{run_id}/feedback")
def submit_feedback(run_id: str, request: RunFeedback) -> dict:
    # Append-only (PRD §9). The service gates on the run being `done` (409) and
    # validates gap ids (400); `direction` / minutes are bounded by RunFeedback.
    idea_run_service.submit_feedback(run_id, request)
    return {"ok": True}


@router.post("/{run_id}/report")
def report_run(run_id: str, request: RunReport, http_request: Request) -> dict:
    # No auth in v1 (PRD §5) — the only griefing guard is the shared per-IP run
    # budget (issue #59). Rate-check before the write, then count it on success
    # so an accepted report consumes the same 3/hr, 10/day window as POST /runs.
    ip = rate_limit_service.client_ip(http_request)
    rate_limit_service.check_can_report(ip)
    idea_run_service.report_run(run_id, request)
    rate_limit_service.record_run(ip)
    return {"ok": True}
