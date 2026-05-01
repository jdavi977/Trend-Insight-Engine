from app.ingestion.youtubeComments import getVideoId, getYoutubeComments
from app.preprocessing.commentClean import loadAndClean
from app.llm.extractInsights import extractInsights
from app.llm.validateOutput import validateOutput
from app.config.prompts import youtubeSystemPrompt, youtubePromptOutput
from app.config.keywords import YOUTUBE_KEYWORDS

def youtube_manual(link: str):
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    cleaned_data = loadAndClean(all_items, YOUTUBE_KEYWORDS)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    validated_data = validateOutput(insights)
    return validated_data

    