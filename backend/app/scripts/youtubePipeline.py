from ingestion.youtubeComments import getVideoId, getYoutubeComments
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput
from config.keywords import YOUTUBE_KEYWORDS

def youtube_manual(link: str):
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    cleaned_data = loadAndClean(all_items, YOUTUBE_KEYWORDS)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    return insights