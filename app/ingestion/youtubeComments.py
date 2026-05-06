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
    rows = list_comment_threads(id, order, YOUTUBE_COMMENTS_AMOUNT)
    return [{"Id": id, "Title": title, **row} for row in rows]


def getMostPopularVideos(category):
    return list_most_popular(category, YOUTUBE_VIDEO_AMOUNT)
