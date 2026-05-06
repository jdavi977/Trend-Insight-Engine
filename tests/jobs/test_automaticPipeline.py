"""Unit tests for app/jobs/automaticPipeline.py.

All tests use a fake SourceAdapter built from MagicMocks so no
external services (Supabase, YouTube, OpenAI) are touched.
extractInsights is patched at the module boundary where the pipeline
imports it.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from app.jobs.automaticPipeline import SourceAdapter, run_automatic_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ITEM = {"id": "vid1"}

_ONE_PROBLEM = [
    {
        "problem": "app crashes on launch",
        "type": "complaint",
        "total_likes": 10,
        "severity": 4,
        "frequency": 3,
    }
]

_TWO_PROBLEMS = [
    {
        "problem": "app crashes on launch",
        "type": "complaint",
        "total_likes": 10,
        "severity": 4,
        "frequency": 3,
    },
    {
        "problem": "loading is too slow",
        "type": "performance",
        "total_likes": 5,
        "severity": 2,
        "frequency": 2,
    },
]


def _make_adapter(**overrides) -> SourceAdapter:
    """Return a SourceAdapter whose fields are MagicMocks by default."""
    defaults: dict = dict(
        item_id=lambda item: item["id"],
        check_existing=MagicMock(return_value=[]),
        bump_date=MagicMock(),
        ingest=MagicMock(return_value=["raw comment"]),
        clean=MagicMock(return_value=["cleaned comment"]),
        system_prompt="system",
        output_prompt="output",
        build_row=MagicMock(return_value={"built": "row"}),
        persist_row=MagicMock(),
    )
    defaults.update(overrides)
    return SourceAdapter(**defaults)


def _good_insights(problems=_ONE_PROBLEM, title="Cool Video") -> str:
    return json.dumps({"title": title, "problems": problems})


PATCH_TARGET = "app.jobs.automaticPipeline.extractInsights"

# ---------------------------------------------------------------------------
# Existing-id short-circuit
# ---------------------------------------------------------------------------


class TestExistingIdShortCircuit:
    def test_bumps_date_when_id_already_exists(self):
        existing_rows = [{"key": "vid1", "date": "2026-01-01"}]
        adapter = _make_adapter(check_existing=MagicMock(return_value=existing_rows))

        with patch(PATCH_TARGET) as mock_extract:
            run_automatic_pipeline([ITEM], [], adapter)

        adapter.bump_date.assert_called_once()
        mock_extract.assert_not_called()

    def test_existing_rows_appended_to_return_value(self):
        existing_rows = [{"key": "vid1", "date": "2026-01-01"}]
        adapter = _make_adapter(check_existing=MagicMock(return_value=existing_rows))

        with patch(PATCH_TARGET):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert result == [existing_rows]

    def test_ingest_not_called_when_id_exists(self):
        existing_rows = [{"key": "vid1"}]
        adapter = _make_adapter(check_existing=MagicMock(return_value=existing_rows))

        with patch(PATCH_TARGET):
            run_automatic_pipeline([ITEM], [], adapter)

        adapter.ingest.assert_not_called()


# ---------------------------------------------------------------------------
# Empty clean() output
# ---------------------------------------------------------------------------


class TestEmptyCleanSkip:
    def test_skips_item_when_clean_returns_empty_list(self):
        adapter = _make_adapter(clean=MagicMock(return_value=[]))

        with patch(PATCH_TARGET) as mock_extract:
            result = run_automatic_pipeline([ITEM], [], adapter)

        mock_extract.assert_not_called()
        assert result == []

    def test_build_row_not_called_when_clean_is_empty(self):
        adapter = _make_adapter(clean=MagicMock(return_value=[]))

        with patch(PATCH_TARGET):
            run_automatic_pipeline([ITEM], [], adapter)

        adapter.build_row.assert_not_called()


# ---------------------------------------------------------------------------
# list / dict normalisation
# ---------------------------------------------------------------------------


class TestListNormalization:
    def test_single_element_list_is_normalized_to_first_element(self):
        data_obj = {"title": "T", "problems": _ONE_PROBLEM}
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=json.dumps([data_obj])):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert adapter.build_row.called
        assert len(result) == 1

    def test_empty_list_response_skips_item(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=json.dumps([])):
            result = run_automatic_pipeline([ITEM], [], adapter)

        adapter.build_row.assert_not_called()
        assert result == []


# ---------------------------------------------------------------------------
# Empty / missing problems
# ---------------------------------------------------------------------------


class TestEmptyProblemsSkip:
    def test_empty_problems_list_skips_item(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=json.dumps({"title": "T", "problems": []})):
            result = run_automatic_pipeline([ITEM], [], adapter)

        adapter.build_row.assert_not_called()
        assert result == []

    def test_missing_problems_key_skips_item(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=json.dumps({"title": "T"})):
            result = run_automatic_pipeline([ITEM], [], adapter)

        adapter.build_row.assert_not_called()
        assert result == []


# ---------------------------------------------------------------------------
# Per-problem fan-out
# ---------------------------------------------------------------------------


class TestPerProblemFanOut:
    def test_one_build_row_call_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_good_insights(problems=_TWO_PROBLEMS)):
            run_automatic_pipeline([ITEM], [], adapter)

        assert adapter.build_row.call_count == 2

    def test_one_persist_row_call_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_good_insights(problems=_TWO_PROBLEMS)):
            run_automatic_pipeline([ITEM], [], adapter)

        assert adapter.persist_row.call_count == 2

    def test_return_value_contains_one_entry_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_good_insights(problems=_TWO_PROBLEMS)):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert len(result) == 2

    def test_return_value_is_list_of_persisted_rows_in_order(self):
        built_row = {"built": "row"}
        adapter = _make_adapter(build_row=MagicMock(return_value=built_row))

        with patch(PATCH_TARGET, return_value=_good_insights(problems=_ONE_PROBLEM)):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert result == [[built_row]]

    def test_build_row_receives_item_problem_today_and_data(self):
        adapter = _make_adapter()
        data_obj = {"title": "Vid", "problems": _ONE_PROBLEM}

        with patch(PATCH_TARGET, return_value=json.dumps(data_obj)):
            run_automatic_pipeline([ITEM], [], adapter)

        call_args = adapter.build_row.call_args
        item_arg, problem_arg, today_arg, data_arg = call_args.args
        assert item_arg is ITEM
        assert problem_arg == _ONE_PROBLEM[0]
        assert isinstance(today_arg, str)
        assert data_arg == data_obj
