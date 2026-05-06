"""Safety-net tests for the LLM extraction seam, written against the current
validateOutput implementation before PR 2 replaces it with extract_insights.

These tests document the expected contract so the PR 2 rewrite can be
validated against them without changing any assertions.
"""
import json

import pytest

from app.llm.validateOutput import validateOutput
from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem


def _yt_payload(problems, title="Test Video"):
    return json.dumps({"source": "youtube", "title": title, "problems": problems})


def _as_payload(problems, title="Test App"):
    return json.dumps({"source": "app_store", "title": title, "problems": problems})


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


class TestHappyPath:
    def test_youtube_valid_payload_returns_LLMExtraction(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = validateOutput(_yt_payload([VALID_YT_PROBLEM]))

        assert isinstance(result, LLMExtraction)
        assert result.source == "youtube"
        assert len(result.problems) == 1
        assert isinstance(result.problems[0], YoutubeProblemItem)
        assert result.problems[0].problem == "app crashes on startup"

    def test_appstore_valid_payload_returns_LLMExtraction(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = validateOutput(_as_payload([VALID_AS_PROBLEM]))

        assert isinstance(result, LLMExtraction)
        assert result.source == "app_store"
        assert len(result.problems) == 1
        assert isinstance(result.problems[0], AppStoreProblemItem)
        assert result.problems[0].problem == "notifications never arrive"
        assert result.problems[0].average_rating == pytest.approx(2.1)

    def test_multiple_valid_problems_all_kept(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        second = {**VALID_YT_PROBLEM, "problem": "video stutters on playback"}
        result = validateOutput(_yt_payload([VALID_YT_PROBLEM, second]))

        assert isinstance(result, LLMExtraction)
        assert len(result.problems) == 2


class TestQuarantine:
    def test_malformed_item_dropped_valid_item_kept(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        result = validateOutput(_yt_payload([VALID_YT_PROBLEM, bad]))

        assert isinstance(result, LLMExtraction)
        assert len(result.problems) == 1
        assert result.problems[0].problem == VALID_YT_PROBLEM["problem"]

    def test_quarantine_file_written_for_invalid_items(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        validateOutput(_yt_payload([VALID_YT_PROBLEM, bad]))

        invalid_dir = tmp_path / "data" / "invalid_data"
        assert invalid_dir.exists()
        run_dirs = list(invalid_dir.iterdir())
        assert len(run_dirs) == 1
        quarantined = json.loads((run_dirs[0] / "run.json").read_text())
        assert len(quarantined) == 1
        assert quarantined[0]["severity"] == 99

    def test_quarantine_collision_safe(self, tmp_path, monkeypatch):
        """Two calls with bad items in the same second must not crash."""
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        validateOutput(_yt_payload([VALID_YT_PROBLEM, bad]))
        validateOutput(_yt_payload([VALID_YT_PROBLEM, bad]))


class TestEmptyOrNoProblems:
    def test_empty_problems_list_returns_raw_dict(self):
        raw = json.dumps({"source": "youtube", "title": "Vid", "problems": []})
        result = validateOutput(raw)
        assert result == {"source": "youtube", "title": "Vid", "problems": []}

    def test_all_problems_invalid_returns_raw_dict(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        bad = {**VALID_YT_PROBLEM, "severity": 99}
        result = validateOutput(_yt_payload([bad]))
        assert not isinstance(result, LLMExtraction)
