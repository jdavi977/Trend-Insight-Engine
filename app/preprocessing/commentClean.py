import re
from app.config.keywords import YOUTUBE_KEYWORDS
from app.utilities.textCleaning import keyword_filtering, exclude_keywords, remove_emojis, remove_duplicates

#TODO: stopword removal? remove urls?

def loadAndClean(data, keywords: list):
    cleaned = []

    # Filtering based off likes
    for comment in data:
        try:
            likes = comment.get('Likes', 0)
        except:
            likes = 0
        if likes >= 50:
            cleaned.append({
                "Title": comment['Title'],
                "Likes": likes,
                "Content": comment['Text'].lower().strip(),
            })

    # if exclude:
    #     print("2.1")
    #     exclude = exclude_keywords(cleaned, exclude)
    #     filtered = keyword_filtering(exclude, keywords)
    # else: 
    #     print("2.2")
    #     filtered = keyword_filtering(cleaned, keywords)
    
    # Clean out emojis
    emoji_removed = remove_emojis(cleaned)

    # Filtering duplicates
    finished = remove_duplicates(emoji_removed)
    return finished

