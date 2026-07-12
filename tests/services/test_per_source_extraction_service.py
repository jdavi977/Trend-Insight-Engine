"""Per-source extraction service tests (issue #47 / spec §8 + §13).

The LLM call is mocked at the module's `create_chat_completion`; we drive
candidate pain-item sets directly to exercise the engagement filter, the
quote-id stability property, the grounding contract, and the idea-blinding
structural guarantee.
"""
from __future__ import annotations

import inspect
import json
import logging

import pytest

from app.schemas.runs import SourceMetadata
from app.services import per_source_extraction_service as svc
from app.services.per_source_extraction_service import extract_per_source
from tests.conftest import load_fixture

LLM_TARGET = "app.services.per_source_extraction_service.create_chat_completion"


@pytest.fixture
def fixture():
    raw = load_fixture("per_source_comments_notion.json")
    return {
        "comments": raw["comments"],
        "metadata": SourceMetadata(**raw["source_metadata"]),
    }


def _mock_llm(mocker, pain_items_payload):
    return mocker.patch(LLM_TARGET, return_value=json.dumps({"pain_items": pain_items_payload}))


class TestSignatureIdeaBlinded:
    """The structural guarantee from spec §13: the function physically cannot
    see `idea` / `target_gap`. Verified by inspecting the signature so a future
    refactor that adds those parameters fails CI loudly."""

    def test_signature_has_no_idea_parameter(self):
        params = set(inspect.signature(extract_per_source).parameters)
        assert "idea" not in params
        assert "target_gap" not in params

    def test_signature_accepts_only_comments_and_metadata(self):
        params = list(inspect.signature(extract_per_source).parameters)
        assert params == ["comments", "source_metadata"]


class TestEngagementFilter:
    def test_low_engagement_comments_dropped_before_llm(self, fixture, mocker):
        mock_llm = _mock_llm(mocker, [])

        _, quotes = extract_per_source(**{
            "comments": fixture["comments"], "source_metadata": fixture["metadata"],
        })

        # Productivity defaults: youtube min likes = 50. Fixture has 5 above
        # threshold (142, 88, 60, 33→no it's 33<50 so drops, 71). Wait — recount.
        # Above 50: 142, 88, 60, 71 → 4 quotes.
        assert len(quotes) == 4
        assert all(q.like_count >= 50 for q in quotes)
        assert mock_llm.call_count == 1

    def test_empty_pool_skips_llm_call(self, mocker):
        mock_llm = _mock_llm(mocker, [])
        metadata = SourceMetadata(
            source="youtube", source_id="vid_x", category="productivity"
        )
        # All below threshold.
        comments = [{"Likes": 1, "Text": "barely any engagement"}]

        pain_items, quotes = extract_per_source(comments, metadata)

        assert pain_items == []
        assert quotes == []
        mock_llm.assert_not_called()

    def test_threshold_swaps_with_category(self, mocker):
        """b2b-saas drops the youtube threshold from 50 to 10 — comments that
        productivity would reject now pass."""
        _mock_llm(mocker, [])
        comments = [{"Likes": 15, "Text": "Found this niche devtool genuinely solves my prompt-mgmt pain."}]

        prod_meta = SourceMetadata(source="youtube", source_id="v", category="productivity")
        saas_meta = SourceMetadata(source="youtube", source_id="v", category="b2b-saas")

        assert extract_per_source(comments, prod_meta)[1] == []
        assert len(extract_per_source(comments, saas_meta)[1]) == 1

    def test_appstore_uses_vote_count_field(self, mocker):
        _mock_llm(mocker, [])
        # mobile-game appstore threshold = 4. vote_count comes through as a
        # string from the iTunes RSS feed; the filter must coerce it.
        comments = [
            {"vote_count": "9", "content": "Sync between devices is totally broken for me."},
            {"vote_count": "1", "content": "Below threshold review that should not enter the pool."},
        ]
        metadata = SourceMetadata(
            source="appstore", source_id="app_bundle_x", category="mobile-game"
        )

        _, quotes = extract_per_source(comments, metadata)

        assert len(quotes) == 1
        assert quotes[0].like_count == 9


class TestQuoteIdStability:
    def test_quote_ids_are_deterministic_per_input(self, fixture, mocker):
        _mock_llm(mocker, [])

        _, q1 = extract_per_source(fixture["comments"], fixture["metadata"])
        _, q2 = extract_per_source(fixture["comments"], fixture["metadata"])

        assert [q.quote_id for q in q1] == [q.quote_id for q in q2]

    def test_same_text_different_source_id_yields_different_ids(self, mocker):
        _mock_llm(mocker, [])
        comments = [{"Likes": 100, "Text": "Sync is broken on long flights."}]

        a = extract_per_source(
            comments, SourceMetadata(source="youtube", source_id="video_a", category="productivity")
        )[1]
        b = extract_per_source(
            comments, SourceMetadata(source="youtube", source_id="video_b", category="productivity")
        )[1]

        assert a[0].quote_id != b[0].quote_id

    def test_identical_comments_collapse_to_one_quote(self, mocker):
        """Stable IDs imply duplicate texts from one source dedupe naturally."""
        _mock_llm(mocker, [])
        comments = [
            {"Likes": 100, "Text": "Sync is broken on long flights."},
            {"Likes": 200, "Text": "Sync is broken on long flights."},
        ]
        metadata = SourceMetadata(
            source="youtube", source_id="vid", category="productivity"
        )

        _, quotes = extract_per_source(comments, metadata)

        assert len(quotes) == 1


