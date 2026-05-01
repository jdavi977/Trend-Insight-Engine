"""`schemas/api.py` is the single home for HTTP request bodies.

Verifies the three Pydantic models accept their canonical payload shapes
and reject missing fields. The endpoint smoke tests in `test_routes.py`
guard the wiring; these guard the contract.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.api import (
    AppStoreAnalyzeRequest,
    DataSave,
    YoutubeAnalyzeRequest,
)


def test_youtube_analyze_request_accepts_url():
    model = YoutubeAnalyzeRequest(youtubeURL="https://youtube.com/watch?v=x")
    assert model.youtubeURL == "https://youtube.com/watch?v=x"


def test_youtube_analyze_request_rejects_missing_url():
    with pytest.raises(ValidationError):
        YoutubeAnalyzeRequest()


def test_appstore_analyze_request_accepts_url():
    model = AppStoreAnalyzeRequest(appStoreURL="https://apps.apple.com/app/id1")
    assert model.appStoreURL == "https://apps.apple.com/app/id1"


def test_appstore_analyze_request_rejects_missing_url():
    with pytest.raises(ValidationError):
        AppStoreAnalyzeRequest()


def test_data_save_accepts_dict_payload():
    model = DataSave(data={"foo": "bar"})
    assert model.data == {"foo": "bar"}


def test_data_save_rejects_non_dict():
    with pytest.raises(ValidationError):
        DataSave(data="not-a-dict")
