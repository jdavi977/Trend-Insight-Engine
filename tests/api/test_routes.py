"""Smoke tests for the four FastAPI endpoints with services mocked.

This file is the load-bearing safety net for PR 4 (api/ carve-out). It should
keep passing after main.py is split into routers, with at most a patch-path
update if a route's collaborators move modules.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_post_analyze_youtube_valid_url_returns_service_payload(client, mocker):
    mocker.patch(
        "app.main.youtube_manual",
        return_value={"source": "youtube", "problems": []},
    )
    response = client.post(
        "/analyze/youtube",
        json={"youtubeURL": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    )
    assert response.status_code == 200
    assert response.json() == {"source": "youtube", "problems": []}


def test_post_analyze_youtube_invalid_url_returns_400(client, mocker):
    service = mocker.patch("app.main.youtube_manual")
    response = client.post(
        "/analyze/youtube",
        json={"youtubeURL": "https://vimeo.com/123"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid link"
    service.assert_not_called()


def test_post_analyze_appstore_valid_url_returns_service_payload(client, mocker):
    mocker.patch(
        "app.main.app_store_manual",
        return_value={"source": "app_store", "problems": []},
    )
    response = client.post(
        "/analyze/appStore",
        json={"appStoreURL": "https://apps.apple.com/us/app/instagram/id389801252"},
    )
    assert response.status_code == 200
    assert response.json() == {"source": "app_store", "problems": []}


def test_post_analyze_appstore_invalid_url_returns_400(client, mocker):
    service = mocker.patch("app.main.app_store_manual")
    response = client.post(
        "/analyze/appStore",
        json={"appStoreURL": "https://play.google.com/foo"},
    )
    assert response.status_code == 400
    service.assert_not_called()


def test_get_home_page_returns_three_category_buckets(client, mocker):
    mocker.patch(
        "app.main.get_weekly_ids",
        side_effect=[
            {"category": "game", "ids": [1]},
            {"category": "scitech", "ids": [2]},
            {"category": "howto_style", "ids": [3]},
        ],
    )
    response = client.get("/get/homePage")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert payload[0]["category"] == "game"


def test_post_data_send_invokes_persistence(client, mocker):
    save = mocker.patch("app.main.data_save")
    response = client.post("/data/send", json={"data": {"foo": "bar"}})
    assert response.status_code == 200
    save.assert_called_once_with({"foo": "bar"})
