from app.ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from app.preprocessing.commentClean import loadAndClean
from app.llm.extractInsights import extractInsights
from app.config.prompts import youtubePromptOutput, youtubeGameSystemPrompt
from app.config.keywords import GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS
from app.config.settings import GAME_CATEGORY_ID
from app.lib.db import update_automatic_trend, check_youtube_id, update_automatic_video_date
from app.utilities.getDate import getCurrentDate
import json

# fix exclude issue, it exclude is not given it will exclude all comments due to ""
def youtube_automatic(ids: list[str], category: int, keywords: list):

    today = str(getCurrentDate())

    page_data = []
    for id in ids:
        print(id['Id'])
        check = check_youtube_id(id['Id'])
        
        if check:
            print("Updating data")
            print(f"Skipped key: {id['Id']}. Found in Database.")
            update_automatic_video_date(id['Id'], today)
            page_data.append(check)
            continue
        else:
            relevance = getYoutubeComments(id['Id'], "relevance", id['Title'])
            cleaned_data = loadAndClean(relevance, keywords)

            if len(cleaned_data) <= 0:
                print(f"Skipping key: {id['Id']} due to no problems found.")
                continue
            
            insights = extractInsights(cleaned_data, youtubeGameSystemPrompt, youtubePromptOutput)
        
            data = json.loads(insights)

            # Makes sure data is a dictionary before accessing problems
            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    print(f"Skipping key: {id['Id']} due to no problems found.")
                    continue 
            
            if not data["problems"]:
                print(f"Skipping key: {id['Id']} due to no problems found.")
                continue
            
            for item in data["problems"]:
                trend_data = []
                trend_data.append({
                    "key": id['Id'],
                    "date": today,
                    "category": category,
                    "title": data["title"],
                    "problems": {
                        "problem": item["problem"],
                        "type": item["type"],
                        "total_likes": item["total_likes"],
                        "severity": item["severity"],
                        "frequency": item["frequency"]}
                })
                if trend_data:
                    print("Updating data")
                    update_automatic_trend(trend_data)
                    page_data.append(trend_data)
    return page_data

if __name__ == "__main__":
    category = 20
    test = getMostPopularVideos(category)
    print(youtube_automatic(test, category, GAME_KEYWORDS))

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

# step 0 look at loadandclean funciton  1
# step 1: check if automaticYoutube works  1
# 2. check if data is being sent to the backend  1
# 3. make sure id is being sent  1
# 4. make automatic pipeline first check database if youtubeid is already present 1
# 5. if present we skip processing the id and instead pull data 1
# 5.5 Make automatic_youtube only be a function to send popular page data to backend
# 5.6 Figure out a way to get react page to get specific category data from database
# Notes:
# React page cant just pull latest date + category since a video may be on there from 2 weeks ago, not having a updated date
# Unless we update the row date to current date when going through ids
# Step 1:
# Create category field in db -done
# Create date field in db -done
# Create funciton to get current date -done
# Send date field to database -done
# Update date field for exisitng ids in database that dont have matching dates -done

# Todo:
# Make function to fetch database problems ->  cron will be scheduled for sunday night
# Make function to get sunday date -done
# Create function to fetch data with ids that have sunday date -done

# 6. make main page in react


# 7. transfer data onto the page
# 8. make weekly cron job
# 9. add more categories other than just games
