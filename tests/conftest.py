"""Shared fixtures for the test suite.

External services (YouTube Data API, iTunes RSS, OpenAI, Supabase) are mocked
at their call sites. Pure modules (preprocessing, validateUrl, schemas) run
for real — mocking deterministic functions tests nothing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())
