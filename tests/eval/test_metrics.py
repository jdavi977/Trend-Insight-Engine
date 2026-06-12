"""Unit tests for the four PRD §7.9 eval scorers (slice 3 §4).

These hit `app.eval.metrics` for real — the scorers are pure functions over
domain models with no service/network imports, so no mocking is needed.
"""
from __future__ import annotations

from app.eval import metrics
from app.schemas.runs import Coverage, GapItem


def _gap(gap_id="g1", gap="sync drops edits", severity=3, frequency=5, spread=2,
         evidence_quote_ids=("q1", "q2")):
    return GapItem(
        gap_id=gap_id,
        gap=gap,
        severity=severity,
        frequency=frequency,
        spread=spread,
        competitors_present=["A", "B"],
        evidence_quote_ids=list(evidence_quote_ids),
    )


# --- gap recall -------------------------------------------------------------


def test_gap_recall_exact_topic_match_is_hit():
    result = metrics.gap_recall(
        ["offline sync silently drops edits"],
        ["users report offline sync silently drops their edits"],
    )
    assert result.hit == 1
    assert result.miss == 0
    assert result.per_gap[0].matched is True
    assert result.per_gap[0].best_match is not None


def test_gap_recall_unrelated_gap_is_miss():
    result = metrics.gap_recall(
        ["offline sync silently drops edits"],
        ["the onboarding tutorial is confusing"],
    )
    assert result.hit == 0
    assert result.miss == 1
    assert result.per_gap[0].matched is False
    # No credited match → best_match suppressed.
    assert result.per_gap[0].best_match is None


def test_gap_recall_picks_best_of_several_outputs():
    result = metrics.gap_recall(
        ["aggressive ads interrupt gameplay"],
        [
            "the soundtrack is repetitive",
            "aggressive ads constantly interrupt gameplay runs",
        ],
    )
    assert result.hit == 1
    assert result.per_gap[0].best_match == "aggressive ads constantly interrupt gameplay runs"


def test_gap_recall_partial_overlap_below_threshold_is_miss():
    # Shares only "sync" out of three meaningful tokens (1/3 < 0.6).
    result = metrics.gap_recall(
        ["offline sync conflicts"],
        ["calendar sync between phones"],
    )
    assert result.per_gap[0].matched is False
    assert 0.0 < result.per_gap[0].score < metrics.GAP_RECALL_MATCH_THRESHOLD


def test_gap_recall_stopword_only_label_scores_zero():
    result = metrics.gap_recall(["the it is"], ["anything at all here"])
    assert result.per_gap[0].score == 0.0
    assert result.per_gap[0].matched is False


def test_gap_recall_counts_across_multiple_expected():
    result = metrics.gap_recall(
        ["offline sync drops edits", "ads interrupt gameplay"],
        ["offline sync drops user edits"],
    )
    assert result.hit == 1
    assert result.miss == 1


# --- hallucination rate -----------------------------------------------------


def test_hallucination_zero_when_all_grounded():
    gaps = [_gap(evidence_quote_ids=("q1", "q2")), _gap(gap_id="g2", evidence_quote_ids=("q2", "q3"))]
    assert metrics.hallucination_count(gaps, {"q1", "q2", "q3"}) == 0


def test_hallucination_flags_unknown_quote_id():
    gaps = [_gap(evidence_quote_ids=("q1", "qX"))]
    assert metrics.hallucination_count(gaps, {"q1", "q2"}) == 1


def test_hallucination_counts_each_bad_gap_once():
    # Both cited ids are outside the pool — still a single hallucination, not two.
    gaps = [_gap(evidence_quote_ids=("qX", "qY"))]
    assert metrics.hallucination_count(gaps, {"q1", "q2"}) == 1


# --- citation ratio ---------------------------------------------------------


def test_citation_ratio_passes_through_coverage():
    cov = Coverage(quotes_retrieved=10, quotes_cited=4, citation_ratio=0.4)
    assert metrics.citation_ratio(cov) == 0.4


def test_citation_ratio_none_coverage_is_zero():
    assert metrics.citation_ratio(None) == 0.0


# --- severity calibration ---------------------------------------------------


def test_severity_flag_inflation_when_top_heavy():
    # 9/10 gaps at severity 4–5.
    assert metrics.severity_flag([0, 1, 0, 4, 5]) == "inflation"


def test_severity_flag_deflation_when_bottom_heavy():
    assert metrics.severity_flag([6, 3, 0, 0, 1]) == "deflation"


def test_severity_flag_none_when_balanced():
    assert metrics.severity_flag([1, 1, 2, 1, 1]) is None


def test_severity_flag_none_when_no_gaps():
    assert metrics.severity_flag([0, 0, 0, 0, 0]) is None


def test_severity_flag_boundary_not_flagged_at_exactly_80pct():
    # 8/10 at 4–5 is exactly 0.8 — the threshold is strict (>0.8), so no flag.
    assert metrics.severity_flag([1, 1, 0, 4, 4]) is None
