from ingestion.youtubeComments import getVideoId, getComments
from preprocessing.commentClean import load
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput
from config.keywords import YOUTUBE_KEYWORDS

def youtube_manual(link: str):
    id = getVideoId(link)
    relevance = getComments(id, "relevance")
    time = getComments(id, "time")
    all_items = relevance + time
    cleaned_data = load(all_items, YOUTUBE_KEYWORDS)
    print(cleaned_data)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    print(insights)
    return insights