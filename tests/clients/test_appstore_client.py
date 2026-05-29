"""Behavior tests for `app.clients.appstore`.

Wraps the iTunes RSS GET so ingestion no longer talks to `requests` directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from tests.conftest import load_fixture


def test_itunes_search_normalizes_recorded_fixture(mocker):
    """v2 spec §7: itunes_search returns app candidates from the iTunes Search API."""
    from app.clients import appstore

    mocker.patch.object(appstore.time, "sleep")  # don't sleep in tests
    response = MagicMock(status_code=200)
    response.json.return_value = load_fixture("itunes_search_notes.json")
    get = mocker.patch.object(appstore.requests, "get", return_value=response)

    result = appstore.itunes_search("note taking app", limit=5)

    assert get.call_args.args[0] == "https://itunes.apple.com/search"
    assert get.call_args.kwargs["params"] == {
        "term": "note taking app",
        "entity": "software",
        "limit": 5,
        "country": "us",
    }
    assert get.call_args.kwargs["timeout"] == 10

    assert [a["bundle_id"] for a in result] == [
        "md.obsidian.Obsidian",
        "com.bear-writer",
        "com.standardnotes.standardnotes",
    ]
    assert result[0] == {
        "bundle_id": "md.obsidian.Obsidian",
        "name": "Obsidian",
        "genre": "Productivity",
        "description": (
            "Obsidian is a private and flexible note-taking app that adapts to "
            "the way you think. Build a personal knowledge base with markdown "
            "files stored locally on your device. Includes graph view, "
            "backlinks, and a plugin ecosystem."
        ),
        "rating_count": 4321,
        "url": "https://apps.apple.com/us/app/obsidian/id1557175442",
    }
    # null description coerced to empty string, not propagated as None
    assert result[2]["description"] == ""


def test_itunes_search_truncates_long_descriptions(mocker):
    from app.clients import appstore

    mocker.patch.object(appstore.time, "sleep")
    long_desc = "x" * 1000
    response = MagicMock(status_code=200)
    response.json.return_value = {
        "results": [{
            "bundleId": "id",
            "trackName": "name",
            "primaryGenreName": "g",
            "description": long_desc,
            "userRatingCount": 1,
            "trackViewUrl": "u",
        }]
    }
    mocker.patch.object(appstore.requests, "get", return_value=response)

    result = appstore.itunes_search("q")

    assert len(result[0]["description"]) == 300


def test_itunes_search_returns_empty_when_no_results(mocker):
    from app.clients import appstore

    mocker.patch.object(appstore.time, "sleep")
    response = MagicMock(status_code=200)
    response.json.return_value = {"resultCount": 0}
    mocker.patch.object(appstore.requests, "get", return_value=response)

    assert appstore.itunes_search("nonsense query xyz") == []


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
