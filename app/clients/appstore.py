import requests


def fetch_reviews_page(app_id: str, sort_by: str, page: int, timeout: int = 10) -> dict:
    url = (
        f"https://itunes.apple.com/rss/customerreviews/id={app_id}/"
        f"sortBy={sort_by}/page={page}/json"
    )
    response = requests.get(url, timeout=timeout)
    if response.status_code != 200:
        print(f"Stopped at page: {page}, status: {response.status_code}")
    return response.json()


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
