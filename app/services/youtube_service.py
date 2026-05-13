from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.reviewPipeline import clean
from app.llm.extractInsights import extract_insights
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.config.genres import get_default_genre
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, retrieve_similar
from app.clients.youtube import get_video_metadata
from app.schemas.api import YoutubeAnalysisResponse


def youtube_manual(link: str):
    default = get_default_genre("youtube")
    id = getVideoId(link)

    meta = {}
    prior_insights = []
    if RAG_READ_ENABLED or RAG_WRITE_ENABLED:
        meta = get_video_metadata(id)
    if RAG_READ_ENABLED and meta.get("title"):
        prior_insights = retrieve_similar(query=meta["title"])

    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    rows = [{**item, "Content": item["Text"]} for item in all_items]
    cleaned_data = clean(rows, **YOUTUBE_PREPROCESS)
    result = extract_insights(cleaned_data, build_youtube_prompt(default, prior_insights), youtubePromptOutput, source="youtube")
    if RAG_WRITE_ENABLED and result is not None:
        result.title = meta.get("title")
        embed_and_store(result, link)
    if result is None:
        return None
    return YoutubeAnalysisResponse(
        **result.model_dump(),
        retrieved_context=prior_insights,
        channel_name=meta.get("channel_name"),
        published_at=meta.get("published_at"),
        view_count=meta.get("view_count"),
        like_count=meta.get("like_count"),
        comment_count=meta.get("comment_count"),
        subscriber_count=meta.get("subscriber_count"),
        duration=meta.get("duration"),
    )
