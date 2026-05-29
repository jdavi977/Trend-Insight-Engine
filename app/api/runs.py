"""Idea-run HTTP surface — spec §6 (v2 slice 1).

POST /runs, GET /runs/:id, GET /runs land in this PR. POST /runs/:id/approve
returns 501 until the background-pipeline issue lands.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.runs import (
    RunCreate,
    RunCreateResponse,
    RunFeedItem,
    RunStateResponse,
)
from app.services import idea_run_service

router = APIRouter(prefix="/runs")


@router.post("", response_model=RunCreateResponse)
def create_run(request: RunCreate) -> RunCreateResponse:
    return idea_run_service.create_run(request)


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
def approve_run(run_id: str):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Background pipeline wired in next issue (v2 slice 1 PR 8).",
    )
