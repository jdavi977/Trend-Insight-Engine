from ingestion.appStoreReviews import getAppId, getAppReviews
from preprocessing.reviewClean import appReviewClean
from config.settings import APP_REVIEW_PAGES
from config.prompts import appStoreSystemPrompt, appStorePromptOutput
from llm.extractInsights import extractInsights

def run_app_pipeline(link):
    id = getAppId(link)
    raw_data = getAppReviews(id, APP_REVIEW_PAGES)
    cleaned_data = appReviewClean(raw_data)
    insights = extractInsights(cleaned_data, appStoreSystemPrompt, appStorePromptOutput)
    return insights
