"""Behavior tests for `app.clients.appstore`.

Wraps the iTunes RSS GET so ingestion no longer talks to `requests` directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock


def test_fetch_reviews_page_builds_url_and_returns_json(mocker):
    from app.clients import appstore

    response = MagicMock(status_code=200)
    response.json.return_value = {"feed": {"entry": []}}
    get = mocker.patch.object(appstore.requests, "get", return_value=response)

    result = appstore.fetch_reviews_page("999", "mostHelpful", page=2)

    assert result == {"feed": {"entry": []}}
    called_url = get.call_args.args[0]
    assert "id=999" in called_url
    assert "sortBy=mostHelpful" in called_url
    assert "page=2" in called_url
    assert get.call_args.kwargs["timeout"] == 10


def test_fetch_reviews_page_still_returns_json_on_non_200(mocker, capsys):
    from app.clients import appstore

    response = MagicMock(status_code=500)
    response.json.return_value = {"feed": {}}
    mocker.patch.object(appstore.requests, "get", return_value=response)

    result = appstore.fetch_reviews_page("1", "mostRecent", page=1)

    assert result == {"feed": {}}
    assert "Stopped at page: 1, status: 500" in capsys.readouterr().out
