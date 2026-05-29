"""Tests for `app.llm.preflight` — the two pre-flight LLM calls (spec §7)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

from app.llm import preflight


def _stub_openai(mocker, content: dict):
    client = MagicMock()
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=json.dumps(content)))]
    client.chat.completions.create.return_value = response
    mocker.patch.object(preflight, "get_openai_client", return_value=client)
    return client


def test_generate_queries_routes_through_resolver(mocker):
    client = _stub_openai(mocker, {
        "appstore": ["notes app", "markdown notes"],
        "youtube":  ["best notes app review", "obsidian vs notion"],
        "category": "note-taking",
        "signal_strength": "high",
        "signal_reasoning": "established consumer category.",
    })

    result = preflight.generate_queries("note-taking app with better offline sync")

    assert result["signal_strength"] == "high"
    assert result["category"] == "note-taking"

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o"  # spec §9: v1 routes every stage to gpt-4o
    assert kwargs["response_format"] == {"type": "json_object"}
    system_msg = kwargs["messages"][0]["content"]
    assert "signal-strength rubric" in system_msg.lower()


def test_rank_candidates_resolves_urls_server_side(mocker):
    """Spec safeguard: URLs come from raw candidate dicts, not LLM echo —
    a hallucinated identifier surfaces as an empty URL, not a fake link."""
    _stub_openai(mocker, {
        "apps": [
            {"bundle_id": "real.app", "name": "Real", "justification": "j"},
            {"bundle_id": "hallucinated.app", "name": "Fake", "justification": "j"},
        ],
        "videos": [
            {"video_id": "abc123", "title": "Review", "justification": "j"},
            {"video_id": "deadbeef", "title": "Trailer", "justification": "j"},
        ],
    })

    apps = [{
        "bundle_id": "real.app", "name": "Real", "genre": "Productivity",
        "description": "d", "rating_count": 100, "url": "https://apps.apple.com/real",
    }]
    videos = [{
        "video_id": "abc123", "title": "Review", "channel": "Ch",
        "description": "d", "url": "https://www.youtube.com/watch?v=abc123",
    }]

    ranked = preflight.rank_candidates("idea", apps, videos)

    assert ranked["apps"][0]["url"] == "https://apps.apple.com/real"
    assert ranked["apps"][1]["url"] == ""  # hallucinated id → no URL
    assert ranked["videos"][0]["url"] == "https://www.youtube.com/watch?v=abc123"
    assert ranked["videos"][1]["url"] == ""


def test_rank_candidates_uses_preflight_rank_stage(mocker):
    client = _stub_openai(mocker, {"apps": [], "videos": []})

    preflight.rank_candidates("idea", [], [])

    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-4o"
    # Tightened ranker prompt (PRD §14.18) should still flag gameplay exclusions.
    system_msg = kwargs["messages"][0]["content"]
    assert "let's-plays" in system_msg.lower() or "lets-plays" in system_msg.lower()
    assert "trailer" in system_msg.lower()
