from ingestion.DatasetCreation import getVideoId, getYoutubeComments
from preprocessing.CommentClean import loadAndClean
from llm.ExtractInsights import extractInsights

def run_pipeline(link):
    id = getVideoId(link)
    raw_data = getYoutubeComments(id)
    cleaned_data = loadAndClean(raw_data)
    insights = extractInsights(cleaned_data)
    print(insights)

run_pipeline("https://www.youtube.com/watch?v=VfNRd5Rk0cM")