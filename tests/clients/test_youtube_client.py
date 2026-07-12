"""Behavior tests for `app.clients.youtube`.

PR 5 moves `app/utilities/youtubeApiHelper.py` to `app/clients/youtube.py`
and drops the `__main__` scratch block.
"""
from __future__ import annotations

import json

import pytest
from googleapiclient.errors import HttpError


def _build_categories_service(mocker, items):
    response = {"items": items}
    request = mocker.Mock()
    request.execute.return_value = response
    service = mocker.Mock()
    service.videoCategories.return_value.list.return_value = request
    return service


def test_get_video_categories_returns_id_title_pairs(mocker):
    from app.clients import youtube as yt

    service = _build_categories_service(
        mocker,
        items=[
            {"id": "1", "snippet": {"title": "Film & Animation"}},
            {"id": "20", "snippet": {"title": "Gaming"}},
        ],
    )
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.getVideoCategories()

    assert result == [
        {"Id": "1", "Title": "Film & Animation"},
        {"Id": "20", "Title": "Gaming"},
    ]
    service.close.assert_called_once_with()


def test_get_video_categories_requests_us_region_snippets(mocker):
    from app.clients import youtube as yt

    service = _build_categories_service(mocker, items=[])
    mocker.patch.object(yt, "build", return_value=service)

    yt.getVideoCategories()

    service.videoCategories.return_value.list.assert_called_once_with(
        part="snippet",
        regionCode="US",
    )


def _build_comment_threads_service(mocker, raw_items):
    response = {"items": raw_items}
    request = mocker.Mock()
    request.execute.return_value = response
    service = mocker.Mock()
    service.commentThreads.return_value.list.return_value = request
    return service


def test_list_comment_threads_maps_vendor_json_to_domain_rows(mocker):
    from app.clients import youtube as yt

    raw = [
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {"likeCount": 12, "textDisplay": "great vid"},
                },
            },
        },
        {
            "snippet": {
                "topLevelComment": {
                    "snippet": {"likeCount": 0, "textDisplay": "meh"},
                },
            },
        },
    ]
    service = _build_comment_threads_service(mocker, raw)
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.list_comment_threads("vid123", "relevance", 100)

    assert result == [
        {"Likes": 12, "Text": "great vid"},
        {"Likes": 0, "Text": "meh"},
    ]
    service.commentThreads.return_value.list.assert_called_once_with(
        part="snippet",
        videoId="vid123",
        maxResults=100,
        order="relevance",
        textFormat="plainText",
    )
    service.close.assert_called_once_with()


class _FakeResp:
    def __init__(self, status):
        self.status = status
        self.reason = "Forbidden" if status == 403 else "Not Found"


def _http_error(status, reason):
    body = {
        "error": {
            "code": status,
            "message": f"vendor message for {reason}",
            "errors": [{"message": "x", "domain": "youtube.commentThread", "reason": reason}],
        }
    }
    return HttpError(_FakeResp(status), json.dumps(body).encode("utf-8"))


def _build_erroring_comment_threads_service(mocker, status, reason):
    request = mocker.Mock()
    request.execute.side_effect = _http_error(status, reason)
    service = mocker.Mock()
    service.commentThreads.return_value.list.return_value = request
    return service


@pytest.mark.parametrize(
    "status,reason",
    [(403, "commentsDisabled"), (404, "videoNotFound")],
)
def test_list_comment_threads_returns_empty_for_benign_reasons(mocker, status, reason):
    from app.clients import youtube as yt

    service = _build_erroring_comment_threads_service(mocker, status, reason)
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.list_comment_threads("vid123", "relevance", 100)

    assert result == []
    service.close.assert_called_once_with()


@pytest.mark.parametrize(
    "status,reason",
    [(403, "quotaExceeded"), (403, "forbidden"), (404, "someOtherReason")],
)
def test_list_comment_threads_reraises_non_benign_errors(mocker, status, reason):
    from app.clients import youtube as yt

    service = _build_erroring_comment_threads_service(mocker, status, reason)
    mocker.patch.object(yt, "build", return_value=service)

    with pytest.raises(HttpError):
        yt.list_comment_threads("vid123", "relevance", 100)

    service.close.assert_called_once_with()


def _build_videos_list_service(mocker, raw_items):
    response = {"items": raw_items}
    request = mocker.Mock()
    request.execute.return_value = response
    service = mocker.Mock()
    service.videos.return_value.list.return_value = request
    return service


def test_list_most_popular_picks_maxres_when_available(mocker):
    from app.clients import youtube as yt

    raw = [
        {
            "id": "v1",
            "snippet": {
                "title": "First",
                "thumbnails": {
                    "default": {"url": "d", "width": 120, "height": 90},
                    "medium": {"url": "m", "width": 320, "height": 180},
                    "high": {"url": "h", "width": 480, "height": 360},
                    "standard": {"url": "s", "width": 640, "height": 480},
                    "maxres": {"url": "mx", "width": 1280, "height": 720},
                },
            },
        },
    ]
    service = _build_videos_list_service(mocker, raw)
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.list_most_popular(20, 5)

    assert result == [
        {
            "Id": "v1",
            "Title": "First",
            "Thumbnail": {"url": "mx", "width": 1280, "height": 720},
        },
    ]
    service.videos.return_value.list.assert_called_once_with(
        part="snippet",
        chart="mostPopular",
        videoCategoryId=20,
        maxResults=5,
    )
    service.close.assert_called_once_with()


def test_list_most_popular_falls_back_through_priority_when_maxres_missing(mocker):
    from app.clients import youtube as yt

    raw = [
        {
            "id": "v2",
            "snippet": {
                "title": "Second",
                "thumbnails": {
                    "default": {"url": "d"},
                    "medium": {"url": "m"},
                    "high": {"url": "h"},
                },
            },
        },
    ]
    service = _build_videos_list_service(mocker, raw)
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.list_most_popular(20, 10)

    assert result == [
        {"Id": "v2", "Title": "Second", "Thumbnail": {"url": "h"}},
    ]


def test_list_most_popular_returns_none_thumbnail_when_no_sizes_present(mocker):
    from app.clients import youtube as yt

    raw = [
        {
            "id": "v3",
            "snippet": {"title": "Third", "thumbnails": {}},
        },
    ]
    service = _build_videos_list_service(mocker, raw)
    mocker.patch.object(yt, "build", return_value=service)

    result = yt.list_most_popular(20, 10)

    assert result == [
        {"Id": "v3", "Title": "Third", "Thumbnail": None},
    ]
