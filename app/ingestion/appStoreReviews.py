from app.clients.appstore import fetch_reviews_page


def getAppId(link):
    id = link.split("/id")[1]
    return id


def getAppReviews(id, sortBy, max_pages):
    all_reviews = []
    for page in range(1, max_pages + 1):
        data = fetch_reviews_page(id, sortBy, page)
        if not data['feed']:
            break
        feed = data['feed']
        entry = feed.get("entry", [])
        if not entry or len(entry) <= 1:
            break
        for review in entry:
            review = {
                "rating": review.get("im:rating").get("label"),
                "title": review.get("title").get("label"),
                "content": review.get("content").get("label"),
                "vote_count": review.get("im:voteCount").get("label")
            }
            all_reviews.append(review)
    return all_reviews
