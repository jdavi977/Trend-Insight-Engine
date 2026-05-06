"""Unified review preprocessing pipeline.

Both YouTube comments and App Store reviews flow through the same cleaning
stages; callers supply source-specific config via keyword arguments.

Callers are expected to present rows with a ``Content`` key already set
(mapping their source's raw text field to ``Content`` before calling).
Use :func:`appstore_rows_for_llm` for App Store ingestion dicts (``content``,
``vote_count``) destined for the LLM; it maps to legacy ``Votes`` / ``Content``
records after :func:`clean`.
"""
from __future__ import annotations

import re
from typing import Optional

from app.config.preprocessing import APPSTORE_PREPROCESS
from app.config.regex import EMOJI_REGEX


def clean(
    rows: list[dict],
    *,
    engagement_field: str,
    threshold: int | float,
    keyword_filter: Optional[tuple[str, ...]] = None,
) -> list[dict]:
    """Clean and filter a list of raw comment/review dicts.

    Pipeline stages (in order):

    1. **Engagement-threshold filter** — keep rows where
       ``row[engagement_field] >= threshold``.  A missing or unparseable
       field is treated as 0 and therefore dropped.

       Threshold semantics across the two call sites:

       - YouTube: ``likes >= 50``
         → pass ``threshold=50``.
       - App Store: legacy rule was ``vote_count > 5``; use ``threshold=6``
         (equivalent for integer counts with ``>=``).

       Integer vote counts make ``>= 6`` losslessly equivalent to ``> 5``.
       The unified rule ``>= threshold`` is cleaner: callers choose the
       threshold and the inequality is always "at least N".

    2. **Lowercase + strip** ``Content``.
    3. **Emoji strip**.
    4. **Optional keyword filter** — keep a row if *any* keyword in
       ``keyword_filter`` matches on a word boundary (``\\b``).  Breaks on
       first match so each passing row is appended at most once.  This fixes
       the N-copies bug in ``textCleaning.keyword_filtering``, which
       iterated all keywords and appended the row once per match.
       Pass ``keyword_filter=None`` to skip this stage (YouTube path).
    5. **Dedup** by ``Content`` (last-seen wins, insertion order preserved).

    Args:
        rows: Dicts from ingestion.  Each must contain an ``engagement_field``
            key and a ``Content`` key (callers are responsible for mapping their
            source's raw text field to ``Content`` before calling).
        engagement_field: Key to read for the engagement score
            (e.g. ``"Likes"`` for YouTube, ``"vote_count"`` for App Store).
        threshold: Minimum engagement score (inclusive) to keep a row.
        keyword_filter: Optional tuple of keyword strings.  Only rows matching
            at least one keyword (word-boundary regex) are kept.
            ``None`` disables filtering entirely.

    Returns:
        Cleaned, filtered, deduplicated list of dicts with normalised
        ``Content``.
    """
    after_threshold = _filter_engagement(rows, engagement_field, threshold)
    normalised = _normalise_content(after_threshold)
    after_emoji = _strip_emojis(normalised)
    after_keywords = _apply_keyword_filter(after_emoji, keyword_filter)
    return _dedup(after_keywords)


def appstore_rows_for_llm(
    raw: list[dict],
    keywords: list[str] | tuple[str, ...],
) -> list[dict]:
    """Run :func:`clean` on App Store review dicts and shape rows for the LLM.

    Ingestion uses lowercase ``content`` / ``vote_count``; prompts expect
    ``Content`` and ``Votes`` (shape expected by App Store prompts).
    """
    rows = [{**item, "Content": item["content"]} for item in raw]
    kw = tuple(keywords) if keywords else None
    cleaned = clean(
        rows,
        engagement_field=APPSTORE_PREPROCESS["engagement_field"],
        threshold=APPSTORE_PREPROCESS["threshold"],
        keyword_filter=kw,
    )
    return [{"Votes": r.get("vote_count", 0), "Content": r["Content"]} for r in cleaned]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _filter_engagement(
    rows: list[dict], field: str, threshold: int | float
) -> list[dict]:
    kept = []
    for row in rows:
        try:
            score = float(row.get(field, 0) or 0)
        except (ValueError, TypeError):
            score = 0.0
        if score >= threshold:
            kept.append(row)
    return kept


def _normalise_content(rows: list[dict]) -> list[dict]:
    return [{**row, "Content": row["Content"].lower().strip()} for row in rows]


def _strip_emojis(rows: list[dict]) -> list[dict]:
    return [{**row, "Content": EMOJI_REGEX.sub("", row["Content"])} for row in rows]


def _apply_keyword_filter(
    rows: list[dict], keywords: Optional[tuple[str, ...]]
) -> list[dict]:
    if not keywords:
        return rows
    kept = []
    for row in rows:
        for keyword in keywords:
            pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
            if pattern.search(row["Content"]):
                kept.append(row)
                break  # first match — row added at most once
    return kept


def _dedup(rows: list[dict]) -> list[dict]:
    return list({row["Content"]: row for row in rows}.values())
