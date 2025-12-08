import re
from config.keywords import YOUTUBE_KEYWORDS
from utilities.text_cleaning import keyword_filtering, remove_emojis, remove_duplicates

#TODO: stopword removal? remove urls?

def loadAndClean(data):
    cleaned = []

    # Filtering based off likes
    for comment in data:
        try:
            likes = comment.get('Likes', 0)
        except:
            likes = 0
        if likes >= 50:
            cleaned.append({
                "Likes": likes,
                "Content": comment['Text'].lower().strip(),
            })

    # Filtering for keywords
    filtered = keyword_filtering(cleaned, YOUTUBE_KEYWORDS)

    # Clean out emojis
    emoji_removed = remove_emojis(filtered)

    # Filtering duplicates
    finished = remove_duplicates(emoji_removed)
    return finished