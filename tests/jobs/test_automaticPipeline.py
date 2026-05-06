"""Unit tests for app/jobs/automaticPipeline.py.

All tests use a fake SourceAdapter built from MagicMocks so no
external services (Supabase, YouTube, OpenAI) are touched.
extract_insights is patched at the module boundary where the pipeline
imports it.
"""
from unittest.mock import MagicMock, patch

import pytest

from app.jobs.automaticPipeline import SourceAdapter, run_automatic_pipeline
from app.schemas.llm import LLMExtraction, YoutubeProblemItem

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ITEM = {"id": "vid1"}

_PROBLEM_ONE = YoutubeProblemItem(
    problem="app crashes on launch",
    type="complaint",
    total_likes=10,
    severity=4,
    frequency=3,
)

_PROBLEM_TWO = YoutubeProblemItem(
    problem="loading is too slow",
    type="performance",
    total_likes=5,
    severity=2,
    frequency=2,
)


def _make_extraction(problems=None, title="Cool Video") -> LLMExtraction:
    return LLMExtraction(
        source="youtube",
        title=title,
        problems=problems if problems is not None else [_PROBLEM_ONE],
    )


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


PATCH_TARGET = "app.jobs.automaticPipeline.extract_insights"

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
# No problems (extract_insights returns None)
# ---------------------------------------------------------------------------


class TestNoneResultSkip:
    def test_skips_item_when_extract_insights_returns_none(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=None):
            result = run_automatic_pipeline([ITEM], [], adapter)

        adapter.build_row.assert_not_called()
        assert result == []

    def test_persist_row_not_called_when_result_is_none(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=None):
            run_automatic_pipeline([ITEM], [], adapter)

        adapter.persist_row.assert_not_called()


# ---------------------------------------------------------------------------
# Per-problem fan-out
# ---------------------------------------------------------------------------


class TestPerProblemFanOut:
    def test_one_build_row_call_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_make_extraction(problems=[_PROBLEM_ONE, _PROBLEM_TWO])):
            run_automatic_pipeline([ITEM], [], adapter)

        assert adapter.build_row.call_count == 2

    def test_one_persist_row_call_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_make_extraction(problems=[_PROBLEM_ONE, _PROBLEM_TWO])):
            run_automatic_pipeline([ITEM], [], adapter)

        assert adapter.persist_row.call_count == 2

    def test_return_value_contains_one_entry_per_problem(self):
        adapter = _make_adapter()

        with patch(PATCH_TARGET, return_value=_make_extraction(problems=[_PROBLEM_ONE, _PROBLEM_TWO])):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert len(result) == 2

    def test_return_value_is_list_of_persisted_rows_in_order(self):
        built_row = {"built": "row"}
        adapter = _make_adapter(build_row=MagicMock(return_value=built_row))

        with patch(PATCH_TARGET, return_value=_make_extraction()):
            result = run_automatic_pipeline([ITEM], [], adapter)

        assert result == [[built_row]]

    def test_build_row_receives_item_typed_problem_today_and_extraction(self):
        adapter = _make_adapter()
        extraction = _make_extraction(title="Vid")

        with patch(PATCH_TARGET, return_value=extraction):
            run_automatic_pipeline([ITEM], [], adapter)

        call_args = adapter.build_row.call_args
        item_arg, problem_arg, today_arg, data_arg = call_args.args
        assert item_arg is ITEM
        assert isinstance(problem_arg, YoutubeProblemItem)
        assert problem_arg.problem == _PROBLEM_ONE.problem
        assert isinstance(today_arg, str)
        assert isinstance(data_arg, LLMExtraction)
        assert data_arg.title == "Vid"
