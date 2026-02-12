from app.ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from app.preprocessing.commentClean import loadAndClean
from app.llm.extractInsights import extractInsights
from app.config.prompts import youtubePromptOutput, youtubeGameSystemPrompt
from app.config.keywords import GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS
from app.config.settings import GAME_CATEGORY_ID
from app.lib.db import update_automatic_trend
import json

# fix exclude issue, it exclude is not given it will exclude all comments due to ""
def youtube_automatic(ids: list[str], keywords: list):
    list = []
    for id in ids:

        

        # Check if id is already in database
        # if id is in database, fetch data
        # else continue pipeline

        relevance = getYoutubeComments(id['Id'], "relevance", id['Title'])
        cleaned_data = loadAndClean(relevance, keywords)

        if len(cleaned_data) <= 0:
            continue

        insights = extractInsights(cleaned_data, youtubeGameSystemPrompt, youtubePromptOutput)
        data = json.loads(insights)
        for item in data["problems"]:
            list = []
            list.append({
                "key": id['Id'],
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

if __name__ == "__main__":
    test = getMostPopularVideos(20)
    youtube_automatic(test, GAME_KEYWORDS)

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
# DB schema + idempotency (so automatic ingestion doesn’t spam duplicates)
# Automatic ingestion categories (now it’s safe to run repeatedly)
# Cron weekly run + weekly rollups (this is the core value)
# Web page last (because now you have stable data + endpoints)

# idempotency - use vid_id, app_id so if it already exists we dont rerun

# step 0 look at loadandclean funciton  1
# step 1: check if automaticYoutube works  1
# 2. check if data is being sent to the backend  1
# 3. make sure id is being sent  1
# 4. make automatic pipeline first check database if youtubeid is already present
# 5. if present we skip processing the id and instead pull data
# 6. make page in react
# 7. transfer data onto the page
# 8. make weekly cron job
# 9. add more categories other than just games
