APP_REVIEW_PAGES = 10
GAME_CATEGORY_ID = 20
SCIENCE_TECH_ID = 28
HOW_TO_STYLE_ID = 26

YOUTUBE_COMMENTS_AMOUNT = 100
YOUTUBE_VIDEO_AMOUNT = 5

APPLE_GAMES_GENRE_ID = 6014
APPLE_SOCIAL_GENRE_ID = 6005
APPLE_UTILITIES_GENRE_ID = 6002

# Partial-completion threshold (slice 2 §5.1, US-S3, issue #60). A run survives
# as `done` (with a partial_sources banner) only when at least this fraction of
# its sources succeed; below it the run is `failed` with
# failure_reason=sources_below_threshold. In config, not hardcoded in the
# pipeline (issue #60 acceptance criterion).
PARTIAL_SOURCE_THRESHOLD = 0.70

# Low-signal acknowledgement threshold (slice 3 §6, US-S1 fold-in, issue #69,
# Open Question 4). Re-keys the approve-time gate off the *observed* pre-flight
# candidate count instead of the LLM-guessed `signal_strength`. One evidence
# axis: 0 candidates → US-S1 no-sources state; 1..threshold-1 → low-signal
# acknowledgement required to approve; >= threshold → proceed freely. Hardcoded
# in config (proposed 4; the pre-flight validation per-idea floor was 15/15, so 4
# flags genuinely thin runs without false-flagging healthy ones).
LOW_SIGNAL_CANDIDATE_THRESHOLD = 4

# Per-source retry policy (slice 2 §5.1, PRD §8: "one retry with exponential
# backoff"). A source is attempted SOURCE_RETRY_ATTEMPTS times total; the wait
# before retry N (0-indexed) is SOURCE_RETRY_BACKOFF_BASE_SECONDS * 2**N. A
# source that exhausts its attempts is recorded as failed, not raised.
SOURCE_RETRY_ATTEMPTS = 2
SOURCE_RETRY_BACKOFF_BASE_SECONDS = 0.5

# Model routing for v2 pipeline (PRD §10.1, spec §9). Every LLM call in slice 1
# goes through app/llm/router.py::resolve(stage); v1 ships gpt-4o for every stage.
MODEL_ROUTING = {
    "preflight_classify": {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 1500},
    "preflight_rank":     {"model": "gpt-4o", "temperature": 0.2, "max_tokens": 2000},
    "per_source_extract": {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 4000},
    "synthesis":          {"model": "gpt-4o", "temperature": 0.3, "max_tokens": 6000},
}

# Retry-After hint (seconds) returned with 429 busy by
# run_pipeline_service.check_not_busy — the concurrency guard has no window to
# expire, so it's a fixed polite back-off matched to the frontend's 5s status
# poll cadence (spec §9 New Run 429 handling).
BUSY_RETRY_AFTER_SECONDS = 60

# Per-category engagement thresholds (PRD §7.5, spec §7 + §8). Consumed by the
# per-source extractor before the LLM call — a comment must clear its source's
# threshold for the run's category to enter the quote pool. Unknown categories
# fall back to "other". Per-run tuning is a v1.1 candidate (PRD §15).
ENGAGEMENT_FILTERS = {
    "consumer-app": {"youtube": 10, "appstore": 6},
    "mobile-game":  {"youtube": 10, "appstore": 4},
    "creator-tool": {"youtube": 10, "appstore": 3},
    "productivity": {"youtube": 10, "appstore": 6},
    "b2b-saas":     {"youtube": 10, "appstore": 2},
    "devtools":     {"youtube": 10, "appstore": 2},
    "enterprise":   {"youtube": 10, "appstore": 2},
    "other":        {"youtube": 10, "appstore": 6},
}


def engagement_threshold(source: str, category: str) -> int:
    """Return min likes / vote_count for *source* under *category*.

    Falls back to the ``other`` row when the category isn't in the table — the
    pre-flight classifier may emit free-form categories, and a missing entry
    should not crash the pipeline.
    """
    bucket = ENGAGEMENT_FILTERS.get(category, ENGAGEMENT_FILTERS["other"])
    return bucket[source]