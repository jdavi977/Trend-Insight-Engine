APP_REVIEW_PAGES = 10
MANUAL_REVIEW_PAGES = 2
GAME_CATEGORY_ID = 20
SCIENCE_TECH_ID = 28
HOW_TO_STYLE_ID = 26

YOUTUBE_COMMENTS_AMOUNT = 100
YOUTUBE_VIDEO_AMOUNT = 5

APPLE_GAMES_GENRE_ID = 6014
APPLE_SOCIAL_GENRE_ID = 6005
APPLE_UTILITIES_GENRE_ID = 6002
APPLE_TOP_APPS_LIMIT = 5
APPLE_COUNTRY = "us"

RAG_QUERY_MAX_CHARS = 2000
RAG_TOP_K = 5
RAG_MIN_SIMILARITY = 0.60
RAG_DEDUP_SIMILARITY = 0.75
RAG_COLLECTION = "insights"

# Model routing for v2 pipeline (PRD §10.1, spec §9). Every LLM call in slice 1
# goes through app/llm/router.py::resolve(stage); v1 ships gpt-4o for every stage.
MODEL_ROUTING = {
    "preflight_classify": {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 1500},
    "preflight_rank":     {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 2000},
    "per_source_extract": {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000},
    "synthesis":          {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 6000},
    "idea_match":         {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 1500},
}

# Per-category engagement thresholds (PRD §7.5, spec §7 + §8). Consumed by the
# per-source extractor before the LLM call — a comment must clear its source's
# threshold for the run's category to enter the quote pool. Unknown categories
# fall back to "other". Per-run tuning is a v1.1 candidate (PRD §15).
ENGAGEMENT_FILTERS = {
    "consumer-app": {"youtube": 50, "appstore": 6},
    "mobile-game":  {"youtube": 30, "appstore": 4},
    "creator-tool": {"youtube": 25, "appstore": 3},
    "productivity": {"youtube": 50, "appstore": 6},
    "b2b-saas":     {"youtube": 10, "appstore": 2},
    "devtools":     {"youtube": 10, "appstore": 2},
    "enterprise":   {"youtube": 10, "appstore": 2},
    "other":        {"youtube": 50, "appstore": 6},
}


def engagement_threshold(source: str, category: str) -> int:
    """Return min likes / vote_count for *source* under *category*.

    Falls back to the ``other`` row when the category isn't in the table — the
    pre-flight classifier may emit free-form categories, and a missing entry
    should not crash the pipeline.
    """
    bucket = ENGAGEMENT_FILTERS.get(category, ENGAGEMENT_FILTERS["other"])
    return bucket[source]