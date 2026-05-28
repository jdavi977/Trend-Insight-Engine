"""Domain models for v2 idea-runs pipeline.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §5.
Persisted shape: planning/specs/v2-slice-1-end-to-end_spec.md §4.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

SourceLiteral = Literal["youtube", "appstore"]
SignalStrength = Literal["high", "medium", "low"]
RunStatus = Literal["pending", "preflight_ready", "running", "done", "failed"]
IdeaMatchVerdict = Literal["matches", "partial", "no_match"]


class RunCreate(BaseModel):
    idea: str = Field(min_length=1)
    target_gap: Optional[str] = None


class Competitor(BaseModel):
    source: SourceLiteral
    url: str = Field(min_length=1)
    name: str = Field(min_length=1)
    identifier: str = Field(min_length=1)


class RunApprove(BaseModel):
    competitors: List[Competitor] = Field(min_length=1)
    acknowledged_low_signal: Optional[bool] = None


class Quote(BaseModel):
    quote_id: str = Field(min_length=1)
    source: SourceLiteral
    source_id: str = Field(min_length=1)
    text_redacted: str
    like_count: int = Field(ge=0)


class PainItem(BaseModel):
    source: SourceLiteral
    source_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    quote_ids: List[str] = Field(min_length=1)


class GapItem(BaseModel):
    gap_id: str = Field(min_length=1)
    gap: str = Field(min_length=1)
    severity: int = Field(ge=1, le=5)
    frequency: int = Field(ge=0)
    spread: int = Field(ge=0)
    competitors_present: List[str] = Field(default_factory=list)
    evidence_quote_ids: List[str] = Field(min_length=2)


class Coverage(BaseModel):
    quotes_retrieved: int = Field(ge=0)
    quotes_cited: int = Field(ge=0)
    citation_ratio: float = Field(ge=0.0, le=1.0)


class IdeaMatch(BaseModel):
    gap_id: str = Field(min_length=1)
    verdict: IdeaMatchVerdict
    evidence_quote_ids: List[str] = Field(default_factory=list)


class PreflightResult(BaseModel):
    category: str
    signal_strength: SignalStrength
    signal_reasoning: str
    candidates: List[Competitor]


class RunResult(BaseModel):
    run_id: str
    idea: str
    target_gap: Optional[str] = None
    created_at: datetime
    category: str
    signal_strength: SignalStrength
    signal_reasoning: str
    competitors: List[Competitor]
    gaps: List[GapItem]
    quotes: dict[str, Quote]
    coverage: Coverage
    idea_match: Optional[IdeaMatch] = None
