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
        "status": status_,
        "category": category,
        "signal_strength": signal_strength,
        "signal_reasoning": signal_reasoning,
        "competitors_json": competitors or [],
        "quotes_json": {},
        "coverage_json": None,
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
        json={"idea": "note-taking app with better offline sync"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == pending["id"]
    assert body["status"] == "preflight_ready"
    assert body["preflight"]["category"] == "note-taking"
    assert body["preflight"]["signal_strength"] == "high"
    assert len(body["preflight"]["candidates"]) == 1

    insert.assert_called_once_with("note-taking app with better offline sync")
    update.assert_called_once()
    update_kwargs = update.call_args.kwargs
    assert update_kwargs["run_id"] == pending["id"]
    assert update_kwargs["category"] == "note-taking"
    assert update_kwargs["candidates"] == [{
        "source": "appstore", "url": "https://apps.apple.com/obsidian",
        "name": "Obsidian", "identifier": "md.obsidian",
    }]


def test_post_runs_ignores_a_stale_target_gap_field(client, mocker):
    """`target_gap` folded into `idea` (#88, spec D5): the field is gone from the
    contract, but a client still sending it must not hard-fail — Pydantic drops
    the unknown key and the run is created from `idea` alone."""
    pending = _row()
    insert = mocker.patch(
        "app.services.idea_run_service.insert_idea_run", return_value=pending,
    )
    mocker.patch("app.services.idea_run_service.update_idea_run_preflight")
    mocker.patch(
        "app.services.idea_run_service.preflight_service.run",
        return_value=_preflight(),
    )

    response = client.post(
        "/runs", json={"idea": "note app", "target_gap": "offline sync"},
    )

    assert response.status_code == 200
    insert.assert_called_once_with("note app")


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

    post = client.post("/runs", json={"idea": "idea"})
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


def test_get_done_run_includes_gaps_from_gaps_table(client, mocker):
    done = _row(status_="preflight_ready", category="productivity",
                signal_strength="high", signal_reasoning="r")
    done["status"] = "done"
    mocker.patch(
        "app.services.idea_run_service.get_idea_run", return_value=done,
    )
    mocker.patch(
        "app.services.idea_run_service.list_gaps_for_run",
        return_value=[{
            "gap_id": "gap_001", "run_id": done["id"], "gap": "Offline edits lost",
            "severity": 5, "frequency": 4, "spread": 2,
            "competitors_present_json": ["youtube:v1", "appstore:a1"],
            "evidence_quote_ids_json": ["q01", "q02"], "ordinal": 1,
        }],
    )

    response = client.get(f"/runs/{done['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert len(body["gaps"]) == 1
    assert body["gaps"][0]["gap_id"] == "gap_001"
    assert body["gaps"][0]["competitors_present"] == ["youtube:v1", "appstore:a1"]
    assert body["gaps"][0]["evidence_quote_ids"] == ["q01", "q02"]


def test_get_done_run_surfaces_partial_sources_banner(client, mocker):
    # A run that completed above the 70% threshold persists partial_sources_json;
    # GET /runs/:id must surface it so the frontend can render the banner (#60).
    done = _row(status_="done", category="productivity",
                signal_strength="high", signal_reasoning="r")
    done["partial_sources_json"] = {
        "failed": [{"source": "youtube", "name": "Vid 3", "reason": "RuntimeError: boom"}],
        "succeeded_count": 9,
        "total_count": 10,
    }
    mocker.patch("app.services.idea_run_service.get_idea_run", return_value=done)
    mocker.patch("app.services.idea_run_service.list_gaps_for_run", return_value=[])

    response = client.get(f"/runs/{done['id']}")

    assert response.status_code == 200
    partial = response.json()["partial_sources"]
    assert partial["succeeded_count"] == 9
    assert partial["total_count"] == 10
    assert partial["failed"][0]["name"] == "Vid 3"


def test_get_preflight_run_does_not_query_gaps(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="c",
                          signal_strength="high", signal_reasoning="r"),
    )
    gaps = mocker.patch("app.services.idea_run_service.list_gaps_for_run")

    response = client.get("/runs/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    assert response.json()["gaps"] == []
    gaps.assert_not_called()


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


def _competitor_body() -> dict:
    return {
        "source": "appstore",
        "url": "https://apps.apple.com/us/app/obsidian/id1557175442",
        "name": "Obsidian",
        "identifier": "md.obsidian",
    }


def _candidates(n: int) -> list[dict]:
    """Build *n* pre-flight candidate rows for `competitors_json` — the pool the
    low-signal gate (issue #69) counts to decide whether an ack is required."""
    return [{**_competitor_body(), "identifier": f"c{i}"} for i in range(n)]


def test_approve_validates_body_requires_competitors(client):
    response = client.post("/runs/abc/approve", json={"competitors": []})

    assert response.status_code == 422


def test_approve_happy_path_returns_running_and_enqueues(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="productivity",
                          signal_strength="high", signal_reasoning="r",
                          competitors=_candidates(5)),
    )
    mocker.patch("app.services.run_pipeline_service.update_idea_run_running")
    # Stub the background task so the pipeline doesn't actually run under TestClient.
    pipeline = mocker.patch("app.services.run_pipeline_service.run_pipeline")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "11111111-1111-1111-1111-111111111111", "status": "running",
    }
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    pipeline.assert_called_once()  # ran as a background task after the response


