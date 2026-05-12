from app.rag.rag import retrieve_similar
from app.schemas.rag import RetrievedInsight, SimilarInsightsResponse


def similar(query: str, k: int) -> SimilarInsightsResponse:
    results: list[RetrievedInsight] = retrieve_similar(query, k)
    return SimilarInsightsResponse(query=query, results=results)
