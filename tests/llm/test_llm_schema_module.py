"""`schemas/llm_insights.py` is renamed to `schemas/llm.py` to mirror the
direction-based split (`api.py` for inbound, `llm.py` for LLM output).

This test pins the new path. Richer behavior is covered by test_extract_insights.py.
"""
from __future__ import annotations


def test_llm_schema_module_exposes_models():
    from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem

    assert LLMExtraction.__name__ == "LLMExtraction"
    assert YoutubeProblemItem.__name__ == "YoutubeProblemItem"
    assert AppStoreProblemItem.__name__ == "AppStoreProblemItem"
