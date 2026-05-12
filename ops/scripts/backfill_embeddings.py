"""Backfill embeddings for all existing rows in automatic_table and automatic_apple_table.

Idempotent: re-running produces no duplicate rows because embed_and_store uses
a deterministic upsert key (sha256 of source_url + problem_text).

Usage:
    RAG_WRITE_ENABLED=true python -m ops.scripts.backfill_embeddings
"""
from __future__ import annotations

import logging

from app.clients.supabase import supabase_client
from app.rag.rag import embed_and_store
from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _backfill_youtube() -> int:
    rows = supabase_client.table("automatic_table").select("*").execute().data or []
    count = 0
    for row in rows:
        try:
            problems_data = row.get("problems") or {}
            extraction = LLMExtraction(
                source="youtube",
                title=row.get("title"),
                problems=[
                    YoutubeProblemItem(
                        problem=problems_data["problem"],
                        type=problems_data["type"],
                        total_likes=problems_data.get("total_likes", 0),
                        severity=problems_data["severity"],
                        frequency=problems_data["frequency"],
                    )
                ],
            )
            source_url = f"https://www.youtube.com/watch?v={row['key']}"
            embed_and_store(extraction, source_url)
            count += 1
        except Exception:
            logger.exception("Failed to backfill YouTube row: %s", row.get("key"))
    return count


def _backfill_appstore() -> int:
    rows = supabase_client.table("automatic_apple_table").select("*").execute().data or []
    count = 0
    for row in rows:
        try:
            problems_data = row.get("problems") or {}
            extraction = LLMExtraction(
                source="app_store",
                title=row.get("app_title"),
                problems=[
                    AppStoreProblemItem(
                        problem=problems_data["problem"],
                        type=problems_data["type"],
                        average_rating=problems_data.get("average_rating", 0.0),
                        severity=problems_data["severity"],
                        frequency=problems_data["frequency"],
                        example_reviews=problems_data.get("example_reviews", [""]),
                    )
                ],
            )
            source_url = f"https://apps.apple.com/app/id{row['app_id']}"
            embed_and_store(extraction, source_url)
            count += 1
        except Exception:
            logger.exception("Failed to backfill App Store row: %s", row.get("app_id"))
    return count


def main() -> None:
    logger.info("Starting YouTube backfill...")
    yt_count = _backfill_youtube()
    logger.info("YouTube: %d rows processed", yt_count)

    logger.info("Starting App Store backfill...")
    as_count = _backfill_appstore()
    logger.info("App Store: %d rows processed", as_count)

    logger.info("Backfill complete. Total: %d rows", yt_count + as_count)


if __name__ == "__main__":
    main()
