from typing import Literal, Optional

from pydantic import BaseModel


class RetrievedInsight(BaseModel):
    problem: str
    type: str
    severity: int
    frequency: int
    source: Literal["youtube", "app_store"]
    source_url: str
    title: Optional[str] = None
    extracted_at: str
    similarity: float


class SimilarInsightsResponse(BaseModel):
    query: str
    results: list[RetrievedInsight]
