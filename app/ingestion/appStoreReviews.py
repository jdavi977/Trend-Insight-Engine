from app.clients.appstore import list_reviews


def getAppId(link):
    id = link.split("/id")[1]
    return id


def getAppReviews(id, sortBy, max_pages, title=None):
    all_reviews = []
    for page in range(1, max_pages + 1):
        rows = list_reviews(id, sortBy, page)
        if not rows:
            break
        all_reviews.extend([{"Id": id, "Title": title, **row} for row in rows])
    return all_reviews
