from ingestion.youtubeComments import getVideoId, getYoutubeComments
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput

def run_youtube_pipeline(link):
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    print(relevance)
    time = getYoutubeComments(id, "time")
    print(time)
    all_items = relevance + time
    cleaned_data = loadAndClean(all_items)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    return insights