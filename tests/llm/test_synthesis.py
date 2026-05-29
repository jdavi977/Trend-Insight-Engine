"""Synthesis stage tests — grounding contract + coverage maths.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §5 (grounding rules), §8.
The LLM call is mocked at app.llm.synthesis.create_chat_completion; we drive
candidate sets directly to exercise the validator and coverage paths.
"""
from __future__ import annotations

import json

import pytest

from app.llm.synthesis import synthesize
from app.schemas.runs import PainItem, Quote
from tests.conftest import load_fixture

MOCK_TARGET = "app.llm.synthesis.create_chat_completion"
RESOLVE_TARGET = "app.llm.synthesis.resolve"


@pytest.fixture
def pool():
    raw = load_fixture("synthesis_quote_pool.json")
    quotes = [Quote(**q) for q in raw["quotes"]]
    pain_items = [PainItem(**p) for p in raw["pain_items"]]
    return {
        "idea": raw["idea"],
        "target_gap": raw["target_gap"],
        "quotes": quotes,
        "pain_items": pain_items,
    }


def _mock_llm(mocker, gaps_payload):
    mocker.patch(MOCK_TARGET, return_value=json.dumps({"gaps": gaps_payload}))


class TestHappyPath:
    def test_three_grounded_gaps_all_survive(self, pool, mocker):
        _mock_llm(mocker, [
            {
                "gap": "Offline edits lost or overwritten on reconnect",
                "severity": 5,
                "evidence_quote_ids": ["q01", "q05", "q09", "q13", "q17", "q20"],
            },
            {
                "gap": "Mobile editor lags on long notes",
                "severity": 3,
                "evidence_quote_ids": ["q02", "q07", "q12", "q18"],
            },
            {
                "gap": "Pricing perceived as excessive",
                "severity": 2,
                "evidence_quote_ids": ["q03", "q14"],
            },
        ])

        gaps, coverage = synthesize(**pool)

        assert len(gaps) == 3
        assert gaps[0].gap_id == "gap_001"
        assert gaps[1].gap_id == "gap_002"
        assert gaps[2].gap_id == "gap_003"
        assert all(len(g.evidence_quote_ids) >= 2 for g in gaps)
        assert coverage.quotes_retrieved == 21
        # 6 + 4 + 2 = 12 distinct cited IDs
        assert coverage.quotes_cited == 12
        assert coverage.citation_ratio == pytest.approx(12 / 21)

    def test_spread_and_competitors_present_computed_from_quote_sources(self, pool, mocker):
        _mock_llm(mocker, [
            {
                "gap": "Offline edits lost on reconnect",
                "severity": 5,
                "evidence_quote_ids": ["q01", "q09", "q13", "q17"],
            },
        ])

        gaps, _ = synthesize(**pool)

        gap = gaps[0]
        assert gap.frequency == 4
        assert gap.spread == 4
        assert set(gap.competitors_present) == {
            "youtube:notion_review",
            "youtube:obsidian_review",
            "appstore:bear_app",
            "appstore:evernote",
        }

    def test_single_competitor_gap_has_spread_one(self, pool, mocker):
        _mock_llm(mocker, [
            {
                "gap": "Bear iCloud sync drops edits",
                "severity": 4,
                "evidence_quote_ids": ["q11", "q13"],
            },
        ])

        gaps, _ = synthesize(**pool)

        assert gaps[0].spread == 1
        assert gaps[0].competitors_present == ["appstore:bear_app"]


