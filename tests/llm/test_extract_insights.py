import json

import pytest

from app.llm.extractInsights import extract_insights
from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem

MOCK_TARGET = "app.llm.extractInsights.create_response"

VALID_YT_PROBLEM = {
    "problem": "app crashes on startup",
    "type": "complaint",
    "total_likes": 15,
    "severity": 5,
    "frequency": 4,
}

VALID_AS_PROBLEM = {
    "problem": "notifications never arrive",
    "type": "complaint",
    "average_rating": 2.1,
    "severity": 4,
    "frequency": 3,
    "example_reviews": ["never gets notifs", "push broken for months"],
}


def _yt_json(problems, title="Test Video"):
    return json.dumps({"source": "youtube", "title": title, "problems": problems})


def _as_json(problems, title="Test App"):
    return json.dumps({"source": "app_store", "title": title, "problems": problems})


class TestHappyPath:
    def test_youtube_valid_payload_returns_LLMExtraction(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        mocker.patch(MOCK_TARGET, return_value=_yt_json([VALID_YT_PROBLEM]))

        result = extract_insights(["some comment"], "sys", "out")

        assert isinstance(result, LLMExtraction)
        assert result.source == "youtube"
        assert len(result.problems) == 1
        assert isinstance(result.problems[0], YoutubeProblemItem)
        assert result.problems[0].problem == "app crashes on startup"

    def test_appstore_valid_payload_returns_LLMExtraction(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        mocker.patch(MOCK_TARGET, return_value=_as_json([VALID_AS_PROBLEM]))

        result = extract_insights(["some review"], "sys", "out")

        assert isinstance(result, LLMExtraction)
        assert result.source == "app_store"
        assert len(result.problems) == 1
        assert isinstance(result.problems[0], AppStoreProblemItem)
        assert result.problems[0].problem == "notifications never arrive"
        assert result.problems[0].average_rating == pytest.approx(2.1)

    def test_multiple_valid_problems_all_kept(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        second = {**VALID_YT_PROBLEM, "problem": "video stutters on playback"}
        mocker.patch(MOCK_TARGET, return_value=_yt_json([VALID_YT_PROBLEM, second]))

        result = extract_insights([], "sys", "out")

        assert isinstance(result, LLMExtraction)
        assert len(result.problems) == 2


class TestListEnvelopeUnwrap:
    def test_list_shaped_response_unwrapped_to_first_element(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        payload = {"source": "youtube", "title": "T", "problems": [VALID_YT_PROBLEM]}
        mocker.patch(MOCK_TARGET, return_value=json.dumps([payload]))

        result = extract_insights([], "sys", "out")

        assert isinstance(result, LLMExtraction)
        assert result.problems[0].problem == VALID_YT_PROBLEM["problem"]

    def test_empty_list_response_returns_none(self, mocker):
        mocker.patch(MOCK_TARGET, return_value=json.dumps([]))

        result = extract_insights([], "sys", "out")

        assert result is None


class TestEmptyOrNoProblems:
    def test_empty_problems_list_returns_none(self, mocker):
        mocker.patch(MOCK_TARGET, return_value=_yt_json([]))

        result = extract_insights([], "sys", "out")

        assert result is None

    def test_missing_problems_key_returns_none(self, mocker):
        mocker.patch(MOCK_TARGET, return_value=json.dumps({"source": "youtube", "title": "T"}))

        result = extract_insights([], "sys", "out")

        assert result is None

    def test_all_problems_invalid_returns_none(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        mocker.patch(MOCK_TARGET, return_value=_yt_json([bad]))

        result = extract_insights([], "sys", "out")

        assert result is None


class TestQuarantine:
    def test_malformed_item_dropped_valid_item_kept(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        mocker.patch(MOCK_TARGET, return_value=_yt_json([VALID_YT_PROBLEM, bad]))

        result = extract_insights([], "sys", "out")

        assert isinstance(result, LLMExtraction)
        assert len(result.problems) == 1
        assert result.problems[0].problem == VALID_YT_PROBLEM["problem"]

    def test_quarantine_file_written_for_invalid_items(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        mocker.patch(MOCK_TARGET, return_value=_yt_json([VALID_YT_PROBLEM, bad]))

        extract_insights([], "sys", "out")

        invalid_dir = tmp_path / "data" / "invalid_data"
        assert invalid_dir.exists()
        run_dirs = list(invalid_dir.iterdir())
        assert len(run_dirs) == 1
        quarantined = json.loads((run_dirs[0] / "run.json").read_text())
        assert len(quarantined) == 1
        assert quarantined[0]["severity"] == 99

    def test_quarantine_collision_safe(self, tmp_path, monkeypatch, mocker):
        """Two calls with bad items in the same second must not crash and both write."""
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        mocker.patch(MOCK_TARGET, return_value=_yt_json([VALID_YT_PROBLEM, bad]))

        extract_insights([], "sys", "out")
        extract_insights([], "sys", "out")

        invalid_dir = tmp_path / "data" / "invalid_data"
        run_dirs = list(invalid_dir.iterdir())
        assert len(run_dirs) == 2


class TestEnvelopeValidationFailure:
    def test_invalid_envelope_source_returns_none(self, tmp_path, monkeypatch, mocker):
        monkeypatch.chdir(tmp_path)
        payload = {"source": "unknown_source", "problems": [VALID_YT_PROBLEM]}
        mocker.patch(MOCK_TARGET, return_value=json.dumps(payload))

        result = extract_insights([], "sys", "out")

        assert result is None

    def test_invalid_json_returns_none(self, mocker):
        mocker.patch(MOCK_TARGET, return_value="not valid json {{{")

        result = extract_insights([], "sys", "out")

        assert result is None
