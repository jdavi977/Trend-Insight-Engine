from app.preprocessing.reviewClean import appReviewClean


def test_appReviewClean_keeps_high_vote_keyword_matches_and_strips_emojis():
    raw = [
        {"vote_count": 10, "content": "  The app CRASHES on launch 🔥  "},
        {"vote_count": "8", "content": "Frequent bug after update"},
        {"vote_count": 3, "content": "Crashes for me too"},
        {"vote_count": 20, "content": "Love the colour scheme and design"},
        {"vote_count": 50, "content": "the app crashes on launch"},
    ]

    result = appReviewClean(raw)

    contents = [row["Content"] for row in result]
    assert "the app crashes on launch" in contents
    assert "frequent bug after update" in contents
    assert all("love the colour scheme" not in c for c in contents)
    assert all("crashes for me too" not in c for c in contents)
    assert contents.count("the app crashes on launch") == 1


def test_appReviewClean_drops_reviews_with_vote_count_at_or_below_five():
    raw = [
        {"vote_count": 5, "content": "app crashes constantly"},
        {"vote_count": 0, "content": "crash bug"},
    ]
    assert appReviewClean(raw) == []


def test_appReviewClean_returns_empty_for_empty_input():
    assert appReviewClean([]) == []
