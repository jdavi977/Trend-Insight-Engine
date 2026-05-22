"""Pre-flight prototype — tracer bullet for v2.1 pre-flight pipeline.

One idea, end-to-end, real APIs (OpenAI + iTunes Search + YouTube Data).
Throwaway research code. See planning/specs/preflight-prototype_spec.md.

Run from project root:
    python -m planning.prototypes.preflight.run_preflight
"""
import csv
import json
import sys
import time
from pathlib import Path

import requests
from googleapiclient.discovery import build

# Allow direct execution: add project root to sys.path so app.* imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.clients.openai import get_openai_client  # noqa: E402
from app.config.secrets import keyChecker  # noqa: E402

YOUTUBE_API = keyChecker("YOUTUBE_API")
_MODEL = "gpt-4o"

IDEAS = [
    {"id": 1, "text": "note-taking app with better offline sync"},
    {"id": 2, "text": "habit tracker that uses streaks"},
    {"id": 3, "text": "podcast player with better chapter navigation"},
    {"id": 4, "text": "meditation app for sleep"},
    {"id": 5, "text": "expense tracker for freelancers"},
    {"id": 6, "text": "2.5d vampire survivors-like game"},
    {"id": 7, "text": "roguelike deckbuilder"},
    {"id": 8, "text": "city-builder with realistic logistics"},
    {"id": 9, "text": "productivity app"},
    {"id": 10, "text": "fitness app"},
    {"id": 11, "text": "note-taking app for ADHD users with spaced repetition"},
    {"id": 12, "text": "video editor for short-form creators"},
    {"id": 13, "text": "Slack alternative for solo developers"},
    {"id": 14, "text": "tool for prompt engineers to manage prompts"},
    {"id": 15, "text": "AI companion app for processing dreams"},
]

OUTPUT_DIR = Path(__file__).parent
RESULTS_CSV = OUTPUT_DIR / "results.csv"
QUERIES_CSV = OUTPUT_DIR / "queries.csv"

_GENERATE_QUERIES_SYSTEM = """You help a builder de-risk a product idea by finding competitors.

Given a product idea, produce App Store and YouTube search queries that will surface
real competitor apps and discussion videos, and grade the idea's signal strength.

Signal-strength rubric:
- "high": established consumer category with many existing apps and discussion videos
  (e.g. note-taking, habit tracking, meditation, podcast players).
- "medium": category exists but a qualifier or audience is hard to search
  (e.g. visual-style qualifiers like "2.5D", or niche audience modifiers).
- "low": B2B/devtools/novel categories where the App Store + YouTube are unlikely
  to return useful competitors (e.g. "Slack alternative for solo devs",
  "tool for prompt engineers", brand-new categories with no incumbents).

Return JSON with this exact schema:
{
  "appstore": [string, ...],   // 2-3 App Store search queries
  "youtube":  [string, ...],   // 2-3 YouTube search queries
  "category": string,           // best-guess product category
  "signal_strength": "high" | "medium" | "low",
  "signal_reasoning": string    // 1-sentence justification
}
"""

_RANK_SYSTEM = """You help a builder pick competitors and discussion videos for a product idea.

From the raw candidate lists, pick the top 5 apps and top 5 videos a builder would
actually study. Choose using only the data provided — do not invent identifiers.

Apps: prefer real competitors in the right category with meaningful rating counts.
Videos: prefer review / "best X" / "X vs Y" / discussion-style titles whose comments
are likely to contain user pain. Avoid pure gameplay let's-plays.

Return JSON with this exact schema:
{
  "apps":   [{"bundle_id": str, "name": str, "justification": str}, ... 5 items],
  "videos": [{"video_id": str, "title": str, "justification": str}, ... 5 items]
}

`justification` is one short sentence on why a builder should look at this candidate.
"""


def generate_queries(idea: str) -> dict:
    """LLM call #1: search queries + signal-strength assessment."""
    client = get_openai_client()
    response = client.chat.completions.create(
        model=_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _GENERATE_QUERIES_SYSTEM},
            {"role": "user", "content": f"Idea: {idea}"},
        ],
    )
    return json.loads(response.choices[0].message.content)


def itunes_search(query: str, limit: int = 10) -> list[dict]:
    """iTunes Search API. Thin function — not yet productionized into app/clients/."""
    response = requests.get(
        "https://itunes.apple.com/search",
        params={
            "term": query,
            "entity": "software",
            "limit": limit,
            "country": "us",
        },
        timeout=10,
    )
    results = response.json().get("results", [])
    apps = [
        {
            "bundle_id": item.get("bundleId"),
            "name": item.get("trackName"),
            "genre": item.get("primaryGenreName"),
            "description": (item.get("description") or "")[:300],
            "rating_count": item.get("userRatingCount"),
            "url": item.get("trackViewUrl"),
        }
        for item in results
    ]
    time.sleep(0.5)  # iTunes is rate-limited (~20/min, undocumented) — spec §9.
    return apps


