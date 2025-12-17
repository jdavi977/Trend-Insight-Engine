import re
from config.keywords import APPLE_KEYWORDS
from utilities.textCleaning import keyword_filtering, remove_emojis, remove_duplicates

def appReviewClean(data):
    cleaned = []

    for review in data:
        try:
            vote_count = review.get('vote_count', 0)
        except:
            vote_count = 0
        if int(vote_count) > 5:
            cleaned.append({
                "Votes": vote_count,
                "Content": review['content'].lower().strip(),
            })
    
    filtered = keyword_filtering(cleaned, APPLE_KEYWORDS)

    emoji_removed = remove_emojis(filtered)

    finished = remove_duplicates(emoji_removed)

    return finished

