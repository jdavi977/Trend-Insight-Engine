"""Tests for app/clients/openai.py.

The OpenAI SDK is mocked — we don't make real API calls. We verify our wrapper
passes the right messages and returns the model's text output.
"""
from __future__ import annotations

from unittest.mock import MagicMock


class TestGetOpenAIClient:
    def test_returns_a_client_instance(self, mocker):
        from app.clients import openai as openai_client

        sentinel = object()
        mocker.patch.object(openai_client, "OpenAI", return_value=sentinel)
        # Reset cached singleton if present.
        openai_client._client = None

        result = openai_client.get_openai_client()

        assert result is sentinel

    def test_caches_the_client_across_calls(self, mocker):
        from app.clients import openai as openai_client

        ctor = mocker.patch.object(openai_client, "OpenAI", return_value=object())
        openai_client._client = None

        first = openai_client.get_openai_client()
        second = openai_client.get_openai_client()

        assert first is second
        assert ctor.call_count == 1


class TestCreateChatCompletion:
    """Transport behaviour, previously only covered incidentally by the removed
    daily-budget accounting tests."""

    def _fake_client(self, content="ok"):
        client = MagicMock()
        client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))]
        )
        return client

    def test_forwards_call_params_and_returns_message_content(self, mocker):
        from app.clients import openai as openai_client

        fake = self._fake_client("the answer")
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake)

        result = openai_client.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            temperature=0.2,
            max_tokens=100,
        )

        assert result == "the answer"
        kwargs = fake.chat.completions.create.call_args.kwargs
        assert kwargs["messages"] == [{"role": "user", "content": "hi"}]
        assert kwargs["model"] == "gpt-4o"
        assert kwargs["temperature"] == 0.2
        assert kwargs["max_tokens"] == 100
        # Omitted rather than passed as None — the SDK rejects a null value.
        assert "response_format" not in kwargs

    def test_forwards_response_format_when_given(self, mocker):
        from app.clients import openai as openai_client

        fake = self._fake_client()
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake)

        openai_client.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            temperature=0.2,
            max_tokens=100,
            response_format={"type": "json_object"},
        )

        kwargs = fake.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}
