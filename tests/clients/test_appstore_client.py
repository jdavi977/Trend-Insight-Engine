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

    result = appstore._fetch_reviews_page("999", "mostHelpful", page=2)

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

    result = appstore._fetch_reviews_page("1", "mostRecent", page=1)

    assert result == {"feed": {}}
    assert "Stopped at page: 1, status: 500" in capsys.readouterr().out


def _vendor_review_entry(rating, title, content, votes):
    return {
        "im:rating": {"label": rating},
        "title": {"label": title},
        "content": {"label": content},
        "im:voteCount": {"label": votes},
    }


def test_list_reviews_maps_vendor_entries_to_domain_rows(mocker):
    from app.clients import appstore

    payload = {
        "feed": {
            "entry": [
                _vendor_review_entry("5", "Great", "Love it", "10"),
                _vendor_review_entry("1", "Bad", "Hate it", "2"),
            ]
        }
    }
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    mocker.patch.object(appstore.requests, "get", return_value=response)

    result = appstore.list_reviews("123", "mostRecent", page=1)

    assert result == [
        {"rating": "5", "title": "Great", "content": "Love it", "vote_count": "10"},
        {"rating": "1", "title": "Bad", "content": "Hate it", "vote_count": "2"},
    ]


def test_list_reviews_returns_empty_when_at_most_one_entry(mocker):
    from app.clients import appstore

    for payload in (
        {"feed": {"entry": [_vendor_review_entry("5", "t", "c", "0")]}},
        {"feed": {"entry": []}},
    ):
        response = MagicMock(status_code=200)
        response.json.return_value = payload
        mocker.patch.object(appstore.requests, "get", return_value=response)
        assert appstore.list_reviews("123", "mostRecent", page=1) == []


def test_list_reviews_returns_empty_when_feed_empty_or_missing(mocker):
    from app.clients import appstore

    for payload in ({}, {"feed": {}}, {"feed": None}):
        response = MagicMock(status_code=200)
        response.json.return_value = payload
        mocker.patch.object(appstore.requests, "get", return_value=response)
        assert appstore.list_reviews("123", "mostRecent", page=1) == []


def test_list_reviews_normalizes_single_dict_entry_to_list_then_sentinel(mocker):
    from app.clients import appstore

    payload = {"feed": {"entry": _vendor_review_entry("5", "solo", "c", "1")}}
    response = MagicMock(status_code=200)
    response.json.return_value = payload
    mocker.patch.object(appstore.requests, "get", return_value=response)

    assert appstore.list_reviews("123", "mostRecent", page=1) == []