class TestGroundingValidator:
    def test_gap_with_one_citation_rejected(self, pool, mocker):
        _mock_llm(mocker, [
            {"gap": "Solo gripe", "severity": 3, "evidence_quote_ids": ["q01"]},
            {
                "gap": "Real recurring gap",
                "severity": 4,
                "evidence_quote_ids": ["q01", "q05", "q17"],
            },
        ])

        gaps, coverage = synthesize(**pool)

        assert len(gaps) == 1
        assert gaps[0].gap == "Real recurring gap"
        assert gaps[0].gap_id == "gap_001"
        assert coverage.quotes_cited == 3

    def test_gap_with_hallucinated_quote_id_rejected(self, pool, mocker):
        _mock_llm(mocker, [
            {
                "gap": "Hallucinated cite",
                "severity": 5,
                "evidence_quote_ids": ["q01", "q999"],
            },
            {
                "gap": "Grounded cite",
                "severity": 4,
                "evidence_quote_ids": ["q02", "q07"],
            },
        ])

        gaps, coverage = synthesize(**pool)

        assert len(gaps) == 1
        assert gaps[0].gap == "Grounded cite"
        assert coverage.quotes_cited == 2

    def test_duplicate_quote_ids_collapsed_then_count_checked(self, pool, mocker):
        """A gap citing the same ID twice has only one real citation — reject."""
        _mock_llm(mocker, [
            {
                "gap": "Looks-like-two-but-is-one",
                "severity": 3,
                "evidence_quote_ids": ["q01", "q01"],
            },
        ])

        gaps, coverage = synthesize(**pool)

        assert gaps == []
        assert coverage.quotes_cited == 0
        assert coverage.citation_ratio == 0.0

    def test_invalid_severity_drops_only_that_gap(self, pool, mocker):
        _mock_llm(mocker, [
            {"gap": "Bad severity", "severity": 99, "evidence_quote_ids": ["q01", "q05"]},
            {"gap": "Good gap", "severity": 4, "evidence_quote_ids": ["q11", "q13"]},
        ])

        gaps, _ = synthesize(**pool)

        assert len(gaps) == 1
        assert gaps[0].gap == "Good gap"


class TestRoutingAndPromptShape:
    def test_synthesis_call_uses_router_resolved_config(self, pool, mocker):
        mock_call = mocker.patch(
            MOCK_TARGET,
            return_value=json.dumps({"gaps": [
                {"gap": "g", "severity": 3, "evidence_quote_ids": ["q01", "q05"]}
            ]}),
        )

        synthesize(**pool)

        kwargs = mock_call.call_args.kwargs
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == pytest.approx(0.3)
        assert kwargs["max_tokens"] == 6000

    def test_user_message_includes_idea_target_gap_and_every_quote_id(self, pool, mocker):
        mock_call = mocker.patch(
            MOCK_TARGET,
            return_value=json.dumps({"gaps": []}),
        )
        pool["target_gap"] = "offline reliability"

        synthesize(**pool)

        user_msg = mock_call.call_args.kwargs["messages"][1]["content"]
        assert "idea:" in user_msg
        assert pool["idea"] in user_msg
        assert "offline reliability" in user_msg
        for q in pool["quotes"]:
            assert q.quote_id in user_msg


class TestDegenerateLLMOutput:
    def test_invalid_json_returns_empty_gaps_with_zero_coverage(self, pool, mocker):
        mocker.patch(MOCK_TARGET, return_value="not valid json {{{")

        gaps, coverage = synthesize(**pool)

        assert gaps == []
        assert coverage.quotes_retrieved == 21
        assert coverage.quotes_cited == 0
        assert coverage.citation_ratio == 0.0

    def test_missing_gaps_key_returns_empty(self, pool, mocker):
        mocker.patch(MOCK_TARGET, return_value=json.dumps({"problems": []}))

        gaps, coverage = synthesize(**pool)

        assert gaps == []
        assert coverage.quotes_cited == 0

    def test_bare_list_response_treated_as_gaps(self, pool, mocker):
        mocker.patch(
            MOCK_TARGET,
            return_value=json.dumps([
                {"gap": "wrapped", "severity": 3, "evidence_quote_ids": ["q01", "q05"]},
            ]),
        )

        gaps, _ = synthesize(**pool)

        assert len(gaps) == 1
        assert gaps[0].gap == "wrapped"

    def test_empty_pool_yields_zero_ratio_no_divide_by_zero(self, mocker):
        mocker.patch(MOCK_TARGET, return_value=json.dumps({"gaps": []}))

        gaps, coverage = synthesize(
            idea="x", target_gap=None, quotes=[], pain_items=[]
        )

        assert gaps == []
        assert coverage.quotes_retrieved == 0
        assert coverage.citation_ratio == 0.0
