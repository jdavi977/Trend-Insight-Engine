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
    """Isolate the in-process job registry between tests.

    `_jobs` is a module-level singleton backing the single-active-run guard;
    without a reset it leaks across tests and makes the `429 busy` assertions
    order-dependent. The per-IP rate-limit buckets and daily OpenAI spend total
    that this fixture also used to clear were removed with those guards.
    """
    from app.services import run_pipeline_service

    def _clear():
        run_pipeline_service._jobs.clear()

    _clear()
    yield
    _clear()
