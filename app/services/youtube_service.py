from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.reviewPipeline import clean
from app.llm.extractInsights import extract_insights
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.config.genres import get_default_genre
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, enrich_problems
from app.clients.youtube import get_video_metadata
from app.schemas.api import YoutubeAnalysisResponse


def youtube_manual(link: str):
    default = get_default_genre("youtube")
    id = getVideoId(link)

    meta = {}
    if RAG_READ_ENABLED or RAG_WRITE_ENABLED:
        meta = get_video_metadata(id)

    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    rows = [{**item, "Content": item["Text"]} for item in all_items]
    cleaned_data = clean(rows, **YOUTUBE_PREPROCESS)
    result = extract_insights(cleaned_data, build_youtube_prompt(default, []), youtubePromptOutput, source="youtube")
    if result is None:
        return None
    if RAG_READ_ENABLED:
        enrich_problems(result)
    if RAG_WRITE_ENABLED:
        result.title = meta.get("title")
        embed_and_store(result, link)
    return YoutubeAnalysisResponse(
        **result.model_dump(),
        channel_name=meta.get("channel_name"),
        published_at=meta.get("published_at"),
        view_count=meta.get("view_count"),
        like_count=meta.get("like_count"),
        comment_count=meta.get("comment_count"),
        subscriber_count=meta.get("subscriber_count"),
        duration=meta.get("duration"),
    )
