from ingestion.appStoreReviews import getAppId, getAppReviews
from preprocessing.reviewClean import appReviewClean
from config.settings import APP_REVIEW_PAGES

def run_pipeline(link):
    id = getAppId(link)
    raw_data = getAppReviews(id, APP_REVIEW_PAGES)
    cleaned_data = appReviewClean(raw_data)
    return cleaned_data


print(run_pipeline("https://apps.apple.com/ca/app/focus-friend-by-hank-green/id6742278016"))

# [{'Votes': '11', 'Content': 'best productivity app hands down. you don’t have to be 
# a student to use this. working adult here who gets easily distracted by my phone and 
# scrolling — it locks all your apps down. i’ve disturbed my bean guy a few times and 
# it’s a horrible feeling, so never again and stay focused! i use this almost daily 
# get through my 9-5 work day. love all the customizations and i hope to see more 
# cool features in the future. also you can decorate with cool, nerdy space themes 
# which is awesome :)'}, {'Votes': '9', 'Content': 'this is the only productivity app 
# of minimum two dozen i’ve tried that i used consistently and was helpful. after i 
# fully decorated the only room available when the app was released, my screen time 
# more than doubled and i got overwhelmingly behind on chores. now, i have turned off 
# the reward multiplier because i need to take as long decorating the new room as 
# possible so i can catch up on laundry. make brain rot work for you.'}, {'Votes': '7', 'Content': 'i used to use forest app but then switched to this app because i love the incentive of decorating my bean’s room. however, i’d prefer to have a stopwatch rather than a timer. i also like seeing my stats, like how many hours i studied in a day, a week, a month, and even a year. these features would be extremely helpful and useful for someone like me who likes to keep track of study commitments like me. otherwise, this app is so cute, i love the art style, and the developers did a good job so far!'}]