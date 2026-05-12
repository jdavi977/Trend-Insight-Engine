from app.config.preprocessing import YOUTUBE_PREPROCESS
from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.reviewPipeline import clean
from app.llm.extractInsights import extract_insights
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.config.genres import get_default_genre
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, retrieve_similar
from app.clients.youtube import get_video_title
from app.schemas.api import YoutubeAnalysisResponse


def youtube_manual(link: str):
    default = get_default_genre("youtube")
    id = getVideoId(link)

    prior_insights = []
    if RAG_READ_ENABLED:
        title = get_video_title(id)
        prior_insights = retrieve_similar(query=title)

    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    rows = [{**item, "Content": item["Text"]} for item in all_items]
    cleaned_data = clean(rows, **YOUTUBE_PREPROCESS)
    result = extract_insights(cleaned_data, build_youtube_prompt(default, prior_insights), youtubePromptOutput)
    if RAG_WRITE_ENABLED and result is not None:
        embed_and_store(result, link)
    if result is None:
        return None
    return YoutubeAnalysisResponse(**result.model_dump(), retrieved_context=prior_insights)
