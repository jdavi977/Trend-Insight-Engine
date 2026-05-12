from googleapiclient.discovery import build

from app.config.secrets import keyChecker

YOUTUBE_API = keyChecker("YOUTUBE_API")


def _service():
    return build("youtube", "v3", developerKey=YOUTUBE_API)


def _pick_largest_thumbnail(thumbs: dict) -> dict | None:
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbs:
            return thumbs[size]
    return None


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
        raw_items = request.execute()["items"]
        rows = []
        for item in raw_items:
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            rows.append({
                "Likes": snippet["likeCount"],
                "Text": snippet["textDisplay"],
            })
        return rows
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
        raw_items = request.execute()["items"]
        rows = []
        for item in raw_items:
            snippet = item["snippet"]
            thumbs = snippet.get("thumbnails") or {}
            rows.append({
                "Id": item["id"],
                "Title": snippet["title"],
                "Thumbnail": _pick_largest_thumbnail(thumbs),
            })
        return rows
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


def get_video_title(video_id: str) -> str:
    service = _service()
    try:
        response = service.videos().list(part="snippet", id=video_id).execute()
        items = response.get("items", [])
        if not items:
            return video_id
        return items[0]["snippet"]["title"]
    finally:
        service.close()
