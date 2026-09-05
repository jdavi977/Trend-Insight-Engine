"""Boundary tests for app/schemas/runs.py (spec §5).

Covers serialization round-trip + validation rules: GapItem requires ≥2
evidence_quote_ids (PRD §7.7), Coverage.citation_ratio is bounded, spread is
1..5, RunApprove must carry at least one competitor.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import get_args

import pytest
from pydantic import ValidationError

from app.schemas.runs import (
    Competitor,
    Coverage,
    FailedSource,
    FailureReason,
    GapItem,
    PainItem,
    PartialSources,
    PreflightResult,
    Quote,
    RunApprove,
    RunCreate,
    RunResult,
    RunStatus,
)


def _competitor(**overrides):
    base = {
        "source": "youtube",
        "url": "https://youtube.com/watch?v=abc",
        "name": "Competitor",
        "identifier": "abc",
    }
    return Competitor(**{**base, **overrides})


def _quote(qid="q1", **overrides):
    base = {
        "quote_id": qid,
        "source": "youtube",
        "source_id": "abc",
        "text_redacted": "this is the redacted text",
        "like_count": 0,
    }
    return Quote(**{**base, **overrides})


def _gap(**overrides):
    base = {
        "gap_id": "g1",
        "gap": "no offline sync",
        "spread": 3,
        "competitors_present": ["Notion", "Obsidian"],
        "evidence_quote_ids": ["q1", "q2"],
    }
    return GapItem(**{**base, **overrides})


class TestRunCreate:
    def test_requires_non_empty_idea(self):
        with pytest.raises(ValidationError):
            RunCreate(idea="")

    def test_idea_is_the_only_field(self):
        """`target_gap` was folded into `idea` (#88, spec D5) — a run is created
        from one idea string, and a stale extra key is dropped, not rejected."""
        rc = RunCreate(idea="note app", target_gap="offline sync")
        assert rc.model_dump() == {"idea": "note app"}

    def test_round_trip(self):
        rc = RunCreate(idea="note app")
        assert RunCreate.model_validate(rc.model_dump()) == rc


class TestCompetitor:
    def test_source_must_be_known(self):
        with pytest.raises(ValidationError):
            _competitor(source="reddit")

    def test_appstore_source_accepted(self):
        c = _competitor(source="appstore")
        assert c.source == "appstore"


class TestRunApprove:
    def test_requires_at_least_one_competitor(self):
        with pytest.raises(ValidationError):
            RunApprove(competitors=[])

    def test_low_signal_ack_defaults_none(self):
        ra = RunApprove(competitors=[_competitor()])
        assert ra.acknowledged_low_signal is None


class TestQuote:
    def test_like_count_non_negative(self):
        with pytest.raises(ValidationError):
            _quote(like_count=-1)


class TestPainItem:
    def test_requires_quote_ids(self):
        with pytest.raises(ValidationError):
            PainItem(source="youtube", source_id="abc", text="bad ui", quote_ids=[])


class TestGapItem:
    def test_requires_two_evidence_quote_ids(self):
        with pytest.raises(ValidationError):
            _gap(evidence_quote_ids=["q1"])

    def test_spread_non_negative(self):
        with pytest.raises(ValidationError):
            _gap(spread=-1)

    def test_round_trip(self):
        g = _gap()
        assert GapItem.model_validate(g.model_dump()) == g


class TestCoverage:
    def test_citation_ratio_bounded(self):
        with pytest.raises(ValidationError):
            Coverage(quotes_retrieved=100, quotes_cited=12, citation_ratio=1.5)

    def test_happy_path(self):
        c = Coverage(quotes_retrieved=184, quotes_cited=12, citation_ratio=0.065)
        assert c.citation_ratio == pytest.approx(0.065)


class TestPreflightResult:
    def test_signal_strength_constrained(self):
        with pytest.raises(ValidationError):
            PreflightResult(
                category="notes",
                signal_strength="strong",
                signal_reasoning="r",
                candidates=[_competitor()],
            )

    def test_round_trip(self):
        pr = PreflightResult(
            category="notes",
            signal_strength="high",
            signal_reasoning="established consumer category",
            candidates=[_competitor()],
        )
        assert PreflightResult.model_validate(pr.model_dump()) == pr

    def test_no_sources_false_when_candidates_present(self):
        # US-S1 signal (slice 2 §6): driven by candidate count, serialised out.
        pr = PreflightResult(
            category="notes",
            signal_strength="high",
            signal_reasoning="r",
            candidates=[_competitor()],
        )
        assert pr.no_sources is False
        assert pr.model_dump()["no_sources"] is False

    def test_no_sources_true_when_zero_candidates(self):
        pr = PreflightResult(
            category="notes",
            signal_strength="low",
            signal_reasoning="r",
            candidates=[],
        )
        assert pr.no_sources is True
        assert pr.model_dump()["no_sources"] is True

    def _pr(self, n_candidates, signal_strength="high"):
        return PreflightResult(
            category="notes",
            signal_strength=signal_strength,
            signal_reasoning="r",
            candidates=[
                _competitor(identifier=f"c{i}") for i in range(n_candidates)
            ],
        )

    def test_low_signal_true_below_threshold(self):
        # 1..threshold-1 candidates → the low-signal acknowledgement band (issue #69).
        pr = self._pr(3)
        assert pr.low_signal is True
        assert pr.model_dump()["low_signal"] is True

    def test_low_signal_false_at_threshold(self):
        # >= threshold (4) candidates proceed freely regardless of LLM grade.
        pr = self._pr(4, signal_strength="low")
        assert pr.low_signal is False
        assert pr.model_dump()["low_signal"] is False

    def test_low_signal_false_when_zero_candidates(self):
        # 0 candidates is the US-S1 no-sources band, not low-signal — mutually exclusive.
        pr = self._pr(0)
        assert pr.low_signal is False
        assert pr.no_sources is True


class TestRunStatus:
    def test_lifecycle_states(self):
        """`reported` left with the feedback + report surface (scope-down #89):
        the lifecycle is pending → preflight_ready → running → done | failed."""
        assert set(get_args(RunStatus)) == {
            "pending",
            "preflight_ready",
            "running",
            "done",
            "failed",
        }


class TestFailureReason:
    def test_enum_values(self):
        assert {r.value for r in FailureReason} == {
            "server_restart",
            "sources_below_threshold",
            "internal_error",
        }


class TestPartialSources:
    def test_round_trip(self):
        ps = PartialSources(
            failed=[FailedSource(source="youtube", name="Obsidian demo", reason="timeout")],
            succeeded_count=8,
            total_count=10,
        )
        assert PartialSources.model_validate(ps.model_dump()) == ps

    def test_failed_source_requires_non_empty_reason(self):
        with pytest.raises(ValidationError):
            FailedSource(source="appstore", name="Notion", reason="")

    def test_counts_non_negative(self):
        with pytest.raises(ValidationError):
            PartialSources(failed=[], succeeded_count=-1, total_count=0)


class TestRunResult:
    def test_full_round_trip(self):
        rr = RunResult(
            run_id="11111111-1111-1111-1111-111111111111",
            idea="note app",
            created_at=datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc),
            category="notes",
            signal_strength="high",
            signal_reasoning="established consumer category",
            competitors=[_competitor()],
            gaps=[_gap()],
            quotes={"q1": _quote("q1"), "q2": _quote("q2")},
            coverage=Coverage(quotes_retrieved=184, quotes_cited=12, citation_ratio=0.065),
        )
        assert RunResult.model_validate(rr.model_dump()) == rr

    def test_carries_no_idea_match(self):
        """The idea-match stage was folded away (#88, spec A4) — a terminal
        result is gaps + quotes + coverage, with no separate match verdict."""
        rr = RunResult(
            run_id="r",
            idea="x",
            created_at=datetime(2026, 5, 28, tzinfo=timezone.utc),
            category="c",
            signal_strength="medium",
            signal_reasoning="r",
            competitors=[_competitor()],
            gaps=[_gap()],
            quotes={"q1": _quote("q1"), "q2": _quote("q2")},
            coverage=Coverage(quotes_retrieved=10, quotes_cited=2, citation_ratio=0.2),
        )
        assert "idea_match" not in rr.model_dump()
