# EX
# {'rating': '4', 'title': 'Abuse of power? 😅', 'content': 'How old is the bean? I just feel like I’m breaking child labor laws making him knit 100s of socks for me every day', 'vote_count': '0'}, {'rating': '5', 'title': 'friends and tags, please!', 'content': 'i love the app, it’s stimulating and rewarding to use. 
# \n\nhowever, bean could benefit from having its friends added by their ID, so bean could cheer them up! \nanother nice update would be to be able to add tags to the tasks such as (Reading, Practicing, Studying etc.)  \n\nthank you for bean<3', 'vote_count': '0'}
#

# FIlter based off votecount
# Filter for keywords
# Remove dupliates
# Remove emojis

import re
from config.keywords import APPLE_KEYWORDS

def appReviewClean(data):
    cleaned = []
    filtered = []

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

    for review in cleaned:
        for key in APPLE_KEYWORDS:
            pattern = re.compile(r"\b" + re.escape(key) + r"\b")
            match = pattern.search(review['Content'])
            if match:
                filtered.append(review)
                pass
            else:
                pass

    unique = list({r["Content"]: r for r in cleaned}.values())
    return unique

