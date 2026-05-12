"""Tests for app/rag/rag.py — embed_and_store and retrieve_similar."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from app.schemas.llm import LLMExtraction, YoutubeProblemItem


_EXTRACTION = LLMExtraction(
    source="youtube",
    title="Cool Video",
    problems=[
        YoutubeProblemItem(problem="battery dies fast", type="complaint", total_likes=100, severity=4, frequency=3),
        YoutubeProblemItem(problem="UI is confusing", type="usability", total_likes=50, severity=3, frequency=2),
    ],
)

_FAKE_EMBEDDING = [0.1] * 1536


class TestEmbedAndStore:
    def test_upserts_one_row_per_problem(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        upsert = mocker.patch.object(rag, "upsert_embedding")

        rag.embed_and_store(_EXTRACTION, "https://www.youtube.com/watch?v=abc")

        assert upsert.call_count == 2

    def test_upsert_row_has_correct_metadata(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        upsert = mocker.patch.object(rag, "upsert_embedding")

        rag.embed_and_store(_EXTRACTION, "https://www.youtube.com/watch?v=abc")

        first_call_kwargs = upsert.call_args_list[0].kwargs
        assert first_call_kwargs["problem"] == "battery dies fast"
        assert first_call_kwargs["type"] == "complaint"
        assert first_call_kwargs["severity"] == 4
        assert first_call_kwargs["frequency"] == 3
        assert first_call_kwargs["source"] == "youtube"
        assert first_call_kwargs["source_url"] == "https://www.youtube.com/watch?v=abc"
        assert first_call_kwargs["title"] == "Cool Video"
        assert first_call_kwargs["embedding"] == _FAKE_EMBEDDING

    def test_deterministic_id_same_input(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        upsert = mocker.patch.object(rag, "upsert_embedding")

        url = "https://www.youtube.com/watch?v=abc"
        rag.embed_and_store(_EXTRACTION, url)
        first_id = upsert.call_args_list[0].kwargs["id"]

        upsert.reset_mock()
        rag.embed_and_store(_EXTRACTION, url)
        second_id = upsert.call_args_list[0].kwargs["id"]

        assert first_id == second_id

    def test_swallows_embedding_error(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", side_effect=RuntimeError("API down"))
        upsert = mocker.patch.object(rag, "upsert_embedding")

        rag.embed_and_store(_EXTRACTION, "https://www.youtube.com/watch?v=abc")

        upsert.assert_not_called()

    def test_swallows_upsert_error(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        mocker.patch.object(rag, "upsert_embedding", side_effect=RuntimeError("DB down"))

        rag.embed_and_store(_EXTRACTION, "https://www.youtube.com/watch?v=abc")


class TestRetrieveSimilar:
    def test_returns_empty_list_when_store_empty(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        mocker.patch.object(rag, "query_similar", return_value=[])

        result = rag.retrieve_similar("battery issue")

        assert result == []

    def test_returns_retrieved_insights_in_order(self, mocker):
        from app.rag import rag
        from app.schemas.rag import RetrievedInsight

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        mocker.patch.object(rag, "query_similar", return_value=[
            {
                "problem": "battery dies fast",
                "type": "complaint",
                "severity": 4,
                "frequency": 3,
                "source": "youtube",
                "source_url": "https://www.youtube.com/watch?v=abc",
                "title": "Cool Video",
                "extracted_at": "2026-05-01T00:00:00+00:00",
                "similarity": 0.92,
            }
        ])

        result = rag.retrieve_similar("battery drain")

        assert len(result) == 1
        assert isinstance(result[0], RetrievedInsight)
        assert result[0].problem == "battery dies fast"
        assert result[0].similarity == 0.92

    def test_respects_k_limit(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        query_mock = mocker.patch.object(rag, "query_similar", return_value=[])

        rag.retrieve_similar("query", k=3)

        _, called_threshold, called_k = query_mock.call_args.args
        assert called_k == 3

    def test_optional_title_field(self, mocker):
        from app.rag import rag

        mocker.patch.object(rag, "create_embedding", return_value=_FAKE_EMBEDDING)
        mocker.patch.object(rag, "query_similar", return_value=[
            {
                "problem": "crashes on launch",
                "type": "complaint",
                "severity": 5,
                "frequency": 4,
                "source": "app_store",
                "source_url": "https://apps.apple.com/app/id999",
                "title": None,
                "extracted_at": "2026-05-01T00:00:00+00:00",
                "similarity": 0.80,
            }
        ])

        result = rag.retrieve_similar("crash")

        assert result[0].title is None
