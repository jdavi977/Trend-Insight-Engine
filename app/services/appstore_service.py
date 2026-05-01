from app.ingestion.appStoreReviews import getAppId, getAppReviews
from app.preprocessing.reviewClean import appReviewClean
from app.config.settings import APP_REVIEW_PAGES
from app.config.prompts import appStoreSystemPrompt, appStorePromptOutput
from app.llm.extractInsights import extractInsights

def app_store_manual(link):
    id = getAppId(link)
    mostRecent = getAppReviews(id, "mostRecent", APP_REVIEW_PAGES)
    mostHelpful = getAppReviews(id, "mostHelpful", APP_REVIEW_PAGES)
    all_items = mostRecent + mostHelpful
    cleaned_data = appReviewClean(all_items)
    insights = extractInsights(cleaned_data, appStoreSystemPrompt, appStorePromptOutput)
    return insights
