from app.ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from app.preprocessing.commentClean import loadAndClean
from app.llm.extractInsights import extractInsights
from app.config.prompts import youtubePromptOutput, youtubeGameSystemPrompt, youtubeScienceTechSystemPrompt, youtubeHowtoStyleSystemPrompt
from app.config.keywords import GAME_KEYWORDS, SCIENCE_TECH_KEYWORDS, HOWTO_STYLE_KEYWORDS
from app.config.settings import GAME_CATEGORY_ID, SCIENCE_TECH_ID, HOW_TO_STYLE_ID
from app.lib.db import update_automatic_trend, check_youtube_id, update_automatic_video_date
from app.utilities.getDate import getCurrentDate
import json

def youtube_automatic(ids: list[str], category: int, categoryPrompt: str, keywords: list):

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
            
            insights = extractInsights(cleaned_data, categoryPrompt, youtubePromptOutput)
        
            data = json.loads(insights)

            # Makes sure data is a dictionary before accessing problems
            print(data)

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
    test = getMostPopularVideos(HOW_TO_STYLE_ID)
    #print(youtube_automatic(test, category, youtubeGameSystemPrompt, GAME_KEYWORDS)) #GAME CAT
    #print(youtube_automatic(test, SCIENCE_TECH_ID, youtubeScienceTechSystemPrompt, SCIENCE_TECH_KEYWORDS)) #SCITECH CAT
    print(youtube_automatic(test, HOW_TO_STYLE_ID, youtubeHowtoStyleSystemPrompt, HOWTO_STYLE_KEYWORDS)) #HOWTOSTYLE CAT



# TODO:
# use an AI program to style frontend
# 8. make weekly cron job
# 9. add more categories other than just games
