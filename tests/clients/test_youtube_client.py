"""Behavior tests for `app.clients.youtube`.

PR 5 moves `app/utilities/youtubeApiHelper.py` to `app/clients/youtube.py`
and drops the `__main__` scratch block.
"""
from __future__ import annotations


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
