from ingestion.appStoreReviews import getAppId, getAppReviews
from preprocessing.reviewClean import appReviewClean
from config.settings import APP_REVIEW_PAGES
from config.prompts import appStoreSystemPrompt, appStorePromptOutput
from llm.extractInsights import extractInsights

def app_store_manual(link):
    id = getAppId(link)
    mostRecent = getAppReviews(id, "mostRecent", APP_REVIEW_PAGES)
    mostHelpful = getAppReviews(id, "mostHelpful", APP_REVIEW_PAGES)
    all_items = mostRecent + mostHelpful
    cleaned_data = appReviewClean(all_items)
    insights = extractInsights(cleaned_data, appStoreSystemPrompt, appStorePromptOutput)
    return insights