class TestGroundingContract:
    def test_pain_items_only_reference_returned_quote_ids(self, fixture, mocker):
        # Build the pool first to learn the IDs that the LLM will be allowed to cite.
        _mock_llm(mocker, [])
        _, pool = extract_per_source(fixture["comments"], fixture["metadata"])
        valid_ids = [q.quote_id for q in pool]
        assert len(valid_ids) >= 2

        # Now run with an LLM that emits ONE grounded pain item + ONE hallucinated.
        _mock_llm(mocker, [
            {"text": "offline edits lost on reconnect", "quote_ids": [valid_ids[0], valid_ids[1]]},
            {"text": "hallucinated complaint", "quote_ids": ["q_deadbeef", "q_cafebabe"]},
        ])

        pain_items, quotes = extract_per_source(fixture["comments"], fixture["metadata"])

        assert len(pain_items) == 1
        pool_ids = {q.quote_id for q in quotes}
        for item in pain_items:
            assert set(item.quote_ids).issubset(pool_ids)

    def test_partial_hallucinated_ids_filtered_but_item_kept(self, fixture, mocker):
        _mock_llm(mocker, [])
        _, pool = extract_per_source(fixture["comments"], fixture["metadata"])
        good = pool[0].quote_id

        _mock_llm(mocker, [
            {"text": "partial cite", "quote_ids": [good, "q_notreal"]},
        ])

        pain_items, _ = extract_per_source(fixture["comments"], fixture["metadata"])

        assert len(pain_items) == 1
        assert pain_items[0].quote_ids == [good]

    def test_pain_item_with_no_real_citations_dropped(self, fixture, mocker):
        _mock_llm(mocker, [
            {"text": "fully hallucinated", "quote_ids": ["q_zzz", "q_yyy"]},
        ])

        pain_items, _ = extract_per_source(fixture["comments"], fixture["metadata"])

        assert pain_items == []


class TestRoutingAndPromptShape:
    def test_llm_call_uses_per_source_extract_router_config(self, fixture, mocker):
        mock_call = _mock_llm(mocker, [])

        extract_per_source(fixture["comments"], fixture["metadata"])

        kwargs = mock_call.call_args.kwargs
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == pytest.approx(0.3)
        assert kwargs["max_tokens"] == 4000
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_user_message_contains_every_quote_id_and_source_metadata(self, fixture, mocker):
        mock_call = _mock_llm(mocker, [])

        _, quotes = extract_per_source(fixture["comments"], fixture["metadata"])

        user_msg = mock_call.call_args.kwargs["messages"][1]["content"]
        assert fixture["metadata"].source_id in user_msg
        assert fixture["metadata"].title in user_msg
        for q in quotes:
            assert q.quote_id in user_msg


class TestIdeaBlindingObservable:
    """Spec §11 criterion 4: the constructed prompt is logged so a reviewer
    can grep-verify it does not contain the idea string. Combined with the
    structural signature check above, this gives belt-and-braces evidence
    that idea-blinding holds.
    """

    def test_prompt_logged_and_does_not_contain_idea(self, fixture, mocker, caplog):
        idea = "note-taking app with better offline sync"
        target_gap = "offline reliability"
        _mock_llm(mocker, [])

        with caplog.at_level(logging.INFO, logger=svc.logger.name):
            extract_per_source(fixture["comments"], fixture["metadata"])

        prompt_logs = [r.getMessage() for r in caplog.records if "prompt" in r.getMessage()]
        assert prompt_logs, "expected the constructed prompt to be logged"
        full = "\n".join(prompt_logs)
        assert idea not in full
        assert target_gap not in full


class TestDegenerateLLMOutput:
    def test_invalid_json_returns_empty_pain_items_with_full_pool(self, fixture, mocker):
        mocker.patch(LLM_TARGET, return_value="not valid json {{{")

        pain_items, quotes = extract_per_source(fixture["comments"], fixture["metadata"])

        assert pain_items == []
        assert len(quotes) >= 2  # pool survives regardless of LLM failure

    def test_missing_pain_items_key_returns_empty(self, fixture, mocker):
        mocker.patch(LLM_TARGET, return_value=json.dumps({"problems": []}))

        pain_items, _ = extract_per_source(fixture["comments"], fixture["metadata"])

        assert pain_items == []

    def test_bare_list_response_treated_as_pain_items(self, fixture, mocker):
        _mock_llm(mocker, [])
        _, pool = extract_per_source(fixture["comments"], fixture["metadata"])
        good_ids = [pool[0].quote_id, pool[1].quote_id]

        mocker.patch(
            LLM_TARGET,
            return_value=json.dumps([
                {"text": "wrapped list", "quote_ids": good_ids},
            ]),
        )

        pain_items, _ = extract_per_source(fixture["comments"], fixture["metadata"])

        assert len(pain_items) == 1
        assert pain_items[0].text == "wrapped list"

    def test_markdown_fenced_json_response_still_parses(self, fixture, mocker):
        """Regression: models sometimes wrap JSON in a ```json ... ``` fence
        even under response_format=json_object. Before the fence-stripping
        fallback, this silently degraded to pain_items=[] with no warning —
        seen in production logs (2026-07-11) across an entire run."""
        _mock_llm(mocker, [])
        _, pool = extract_per_source(fixture["comments"], fixture["metadata"])
        good_ids = [pool[0].quote_id, pool[1].quote_id]

        fenced = "```json\n" + json.dumps({
            "pain_items": [{"text": "fenced response", "quote_ids": good_ids}],
        }) + "\n```"
        mocker.patch(LLM_TARGET, return_value=fenced)

        pain_items, _ = extract_per_source(fixture["comments"], fixture["metadata"])

        assert len(pain_items) == 1
        assert pain_items[0].text == "fenced response"
