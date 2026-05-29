"""Integration tests for /runs (v2 slice 1 — spec §6, issue #46).

Layer rule: router → idea_run_service → (mocked) supabase + preflight.
External services (Supabase, the preflight LLM/HTTP stack) are mocked at the
service-module boundary so we exercise the real router and service wiring.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.runs import Competitor, PreflightResult


@pytest.fixture
def client():
    return TestClient(app)


def _row(
    *,
    run_id: str = "11111111-1111-1111-1111-111111111111",
    idea: str = "note-taking app with better offline sync",
    status_: str = "pending",
    category: str | None = None,
    signal_strength: str | None = None,
    signal_reasoning: str | None = None,
    competitors: list[dict] | None = None,
    updated_at: str = "2026-05-28T10:00:00+00:00",
) -> dict:
    return {
        "id": run_id,
        "idea": idea,
        "target_gap": None,
        "status": status_,
        "category": category,
        "signal_strength": signal_strength,
        "signal_reasoning": signal_reasoning,
        "competitors_json": competitors or [],
        "quotes_json": {},
        "coverage_json": None,
        "idea_match_json": None,
        "failure_reason": None,
        "created_at": "2026-05-28T10:00:00+00:00",
        "updated_at": updated_at,
    }


def _preflight() -> PreflightResult:
    return PreflightResult(
        category="note-taking",
        signal_strength="high",
        signal_reasoning="established consumer category",
        candidates=[
            Competitor(
                source="appstore",
                url="https://apps.apple.com/obsidian",
                name="Obsidian",
                identifier="md.obsidian",
            ),
        ],
    )


def test_post_runs_inserts_row_runs_preflight_and_returns_preflight_ready(client, mocker):
    pending = _row()
    ready = _row(
        status_="preflight_ready",
        category="note-taking",
        signal_strength="high",
        signal_reasoning="established consumer category",
        competitors=[{
            "source": "appstore", "url": "https://apps.apple.com/obsidian",
            "name": "Obsidian", "identifier": "md.obsidian",
        }],
    )
    insert = mocker.patch(
        "app.services.idea_run_service.insert_idea_run", return_value=pending,
    )
    update = mocker.patch(
        "app.services.idea_run_service.update_idea_run_preflight", return_value=ready,
    )
    mocker.patch(
        "app.services.idea_run_service.preflight_service.run",
        return_value=_preflight(),
    )

    response = client.post(
        "/runs",
        json={"idea": "note-taking app with better offline sync", "target_gap": None},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == pending["id"]
    assert body["status"] == "preflight_ready"
    assert body["preflight"]["category"] == "note-taking"
    assert body["preflight"]["signal_strength"] == "high"
    assert len(body["preflight"]["candidates"]) == 1

    insert.assert_called_once_with("note-taking app with better offline sync", None)
    update.assert_called_once()
    update_kwargs = update.call_args.kwargs
    assert update_kwargs["run_id"] == pending["id"]
    assert update_kwargs["category"] == "note-taking"
    assert update_kwargs["candidates"] == [{
        "source": "appstore", "url": "https://apps.apple.com/obsidian",
        "name": "Obsidian", "identifier": "md.obsidian",
    }]


def test_post_runs_then_get_runs_returns_current_state(client, mocker):
    pending = _row()
    ready = _row(
        status_="preflight_ready",
        category="note-taking",
        signal_strength="high",
        signal_reasoning="established consumer category",
        competitors=[{
            "source": "appstore", "url": "https://apps.apple.com/obsidian",
            "name": "Obsidian", "identifier": "md.obsidian",
        }],
    )
    mocker.patch(
        "app.services.idea_run_service.insert_idea_run", return_value=pending,
    )
    mocker.patch(
        "app.services.idea_run_service.update_idea_run_preflight", return_value=ready,
    )
    mocker.patch(
        "app.services.idea_run_service.preflight_service.run",
        return_value=_preflight(),
    )
    mocker.patch(
        "app.services.idea_run_service.get_idea_run", return_value=ready,
    )

    post = client.post("/runs", json={"idea": "idea", "target_gap": None})
    run_id = post.json()["run_id"]

    get = client.get(f"/runs/{run_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["run_id"] == run_id
    assert body["status"] == "preflight_ready"
    assert body["category"] == "note-taking"
    assert body["competitors"][0]["identifier"] == "md.obsidian"


def test_get_run_sets_x_robots_tag_header(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(status_="preflight_ready",
                          category="c", signal_strength="high", signal_reasoning="r"),
    )

    response = client.get("/runs/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"


def test_get_run_missing_id_returns_404(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run", return_value=None,
    )

    response = client.get("/runs/does-not-exist")

    assert response.status_code == 404
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert response.json()["detail"] == "Run not found"


def test_list_runs_returns_done_feed(client, mocker):
    list_done = mocker.patch(
        "app.services.idea_run_service.list_done_idea_runs",
        return_value=[
            {"id": "r1", "idea": "first idea", "updated_at": "2026-05-28T09:00:00+00:00"},
            {"id": "r2", "idea": "second idea", "updated_at": "2026-05-27T09:00:00+00:00"},
        ],
    )

    response = client.get("/runs?limit=20&before=2026-05-28T10:00:00Z")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["run_id"] == "r1"
    assert body[0]["idea"] == "first idea"
    assert body[0]["completed_at"].startswith("2026-05-28T09:00:00")

    args = list_done.call_args.kwargs
    assert args["limit"] == 20
    assert args["before"] is not None


def test_list_runs_empty_until_pipeline_lands(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.list_done_idea_runs", return_value=[],
    )

    response = client.get("/runs")

    assert response.status_code == 200
    assert response.json() == []


def test_approve_returns_501_not_implemented(client):
    response = client.post("/runs/abc/approve")

    assert response.status_code == 501
    assert "next issue" in response.json()["detail"]
