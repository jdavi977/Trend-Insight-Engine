"""Seed-set validation + harness smoke run (slice 3 §4 / issue #71).

Two concerns:

1. **Seed set is well-formed** — the 5 checked-in seed files match the schema
   `harness.py` consumes (one per category, 3–5 expected gaps + severity ranges)
   and are flagged `agent_drafted` pending human review.

2. **The harness writes a report for every seed.** The real harness drives the
   live pipeline (OpenAI / YouTube / App Store) — too costly and non-deterministic
   for CI — so here we patch `_drive_pipeline` to a synthetic `RunResult` and
   exercise the load → score → write-report path end to end over all five seeds.
   The live smoke run is an operator step (see `seed/README.md`).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.eval import harness
from app.schemas.runs import (
    Competitor,
    Coverage,
    GapItem,
    QualitySignals,
    Quote,
    RunResult,
)

# Every PRD §7.9 bucket must be represented exactly once across the seed dir.
EXPECTED_CATEGORIES = {
    "consumer-app",
    "mobile-game",
    "creator-tool",
    "productivity",
    "low-signal",
}

SEED_STEMS = sorted(p.stem for p in harness.SEED_DIR.glob("*.json"))


def _synthetic_result(seed: harness.SeedIdea) -> RunResult:
    """A minimal `done` RunResult that surfaces the seed's first expected gap.

    Enough structure for every scorer to run: one grounded gap (so recall finds a
    hit), a quote pool the gap cites (so hallucination_count == 0), coverage, and
    quality_signals carrying a severity distribution.
    """
    quotes = {
        "q1": Quote(quote_id="q1", source="youtube", source_id="v1",
                    text_redacted="users complain it breaks", like_count=3),
        "q2": Quote(quote_id="q2", source="appstore", source_id="a1",
                    text_redacted="same problem here", like_count=1),
    }
    first_gap = seed.expected_gaps[0].gap if seed.expected_gaps else "a gap"
    gaps = [
        GapItem(gap_id="g1", gap=first_gap, severity=4, frequency=5, spread=2,
                competitors_present=["A", "B"], evidence_quote_ids=["q1", "q2"]),
    ]
    return RunResult(
        run_id="evaltest",
        idea=seed.idea,
        target_gap=seed.target_gap,
        created_at=datetime.now(timezone.utc),
        category="consumer_app",
        signal_strength="high",
        signal_reasoning="synthetic",
        competitors=[Competitor(source="appstore", url="https://x", name="A", identifier="1")],
        gaps=gaps,
        quotes=quotes,
        coverage=Coverage(quotes_retrieved=2, quotes_cited=2, citation_ratio=1.0),
        quality_signals=QualitySignals(
            quote_source_diversity=1.0,
            severity_distribution=[0, 0, 0, 1, 0],
            single_source_gap_count=0,
        ),
    )


# --- seed set is well-formed ------------------------------------------------


def test_exactly_five_seed_files():
    assert len(SEED_STEMS) == 5


@pytest.mark.parametrize("stem", SEED_STEMS)
def test_seed_file_matches_schema_and_gap_count(stem):
    seed = harness.load_seed(stem)
    # §4: each seed carries 3–5 hand-labelled expected gaps.
    assert 3 <= len(seed.expected_gaps) <= 5
    for g in seed.expected_gaps:
        lo, hi = g.severity_range
        assert 1 <= lo <= hi <= 5


def test_one_seed_per_category():
    categories = {harness.load_seed(s).category for s in SEED_STEMS}
    assert categories == EXPECTED_CATEGORIES


@pytest.mark.parametrize("stem", SEED_STEMS)
def test_checked_in_seeds_are_agent_drafted(stem):
    # The slice-3 labels are agent-authored and pending human confirmation.
    assert harness.load_seed(stem).label_status == "agent_drafted"


# --- label_status schema default --------------------------------------------


def test_label_status_defaults_to_agent_drafted():
    # An unmarked file is treated as unconfirmed, never mistaken for vetted.
    seed = harness.SeedIdea(idea="x", category="consumer-app")
    assert seed.label_status == "agent_drafted"


def test_label_status_rejects_unknown_value():
    with pytest.raises(ValidationError):
        harness.SeedIdea(idea="x", category="consumer-app", label_status="bogus")


# --- harness writes a report for every seed (smoke run) ---------------------


@pytest.mark.parametrize("stem", SEED_STEMS)
def test_harness_writes_scored_report_per_seed(stem, tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)

    seed = harness.load_seed(stem)
    fake_drive = AsyncMock(return_value=(_synthetic_result(seed), None))
    monkeypatch.setattr(harness, "_drive_pipeline", fake_drive)

    assert harness.main([stem]) == 0

    report_path = tmp_path / f"{stem}.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())

    # §4 report shape + the provenance flag a reviewer reads.
    assert report["idea"] == seed.idea
    assert report["category"] == seed.category
    assert report["label_status"] == "agent_drafted"
    assert {"gap_recall", "hallucination_count", "citation_ratio", "severity_flag"} <= report.keys()
    # The synthetic result echoes the first expected gap → recall finds it.
    assert report["gap_recall"]["hit"] >= 1
    assert report["hallucination_count"] == 0


def test_harness_writes_failure_report_when_run_unscored(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)
    # Pre-flight found nothing → no scorable output, but a report still lands.
    fake_drive = AsyncMock(return_value=(None, "no_candidates"))
    monkeypatch.setattr(harness, "_drive_pipeline", fake_drive)

    assert harness.main(["consumer_app"]) == 0

    report = json.loads((tmp_path / "consumer_app.json").read_text())
    assert report["failure_reason"] == "no_candidates"
    assert report["label_status"] == "agent_drafted"
    assert report["output_gaps"] == []
