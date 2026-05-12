from pydantic import BaseModel

from app.schemas.llm import LLMExtraction
from app.schemas.rag import RetrievedInsight


class YoutubeAnalyzeRequest(BaseModel):
    youtubeURL: str


class AppStoreAnalyzeRequest(BaseModel):
    appStoreURL: str


class DataSave(BaseModel):
    data: dict


class YoutubeAnalysisResponse(LLMExtraction):
    retrieved_context: list[RetrievedInsight] = []


class AppStoreAnalysisResponse(LLMExtraction):
    retrieved_context: list[RetrievedInsight] = []
