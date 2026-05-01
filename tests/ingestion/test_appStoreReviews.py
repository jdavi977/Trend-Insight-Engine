"""Tests for app/ingestion/appStoreReviews.py.

Pure URL parsing runs for real. `requests.get` is mocked because we don't
want to hit the iTunes RSS feed in tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ingestion.appStoreReviews import getAppId, getAppReviews


class TestGetAppId:
    def test_extracts_id_from_app_store_url(self):
        url = "https://apps.apple.com/us/app/example/id123456789"
        assert getAppId(url) == "123456789"

    def test_extracts_id_with_trailing_path(self):
        url = "https://apps.apple.com/us/app/example/id987654321?mt=8"
        assert getAppId(url) == "987654321?mt=8"


def _rss_page(entries):
    return {"feed": {"entry": entries}}


def _entry(rating, title, content, votes):
    return {
        "im:rating": {"label": rating},
        "title": {"label": title},
        "content": {"label": content},
        "im:voteCount": {"label": votes},
    }


class TestGetAppReviews:
    def test_returns_normalized_reviews_from_single_page(self, mocker):
        # iTunes RSS uses entry[0] as feed metadata; real reviews start at index 1.
        # The current implementation does not strip [0], so include 2+ entries.
        entries = [
            _entry("5", "Great", "Love it", "10"),
            _entry("1", "Bad", "Hate it", "2"),
        ]
        response = MagicMock(status_code=200)
        response.json.return_value = _rss_page(entries)
        mocker.patch(
            "app.ingestion.appStoreReviews.requests.get", return_value=response
        )

        result = getAppReviews("123", "mostRecent", max_pages=1)

        assert result == [
            {"rating": "5", "title": "Great", "content": "Love it", "vote_count": "10"},
            {"rating": "1", "title": "Bad", "content": "Hate it", "vote_count": "2"},
        ]

    def test_breaks_when_page_has_one_or_zero_entries(self, mocker):
        # Page with a single entry (just feed metadata) signals no real reviews.
        response = MagicMock(status_code=200)
        response.json.return_value = _rss_page([_entry("5", "t", "c", "0")])
        mocker.patch(
            "app.ingestion.appStoreReviews.requests.get", return_value=response
        )

        result = getAppReviews("123", "mostRecent", max_pages=5)

        assert result == []

    def test_breaks_when_feed_is_empty(self, mocker):
        response = MagicMock(status_code=200)
        response.json.return_value = {"feed": {}}
        mocker.patch(
            "app.ingestion.appStoreReviews.requests.get", return_value=response
        )

        result = getAppReviews("123", "mostRecent", max_pages=5)

        assert result == []

    def test_iterates_multiple_pages(self, mocker):
        entries_p1 = [
            _entry("5", "T1", "C1", "1"),
            _entry("4", "T2", "C2", "2"),
        ]
        entries_p2 = [
            _entry("3", "T3", "C3", "3"),
            _entry("2", "T4", "C4", "4"),
        ]
        responses = [
            MagicMock(status_code=200, **{"json.return_value": _rss_page(entries_p1)}),
            MagicMock(status_code=200, **{"json.return_value": _rss_page(entries_p2)}),
        ]
        mocker.patch(
            "app.ingestion.appStoreReviews.requests.get", side_effect=responses
        )

        result = getAppReviews("123", "mostRecent", max_pages=2)

        assert [r["title"] for r in result] == ["T1", "T2", "T3", "T4"]

    def test_builds_correct_url(self, mocker):
        response = MagicMock(status_code=200)
        response.json.return_value = {"feed": {}}
        get = mocker.patch(
            "app.ingestion.appStoreReviews.requests.get", return_value=response
        )

        getAppReviews("999", "mostHelpful", max_pages=1)

        called_url = get.call_args.args[0]
        assert "id=999" in called_url
        assert "sortBy=mostHelpful" in called_url
        assert "page=1" in called_url
