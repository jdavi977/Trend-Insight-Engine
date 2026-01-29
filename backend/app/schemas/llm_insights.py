from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class ProblemItem(BaseModel):
    problem: str = Field(min_length=5)

    type: str = Field(min_length=2)

    total_likes: int = Field(ge=0)

    severity: int = Field(ge=1, le=5)
    frequency: int = Field(ge=1, le=5)

class LLMExtraction(BaseModel):
    source: Literal["youtube", "app_store"]
    title: Optional[str] = None

    problems: List = Field(min_length=1)