"""Dry-run pipeline test for the Games category.

Fetches 5 most-popular game videos, runs comments through clean → LLM →
validate, and prints results. Does NOT persist to Supabase.

Run with: python -m ops.scripts.testGameYoutube
"""

import json
import sys
import traceback

from app.config.genres import YOUTUBE_GENRES
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.ingestion.youtubeComments import getMostPopularVideos, getYoutubeComments
from app.llm.extractInsights import extractInsights
from app.llm.validateOutput import validateOutput
from app.preprocessing.commentClean import loadAndClean

_GAMES_GENRE = next(g for g in YOUTUBE_GENRES if g.name == "Games")


def run_video(video):
    print(f"\n--- {video['Id']} | {video['Title']} ---")
    print(f"thumbnail: {video.get('Thumbnail')}")

    relevance = getYoutubeComments(video["Id"], "relevance", video["Title"])
    print(f"fetched comments: {len(relevance)}")

    cleaned = loadAndClean(relevance, _GAMES_GENRE.keywords)
    print(f"after clean: {len(cleaned)}")

    if not cleaned:
        print("skip: no comments survived cleaning")
        return None

    raw = extractInsights(cleaned, build_youtube_prompt(_GAMES_GENRE), youtubePromptOutput)

    try:
        validated = validateOutput(raw)
    except Exception as exc:
        print(f"validateOutput failed: {exc!r}")
        print("raw LLM output:")
        print(raw)
        return None

    if hasattr(validated, "model_dump"):
        payload = validated.model_dump()
    else:
        payload = dict(validated)

    payload["thumbnail"] = video.get("Thumbnail")

    print(json.dumps(payload, indent=2, default=str))
    return payload


def main():
    print(f"=== DRY RUN: Games category ({_GAMES_GENRE.id}) ===")
    videos = getMostPopularVideos(_GAMES_GENRE.id)
    print(f"videos fetched: {len(videos)}")

    ok = 0
    failed = 0
    for video in videos:
        try:
            result = run_video(video)
            if result is not None:
                ok += 1
        except Exception:
            traceback.print_exc()
            failed += 1

    print(f"\n=== done: {ok} ok / {failed} failed / {len(videos)} total ===")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
