"""Domain models for v2 idea-runs pipeline.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §5.
Persisted shape: planning/specs/v2-slice-1-end-to-end_spec.md §4.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

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


class SourceMetadata(BaseModel):
    """Per-source descriptor for the idea-blinded extractor (spec §8 / §13).

    Lives here because the extractor's signature is part of the v2 boundary —
    it physically excludes `idea` / `target_gap` so confirmation bias cannot
    leak into per-source prompts.
    """
    source: SourceLiteral
    source_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    title: Optional[str] = None


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


class RunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus
    preflight: PreflightResult


class RunStateResponse(BaseModel):
    """Permissive view of a single `idea_runs` row at any lifecycle stage.

    Fields populated by later pipeline stages (gaps, coverage, idea_match) are
    optional so a `preflight_ready` row serialises cleanly. Once slice 1's
    background pipeline lands, the `done` view is the union of this shape and
    the `gaps` table — RunResult stays the strict "terminal" view.
    """

    run_id: str
    idea: str
    target_gap: Optional[str] = None
    status: RunStatus
    created_at: datetime
    updated_at: datetime
    category: Optional[str] = None
    signal_strength: Optional[SignalStrength] = None
    signal_reasoning: Optional[str] = None
    competitors: List[Competitor] = Field(default_factory=list)
    quotes: Dict[str, Quote] = Field(default_factory=dict)
    gaps: List[GapItem] = Field(default_factory=list)
    coverage: Optional[Coverage] = None
    idea_match: Optional[IdeaMatch] = None
    failure_reason: Optional[str] = None


class RunFeedItem(BaseModel):
    run_id: str
    idea: str
    completed_at: datetime
