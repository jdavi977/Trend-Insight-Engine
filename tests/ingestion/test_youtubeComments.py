"""Tests for app/ingestion/youtubeComments.py.

Pure URL parsing runs for real. The clients/youtube.py wrappers are mocked —
ingestion no longer touches googleapiclient directly.
"""
from __future__ import annotations

from app.ingestion.youtubeComments import (
    getMostPopularVideos,
    getVideoId,
    getYoutubeComments,
)


class TestGetVideoId:
    def test_standard_watch_url(self):
        assert getVideoId("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_youtu_be_url(self):
        assert getVideoId("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert getVideoId("https://www.youtube.com/shorts/abc123XYZ") == "abc123XYZ"

    def test_unrecognized_url_returns_empty(self):
        assert getVideoId("https://example.com/video") == ""

    def test_watch_url_without_v_param_returns_empty(self):
        assert getVideoId("https://www.youtube.com/watch") == ""


class TestGetYoutubeComments:
    def test_returns_normalized_comment_records(self, mocker):
        items = [
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {"likeCount": 12, "textDisplay": "great vid"}
                    }
                }
            },
            {
                "snippet": {
                    "topLevelComment": {
                        "snippet": {"likeCount": 0, "textDisplay": "meh"}
                    }
                }
            },
        ]
        mocker.patch(
            "app.ingestion.youtubeComments.list_comment_threads",
            return_value=items,
        )

        result = getYoutubeComments("vid123", "relevance", title="My Video")

        assert result == [
            {"Id": "vid123", "Title": "My Video", "Likes": 12, "Text": "great vid"},
            {"Id": "vid123", "Title": "My Video", "Likes": 0, "Text": "meh"},
        ]

    def test_passes_video_id_and_order_to_client(self, mocker):
        spy = mocker.patch(
            "app.ingestion.youtubeComments.list_comment_threads",
            return_value=[],
        )

        getYoutubeComments("xyz789", "time")

        spy.assert_called_once()
        args, kwargs = spy.call_args
        called_with = (*args, *kwargs.values())
        assert "xyz789" in called_with
        assert "time" in called_with


class TestGetMostPopularVideos:
    def test_returns_video_summaries(self, mocker):
        items = [
            {
                "id": "v1",
                "snippet": {
                    "title": "First",
                    "thumbnails": {"default": {"url": "thumb1"}},
                },
            },
            {
                "id": "v2",
                "snippet": {
                    "title": "Second",
                    "thumbnails": {"default": {"url": "thumb2"}},
                },
            },
        ]
        mocker.patch(
            "app.ingestion.youtubeComments.list_most_popular",
            return_value=items,
        )

        result = getMostPopularVideos(20)

        assert result == [
            {"Title": "First", "Id": "v1", "Thumbnail": {"url": "thumb1"}},
            {"Title": "Second", "Id": "v2", "Thumbnail": {"url": "thumb2"}},
        ]

    def test_passes_category_id_to_client(self, mocker):
        spy = mocker.patch(
            "app.ingestion.youtubeComments.list_most_popular",
            return_value=[],
        )

        getMostPopularVideos(28)

        spy.assert_called_once()
        args, kwargs = spy.call_args
        called_with = (*args, *kwargs.values())
        assert 28 in called_with
