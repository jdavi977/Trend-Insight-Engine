from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from app.config.settings import YOUTUBE_COMMENTS_AMOUNT, YOUTUBE_VIDEO_AMOUNT
from app.config.config import YOUTUBE_API

def getVideoId(url: str) -> str:
    p = urlparse(url)

    if p.netloc in ("youtu.be", "www.youtu.be"):
        return p.path.strip("/")

    if "youtube.com" in p.netloc and p.path == "/watch":
        return parse_qs(p.query).get("v", [""])[0]

    if "youtube.com" in p.netloc and p.path.startswith("/shorts/"):
        return p.path.split("/shorts/")[1].split("/")[0]

    return ""

def getYoutubeComments(id, order, title=None,):
    service = build('youtube', 'v3', developerKey=YOUTUBE_API)
    request = service.commentThreads().list(
        part="snippet",
        videoId= id,
        maxResults = YOUTUBE_COMMENTS_AMOUNT,
        order = order,
        textFormat = "plainText"
    )

    comments = []
    response = request.execute()

    # Fix not appending title for manual links

    for item in response["items"]:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "Id": id,
            "Title": title,
            "Likes": snippet["likeCount"],
            "Text": snippet["textDisplay"]
        })

    service.close()
    return comments

def getMostPopularVideos(category):
    service = build('youtube', 'v3', developerKey=YOUTUBE_API)
    request = service.videos().list(
        part="snippet",
        chart="mostPopular",
        videoCategoryId=category,
        maxResults=5
    )
    ids = []
    response = request.execute()
    
    for item in response["items"]:
        ids.append({
            "Title": item["snippet"]["title"],
            "Id": item["id"]
        })

    service.close()
    return ids

#if __name__ == "__main__":
    #print(getMostPopularVideos(20))
    #[{'Title': 'I Became King of the Unstable SMP', 'Id': '2WusTNLmBpE'}, {'Title': "Marvel Rivals: What's new in Season 6.5 // Dev Vision Vol. 14", 'Id': 'e12fPPx8-_0'}, {'Title': 'I Got The New LA ROMANTIC GRANDE..', 'Id': 'SgJpGVWwKWY'}, {'Title': 'Hermitcraft 11: Episode 10 - FINISHING THE CAVE!', 'Id': 'xEN85i57UmM'}, {'Title': 'DO NOT Let Me Work at a Quarantine Zone', 'Id': 'AMA6AkkexzE'}]