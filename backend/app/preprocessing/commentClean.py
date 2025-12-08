import re
from config.keywords import YOUTUBE_KEYWORDS

#TODO: stopword removal? remove urls?

def loadAndClean(data):
    cleaned = []
    filtered = []

    # Filtering based off likes
    for comment in data:
        try:
            likes = comment.get('Likes', 0)
        except:
            likes = 0
        if likes >= 50:
            cleaned.append({
                "Text": comment['Text'].lower().strip(),
                "Likes": likes
            })

    # Filtering for keywords
    for comment in cleaned:
        for key in YOUTUBE_KEYWORDS:
            pattern = re.compile(r"\b" + re.escape(key) + r"\b")
            match = pattern.search(comment['Text'])
            if match:
                filtered.append(comment)
                pass
            else:
                pass

    # Filtering duplicates
    unique = list({c["Text"]: c for c in filtered}.values())
    return unique