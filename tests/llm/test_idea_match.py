"""Idea-match stage tests (issue #50 / spec §8 + §5).

The LLM call is mocked at app.llm.idea_match.create_chat_completion; we drive the
verdict / gap_id / evidence payload directly to exercise routing, grounding, and
the degenerate-output fallbacks.
"""
from __future__ import annotations

import json

import pytest

from app.llm.idea_match import match_idea
from app.schemas.runs import GapItem, Quote

MOCK_TARGET = "app.llm.idea_match.create_chat_completion"


def _quote(qid: str) -> Quote:
    return Quote(
        quote_id=qid,
        source="youtube",
        source_id="vid_1",
        text_redacted="offline sync keeps eating my edits",
        like_count=42,
    )


def _gap(gap_id: str, evidence: list[str]) -> GapItem:
    return GapItem(
        gap_id=gap_id,
        gap="Offline edits lost on reconnect",
        severity=5,
        frequency=len(evidence),
        spread=2,
        competitors_present=["youtube:vid_1", "appstore:app_1"],
        evidence_quote_ids=evidence,
    )


@pytest.fixture
def context():
    quotes = [_quote("q01"), _quote("q02"), _quote("q03")]
    gaps = [
        _gap("gap_001", ["q01", "q02"]),
        _gap("gap_002", ["q02", "q03"]),
    ]
    return {
        "idea": "note-taking app with better offline sync",
        "target_gap": "offline reliability",
        "gaps": gaps,
        "quotes": quotes,
    }


def _mock_llm(mocker, payload):
    return mocker.patch(MOCK_TARGET, return_value=json.dumps(payload))


def test_no_gaps_returns_none_without_calling_llm(mocker):
    mock_call = mocker.patch(MOCK_TARGET)

    result = match_idea("idea", "target", gaps=[], quotes=[_quote("q01")])

    assert result is None
    mock_call.assert_not_called()


def test_matches_verdict_with_grounded_evidence(context, mocker):
    _mock_llm(mocker, {
        "gap_id": "gap_001", "verdict": "matches",
        "evidence_quote_ids": ["q01", "q02"],
    })

    result = match_idea(**context)

    assert result.gap_id == "gap_001"
    assert result.verdict == "matches"
    assert result.evidence_quote_ids == ["q01", "q02"]


def test_evidence_outside_pool_is_filtered(context, mocker):
    _mock_llm(mocker, {
        "gap_id": "gap_002", "verdict": "partial",
        "evidence_quote_ids": ["q03", "q_hallucinated"],
    })

    result = match_idea(**context)

    assert result.gap_id == "gap_002"
    assert result.verdict == "partial"
    assert result.evidence_quote_ids == ["q03"]


def test_unknown_gap_id_falls_back_to_top_gap(context, mocker):
    _mock_llm(mocker, {
        "gap_id": "gap_999", "verdict": "no_match", "evidence_quote_ids": [],
    })

    result = match_idea(**context)

    assert result.gap_id == "gap_001"  # top-ranked gap
    assert result.verdict == "no_match"
    assert result.evidence_quote_ids == []


def test_invalid_verdict_defaults_to_no_match(context, mocker):
    _mock_llm(mocker, {
        "gap_id": "gap_001", "verdict": "definitely", "evidence_quote_ids": [],
    })

    result = match_idea(**context)

    assert result.verdict == "no_match"


def test_invalid_json_defaults_to_no_match_on_top_gap(context, mocker):
    mocker.patch(MOCK_TARGET, return_value="not json {{{")

    result = match_idea(**context)

    assert result.gap_id == "gap_001"
    assert result.verdict == "no_match"
    assert result.evidence_quote_ids == []


def test_routing_and_prompt_shape(context, mocker):
    mock_call = _mock_llm(mocker, {
        "gap_id": "gap_001", "verdict": "matches", "evidence_quote_ids": ["q01", "q02"],
    })

    match_idea(**context)

    kwargs = mock_call.call_args.kwargs
    assert kwargs["model"] == "gpt-4o"
    assert kwargs["temperature"] == pytest.approx(0.2)
    assert kwargs["max_tokens"] == 1500

    user_msg = kwargs["messages"][1]["content"]
    assert context["idea"] in user_msg
    assert context["target_gap"] in user_msg
    assert "gap_001" in user_msg
    for q in context["quotes"]:
        assert q.quote_id in user_msg
