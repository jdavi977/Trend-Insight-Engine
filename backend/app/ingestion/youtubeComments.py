from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv()

YOUTUBE_API = os.getenv("YOUTUBE_API")

def getVideoId(link):
    id = link.split("v=")[1]
    return id

def getYoutubeComments(id, order):
    service = build('youtube', 'v3', developerKey=YOUTUBE_API)
    request = service.commentThreads().list(
        part="snippet",
        videoId= id,
        maxResults = 100,
        order = order,
        textFormat = "plainText"
    )
    comments = []
    response = request.execute()

    for item in response["items"]:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "Likes": snippet["likeCount"],
            "Text": snippet["textDisplay"]
        })
    service.close()
    return comments
