import requests
import json

# EXAMPLE
# https://apps.apple.com/ca/app/focus-friend-by-hank-green/id6742278016


def getAppId(link):
    id = link.split("/id")[1]
    return id

def getAppReviews(id, max_pages):
    all_reviews = []
    for page in range(1, max_pages + 1):
        url = f"https://itunes.apple.com/rss/customerreviews/id={id}/sortBy=mostRecent/page={page}/json"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"Stopped at page: {page}, status: {response.status_code}")

        data = response.json()
        entry = data['feed']['entry']
        for review in entry[1:]:
            review = {
                "rating": review.get("im:rating").get("label"),
                "title": review.get("title").get("label"),
                "content": review.get("content").get("label"),
                "vote_count": review.get("im:voteCount").get("label")
            }
            all_reviews.append(review)
    return all_reviews