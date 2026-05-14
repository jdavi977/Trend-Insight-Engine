"""Unified review preprocessing pipeline.

Both YouTube comments and App Store reviews flow through the same cleaning
stages; callers supply source-specific config via keyword arguments.

Callers are expected to present rows with a ``Content`` key already set
(mapping their source's raw text field to ``Content`` before calling).
"""
from __future__ import annotations

import re
from typing import Optional

from app.config.regex import EMOJI_REGEX


def clean(
    rows: list[dict],
    *,
    engagement_field: str,
    threshold: int | float,
    keyword_filter: Optional[tuple[str, ...]] = None,
    min_length: int = 20,
) -> list[dict]:
    patterns = (
        [re.compile(r"\b" + re.escape(kw) + r"\b") for kw in keyword_filter]
        if keyword_filter
        else None
    )

    seen: dict[str, dict] = {}
    for row in rows:
        # 1. Engagement filter
        try:
            score = float(row.get(engagement_field, 0) or 0)
        except (ValueError, TypeError):
            score = 0.0
        if score < threshold:
            continue

        # 2. Normalise
        content = EMOJI_REGEX.sub("", row["Content"].lower().strip())

        # 3. Min-length
        if len(content) < min_length:
            continue

        # 4. Keyword filter (pre-compiled patterns, short-circuit on first match)
        if patterns and not any(p.search(content) for p in patterns):
            continue

        # 5. Dedup — last-seen wins
        seen[content] = {**row, "Content": content}

    return list(seen.values())
