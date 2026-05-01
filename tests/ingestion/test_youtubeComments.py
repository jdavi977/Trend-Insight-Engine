"""Tests for app/ingestion/youtubeComments.py.

Pure URL parsing runs for real. The googleapiclient `build()` is mocked because
we don't want to hit the YouTube Data API in tests.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
        fake_response = {
            "items": [
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
        }
        service = MagicMock()
        service.commentThreads.return_value.list.return_value.execute.return_value = (
            fake_response
        )
        mocker.patch(
            "app.ingestion.youtubeComments.build", return_value=service
        )

        result = getYoutubeComments("vid123", "relevance", title="My Video")

        assert result == [
            {"Id": "vid123", "Title": "My Video", "Likes": 12, "Text": "great vid"},
            {"Id": "vid123", "Title": "My Video", "Likes": 0, "Text": "meh"},
        ]
        service.close.assert_called_once()

    def test_passes_video_id_and_order_to_api(self, mocker):
        service = MagicMock()
        service.commentThreads.return_value.list.return_value.execute.return_value = {
            "items": []
        }
        mocker.patch(
            "app.ingestion.youtubeComments.build", return_value=service
        )

        getYoutubeComments("xyz789", "time")

        kwargs = service.commentThreads.return_value.list.call_args.kwargs
        assert kwargs["videoId"] == "xyz789"
        assert kwargs["order"] == "time"
        assert kwargs["part"] == "snippet"
        assert kwargs["textFormat"] == "plainText"


class TestGetMostPopularVideos:
    def test_returns_video_summaries(self, mocker):
        fake_response = {
            "items": [
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
        }
        service = MagicMock()
        service.videos.return_value.list.return_value.execute.return_value = (
            fake_response
        )
        mocker.patch(
            "app.ingestion.youtubeComments.build", return_value=service
        )

        result = getMostPopularVideos(20)

        assert result == [
            {"Title": "First", "Id": "v1", "Thumbnail": {"url": "thumb1"}},
            {"Title": "Second", "Id": "v2", "Thumbnail": {"url": "thumb2"}},
        ]
        service.close.assert_called_once()

    def test_passes_category_id_to_api(self, mocker):
        service = MagicMock()
        service.videos.return_value.list.return_value.execute.return_value = {"items": []}
        mocker.patch(
            "app.ingestion.youtubeComments.build", return_value=service
        )

        getMostPopularVideos(28)

        kwargs = service.videos.return_value.list.call_args.kwargs
        assert kwargs["videoCategoryId"] == 28
        assert kwargs["chart"] == "mostPopular"
