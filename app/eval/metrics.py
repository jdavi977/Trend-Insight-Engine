"""The four PRD §7.9 eval scorers, as pure functions.

Spec: planning/specs/v2-slice-3-eval-and-v1-removal_spec.md §4 (metrics table).

Every function here is pure: it takes already-computed pipeline output (gaps,
the quote pool, coverage, the severity distribution) and returns a score. No
network, no service imports, no `resolve(stage)` — only `app.schemas.runs`
domain models — so the scorers are unit-testable without a live pipeline. The
harness ([app/eval/harness.py](harness.py)) drives the real pipeline and feeds
its output into these.

Pinned thresholds (Open Question 2 / §4) live in this file by design: a scorer's
verdict must be reproducible from the source, not a runtime config. Changing one
is an explicit, reviewable edit here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.schemas.runs import Coverage, GapItem

# --- pinned thresholds (OQ2 / §4) -------------------------------------------

# Gap-recall matcher: a labelled gap counts as "surfaced" when at least this
# fraction of its meaningful (non-stopword) tokens appear in some output gap's
# text. Recall-oriented overlap (see `_match_score`) — forgiving of an output
# gap that restates the labelled pain in more words, strict on topic drift.
GAP_RECALL_MATCH_THRESHOLD = 0.6

# Severity calibration: flag a run as mis-calibrated when more than this share of
# its gaps cluster at the top (4–5 → inflation) or bottom (1–2 → deflation) of
# the rubric. >80% one-sided is the §4 inflation/deflation trip wire.
SEVERITY_SKEW_THRESHOLD = 0.8

# Grounding contract (§4 hallucination): every gap must cite at least this many
# quotes, all from the retrieval pool. Mirrors the synthesis validator
# (schemas/runs.py GapItem.evidence_quote_ids min_length=2) so a non-zero
# hallucination count in eval means that validator regressed.
_MIN_CITATIONS = 2

# Tokens that carry no topical signal — dropped before matching so a labelled
# gap and an output gap aren't credited for sharing "the" or "with".
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "could",
    "do", "for", "from", "has", "have", "in", "is", "it", "its", "more", "no",
    "not", "of", "on", "or", "that", "the", "their", "them", "they", "this",
    "to", "too", "very", "was", "what", "when", "which", "with", "you", "your",
})

_TOKEN_RE = re.compile(r"[a-z0-9]+")


# --- gap recall -------------------------------------------------------------


@dataclass
class PerGapRecall:
    """Whether one labelled gap surfaced, and the best output match it found."""

    expected: str
    matched: bool
    score: float
    best_match: Optional[str]


@dataclass
class GapRecallResult:
    """Per-idea gap-recall scorecard (§4): how many labelled gaps surfaced."""

    hit: int
    miss: int
    per_gap: list[PerGapRecall] = field(default_factory=list)


def _tokens(text: str) -> set[str]:
    """Lowercase, split to alphanumeric tokens, drop stopwords."""
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _match_score(expected: str, output: str) -> float:
    """Fraction of the labelled gap's meaningful tokens present in the output gap.

    Recall-oriented overlap (|expected ∩ output| / |expected|) rather than
    Jaccard: an output gap that describes the same pain in extra words shouldn't
    be penalised for length, but an output that covers only part of the labelled
    pain scores below 1. Empty expected-token sets (all-stopword labels) score 0.
    """
    expected_tokens = _tokens(expected)
    if not expected_tokens:
        return 0.0
    return len(expected_tokens & _tokens(output)) / len(expected_tokens)


def gap_recall(expected_gaps: list[str], output_gap_texts: list[str]) -> GapRecallResult:
    """Score each labelled gap against the output gap texts (§4 gap recall).

    For every expected gap, find its best fuzzy token-set match among the output
    gaps; it's a *hit* when that best score ≥ `GAP_RECALL_MATCH_THRESHOLD`. Pure
    over the strings — the harness passes labelled gap strings and the synthesised
    `GapItem.gap` texts.
    """
    per_gap: list[PerGapRecall] = []
    for expected in expected_gaps:
        best_score = 0.0
        best_match: Optional[str] = None
        for output in output_gap_texts:
            score = _match_score(expected, output)
            if score > best_score:
                best_score = score
                best_match = output
        matched = best_score >= GAP_RECALL_MATCH_THRESHOLD
        per_gap.append(
            PerGapRecall(
                expected=expected,
                matched=matched,
                score=round(best_score, 4),
                best_match=best_match if matched else None,
            )
        )

    hit = sum(1 for p in per_gap if p.matched)
    return GapRecallResult(hit=hit, miss=len(per_gap) - hit, per_gap=per_gap)


# --- hallucination rate -----------------------------------------------------


def hallucination_count(gaps: list[GapItem], quote_pool_ids: set[str]) -> int:
    """Count gaps with broken grounding (§4 hallucination rate).

    A gap is a hallucination when it cites fewer than `_MIN_CITATIONS` quotes or
    references a `quote_id` outside the retrieval pool. Production rejects these
    pre-persist (synthesis grounding validator), so in eval this should read ~0;
    a non-zero count means that validator regressed.
    """
    count = 0
    for gap in gaps:
        if len(gap.evidence_quote_ids) < _MIN_CITATIONS:
            count += 1
        elif any(qid not in quote_pool_ids for qid in gap.evidence_quote_ids):
            count += 1
    return count


# --- citation ratio ---------------------------------------------------------


def citation_ratio(coverage: Optional[Coverage]) -> float:
    """Fraction of retrieved evidence the synthesis used (§4 citation ratio).

    Pass-through of `coverage.citation_ratio` (already computed in `RunResult`),
    surfaced here so the harness logs one metric per scorer. `0.0` when a run
    produced no coverage (e.g. zero candidates → no retrieval).
    """
    if coverage is None:
        return 0.0
    return coverage.citation_ratio


# --- severity calibration ---------------------------------------------------


def severity_flag(severity_distribution: list[int]) -> Optional[str]:
    """Flag a one-sided severity distribution (§4 severity calibration).

    Reads `quality_signals.severity_distribution` (length-5: gap counts at
    severity 1–5). Returns `"inflation"` when >80% of gaps sit at 4–5,
    `"deflation"` when >80% sit at 1–2, else `None`. No gaps → `None` (nothing to
    calibrate).
    """
    total = sum(severity_distribution)
    if total == 0:
        return None
    high_share = (severity_distribution[3] + severity_distribution[4]) / total
    low_share = (severity_distribution[0] + severity_distribution[1]) / total
    if high_share > SEVERITY_SKEW_THRESHOLD:
        return "inflation"
    if low_share > SEVERITY_SKEW_THRESHOLD:
        return "deflation"
    return None
