"""Behavior tests for `app.clients.supabase`.

The v1 `automatic_table*` accessors were removed with the weekly pipeline in
slice 3 (issue #72); only the v2 `idea_runs`/`gaps`/`feedback_events` surface
remains. The accessor behavior is exercised through the service tests; this
file pins client-level contracts that services rely on.
"""
from __future__ import annotations


def test_insert_feedback_event_appends_to_feedback_events(mocker):
    """Append-only contract (spec §7, PRD §9): inserts a row, never upserts."""
    from app.clients import supabase as sb

    table = mocker.Mock()
    table.insert.return_value.execute.return_value = mocker.Mock(data=[{"id": "fe1"}])
    client = mocker.Mock()
    client.table.return_value = table
    mocker.patch.object(sb, "supabase_client", client)

    row = sb.insert_feedback_event(
        run_id="r1",
        new_to_me_gap_ids=["g1", "g2"],
        direction="continue",
        time_saved_estimate_minutes=30,
    )

    assert row == {"id": "fe1"}
    client.table.assert_called_once_with("feedback_events")
    table.insert.assert_called_once_with({
        "run_id": "r1",
        "new_to_me_gap_ids_json": ["g1", "g2"],
        "direction": "continue",
        "time_saved_estimate_minutes": 30,
    })
    # Append-only: no update/upsert/delete on the append path.
    table.update.assert_not_called()
    table.upsert.assert_not_called()
    table.delete.assert_not_called()
