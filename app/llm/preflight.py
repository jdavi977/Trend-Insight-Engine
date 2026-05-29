"""LLM calls for the pre-flight stage.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §7 / PRD §10.1.

Two stages, both routed through `app.llm.router.resolve`:
- `generate_queries(idea)`  — `preflight_classify`: 2-3 App Store + 2-3 YouTube
  search queries, plus a category guess and signal-strength assessment.
- `rank_candidates(idea, apps, videos)` — `preflight_rank`: pick the top 5 apps
  and top 5 videos a builder should study.

Productionised from the validated prototype at
`planning/prototypes/preflight/run_preflight.py`.
"""
from __future__ import annotations

import json

from app.clients.openai import get_openai_client
from app.config.promptTemplates import (
    PREFLIGHT_GENERATE_QUERIES_SYSTEM,
    PREFLIGHT_RANK_SYSTEM,
)
from app.llm.router import resolve


def generate_queries(idea: str) -> dict:
    """Return ``{appstore, youtube, category, signal_strength, signal_reasoning}``."""
    cfg = resolve("preflight_classify")
    client = get_openai_client()
    response = client.chat.completions.create(
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PREFLIGHT_GENERATE_QUERIES_SYSTEM},
            {"role": "user", "content": f"Idea: {idea}"},
        ],
    )
    return json.loads(response.choices[0].message.content)


def rank_candidates(idea: str, apps: list[dict], videos: list[dict]) -> dict:
    """Pick top-5 apps + top-5 videos from raw candidate pools.

    Returned shape: ``{"apps": [{bundle_id, name, justification, url}, ...],
    "videos": [{video_id, title, justification, url}, ...]}``.

    URLs are resolved server-side from the raw candidate dicts, not echoed by
    the LLM, so a hallucinated identifier surfaces as an empty URL rather than
    a fake link.
    """
    apps_brief = [
        {
            "bundle_id": a["bundle_id"],
            "name": a["name"],
            "genre": a["genre"],
            "description": a["description"],
            "rating_count": a["rating_count"],
        }
        for a in apps
    ]
    videos_brief = [
        {"video_id": v["video_id"], "title": v["title"], "channel": v["channel"]}
        for v in videos
    ]

    cfg = resolve("preflight_rank")
    client = get_openai_client()
    response = client.chat.completions.create(
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PREFLIGHT_RANK_SYSTEM},
            {
                "role": "user",
                "content": json.dumps({
                    "idea": idea,
                    "candidate_apps": apps_brief,
                    "candidate_videos": videos_brief,
                }),
            },
        ],
    )
    ranked = json.loads(response.choices[0].message.content)

    app_url_by_id = {a["bundle_id"]: a["url"] for a in apps if a["bundle_id"]}
    video_url_by_id = {v["video_id"]: v["url"] for v in videos}
    for a in ranked.get("apps", []):
        a["url"] = app_url_by_id.get(a.get("bundle_id"), "")
    for v in ranked.get("videos", []):
        v["url"] = video_url_by_id.get(v.get("video_id"), "")
    return ranked
