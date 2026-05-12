import requests


def get_app_name(app_id: str, timeout: int = 10) -> str:
    url = f"https://itunes.apple.com/lookup?id={app_id}"
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        return app_id
    results = response.json().get("results", [])
    if not results:
        return app_id
    return results[0].get("trackName", app_id)


def _fetch_reviews_page(app_id: str, sort_by: str, page: int, timeout: int = 10) -> dict:
    url = (
        f"https://itunes.apple.com/rss/customerreviews/id={app_id}/"
        f"sortBy={sort_by}/page={page}/json"
    )
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        print(f"Stopped at page: {page}, status: {response.status_code}")
    return response.json()


def list_reviews(
    app_id: str, sort_by: str, page: int, timeout: int = 10
) -> list[dict]:
    """Return App Store review rows from one iTunes RSS page.

    Each row is ``{"rating", "title", "content", "vote_count"}`` (string values).
    Returns ``[]`` when the feed is empty, missing, or has at most one entry
    (iTunes RSS uses the last page as a single metadata row).
    """
    data = _fetch_reviews_page(app_id, sort_by, page, timeout=timeout)
    feed = data.get("feed") or {}
    if not feed:
        return []

    entry = feed.get("entry", [])
    if isinstance(entry, dict):
        entry = [entry]
    if len(entry) <= 1:
        return []

    rows: list[dict] = []
    for item in entry:
        rows.append(
            {
                "rating": (item.get("im:rating") or {}).get("label"),
                "title": (item.get("title") or {}).get("label"),
                "content": (item.get("content") or {}).get("label"),
                "vote_count": (item.get("im:voteCount") or {}).get("label"),
            }
        )
    return rows


def list_top_apps(genre_id: int, country: str = "us", limit: int = 5, timeout: int = 10) -> list[dict]:
    url = (
        f"https://itunes.apple.com/{country}/rss/topfreeapplications/"
        f"limit={limit}/genre={genre_id}/json"
    )
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        print(f"list_top_apps failed for genre {genre_id}, status: {response.status_code}")
        return []

    feed = response.json().get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]

    apps = []
    for entry in entries:
        images = entry.get("im:image", []) or []
        thumbnail = images[-1].get("label") if images else None
        apps.append({
            "Id": entry.get("id", {}).get("attributes", {}).get("im:id"),
            "Title": entry.get("im:name", {}).get("label"),
            "Artist": entry.get("im:artist", {}).get("label"),
            "Thumbnail": thumbnail,
        })
    return apps