def test_approve_below_threshold_without_ack_returns_400(client, mocker):
    # Fewer than LOW_SIGNAL_CANDIDATE_THRESHOLD pre-flight candidates → ack required.
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="b2b-saas",
                          signal_strength="high", signal_reasoning="thin",
                          competitors=_candidates(2)),
    )
    running = mocker.patch("app.services.run_pipeline_service.update_idea_run_running")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 400
    running.assert_not_called()


def test_approve_below_threshold_with_ack_proceeds(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="b2b-saas",
                          signal_strength="high", signal_reasoning="thin",
                          competitors=_candidates(2)),
    )
    mocker.patch("app.services.run_pipeline_service.update_idea_run_running")
    mocker.patch("app.services.run_pipeline_service.run_pipeline")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()], "acknowledged_low_signal": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_approve_at_threshold_proceeds_without_ack_despite_low_grade(client, mocker):
    # >= threshold candidates approve freely even when the LLM graded the run "low".
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="b2b-saas",
                          signal_strength="low", signal_reasoning="r",
                          competitors=_candidates(4)),
    )
    mocker.patch("app.services.run_pipeline_service.update_idea_run_running")
    mocker.patch("app.services.run_pipeline_service.run_pipeline")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_approve_wrong_status_returns_409(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="done"),
    )

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 409


def test_approve_missing_run_returns_404(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run", return_value=None,
    )

    response = client.post(
        "/runs/does-not-exist/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 404


# --- abuse / cost guards on POST /runs (slice 2 §6, issue #59) ---------------


def _mock_create_run_success(mocker):
    """Wire idea_run_service.create_run to succeed so guards are the only gate."""
    pending = _row()
    ready = _row(status_="preflight_ready", category="note-taking",
                 signal_strength="high")
    mocker.patch("app.services.idea_run_service.insert_idea_run", return_value=pending)
    mocker.patch("app.services.idea_run_service.update_idea_run_preflight",
                 return_value=ready)
    mocker.patch("app.services.idea_run_service.preflight_service.run",
                 return_value=_preflight())


def test_post_runs_busy_429_when_a_pipeline_is_running(client, mocker):
    from app.services import run_pipeline_service

    run_pipeline_service._jobs["other-run"] = {"status": "running", "stage": "synthesis"}

    response = client.post("/runs", json={"idea": "x"})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "busy"
    assert int(response.headers["Retry-After"]) > 0


def test_post_runs_rate_limited_429_after_hourly_limit(client, mocker):
    from app.config.constants import RATE_LIMIT_PER_HOUR
    from app.services import rate_limit_service

    # TestClient's socket peer is "testclient"; seed it to the hourly ceiling.
    for _ in range(RATE_LIMIT_PER_HOUR):
        rate_limit_service.record_run("testclient")

    response = client.post("/runs", json={"idea": "x"})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0


def test_post_runs_budget_exhausted_429(client, mocker):
    mocker.patch(
        "app.services.rate_limit_service.openai_client.is_budget_exhausted",
        return_value=True,
    )

    response = client.post("/runs", json={"idea": "x"})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "budget_exhausted"


def test_post_runs_records_run_against_client_ip_on_success(client, mocker):
    from app.services import rate_limit_service

    _mock_create_run_success(mocker)

    response = client.post(
        "/runs",
        json={"idea": "note-taking app with better offline sync"},
        headers={"X-Forwarded-For": "203.0.113.42"},
    )

    assert response.status_code == 200
    # The first X-Forwarded-For hop is the recorded client, not the socket peer.
    assert "203.0.113.42" in rate_limit_service._ip_runs
    assert "testclient" not in rate_limit_service._ip_runs
