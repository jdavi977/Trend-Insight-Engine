from ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput, youtubeGameSystemPrompt
from config.keywords import GAME_KEYWORDS, YOUTUBE_KEYWORDS, GAME_EXCLUDE_KEYWORDS
from config.settings import GAME_CATEGORY_ID
from lib.db import update_automatic_trend
import json

def youtube_manual(link: str):
    id = getVideoId(link)
    relevance = getYoutubeComments(id, "relevance")
    time = getYoutubeComments(id, "time")
    all_items = relevance + time
    cleaned_data = loadAndClean(all_items, YOUTUBE_KEYWORDS)
    insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
    return insights

def youtube_automatic(ids: list[str], keywords: list, exclude=[""]):
    list = []
    for id in ids:
        relevance = getYoutubeComments(id['Id'], id['Title'], "relevance")
        cleaned_data = loadAndClean(relevance, keywords, exclude)

        if len(cleaned_data) <= 0:
            continue

        insights = extractInsights(cleaned_data, youtubeGameSystemPrompt, youtubePromptOutput)
        data = json.loads(insights)
        for item in data["problems"]:
            list = []
            list.append({
                "source": data["source"],
                "title": data["title"],
                "problems": [
                    "problem: ", item["problem"],
                    "type: ", item["type"],
                    "total_likes: ", item["total_likes"],
                    "severity: ", item["severity"],
                    "frequency: ", item["frequency"]]
            })
            if list:
                update_automatic_trend(list)

youtube_automatic(getMostPopularVideos(GAME_CATEGORY_ID), GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS)