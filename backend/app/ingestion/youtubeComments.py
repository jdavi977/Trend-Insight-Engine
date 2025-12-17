from googleapiclient.discovery import build
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import os

load_dotenv()

YOUTUBE_API = os.getenv("YOUTUBE_API")

def getVideoId(url: str) -> str:
    p = urlparse(url)

    if p.netloc in ("youtu.be", "www.youtu.be"):
        return p.path.strip("/")

    if "youtube.com" in p.netloc and p.path == "/watch":
        return parse_qs(p.query).get("v", [""])[0]

    if "youtube.com" in p.netloc and p.path.startswith("/shorts/"):
        return p.path.split("/shorts/")[1].split("/")[0]

    return ""

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

def getMostPopularVideos(category):
    service = build('youtube', 'v3', developerKey=YOUTUBE_API)
    request = service.videos().list(
        part="id",
        chart="mostPopular",
        videoCategoryId=category,
        maxResults=10
    )
    ids = []
    response = request.execute()
    
    for item in response["items"]:
        ids.append({
            "Id": item["id"]
        })

    service.close()
    return ids