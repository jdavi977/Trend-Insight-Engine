from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Union


class YoutubeProblemItem(BaseModel):
    problem: str = Field(min_length=5)
    type: str = Field(min_length=2)
    total_likes: int = Field(ge=0)
    severity: int = Field(ge=1, le=5)
    frequency: int = Field(ge=1, le=5)


class AppStoreProblemItem(BaseModel):
    problem: str = Field(min_length=5)
    type: str = Field(min_length=2)
    average_rating: float = Field(ge=0, le=5)
    severity: int = Field(ge=1, le=5)
    frequency: int = Field(ge=1, le=5)
    example_reviews: List[str] = Field(min_length=1)


ProblemItem = Union[YoutubeProblemItem, AppStoreProblemItem]


class LLMExtraction(BaseModel):
    source: Literal["youtube", "app_store"]
    title: Optional[str] = None
    problems: List[ProblemItem] = Field(min_length=1)