from app.jobs.automaticPipeline import run_automatic_pipeline, SourceAdapter
from app.config.genres import GenreConfig
from app.ingestion.appStoreReviews import getAppReviews
from app.preprocessing.reviewPipeline import clean
from app.config.preprocessing import APPSTORE_PREPROCESS
from app.config.promptTemplates import build_appstore_prompt, appStorePromptOutput
from app.config.constants import APP_REVIEW_PAGES, APPLE_COUNTRY
from app.clients.supabase import (
    update_automatic_apple_trend,
    check_appstore_id,
    delete_appstore_id,
)
from app.config.secrets import RAG_WRITE_ENABLED
from app.rag.rag import embed_and_store


def _appstore_clean(raw: list, keywords: list) -> list:
    rows = [{**item, "Content": item["content"]} for item in raw]
    kw = tuple(keywords) if keywords else None
    return clean(rows, **{**APPSTORE_PREPROCESS, "keyword_filter": kw})


def _appstore_post_extract(result, item):
    result.title = item.get("Title")
    if RAG_WRITE_ENABLED:
        source_url = f"https://apps.apple.com/app/id{item['Id']}"
        embed_and_store(result, source_url)


def appstore_automatic(apps: list[dict], genre_id: int, genre: GenreConfig, keywords: list) -> list[dict]:
    def _build_prompt(item: dict) -> str:
        return build_appstore_prompt(genre)

    adapter = SourceAdapter(
        item_id=lambda item: int(item["Id"]),
        check_existing=check_appstore_id,
        delete_existing=delete_appstore_id,
        helpful=lambda item: getAppReviews(item["Id"], "mostHelpful", APP_REVIEW_PAGES),
        time=lambda item: getAppReviews(item["Id"], "mostRecent", APP_REVIEW_PAGES),
        clean=_appstore_clean,
        system_prompt=_build_prompt,
        output_prompt=appStorePromptOutput,
        source="app_store",
        build_row=lambda item, problem, today, data: {
            "app_id": int(item["Id"]),
            "title": item["Title"],
            "country": APPLE_COUNTRY,
            "genre_id": genre_id,
            "date": today,
            "thumbnail": item["Thumbnail"],
            "problems": {
                "problem": problem.problem,
                "type": problem.type,
                "average_rating": problem.average_rating,
                "vote_count": problem.vote_count,
                "severity": problem.severity,
                "frequency": problem.frequency,
                "example_reviews": problem.example_reviews,
            },
        },
        persist_row=update_automatic_apple_trend,
        post_extract=_appstore_post_extract,
    )
    return run_automatic_pipeline(apps, keywords, adapter)
