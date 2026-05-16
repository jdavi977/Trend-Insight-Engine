import logging

from app.ingestion.appStoreReviews import getAppId, getAppReviews
from app.preprocessing.reviewPipeline import clean
from app.config.preprocessing import APPSTORE_PREPROCESS
from app.config.constants import MANUAL_REVIEW_PAGES
from app.config.promptTemplates import build_appstore_prompt, build_appstore_refinement_prompt, appStorePromptOutput
from app.config.genres import get_default_genre
from app.llm.extractInsights import extract_insights
from app.config.secrets import RAG_WRITE_ENABLED, RAG_READ_ENABLED
from app.rag.rag import embed_and_store, enrich_problems, retrieve_similar
from app.clients.appstore import get_app_metadata
from app.schemas.api import AppStoreAnalysisResponse

logger = logging.getLogger(__name__)


def app_store_manual(link):
    default = get_default_genre("appstore")
    id = getAppId(link)

    meta = get_app_metadata(id)
    app_name = meta["name"]

    mostRecent = getAppReviews(id, "mostRecent", MANUAL_REVIEW_PAGES, title=app_name)
    mostHelpful = getAppReviews(id, "mostHelpful", MANUAL_REVIEW_PAGES, title=app_name)
    all_items = mostRecent + mostHelpful
    rows = [{**item, "Content": item["content"]} for item in all_items]
    cleaned_data = clean(rows, **APPSTORE_PREPROCESS)
    raw_result = extract_insights(cleaned_data, build_appstore_prompt(default, []), appStorePromptOutput, source="app_store")
    if raw_result is None:
        return None

    prior_insights = []
    if RAG_READ_ENABLED:
        seen: set[str] = set()
        for problem in raw_result.problems:
            try:
                matches = retrieve_similar(problem.problem)
                for m in matches:
                    if m.problem not in seen:
                        seen.add(m.problem)
                        prior_insights.append(m)
            except Exception:
                logger.exception("retrieve_similar failed for %r; skipping", problem.problem)

    problems_data = [
        {
            "problem": p.problem,
            "type": p.type,
            "average_rating": p.average_rating,
            "vote_count": p.vote_count,
            "severity": p.severity,
            "frequency": p.frequency,
            "example_reviews": p.example_reviews,
        }
        for p in raw_result.problems
    ]
    result = extract_insights(problems_data, build_appstore_refinement_prompt(default, prior_insights), appStorePromptOutput, source="app_store")
    if result is None:
        result = raw_result
    result.title = app_name
    if RAG_READ_ENABLED:
        enrich_problems(result)
    if RAG_WRITE_ENABLED:
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
