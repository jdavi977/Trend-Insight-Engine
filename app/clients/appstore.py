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
