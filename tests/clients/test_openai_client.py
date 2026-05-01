"""Tests for app/clients/openai.py.

The OpenAI SDK is mocked — we don't make real API calls. We verify our wrapper
passes the right messages and returns the model's text output.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestCreateResponse:
    def test_returns_model_output_text(self, mocker):
        from app.clients import openai as openai_client

        fake_client = MagicMock()
        fake_client.responses.create.return_value = MagicMock(output_text="hello world")
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake_client)

        result = openai_client.create_response(
            system_prompt="sys",
            user_data="data here",
            assistant_prompt="assist",
        )

        assert result == "hello world"

    def test_passes_messages_in_correct_role_order(self, mocker):
        from app.clients import openai as openai_client

        fake_client = MagicMock()
        fake_client.responses.create.return_value = MagicMock(output_text="x")
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake_client)

        openai_client.create_response(
            system_prompt="SYS",
            user_data="USER",
            assistant_prompt="ASSIST",
        )

        kwargs = fake_client.responses.create.call_args.kwargs
        roles = [m["role"] for m in kwargs["input"]]
        assert roles == ["developer", "user", "assistant"]
        contents = [m["content"] for m in kwargs["input"]]
        assert contents[0] == "SYS"
        assert "USER" in contents[1]
        assert contents[2] == "ASSIST"

    def test_uses_configured_model(self, mocker):
        from app.clients import openai as openai_client

        fake_client = MagicMock()
        fake_client.responses.create.return_value = MagicMock(output_text="x")
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake_client)

        openai_client.create_response(system_prompt="s", user_data="d", assistant_prompt="a")

        kwargs = fake_client.responses.create.call_args.kwargs
        assert kwargs["model"] == "gpt-5-mini"


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
