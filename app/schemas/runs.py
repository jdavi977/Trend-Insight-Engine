"""Domain models for v2 idea-runs pipeline.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §5.
Persisted shape: planning/specs/v2-slice-1-end-to-end_spec.md §4.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, computed_field

from app.config.constants import LOW_SIGNAL_CANDIDATE_THRESHOLD

SourceLiteral = Literal["youtube", "appstore"]
SignalStrength = Literal["high", "medium", "low"]
# The whole run lifecycle. The admin-hidden state behind the old
# POST /runs/:id/report left with that surface in the scope-down (issue #89),
# so `done` and `failed` are the only terminal states.
RunStatus = Literal["pending", "preflight_ready", "running", "done", "failed"]


class FailureReason(str, Enum):
    """Constrained failure causes (slice 2 §5.3, promoted from slice-1 freeform).

    `internal_error` is the catch-all the `except Exception` path maps to; the
    others are the specific sad paths the hardening layer detects.

    `budget_exhausted` was removed with the daily OpenAI budget guard — nothing
    can write it any more. The DB CHECK constraint
    (ops/migrations/002_slice2_lifecycle_hardening.sql) still permits the value;
    that is a harmless superset, since no writer emits it.
    """

    server_restart = "server_restart"
    sources_below_threshold = "sources_below_threshold"
    internal_error = "internal_error"


class RunCreate(BaseModel):
    idea: str = Field(min_length=1)


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
    it physically excludes `idea` so confirmation bias cannot leak into
    per-source prompts.
    """
    source: SourceLiteral
    source_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    title: Optional[str] = None


class GapItem(BaseModel):
    gap_id: str = Field(min_length=1)
    gap: str = Field(min_length=1)
    spread: int = Field(ge=0)
    competitors_present: List[str] = Field(default_factory=list)
    evidence_quote_ids: List[str] = Field(min_length=2)


class Coverage(BaseModel):
    quotes_retrieved: int = Field(ge=0)
    quotes_cited: int = Field(ge=0)
    citation_ratio: float = Field(ge=0.0, le=1.0)


class FailedSource(BaseModel):
    """One source that failed the pipeline (slice 2 §5.1)."""

    source: SourceLiteral
    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class PartialSources(BaseModel):
    """Partial-completion summary persisted to `partial_sources_json` (slice 2 §5.1).

    Present on a `done` run only when ≥1 source failed but the ≥70% threshold
    held; drives the Result-page banner naming the failures.
    """

    failed: List[FailedSource] = Field(default_factory=list)
    succeeded_count: int = Field(ge=0)
    total_count: int = Field(ge=0)


class PreflightResult(BaseModel):
    category: str
    signal_strength: SignalStrength
    signal_reasoning: str
    candidates: List[Competitor]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def no_sources(self) -> bool:
        """US-S1 (slice 2 §6): zero candidates → the frontend renders the
        "No public sources found" state instead of an unrunnable approve flow."""
        return len(self.candidates) == 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def low_signal(self) -> bool:
        """Count-derived low-signal flag (slice 3 §6, issue #69).

        True when pre-flight found *some* but **fewer than
        `LOW_SIGNAL_CANDIDATE_THRESHOLD`** candidates — the band that requires an
        explicit `acknowledged_low_signal` to approve. Mutually exclusive with
        `no_sources` (0 candidates): the frontend reads this flag to drive the
        acknowledgement so it never re-implements the threshold, and reads
        `no_sources` for the US-S1 state. Same gate the backend enforces in
        `run_pipeline_service.approve`."""
        return 0 < len(self.candidates) < LOW_SIGNAL_CANDIDATE_THRESHOLD


class RunResult(BaseModel):
    run_id: str
    idea: str
    created_at: datetime
    category: str
    signal_strength: SignalStrength
    signal_reasoning: str
    competitors: List[Competitor]
    gaps: List[GapItem]
    quotes: dict[str, Quote]
    coverage: Coverage
    partial_sources: Optional[PartialSources] = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: RunStatus
    preflight: PreflightResult


class RunStateResponse(BaseModel):
    """Permissive view of a single `idea_runs` row at any lifecycle stage.

    Fields populated by later pipeline stages (gaps, coverage) are optional so a
    `preflight_ready` row serialises cleanly. Once slice 1's background pipeline
    lands, the `done` view is the union of this shape and the `gaps` table —
    RunResult stays the strict "terminal" view.
    """

    run_id: str
    idea: str
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
    partial_sources: Optional[PartialSources] = None
    failure_reason: Optional[str] = None


class RunFeedItem(BaseModel):
    run_id: str
    idea: str
    completed_at: datetime
