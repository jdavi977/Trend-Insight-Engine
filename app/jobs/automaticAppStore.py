from app.jobs.automaticPipeline import run_automatic_pipeline, SourceAdapter
from app.ingestion.appStoreReviews import getAppReviews
from app.preprocessing.reviewPipeline import appstore_rows_for_llm
from app.config.promptTemplates import appStorePromptOutput
from app.config.constants import APP_REVIEW_PAGES, APPLE_COUNTRY
from app.clients.supabase import (
    update_automatic_apple_trend,
    update_automatic_app_date,
    check_appstore_id,
)


def _appstore_clean(raw: list, keywords: list) -> list:
    return appstore_rows_for_llm(raw, keywords)


def appstore_automatic(apps: list[dict], genre_id: int, genre_prompt: str, keywords: list) -> list[dict]:
    adapter = SourceAdapter(
        item_id=lambda item: int(item["Id"]),
        check_existing=check_appstore_id,
        bump_date=update_automatic_app_date,
        ingest=lambda item: getAppReviews(item["Id"], "mostrecent", APP_REVIEW_PAGES),
        clean=_appstore_clean,
        system_prompt=genre_prompt,
        output_prompt=appStorePromptOutput,
        build_row=lambda item, problem, today, data: {
            "app_id": int(item["Id"]),
            "app_title": item["Title"],
            "country": APPLE_COUNTRY,
            "genre_id": genre_id,
            "date": today,
            "thumbnail": item["Thumbnail"],
            "problems": {
                "problem": problem["problem"],
                "type": problem["type"],
                "average_rating": problem["average_rating"],
                "severity": problem["severity"],
                "frequency": problem["frequency"],
                "example_reviews": problem["example_reviews"],
            },
        },
        persist_row=update_automatic_apple_trend,
    )
    return run_automatic_pipeline(apps, keywords, adapter)
