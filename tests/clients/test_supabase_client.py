"""Behavior tests for `app.clients.supabase`.

PR 5 merges `app/lib/db.py` + `app/lib/supabaseClient.py` into a single
`app/clients/supabase.py`. These tests pin the public surface (the four DB
helpers) so the move is safe.
"""
from __future__ import annotations

import pytest


def test_check_youtube_id_returns_rows_when_present(mocker):
    from app.clients import supabase as sb

    fake_response = mocker.Mock(data=[{"key": "abc", "title": "x"}])
    table = mocker.Mock()
    table.select.return_value.eq.return_value.execute.return_value = fake_response
    mocker.patch.object(sb, "supabase_client", mocker.Mock(table=mocker.Mock(return_value=table)))

    assert sb.check_youtube_id("abc") == [{"key": "abc", "title": "x"}]


def test_check_youtube_id_returns_empty_list_when_absent(mocker):
    from app.clients import supabase as sb

    fake_response = mocker.Mock(data=[])
    table = mocker.Mock()
    table.select.return_value.eq.return_value.execute.return_value = fake_response
    mocker.patch.object(sb, "supabase_client", mocker.Mock(table=mocker.Mock(return_value=table)))

    assert sb.check_youtube_id("missing") == []


def test_update_automatic_trend_inserts_into_automatic_table(mocker):
    from app.clients import supabase as sb

    table = mocker.Mock()
    client = mocker.Mock()
    client.table.return_value = table
    mocker.patch.object(sb, "supabase_client", client)

    payload = [{"key": "abc"}]
    sb.update_automatic_trend(payload)

    client.table.assert_called_once_with("automatic_table")
    table.insert.assert_called_once_with(payload)
    table.insert.return_value.execute.assert_called_once_with()


def test_get_weekly_ids_filters_by_sunday_date_and_category(mocker):
    from app.clients import supabase as sb

    mocker.patch.object(sb, "getSundayDate", return_value="2026-04-26")
    fake_response = mocker.Mock(data=[{"key": "x"}])
    select = mocker.Mock()
    select.eq.return_value.eq.return_value.execute.return_value = fake_response
    table = mocker.Mock()
    table.select.return_value = select
    client = mocker.Mock()
    client.table.return_value = table
    mocker.patch.object(sb, "supabase_client", client)

    result = sb.get_weekly_ids(20)

    assert result == [{"key": "x"}]
    select.eq.assert_called_once_with("date", "2026-04-26")
    select.eq.return_value.eq.assert_called_once_with("category", 20)
