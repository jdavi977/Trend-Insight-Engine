from ingestion.youtubeComments import getVideoId, getYoutubeComments, getMostPopularVideos
from preprocessing.commentClean import loadAndClean
from llm.extractInsights import extractInsights
from config.prompts import youtubeSystemPrompt, youtubePromptOutput
from config.keywords import GAME_KEYWORDS, YOUTUBE_KEYWORDS, GAME_EXCLUDE_KEYWORDS
from config.settings import GAME_CATEGORY_ID

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
        print(1)
        relevance = getYoutubeComments(id['Id'], "relevance")
        # change keywords to match for games
        cleaned_data = loadAndClean(relevance, keywords, exclude)

        insights = extractInsights(cleaned_data, youtubeSystemPrompt, youtubePromptOutput)
        print(insights)
        # for problem in insights["problems"]:
        #     list.append({
        #         "source": insights["source"],
        #         "name": insights["name"],
        #         "problems": problem
        #     })
    # return list

youtube_automatic(getMostPopularVideos(GAME_CATEGORY_ID), GAME_KEYWORDS, GAME_EXCLUDE_KEYWORDS)