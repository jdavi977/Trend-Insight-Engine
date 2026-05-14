"""Tests for app.preprocessing.reviewPipeline.clean.

Parameterized over both source configs (YOUTUBE_PREPROCESS and
APPSTORE_PREPROCESS) wherever the behaviour under test is source-agnostic.
Source-specific cases (keyword filter present vs. None) use dedicated tests.
"""
import re
from unittest.mock import patch

import pytest

from app.preprocessing.reviewPipeline import clean
from app.config.preprocessing import APPSTORE_PREPROCESS, YOUTUBE_PREPROCESS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_YOUTUBE_FIELD = YOUTUBE_PREPROCESS["engagement_field"]   # "Likes"
_YOUTUBE_THRESH = YOUTUBE_PREPROCESS["threshold"]          # 50

_APPSTORE_FIELD = APPSTORE_PREPROCESS["engagement_field"]  # "vote_count"
_APPSTORE_THRESH = APPSTORE_PREPROCESS["threshold"]        # 6

_SOURCE_PARAMS = pytest.mark.parametrize(
    "engagement_field,threshold",
    [
        (_YOUTUBE_FIELD, _YOUTUBE_THRESH),
        (_APPSTORE_FIELD, _APPSTORE_THRESH),
    ],
    ids=["youtube", "appstore"],
)


def _row(content: str, field: str, score: int | float) -> dict:
    return {"Content": content, field: score}


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_empty_input_returns_empty(engagement_field, threshold):
    assert clean([], engagement_field=engagement_field, threshold=threshold) == []


# ---------------------------------------------------------------------------
# Engagement-threshold filter
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_threshold_drops_below(engagement_field, threshold):
    rows = [_row("keep me please right now", engagement_field, threshold),
            _row("drop me please right now", engagement_field, threshold - 1)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None, min_length=0)
    contents = [r["Content"] for r in result]
    assert "keep me please right now" in contents
    assert "drop me please right now" not in contents


