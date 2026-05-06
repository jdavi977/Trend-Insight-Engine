from app.ingestion.appStoreReviews import getAppId, getAppReviews
from app.preprocessing.reviewPipeline import appstore_rows_for_llm
from app.config.constants import APP_REVIEW_PAGES
from app.config.promptTemplates import build_appstore_prompt, appStorePromptOutput
from app.config.genres import get_default_genre
from app.llm.extractInsights import extract_insights


def app_store_manual(link):
    default = get_default_genre("appstore")
    id = getAppId(link)
    mostRecent = getAppReviews(id, "mostRecent", APP_REVIEW_PAGES)
    mostHelpful = getAppReviews(id, "mostHelpful", APP_REVIEW_PAGES)
    all_items = mostRecent + mostHelpful
    cleaned_data = appstore_rows_for_llm(all_items, default.keywords)
    return extract_insights(cleaned_data, build_appstore_prompt(default), appStorePromptOutput)
