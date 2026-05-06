"""Source-specific preprocessing configs for ``reviewPipeline.clean``.

Usage::

    from app.config.preprocessing import YOUTUBE_PREPROCESS, APPSTORE_PREPROCESS
    from app.preprocessing.reviewPipeline import clean

    result = clean(rows, **YOUTUBE_PREPROCESS)
    result = clean(rows, **APPSTORE_PREPROCESS)

Each dict carries exactly the keyword arguments accepted by ``clean()``.
"""
from __future__ import annotations

from app.config.keywords import APPLE_KEYWORDS

YOUTUBE_PREPROCESS: dict = {
    "engagement_field": "Likes",
    "threshold": 50,
    "keyword_filter": None,
}

APPSTORE_PREPROCESS: dict = {
    "engagement_field": "vote_count",
    # App Store legacy threshold was ``vote_count > 5``; ``>= 6`` is
    # losslessly equivalent for integer vote counts and keeps the unified
    # ``>= threshold`` rule consistent across sources.
    "threshold": 6,
    "keyword_filter": APPLE_KEYWORDS,
}
