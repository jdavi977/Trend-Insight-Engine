from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.commentClean import loadAndClean
from app.llm.extractInsights import extractInsights
from app.llm.validateOutput import validateOutput
from app.config.promptTemplates import build_youtube_prompt, youtubePromptOutput
from app.config.genres import get_default_genre


def youtube_manual(link: str):
    default = get_default_genre("youtube")
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    cleaned_data = loadAndClean(all_items, default.keywords)
    insights = extractInsights(cleaned_data, build_youtube_prompt(default), youtubePromptOutput)
    validated_data = validateOutput(insights)
    return validated_data
