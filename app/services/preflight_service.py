"""Pre-flight orchestration.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §7.

Pipeline:
    generate_queries(idea)           # LLM call: queries + signal strength
    → iTunes Search + YouTube search.list (one call per query, deduped, cap 30 each)
    → rank_candidates(idea, apps, videos)   # LLM call: top 5 each
    → PreflightResult(category, signal_strength, signal_reasoning, candidates)

Both LLM calls route through `app.llm.router.resolve` (PRD §10.1).
"""
from __future__ import annotations

import logging

from app.clients.appstore import itunes_search
from app.clients.youtube import search_videos
from app.llm.preflight import generate_queries, rank_candidates
from app.schemas.runs import Competitor, PreflightResult

logger = logging.getLogger(__name__)

# Spec §7.5 + prototype spec §9: cap each source's raw pool before ranking.
# Keeps the ranker prompt bounded and the iTunes/YouTube quota predictable.
_RAW_CANDIDATE_CAP = 30


def _dedupe_apps(apps: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for a in apps:
        key = a.get("bundle_id") or a.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _dedupe_videos(videos: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for v in videos:
        key = v.get("video_id")
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _to_competitors(ranked: dict) -> list[Competitor]:
    candidates: list[Competitor] = []
    for a in ranked.get("apps", []):
        bundle_id = a.get("bundle_id")
        url = a.get("url")
        name = a.get("name")
        if not (bundle_id and url and name):
            continue
        candidates.append(Competitor(
            source="appstore",
            url=url,
            name=name,
            identifier=bundle_id,
        ))
    for v in ranked.get("videos", []):
        video_id = v.get("video_id")
        url = v.get("url")
        title = v.get("title")
        if not (video_id and url and title):
            continue
        candidates.append(Competitor(
            source="youtube",
            url=url,
            name=title,
            identifier=video_id,
        ))
    return candidates


def run(idea: str) -> PreflightResult:
    """Run pre-flight for one idea end-to-end. Synchronous; ≤10s budget (spec §6)."""
    queries = generate_queries(idea)

    raw_apps: list[dict] = []
    for q in queries.appstore:
        raw_apps.extend(itunes_search(q))
    raw_apps = _dedupe_apps(raw_apps)[:_RAW_CANDIDATE_CAP]

    raw_videos: list[dict] = []
    for q in queries.youtube:
        raw_videos.extend(search_videos(q))
    raw_videos = _dedupe_videos(raw_videos)[:_RAW_CANDIDATE_CAP]

    ranked = rank_candidates(idea, raw_apps, raw_videos)
    candidates = _to_competitors(ranked)

    logger.info(
        "preflight idea=%r signal=%s raw_apps=%d raw_videos=%d candidates=%d",
        idea, queries.signal_strength, len(raw_apps), len(raw_videos), len(candidates),
    )

    return PreflightResult(
        category=queries.category,
        signal_strength=queries.signal_strength,
        signal_reasoning=queries.signal_reasoning,
        candidates=candidates,
    )
