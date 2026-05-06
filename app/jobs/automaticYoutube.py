from app.jobs.automaticPipeline import run_automatic_pipeline, SourceAdapter
from app.ingestion.youtubeComments import getYoutubeComments
from app.preprocessing.commentClean import loadAndClean
from app.config.promptTemplates import youtubePromptOutput
from app.clients.supabase import (
    check_youtube_id,
    update_automatic_trend,
    update_automatic_video_date,
)


def youtube_automatic(ids: list[dict], category: int, categoryPrompt: str, keywords: list) -> list[dict]:
    adapter = SourceAdapter(
        item_id=lambda item: item["Id"],
        check_existing=check_youtube_id,
        bump_date=update_automatic_video_date,
        ingest=lambda item: getYoutubeComments(item["Id"], "relevance", item["Title"]),
        clean=loadAndClean,
        system_prompt=categoryPrompt,
        output_prompt=youtubePromptOutput,
        build_row=lambda item, problem, today, data: {
            "key": item["Id"],
            "thumbnail": item["Thumbnail"],
            "date": today,
            "category": category,
            "title": data["title"],
            "problems": {
                "problem": problem["problem"],
                "type": problem["type"],
                "total_likes": problem["total_likes"],
                "severity": problem["severity"],
                "frequency": problem["frequency"],
            },
        },
        persist_row=update_automatic_trend,
    )
    return run_automatic_pipeline(ids, keywords, adapter)
