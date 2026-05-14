"""Tests for appstore-style data flowing through reviewPipeline.clean.

The service maps raw review ``content`` → ``Content`` before calling clean().
These tests cover that scenario end-to-end: raw dicts with lowercase ``content``
and ``vote_count`` keys, pre-mapped and passed through clean().
"""
from app.preprocessing.reviewPipeline import clean

_TEST_KEYWORDS = ("crash", "bug", "crashes", "frequent")
_THRESHOLD = 6  # equivalent to old vote_count > 5


def _prep(raw: list[dict]) -> list[dict]:
    return [{**item, "Content": item["content"]} for item in raw]


def test_clean_keeps_high_vote_keyword_matches_and_strips_emojis():
    raw = [
        {"vote_count": 10, "content": "  The app CRASHES on launch 🔥  "},
        {"vote_count": "8", "content": "Frequent bug after update"},
        {"vote_count": 3, "content": "Crashes for me too"},
        {"vote_count": 20, "content": "Love the colour scheme and design"},
        {"vote_count": 50, "content": "the app crashes on launch"},
    ]

    result = clean(_prep(raw), engagement_field="vote_count", threshold=_THRESHOLD, keyword_filter=_TEST_KEYWORDS)

    contents = [row["Content"] for row in result]
    assert "the app crashes on launch" in contents
    assert "frequent bug after update" in contents
    assert all("love the colour scheme" not in c for c in contents)
    assert all("crashes for me too" not in c for c in contents)
    assert contents.count("the app crashes on launch") == 1
    assert all("vote_count" in r and "Content" in r for r in result)


def test_clean_drops_reviews_with_vote_count_at_or_below_five():
    raw = [
        {"vote_count": 5, "content": "app crashes constantly"},
        {"vote_count": 0, "content": "crash bug"},
    ]
    assert clean(_prep(raw), engagement_field="vote_count", threshold=_THRESHOLD, keyword_filter=_TEST_KEYWORDS) == []


def test_clean_returns_empty_for_empty_input():
    assert clean([], engagement_field="vote_count", threshold=_THRESHOLD, keyword_filter=()) == []
