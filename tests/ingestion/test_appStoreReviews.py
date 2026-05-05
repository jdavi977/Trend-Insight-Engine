"""Tests for app/ingestion/appStoreReviews.py.

Pure URL parsing runs for real. The iTunes RSS client is mocked because we
don't want to hit the live feed in tests.
"""
from __future__ import annotations

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
        entries = [
            _entry("5", "Great", "Love it", "10"),
            _entry("1", "Bad", "Hate it", "2"),
        ]
        mocker.patch(
            "app.ingestion.appStoreReviews.fetch_reviews_page",
            return_value=_rss_page(entries),
        )

        result = getAppReviews("123", "mostRecent", max_pages=1)

        assert result == [
            {"rating": "5", "title": "Great", "content": "Love it", "vote_count": "10"},
            {"rating": "1", "title": "Bad", "content": "Hate it", "vote_count": "2"},
        ]

    def test_breaks_when_page_has_one_or_zero_entries(self, mocker):
        mocker.patch(
            "app.ingestion.appStoreReviews.fetch_reviews_page",
            return_value=_rss_page([_entry("5", "t", "c", "0")]),
        )

        result = getAppReviews("123", "mostRecent", max_pages=5)

        assert result == []

    def test_breaks_when_feed_is_empty(self, mocker):
        mocker.patch(
            "app.ingestion.appStoreReviews.fetch_reviews_page",
            return_value={"feed": {}},
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
        mocker.patch(
            "app.ingestion.appStoreReviews.fetch_reviews_page",
            side_effect=[_rss_page(entries_p1), _rss_page(entries_p2)],
        )

        result = getAppReviews("123", "mostRecent", max_pages=2)

        assert [r["title"] for r in result] == ["T1", "T2", "T3", "T4"]

    def test_passes_id_sort_and_page_to_client(self, mocker):
        fetch = mocker.patch(
            "app.ingestion.appStoreReviews.fetch_reviews_page",
            return_value={"feed": {}},
        )

        getAppReviews("999", "mostHelpful", max_pages=1)

        assert fetch.call_args.args[0] == "999"
        assert fetch.call_args.args[1] == "mostHelpful"
        assert fetch.call_args.args[2] == 1
