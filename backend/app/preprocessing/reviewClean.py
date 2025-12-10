# EX
# {'rating': '4', 'title': 'Abuse of power? 😅', 'content': 'How old is the bean? I just feel like I’m breaking child labor laws making him knit 100s of socks for me every day', 'vote_count': '0'}, {'rating': '5', 'title': 'friends and tags, please!', 'content': 'i love the app, it’s stimulating and rewarding to use. 
# \n\nhowever, bean could benefit from having its friends added by their ID, so bean could cheer them up! \nanother nice update would be to be able to add tags to the tasks such as (Reading, Practicing, Studying etc.)  \n\nthank you for bean<3', 'vote_count': '0'}

import re
from config.keywords import APPLE_KEYWORDS
from utilities.text_cleaning import keyword_filtering, remove_emojis, remove_duplicates

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

