import re
from config.keywords import YOUTUBE_KEYWORDS
from utilities.textCleaning import keyword_filtering, exclude_keywords, remove_emojis, remove_duplicates

#TODO: stopword removal? remove urls?

def loadAndClean(data, keywords: list, exclude=[""]):
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

    exclude = exclude_keywords(cleaned, exclude)

    # Filtering for keywords
    filtered = keyword_filtering(exclude, keywords)

    # Clean out emojis
    emoji_removed = remove_emojis(filtered)

    # Filtering duplicates
    finished = remove_duplicates(emoji_removed)
    return finished