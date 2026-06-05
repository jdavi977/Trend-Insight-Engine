"""Tests for app/services/idea_run_service.py.

Slice-2 foundation (issue #57): the append-only `feedback_events` write path.
Endpoint-level gating (done-only, gap existence) lands in a later slice-2 PR.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.runs import RunFeedback
from app.services import idea_run_service, run_pipeline_service


def _running_row(run_id: str = "r1") -> dict:
    now = datetime(2026, 6, 5, tzinfo=timezone.utc)
    return {
        "id": run_id,
        "idea": "an idea",
        "target_gap": None,
        "status": "running",
        "created_at": now,
        "updated_at": now,
    }


def test_submit_feedback_inserts_feedback_event(mocker):
    insert = mocker.patch.object(
        idea_run_service, "insert_feedback_event", return_value={"id": "fe1"}
    )

    row = idea_run_service.submit_feedback(
        "r1",
        RunFeedback(
            new_to_me_gap_ids=["g1"],
            direction="shift",
            time_saved_estimate_minutes=15,
        ),
    )

    assert row == {"id": "fe1"}
    insert.assert_called_once_with(
        run_id="r1",
        new_to_me_gap_ids=["g1"],
        direction="shift",
        time_saved_estimate_minutes=15,
    )


def test_submit_feedback_appends_never_upserts(mocker):
    """Two submissions for the same run insert two rows (append-only, PRD §9)."""
    insert = mocker.patch.object(
        idea_run_service, "insert_feedback_event", return_value={"id": "fe"}
    )

    idea_run_service.submit_feedback("r1", RunFeedback(direction="continue"))
    idea_run_service.submit_feedback("r1", RunFeedback(direction="drop"))

    assert insert.call_count == 2
    assert insert.call_args_list[0].kwargs["direction"] == "continue"
    assert insert.call_args_list[1].kwargs["direction"] == "drop"


def test_submit_feedback_passes_through_empty_feedback(mocker):
    insert = mocker.patch.object(
        idea_run_service, "insert_feedback_event", return_value={"id": "fe"}
    )

    idea_run_service.submit_feedback("r1", RunFeedback())

    insert.assert_called_once_with(
        run_id="r1",
        new_to_me_gap_ids=None,
        direction=None,
        time_saved_estimate_minutes=None,
    )


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
    done_row = {**_running_row(), "status": "done"}
    mocker.patch.object(idea_run_service, "get_idea_run", return_value=done_row)
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