@_SOURCE_PARAMS
def test_threshold_keeps_exactly_at_threshold(engagement_field, threshold):
    rows = [_row("boundary value exactly here", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None, min_length=0)
    assert [r["Content"] for r in result] == ["boundary value exactly here"]


@_SOURCE_PARAMS
def test_missing_engagement_field_treated_as_zero_and_dropped(engagement_field, threshold):
    rows = [{"Content": "no score field present at all"}]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert result == []


# ---------------------------------------------------------------------------
# Content normalisation (lowercase + strip)
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_content_is_lowercased_and_stripped(engagement_field, threshold):
    rows = [_row("  HELLO WORLD LONG ENOUGH  ", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert result[0]["Content"] == "hello world long enough"


# ---------------------------------------------------------------------------
# Emoji strip
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_emojis_are_removed(engagement_field, threshold):
    rows = [_row("great application works well 🔥💥", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert "🔥" not in result[0]["Content"]
    assert "💥" not in result[0]["Content"]
    assert "great application works well" in result[0]["Content"]


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_duplicate_content_rows_are_deduplicated(engagement_field, threshold):
    rows = [
        _row("same text repeated again here", engagement_field, threshold),
        _row("same text repeated again here", engagement_field, threshold + 10),
    ]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert len(result) == 1
    assert result[0]["Content"] == "same text repeated again here"


# ---------------------------------------------------------------------------
# Keyword filter — present
# ---------------------------------------------------------------------------

def test_keyword_filter_keeps_matching_row():
    rows = [
        _row("the app crashes on launch", _APPSTORE_FIELD, _APPSTORE_THRESH),
        _row("really love this design", _APPSTORE_FIELD, _APPSTORE_THRESH),
    ]
    result = clean(rows, **APPSTORE_PREPROCESS)
    contents = [r["Content"] for r in result]
    assert "the app crashes on launch" in contents
    assert "really love this design" not in contents


def test_keyword_filter_none_keeps_all_rows():
    rows = [
        _row("really love this design", _YOUTUBE_FIELD, _YOUTUBE_THRESH),
        _row("totally off topic comment", _YOUTUBE_FIELD, _YOUTUBE_THRESH),
    ]
    result = clean(rows, **YOUTUBE_PREPROCESS)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Regression: row matching N keywords appears exactly once
# ---------------------------------------------------------------------------

def test_multi_keyword_match_row_appears_exactly_once():
    """A row whose Content matches multiple keywords in the filter is kept once.

    The legacy ``textCleaning.keyword_filtering`` appended the row once per
    matched keyword, producing duplicates that were silently masked by a
    subsequent ``remove_duplicates`` call.  ``reviewPipeline.clean`` fixes
    this at the source by breaking on the first match.
    """
    _filter = ("crash", "bug", "broken", "freeze", "lag")
    rows = [_row("app crash bug broken freeze lag", _APPSTORE_FIELD, _APPSTORE_THRESH)]
    result = clean(
        rows,
        engagement_field=_APPSTORE_FIELD,
        threshold=_APPSTORE_THRESH,
        keyword_filter=_filter,
    )
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Keyword filter — word-boundary matching
# ---------------------------------------------------------------------------

def test_keyword_filter_uses_word_boundary():
    _filter = ("crash",)
    rows = [
        _row("app crash after update", _APPSTORE_FIELD, _APPSTORE_THRESH),
        _row("not crashing exactly", _APPSTORE_FIELD, _APPSTORE_THRESH),
    ]
    result = clean(
        rows,
        engagement_field=_APPSTORE_FIELD,
        threshold=_APPSTORE_THRESH,
        keyword_filter=_filter,
    )
    contents = [r["Content"] for r in result]
    assert "app crash after update" in contents
    assert "not crashing exactly" not in contents


# ---------------------------------------------------------------------------
# Config splat integration
# ---------------------------------------------------------------------------

def test_youtube_preprocess_config_splat_works():
    rows = [_row("  Video quality IS terrible  ", _YOUTUBE_FIELD, _YOUTUBE_THRESH)]
    result = clean(rows, **YOUTUBE_PREPROCESS)
    assert result[0]["Content"] == "video quality is terrible"


def test_appstore_preprocess_config_splat_works():
    rows = [_row("App CRASHES constantly 💥", _APPSTORE_FIELD, _APPSTORE_THRESH)]
    result = clean(rows, **APPSTORE_PREPROCESS)
    assert result[0]["Content"] == "app crashes constantly "


# ---------------------------------------------------------------------------
# Min-length filter
# ---------------------------------------------------------------------------

def test_min_length_drops_short_content():
    rows = [_row("ok", _YOUTUBE_FIELD, _YOUTUBE_THRESH)]
    result = clean(rows, engagement_field=_YOUTUBE_FIELD, threshold=_YOUTUBE_THRESH, min_length=20)
    assert result == []


def test_min_length_override_keeps_short_content():
    rows = [_row("ok", _YOUTUBE_FIELD, _YOUTUBE_THRESH)]
    result = clean(rows, engagement_field=_YOUTUBE_FIELD, threshold=_YOUTUBE_THRESH, min_length=2)
    assert len(result) == 1
    assert result[0]["Content"] == "ok"


def test_min_length_applied_after_normalisation():
    # emoji-only string collapses to empty after strip — dropped by min_length
    rows = [_row("🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥", _YOUTUBE_FIELD, _YOUTUBE_THRESH)]
    result = clean(rows, engagement_field=_YOUTUBE_FIELD, threshold=_YOUTUBE_THRESH, min_length=20)
    assert result == []


# ---------------------------------------------------------------------------
# Pre-compiled keyword patterns
# ---------------------------------------------------------------------------

def test_keyword_patterns_compiled_once_per_call():
    """re.compile is called once per keyword, not once per row."""
    _filter = ("crash", "bug")
    rows = [
        _row("app crash on startup every time", _APPSTORE_FIELD, _APPSTORE_THRESH),
        _row("serious bug in the checkout flow", _APPSTORE_FIELD, _APPSTORE_THRESH),
        _row("another crash report from users", _APPSTORE_FIELD, _APPSTORE_THRESH),
    ]
    with patch("app.preprocessing.reviewPipeline.re.compile", wraps=re.compile) as mock_compile:
        clean(
            rows,
            engagement_field=_APPSTORE_FIELD,
            threshold=_APPSTORE_THRESH,
            keyword_filter=_filter,
        )
    assert mock_compile.call_count == len(_filter)


# ---------------------------------------------------------------------------
# Dedup with casing
# ---------------------------------------------------------------------------

def test_duplicate_rows_different_casing_collapsed():
    rows = [
        _row("App Crashes On Launch Every Time", _APPSTORE_FIELD, _APPSTORE_THRESH),
        _row("app crashes on launch every time", _APPSTORE_FIELD, _APPSTORE_THRESH),
    ]
    result = clean(rows, engagement_field=_APPSTORE_FIELD, threshold=_APPSTORE_THRESH, keyword_filter=None)
    assert len(result) == 1
    assert result[0]["Content"] == "app crashes on launch every time"


# ---------------------------------------------------------------------------
# Engagement drop does not mutate original row Content
# ---------------------------------------------------------------------------

def test_dropped_row_content_not_mutated():
    original_content = "Short"
    row = _row(original_content, _YOUTUBE_FIELD, _YOUTUBE_THRESH - 1)
    clean([row], engagement_field=_YOUTUBE_FIELD, threshold=_YOUTUBE_THRESH)
    assert row["Content"] == original_content
