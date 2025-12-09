from ingestion.youtubeComments import getVideoId, getYoutubeComments
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput

def run_youtube_pipeline(link):
    id = getVideoId(link)
    raw_data = getYoutubeComments(id)
    cleaned_data = loadAndClean(raw_data)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    return insights
