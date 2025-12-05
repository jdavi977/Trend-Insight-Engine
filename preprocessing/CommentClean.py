import json
import re
from ingestion.DatasetCreation import getYoutubeComments

#TODO: stopword removal? remove urls?

def loadAndClean(data):
    cleaned = []
    filtered = []
    keywords = [
        "add", "adding", "feature", "wish", "need", "could", "missing", "support",
        "issue", "bug", "problem", "crash", "crashes", "lag", "laggy",
        "slow", "broken", "fix", "fixed", "hard", "confusing", "complicated",
        "easier", "should be easier", "unlike", "better",
        "automatic", "automation", "ai", "automate"
    ]

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
        for key in keywords:
            pattern = re.compile(r"\b" + re.escape(key) + r"\b")
            match = pattern.search(comment['Text'])
            if match:
                filtered.append(comment)
                pass
            else:
                pass

    unique = list({c["Text"]: c for c in filtered}.values())

    return unique