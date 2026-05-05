from urllib.parse import urlparse, parse_qs

from app.clients.youtube import list_comment_threads, list_most_popular
from app.config.constants import YOUTUBE_COMMENTS_AMOUNT, YOUTUBE_VIDEO_AMOUNT


def getVideoId(url: str) -> str:
    p = urlparse(url)

    if p.netloc in ("youtu.be", "www.youtu.be"):
        return p.path.strip("/")

    if "youtube.com" in p.netloc and p.path == "/watch":
        return parse_qs(p.query).get("v", [""])[0]

    if "youtube.com" in p.netloc and p.path.startswith("/shorts/"):
        return p.path.split("/shorts/")[1].split("/")[0]

    return ""


def getYoutubeComments(id, order, title=None):
    items = list_comment_threads(id, order, YOUTUBE_COMMENTS_AMOUNT)
    comments = []
    for item in items:
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "Id": id,
            "Title": title,
            "Likes": snippet["likeCount"],
            "Text": snippet["textDisplay"],
        })
    return comments


def _pick_largest_thumbnail(thumbs):
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbs:
            return thumbs[size]
    return None


def getMostPopularVideos(category):
    items = list_most_popular(category, YOUTUBE_VIDEO_AMOUNT)
    ids = []
    for item in items:
        ids.append({
            "Title": item["snippet"]["title"],
            "Id": item["id"],
            "Thumbnail": _pick_largest_thumbnail(item["snippet"]["thumbnails"]),
        })
    return ids
