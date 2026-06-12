"""Tests for app/clients/openai.py.

The OpenAI SDK is mocked — we don't make real API calls. We verify our wrapper
passes the right messages and returns the model's text output.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


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


class TestBudgetAccounting:
    """Daily OpenAI spend accounting (slice 2 §6, issue #59).

    The transport records usage × per-model config price into a running total so
    the rate-limit service's budget guard sees every stage's spend. `reset_spend`
    is also called by the autouse guard-reset fixture between tests.
    """

    def _usage(self, prompt_tokens, completion_tokens):
        return MagicMock(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    def test_record_usage_adds_usage_times_config_price(self):
        from app.clients import openai as openai_client

        openai_client.reset_spend()
        # gpt-4o config price: input 0.0025, output 0.01 per 1K tokens.
        openai_client._record_usage("gpt-4o", self._usage(1000, 1000))
        assert openai_client.current_spend_usd() == pytest.approx(0.0025 + 0.01)

    def test_record_usage_accumulates_across_calls(self):
        from app.clients import openai as openai_client

        openai_client.reset_spend()
        openai_client._record_usage("gpt-4o", self._usage(1000, 0))
        openai_client._record_usage("gpt-4o", self._usage(1000, 0))
        assert openai_client.current_spend_usd() == pytest.approx(0.005)

    def test_unknown_model_falls_back_to_default_price(self):
        from app.clients import openai as openai_client

        openai_client.reset_spend()
        openai_client._record_usage("some-future-model", self._usage(1000, 1000))
        # DEFAULT_OPENAI_PRICE matches gpt-4o, so spend is still counted (non-zero).
        assert openai_client.current_spend_usd() == pytest.approx(0.0125)

    def test_missing_usage_object_records_nothing(self):
        from app.clients import openai as openai_client

        openai_client.reset_spend()
        openai_client._record_usage("gpt-4o", None)
        assert openai_client.current_spend_usd() == 0.0

    def test_spend_resets_on_utc_day_rollover(self):
        from datetime import timedelta

        from app.clients import openai as openai_client

        openai_client.reset_spend()
        openai_client._record_usage("gpt-4o", self._usage(1000, 1000))
        assert openai_client.current_spend_usd() > 0
        # Pretend the running total was anchored to yesterday.
        openai_client._spend_day = openai_client._spend_day - timedelta(days=1)
        # Next read rolls the day and zeroes the total.
        assert openai_client.current_spend_usd() == 0.0

    def test_is_budget_exhausted_false_when_no_ceiling(self, mocker):
        from app.clients import openai as openai_client

        mocker.patch.object(openai_client.secrets, "OPENAI_DAILY_BUDGET_USD", None)
        openai_client.reset_spend()
        openai_client._record_usage("gpt-4o", self._usage(10_000, 10_000))
        assert openai_client.is_budget_exhausted() is False

    def test_is_budget_exhausted_true_at_or_over_ceiling(self, mocker):
        from app.clients import openai as openai_client

        mocker.patch.object(openai_client.secrets, "OPENAI_DAILY_BUDGET_USD", 0.01)
        openai_client.reset_spend()
        assert openai_client.is_budget_exhausted() is False
        openai_client._record_usage("gpt-4o", self._usage(0, 1000))  # +0.01 → at ceiling
        assert openai_client.is_budget_exhausted() is True

    def test_create_chat_completion_records_spend(self, mocker):
        from app.clients import openai as openai_client

        openai_client.reset_spend()
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="x"))],
            usage=self._usage(1000, 0),
        )
        mocker.patch.object(openai_client, "get_openai_client", return_value=fake_client)

        openai_client.create_chat_completion(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-4o",
            temperature=0.2,
            max_tokens=100,
        )
        assert openai_client.current_spend_usd() == pytest.approx(0.0025)
