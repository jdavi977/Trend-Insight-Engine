from app.ingestion.appStoreReviews import getAppId, getAppReviews
from app.preprocessing.reviewPipeline import appstore_rows_for_llm
from app.config.constants import MANUAL_REVIEW_PAGES
from app.config.promptTemplates import build_appstore_prompt, appStorePromptOutput
from app.config.genres import get_default_genre
from app.llm.extractInsights import extract_insights
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, enrich_problems
from app.clients.appstore import get_app_metadata
from app.schemas.api import AppStoreAnalysisResponse


def app_store_manual(link):
    default = get_default_genre("appstore")
    id = getAppId(link)

    meta = get_app_metadata(id)
    app_name = meta["name"]

    mostRecent = getAppReviews(id, "mostRecent", MANUAL_REVIEW_PAGES)
    mostHelpful = getAppReviews(id, "mostHelpful", MANUAL_REVIEW_PAGES)
    all_items = mostRecent + mostHelpful
    cleaned_data = appstore_rows_for_llm(all_items, default.keywords)
    result = extract_insights(cleaned_data, build_appstore_prompt(default, []), appStorePromptOutput, source="app_store")
    if result is None:
        return None
    if RAG_READ_ENABLED:
        enrich_problems(result)
    if RAG_WRITE_ENABLED:
        result.title = app_name
        embed_and_store(result, link)
    return AppStoreAnalysisResponse(
        **result.model_dump(),
        thumbnail=meta.get("thumbnail"),
        seller=meta.get("seller"),
        genre=meta.get("genre"),
        age_rating=meta.get("age_rating"),
        average_rating=meta.get("average_rating"),
        rating_count=meta.get("rating_count"),
    )
