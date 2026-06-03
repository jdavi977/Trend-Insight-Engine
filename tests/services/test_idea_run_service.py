"""Tests for app/services/idea_run_service.py.

Slice-2 foundation (issue #57): the append-only `feedback_events` write path.
Endpoint-level gating (done-only, gap existence) lands in a later slice-2 PR.
"""
from __future__ import annotations

from app.schemas.runs import RunFeedback
from app.services import idea_run_service


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
