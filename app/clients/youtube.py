import os

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

YOUTUBE_API = os.getenv("YOUTUBE_API")


def _service():
    return build("youtube", "v3", developerKey=YOUTUBE_API)


def list_comment_threads(video_id, order, max_results):
    service = _service()
    try:
        request = service.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=max_results,
            order=order,
            textFormat="plainText",
        )
        return request.execute()["items"]
    finally:
        service.close()


def list_most_popular(category_id, max_results):
    service = _service()
    try:
        request = service.videos().list(
            part="snippet",
            chart="mostPopular",
            videoCategoryId=category_id,
            maxResults=max_results,
        )
        return request.execute()["items"]
    finally:
        service.close()


def getVideoCategories():
    service = _service()
    request = service.videoCategories().list(
        part="snippet",
        regionCode="US",
    )
    list = []
    response = request.execute()

    for item in response["items"]:
        snippet = item["snippet"]
        list.append({
            "Id": item["id"],
            "Title": snippet["title"],
        })
    service.close()
    return list
