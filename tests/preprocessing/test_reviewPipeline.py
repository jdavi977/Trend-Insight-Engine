"""Tests for app.preprocessing.reviewPipeline.clean.

Parameterized over both source configs (YOUTUBE_PREPROCESS and
APPSTORE_PREPROCESS) wherever the behaviour under test is source-agnostic.
Source-specific cases (keyword filter present vs. None) use dedicated tests.
"""
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
    rows = [_row("keep me", engagement_field, threshold),
            _row("drop me", engagement_field, threshold - 1)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    contents = [r["Content"] for r in result]
    assert "keep me" in contents
    assert "drop me" not in contents


@_SOURCE_PARAMS
def test_threshold_keeps_exactly_at_threshold(engagement_field, threshold):
    rows = [_row("boundary", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert [r["Content"] for r in result] == ["boundary"]


@_SOURCE_PARAMS
def test_missing_engagement_field_treated_as_zero_and_dropped(engagement_field, threshold):
    rows = [{"Content": "no score field"}]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert result == []


# ---------------------------------------------------------------------------
# Content normalisation (lowercase + strip)
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_content_is_lowercased_and_stripped(engagement_field, threshold):
    rows = [_row("  HELLO WORLD  ", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert result[0]["Content"] == "hello world"


# ---------------------------------------------------------------------------
# Emoji strip
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_emojis_are_removed(engagement_field, threshold):
    rows = [_row("great app 🔥💥", engagement_field, threshold)]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert "🔥" not in result[0]["Content"]
    assert "💥" not in result[0]["Content"]
    assert "great app" in result[0]["Content"]


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

@_SOURCE_PARAMS
def test_duplicate_content_rows_are_deduplicated(engagement_field, threshold):
    rows = [
        _row("same text", engagement_field, threshold),
        _row("same text", engagement_field, threshold + 10),
    ]
    result = clean(rows, engagement_field=engagement_field, threshold=threshold, keyword_filter=None)
    assert len(result) == 1
    assert result[0]["Content"] == "same text"


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
