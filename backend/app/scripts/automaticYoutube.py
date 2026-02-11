from ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubePromptOutput, youtubeGameSystemPrompt
from config.keywords import GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS
from config.settings import GAME_CATEGORY_ID
from lib.db import update_automatic_trend
import json

# fix exclude issue, it exclude is not given it will exclude all comments due to ""
def youtube_automatic(ids: list[str], keywords: list, exclude=[""]):
    list = []
    for id in ids:
        relevance = getYoutubeComments(id['Id'], "relevance", id['Title'])
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

# youtube_automatic(getMostPopularVideos(GAME_CATEGORY_ID), GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS)
# Current issue:
# Same problems would be sent to supabase because openai changes up the problem phrasing by a little bit
# Could try to create an id for the video and have the problems be foreign keys to the id
# video id could be made using hash? so that it is the same for each title?
#
# Plans:
# Find which categories of videos I want to automatically ingest into the webpage
# Make sure backend works
# Create web page for automatic category 
# Make sure data is properly sent to backend
# Use AI to make the webpage
# Use cron for weekly insights
#
# Better order (still matching your goals)
# Make backend reliably runnable (golden path, fail-fast config, no import side effects)
# DB schema + idempotency (so automatic ingestion doesn’t spam duplicates)
# Automatic ingestion categories (now it’s safe to run repeatedly)
# Cron weekly run + weekly rollups (this is the core value)
# Web page last (because now you have stable data + endpoints)