def youtube_search(query: str, max_results: int = 10) -> list[dict]:
    """YouTube Data API search.list. ~100 quota units per call."""
    service = build("youtube", "v3", developerKey=YOUTUBE_API)
    try:
        response = service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
        ).execute()
    finally:
        service.close()

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        videos.append({
            "video_id": video_id,
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "description": (snippet.get("description") or "")[:200],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return videos


def rank_candidates(idea: str, apps: list[dict], videos: list[dict]) -> dict:
    """LLM call #2: pick top 5 apps + top 5 videos with one-line justifications."""
    # Spec §10 Q2: rank prompt sees name + genre + short description + rating count.
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
        {
            "video_id": v["video_id"],
            "title": v["title"],
            "channel": v["channel"],
        }
        for v in videos
    ]

    client = get_openai_client()
    response = client.chat.completions.create(
        model=_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _RANK_SYSTEM},
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

    # Resolve URLs from raw data so we don't trust LLM-echoed strings.
    app_url_by_id = {a["bundle_id"]: a["url"] for a in apps if a["bundle_id"]}
    video_url_by_id = {v["video_id"]: v["url"] for v in videos}
    for a in ranked.get("apps", []):
        a["url"] = app_url_by_id.get(a.get("bundle_id"), "")
    for v in ranked.get("videos", []):
        v["url"] = video_url_by_id.get(v.get("video_id"), "")
    return ranked


def _dedupe_apps(apps: list[dict]) -> list[dict]:
    seen, out = set(), []
    for a in apps:
        key = a.get("bundle_id") or a.get("name")
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _dedupe_videos(videos: list[dict]) -> list[dict]:
    seen, out = set(), []
    for v in videos:
        key = v.get("video_id")
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def preflight(idea: str) -> dict:
    queries = generate_queries(idea)
    raw_apps = _dedupe_apps([
        a for q in queries["appstore"] for a in itunes_search(q)
    ])
    raw_videos = _dedupe_videos([
        v for q in queries["youtube"] for v in youtube_search(q)
    ])
    # Spec §9: cap raw candidates at ~30 per source before passing to the ranker.
    ranked = rank_candidates(idea, raw_apps[:30], raw_videos[:30])
    return {
        **queries,
        **ranked,
        "raw_app_count": len(raw_apps),
        "raw_video_count": len(raw_videos),
    }


def main() -> None:
    results_rows, queries_rows = [], []

    for idea_obj in IDEAS:
        idea_id, idea = idea_obj["id"], idea_obj["text"]
        print(f"[{idea_id}] {idea}")
        result = preflight(idea)
        print(
            f"  signal: {result['signal_strength']} | "
            f"raw apps: {result['raw_app_count']} | "
            f"raw videos: {result['raw_video_count']}"
        )

        query_common = {
            "idea_id": idea_id,
            "idea": idea,
            "category": result["category"],
            "signal_strength": result["signal_strength"],
            "signal_reasoning": result["signal_reasoning"],
        }
        for q in result["appstore"]:
            queries_rows.append({**query_common, "query_kind": "appstore", "query": q})
        for q in result["youtube"]:
            queries_rows.append({**query_common, "query_kind": "youtube", "query": q})

        common = {
            "idea_id": idea_id,
            "idea": idea,
            "category": result["category"],
            "signal_strength": result["signal_strength"],
            "signal_reasoning": result["signal_reasoning"],
        }
        for a in result["apps"]:
            results_rows.append({
                **common,
                "candidate_kind": "app",
                "name": a.get("name", ""),
                "identifier": a.get("bundle_id", ""),
                "url": a.get("url", ""),
                "llm_justification": a.get("justification", ""),
                "useful_y_n": "",
                "notes": "",
            })
        for v in result["videos"]:
            results_rows.append({
                **common,
                "candidate_kind": "video",
                "name": v.get("title", ""),
                "identifier": v.get("video_id", ""),
                "url": v.get("url", ""),
                "llm_justification": v.get("justification", ""),
                "useful_y_n": "",
                "notes": "",
            })

    with RESULTS_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "idea_id", "idea", "category", "signal_strength", "signal_reasoning",
            "candidate_kind", "name", "identifier", "url", "llm_justification",
            "useful_y_n", "notes",
        ])
        writer.writeheader()
        writer.writerows(results_rows)

    with QUERIES_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "idea_id", "idea", "category", "signal_strength", "signal_reasoning",
            "query_kind", "query",
        ])
        writer.writeheader()
        writer.writerows(queries_rows)

    print(f"\nWrote {len(results_rows)} candidate rows to {RESULTS_CSV}")
    print(f"Wrote {len(queries_rows)} query rows to {QUERIES_CSV}")


if __name__ == "__main__":
    main()
