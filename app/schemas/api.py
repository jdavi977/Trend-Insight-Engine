from typing import Optional

from pydantic import BaseModel

from app.schemas.llm import LLMExtraction


class YoutubeAnalyzeRequest(BaseModel):
    youtubeURL: str


class AppStoreAnalyzeRequest(BaseModel):
    appStoreURL: str


class DataSave(BaseModel):
    data: dict


class YoutubeAnalysisResponse(LLMExtraction):
    channel_name: Optional[str] = None
    published_at: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    subscriber_count: Optional[int] = None
    duration: Optional[str] = None


class AppStoreAnalysisResponse(LLMExtraction):
    thumbnail: Optional[str] = None
    seller: Optional[str] = None
    genre: Optional[str] = None
    age_rating: Optional[str] = None
    average_rating: Optional[float] = None
    rating_count: Optional[int] = None
