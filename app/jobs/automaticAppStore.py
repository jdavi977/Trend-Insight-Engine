from app.ingestion.appStoreReviews import getAppReviews
from app.preprocessing.reviewClean import appReviewClean
from app.llm.extractInsights import extractInsights
from app.config.promptTemplates import appStorePromptOutput
from app.config.constants import APP_REVIEW_PAGES, APPLE_COUNTRY
from app.clients.supabase import (
    update_automatic_apple_trend,
    update_automatic_app_date,
    check_appstore_id,
)
from app.utilities.getDate import getCurrentDate
import json


def appstore_automatic(apps: list[dict], genre_id: int, genre_prompt: str, keywords: list):

    today = str(getCurrentDate())

    page_data = []
    for app in apps:
        app_id = int(app['Id'])
        check = check_appstore_id(app_id)
        print(app_id)

        if check:
            print("Updating data")
            print(f"Skipped key: {app_id}. Found in Database.")
            update_automatic_app_date(app_id, today)
            page_data.append(check)
            continue
        else:
            reviews = getAppReviews(app['Id'], "mostrecent", APP_REVIEW_PAGES)
            cleaned_data = appReviewClean(reviews, keywords)

            if len(cleaned_data) <= 0:
                print(f"Skipping key: {app_id} due to no problems found.")
                continue

            insights = extractInsights(cleaned_data, genre_prompt, appStorePromptOutput)

            data = json.loads(insights)

            print(data)

            if isinstance(data, list):
                if len(data) > 0:
                    data = data[0]
                else:
                    print(f"Skipping key: {app_id} due to no problems found.")
                    continue

            if not data["problems"]:
                print(f"Skipping key: {app_id} due to no problems found.")
                continue

            for item in data["problems"]:
                trend_data = []
                trend_data.append({
                    "app_id": app_id,
                    "app_title": app['Title'],
                    "country": APPLE_COUNTRY,
                    "genre_id": genre_id,
                    "date": today,
                    "thumbnail": app['Thumbnail'],
                    "problems": {
                        "problem": item["problem"],
                        "type": item["type"],
                        "average_rating": item["average_rating"],
                        "severity": item["severity"],
                        "frequency": item["frequency"],
                        "example_reviews": item["example_reviews"],
                    },
                })
                if trend_data:
                    print("Updating data")
                    update_automatic_apple_trend(trend_data)
                    page_data.append(trend_data)
    return page_data
