import logging
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config.secrets import keyChecker

YOUTUBE_API = keyChecker("YOUTUBE_API")

logger = logging.getLogger(__name__)

# Debug trace for this client only: mirrors the run_pipeline / per_source_extraction
# debug logs, into its own file so swallowed-vs-raised HttpError decisions can be
# inspected after the fact regardless of the process-wide LOG_LEVEL.
_DEBUG_LOG_PATH = Path("logs/youtube_client_debug.log")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(_DEBUG_LOG_PATH)
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(_file_handler)
    logger.setLevel(logging.DEBUG)

# Reasons where "no comments" is a legitimate, expected API response — safe to
# swallow into []. Any other 403/404 (quotaExceeded, forbidden, keyInvalid, …)
# is a real failure and must propagate so the pipeline's retry / partial-source
# accounting (run_pipeline_service._process_source_resilient) can see it,
# instead of it silently masquerading as a source with zero comments.
_BENIGN_COMMENT_ERROR_REASONS = {"commentsDisabled", "videoNotFound"}


def _service():
    return build("youtube", "v3", developerKey=YOUTUBE_API)


def _http_error_reason(e: HttpError) -> str:
    """Best-effort extraction of the vendor `reason` code (e.g. `commentsDisabled`).

    Falls back to `e.reason` (the human-readable message) when the structured
    `errors[]` list isn't present in the response body.
    """
    details = e.error_details
    if isinstance(details, list) and details:
        first = details[0]
        if isinstance(first, dict):
            return first.get("reason", "") or e.reason
    return e.reason


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
        try:
            response = request.execute()
        except HttpError as e:
            reason = _http_error_reason(e)
            if e.status_code in (403, 404) and reason in _BENIGN_COMMENT_ERROR_REASONS:
                logger.info(
                    "list_comment_threads: no comments video_id=%s reason=%s",
                    video_id, reason,
                )
                return []
            logger.warning(
                "list_comment_threads: HttpError status=%s reason=%s video_id=%s",
                e.status_code, reason, video_id,
            )
            raise
        rows = []
        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            rows.append({
                "Likes": snippet["likeCount"],
                "Text": snippet["textDisplay"],
            })
        return rows
    finally:
        service.close()


def search_videos(query: str, max_results: int = 10) -> list[dict]:
    """YouTube Data search.list — return candidate videos for a free-text query.

    Each row: ``{video_id, title, channel, description, url}``.
    Description truncated to 200 chars to keep ranker prompts bounded.
    ~100 quota units per call (YouTube Data API v3).
    """
    service = _service()
    try:
        response = service.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
        ).execute()
    finally:
        service.close()

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        video_id = item["id"]["videoId"]
        videos.append({
            "video_id": video_id,
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "description": (snippet.get("description") or "")[:200],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })
    return videos


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


def _parse_duration(iso: str) -> str:
    """Convert ISO 8601 duration (PT14M22S) to mm:ss / h:mm:ss."""
    import re
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return ""
    h, mn, s = (int(x or 0) for x in m.groups())
    if h:
        return f"{h}:{mn:02d}:{s:02d}"
    return f"{mn}:{s:02d}"


def get_video_metadata(video_id: str) -> dict:
    service = _service()
    try:
        resp = service.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_id,
        ).execute()
        items = resp.get("items", [])
        if not items:
            return {"title": video_id}
        item = items[0]
        snippet = item["snippet"]
        stats = item.get("statistics", {})
        duration_raw = item.get("contentDetails", {}).get("duration", "")

        channel_id = snippet.get("channelId")
        subscribers = None
        if channel_id:
            ch_resp = service.channels().list(
                part="statistics", id=channel_id
            ).execute()
            ch_items = ch_resp.get("items", [])
            if ch_items:
                sub_raw = ch_items[0].get("statistics", {}).get("subscriberCount")
                if sub_raw is not None:
                    subscribers = int(sub_raw)

        likes = stats.get("likeCount")
        views = stats.get("viewCount")
        return {
            "title": snippet.get("title", video_id),
            "channel_name": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "view_count": int(views) if views is not None else None,
            "like_count": int(likes) if likes is not None else None,
            "comment_count": int(stats["commentCount"]) if "commentCount" in stats else None,
            "subscriber_count": subscribers,
            "duration": _parse_duration(duration_raw),
        }
    finally:
        service.close()
