from fastapi import APIRouter, Query

from app.config.constants import RAG_TOP_K
from app.schemas.rag import SimilarInsightsResponse
from app.services.rag_service import similar

router = APIRouter()


@router.get("/insights/similar", response_model=SimilarInsightsResponse)
def get_similar_insights(
    query: str = Query(..., min_length=1),
    k: int = Query(RAG_TOP_K, ge=1, le=50),
):
    return similar(query, k)
