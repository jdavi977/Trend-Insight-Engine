"""Shared fixtures for the test suite.

External services (YouTube Data API, iTunes RSS, OpenAI, Supabase) are mocked
at their call sites. Pure modules (preprocessing, schemas) run for real —
mocking deterministic functions tests nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def _reset_guard_state():
    """Isolate the in-process abuse/cost guard state between tests (issue #59).

    The per-IP rate-limit buckets, the daily OpenAI spend total, and the in-memory
    `_jobs` registry are module-level singletons; without a reset they leak across
    tests and make 429 assertions order-dependent.
    """
    from app.clients import openai as openai_client
    from app.services import rate_limit_service, run_pipeline_service

    def _clear():
        rate_limit_service.reset()
        openai_client.reset_spend()
        run_pipeline_service._jobs.clear()

    _clear()
    yield
    _clear()
