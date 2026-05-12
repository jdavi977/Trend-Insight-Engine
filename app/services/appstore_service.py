from app.ingestion.appStoreReviews import getAppId, getAppReviews
from app.preprocessing.reviewPipeline import appstore_rows_for_llm
from app.config.constants import MANUAL_REVIEW_PAGES
from app.config.promptTemplates import build_appstore_prompt, appStorePromptOutput
from app.config.genres import get_default_genre
from app.llm.extractInsights import extract_insights
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, retrieve_similar
from app.clients.appstore import get_app_name
from app.schemas.api import AppStoreAnalysisResponse


def app_store_manual(link):
    default = get_default_genre("appstore")
    id = getAppId(link)

    prior_insights = []
    if RAG_READ_ENABLED:
        app_name = get_app_name(id)
        prior_insights = retrieve_similar(query=app_name)

    mostRecent = getAppReviews(id, "mostRecent", MANUAL_REVIEW_PAGES)
    mostHelpful = getAppReviews(id, "mostHelpful", MANUAL_REVIEW_PAGES)
    all_items = mostRecent + mostHelpful
    cleaned_data = appstore_rows_for_llm(all_items, default.keywords)
    result = extract_insights(cleaned_data, build_appstore_prompt(default, prior_insights), appStorePromptOutput, source="app_store")
    if RAG_WRITE_ENABLED and result is not None:
        embed_and_store(result, link)
    if result is None:
        return None
    return AppStoreAnalysisResponse(**result.model_dump(), retrieved_context=prior_insights)
