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
from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.ingestion.youtubeComments import getMostPopularVideos, getYoutubeComments
from app.llm.extractInsights import extract_insights
from app.preprocessing.reviewPipeline import clean

_GAMES_GENRE = next(g for g in YOUTUBE_GENRES if g.name == "Games")


def run_video(video):
    print(f"\n--- {video['Id']} | {video['Title']} ---")
    print(f"thumbnail: {video.get('Thumbnail')}")

    relevance = getYoutubeComments(video["Id"], "relevance", video["Title"])
    print(f"fetched comments: {len(relevance)}")

    rows = [{**item, "Content": item["Text"]} for item in relevance]
    cleaned = clean(rows, **YOUTUBE_PREPROCESS)
    print(f"after clean: {len(cleaned)}")

    if not cleaned:
        print("skip: no comments survived cleaning")
        return None

    result = extract_insights(cleaned, build_youtube_prompt(_GAMES_GENRE), youtubePromptOutput)

    if result is None:
        print("skip: LLM returned no usable problems")
        return None

    payload = result.model_dump()
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
