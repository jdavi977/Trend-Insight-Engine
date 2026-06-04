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

# Per-model OpenAI prices in USD per 1K tokens (slice 2 §6, issue #59, open
# question Q3). Hardcoded in config next to MODEL_ROUTING rather than read from
# an env/secret — prices churn slowly and a wrong number is a one-line edit. The
# OpenAI transport (app/clients/openai.py) is the single choke point that turns
# usage tokens into spend, so the daily-budget guard sees every stage's cost
# without each call site knowing about the budget. Unknown models fall back to
# DEFAULT_OPENAI_PRICE (conservative, non-zero) so a model swap can't silently
# zero out budget accounting.
OPENAI_PRICES = {
    "gpt-4o":                 {"input": 0.0025,  "output": 0.01},
    "gpt-4o-mini":            {"input": 0.00015, "output": 0.0006},
    "gpt-5-mini":             {"input": 0.00025, "output": 0.002},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}
DEFAULT_OPENAI_PRICE = {"input": 0.0025, "output": 0.01}


def openai_price(model: str) -> dict:
    """Return the {input, output} USD-per-1K-token prices for *model*.

    Falls back to ``DEFAULT_OPENAI_PRICE`` for an unlisted model so a per-stage
    model swap (MODEL_ROUTING is architecture-as-config) keeps counting spend
    instead of silently dropping it.
    """
    return OPENAI_PRICES.get(model, DEFAULT_OPENAI_PRICE)


# Per-IP rate-limit ceilings (PRD §8, US-S6, slice 2 §6). A client may start at
# most RATE_LIMIT_PER_HOUR runs in any rolling hour AND RATE_LIMIT_PER_DAY in
# any rolling day; the 4th/hour or 11th/day POST /runs returns 429 rate_limited.
# In config, not hardcoded in the guard (issue #59 acceptance criterion).
RATE_LIMIT_PER_HOUR = 3
RATE_LIMIT_PER_DAY = 10

# Retry-After hint (seconds) returned with 429 busy — the concurrency guard has
# no window to expire, so it's a fixed polite back-off matched to the frontend's
# 5s status poll cadence (spec §9 New Run 429 handling).
BUSY_RETRY_AFTER_SECONDS = 60

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