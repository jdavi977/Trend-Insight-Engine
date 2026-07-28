"""Tests for app/services/idea_run_service.py.

Slice-3 (issue #68): pre-flight robustness on `create_run`.
Slice-2 (issue #61): read-time restart reconciliation of orphaned `running` rows.
The feedback + report write paths this file also covered left with that surface
in the scope-down (issue #89).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from pydantic import ValidationError

from app.schemas.runs import RunCreate
from app.services import idea_run_service, preflight_service, run_pipeline_service


def _running_row(run_id: str = "r1") -> dict:
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    return {
        "id": run_id,
        "idea": "an idea",
        "status": "running",
        "created_at": now,
        "updated_at": now,
    }


def _done_row(run_id: str = "r1") -> dict:
    return {**_running_row(run_id), "status": "done"}


# --- create_run pre-flight robustness (slice 3 §7.2, issue #68) -------------


def test_create_run_marks_failed_when_preflight_raises(mocker):
    """A pre-flight exception transitions the row off `pending` → failed +
    internal_error and surfaces a clean 500 (no row stranded at `pending`)."""
    mocker.patch.object(
        idea_run_service, "insert_idea_run", return_value={"id": "r1"}
    )
    mocker.patch.object(
        preflight_service, "run", side_effect=RuntimeError("openai down")
    )
    failed = mocker.patch.object(idea_run_service, "update_idea_run_failed")
    preflight_update = mocker.patch.object(
        idea_run_service, "update_idea_run_preflight"
    )

    with pytest.raises(HTTPException) as exc:
        idea_run_service.create_run(RunCreate(idea="an idea"))

    assert exc.value.status_code == 500
    assert exc.value.detail == "internal_error"
    failed.assert_called_once_with("r1", "internal_error")
    preflight_update.assert_not_called()


def test_create_run_marks_failed_on_malformed_preflight_payload(mocker):
    """A malformed generate_queries grade surfaces as a ValidationError out of
    preflight_service.run; create_run maps it to the same internal_error (§7.1)."""
    mocker.patch.object(
        idea_run_service, "insert_idea_run", return_value={"id": "r2"}
    )
    validation_error = ValidationError.from_exception_data("GenerateQueriesResult", [])
    mocker.patch.object(
        preflight_service, "run", side_effect=validation_error
    )
    failed = mocker.patch.object(idea_run_service, "update_idea_run_failed")

    with pytest.raises(HTTPException) as exc:
        idea_run_service.create_run(RunCreate(idea="an idea"))

    assert exc.value.status_code == 500
    assert exc.value.detail == "internal_error"
    failed.assert_called_once_with("r2", "internal_error")


# --- restart reconciliation (US-S4, spec §5.2) ------------------------------


def test_get_run_reconciles_orphaned_running_to_failed(mocker):
    """A `running` row with no live `_jobs` entry → failed + server_restart."""
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=_running_row())
    mocker.patch.object(run_pipeline_service, "is_pipeline_live", return_value=False)
    failed_row = {**_running_row(), "status": "failed", "failure_reason": "server_restart"}
    reconcile = mocker.patch.object(
        idea_run_service, "update_idea_run_failed_if_running", return_value=failed_row
    )

    state = idea_run_service.get_run("r1")

    reconcile.assert_called_once_with("r1", "server_restart")
    assert state.status == "failed"
    assert state.failure_reason == "server_restart"


def test_get_run_does_not_reconcile_live_running_run(mocker):
    """A `running` row WITH a live pipeline entry is never reconciled/clobbered."""
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=_running_row())
    mocker.patch.object(run_pipeline_service, "is_pipeline_live", return_value=True)
    reconcile = mocker.patch.object(
        idea_run_service, "update_idea_run_failed_if_running"
    )

    state = idea_run_service.get_run("r1")

    reconcile.assert_not_called()
    assert state.status == "running"


def test_get_run_keeps_row_when_conditional_write_loses_race(mocker):
    """If the guard finds no `running` row (lost a race), keep what we read."""
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=_running_row())
    mocker.patch.object(run_pipeline_service, "is_pipeline_live", return_value=False)
    # Conditional write returns None: another path already moved the row.
    mocker.patch.object(
        idea_run_service, "update_idea_run_failed_if_running", return_value=None
    )

    state = idea_run_service.get_run("r1")

    assert state.status == "running"


def test_get_run_does_not_reconcile_non_running_status(mocker):
    """Only `running` rows are reconciled — a `done` row is returned untouched."""
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=_done_row())
    mocker.patch.object(idea_run_service, "list_gaps_for_run", return_value=[])
    is_live = mocker.patch.object(run_pipeline_service, "is_pipeline_live")
    reconcile = mocker.patch.object(
        idea_run_service, "update_idea_run_failed_if_running"
    )

    state = idea_run_service.get_run("r1")

    is_live.assert_not_called()
    reconcile.assert_not_called()
    assert state.status == "done"


def test_get_run_integration_orphaned_running_via_real_jobs_registry(mocker):
    """End-to-end through the real `_jobs` registry: an orphaned `running` row
    (no entry in `_jobs`, as after a restart) reconciles to failed on next read."""
    run_pipeline_service._jobs.clear()  # simulate a fresh process after restart
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=_running_row())
    reconcile = mocker.patch.object(
        idea_run_service,
        "update_idea_run_failed_if_running",
        return_value={**_running_row(), "status": "failed", "failure_reason": "server_restart"},
    )

    state = idea_run_service.get_run("r1")

    reconcile.assert_called_once_with("r1", "server_restart")
    assert state.status == "failed"
    assert state.failure_reason == "server_restart"


def test_get_run_integration_live_job_in_registry_not_reconciled(mocker):
    """A present, running `_jobs` entry blocks reconciliation (no clobber)."""
    run_pipeline_service._jobs.clear()
    run_pipeline_service._jobs["r1"] = {"status": "running", "stage": "synthesis"}
    try:
        mocker.patch.object(
            idea_run_service, "get_idea_run", return_value=_running_row()
        )
        reconcile = mocker.patch.object(
            idea_run_service, "update_idea_run_failed_if_running"
        )

        state = idea_run_service.get_run("r1")

        reconcile.assert_not_called()
        assert state.status == "running"
    finally:
        run_pipeline_service._jobs.clear()
