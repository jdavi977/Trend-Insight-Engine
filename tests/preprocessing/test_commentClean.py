from app.preprocessing.commentClean import loadAndClean


def test_loadAndClean_drops_low_like_comments_lowercases_and_dedupes():
    raw = [
        {"Title": "Vid A", "Likes": 100, "Text": "  Battery Life Is Bad  "},
        {"Title": "Vid A", "Likes": 49, "Text": "Below threshold"},
        {"Title": "Vid A", "Likes": 50, "Text": "Crashes a lot 🔥"},
        {"Title": "Vid A", "Likes": 200, "Text": "battery life is bad"},
    ]

    result = loadAndClean(raw, keywords=[])

    assert result == [
        {"Title": "Vid A", "Likes": 200, "Content": "battery life is bad"},
        {"Title": "Vid A", "Likes": 50, "Content": "crashes a lot "},
    ]


def test_loadAndClean_treats_missing_likes_as_zero_and_drops():
    raw = [{"Title": "X", "Text": "no likes field"}]
    assert loadAndClean(raw, keywords=[]) == []


def test_loadAndClean_returns_empty_for_empty_input():
    assert loadAndClean([], keywords=[]) == []
