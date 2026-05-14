from app.jobs.automaticPipeline import run_automatic_pipeline, SourceAdapter
from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.config.genres import GenreConfig
from app.ingestion.youtubeComments import getYoutubeComments
from app.preprocessing.reviewPipeline import clean
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.clients.supabase import (
    check_youtube_id,
    delete_youtube_id,
    update_automatic_trend,
)
from app.config.secrets import RAG_WRITE_ENABLED
from app.rag.rag import embed_and_store


def _youtube_clean(raw: list, _keywords: list) -> list:
    rows = [{**item, "Content": item["Text"]} for item in raw]
    return clean(rows, **YOUTUBE_PREPROCESS)


def _youtube_post_extract(result, item):
    result.title = item.get("Title")
    if RAG_WRITE_ENABLED:
        source_url = f"https://www.youtube.com/watch?v={item['Id']}"
        embed_and_store(result, source_url)


def youtube_automatic(ids: list[dict], category: int, genre: GenreConfig, keywords: list) -> list[dict]:
    def _build_prompt(item: dict) -> str:
        return build_youtube_prompt(genre)

    adapter = SourceAdapter(
        item_id=lambda item: item["Id"],
        check_existing=check_youtube_id,
        delete_existing=delete_youtube_id,
        helpful=lambda item: getYoutubeComments(item["Id"], "relevance", item["Title"]),
        time=lambda item: getYoutubeComments(item["Id"], "time", item["Title"]),
        clean=_youtube_clean,
        system_prompt=_build_prompt,
        output_prompt=youtubePromptOutput,
        source="youtube",
        build_row=lambda item, problem, today, data: {
            "key": item["Id"],
            "thumbnail": item["Thumbnail"],
            "date": today,
            "category": category,
            "title": data.title,
            "problems": {
                "problem": problem.problem,
                "type": problem.type,
                "total_likes": problem.total_likes,
                "severity": problem.severity,
                "frequency": problem.frequency,
            },
        },
        persist_row=update_automatic_trend,
        post_extract=_youtube_post_extract,
    )
    return run_automatic_pipeline(ids, keywords, adapter)
