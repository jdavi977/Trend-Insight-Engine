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


def test_approve_validates_body_requires_competitors(client):
    response = client.post("/runs/abc/approve", json={"competitors": []})

    assert response.status_code == 422


def test_approve_happy_path_returns_running_and_enqueues(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="productivity",
                          signal_strength="high", signal_reasoning="r"),
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


def test_approve_low_signal_without_ack_returns_400(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="b2b-saas",
                          signal_strength="low", signal_reasoning="thin"),
    )
    running = mocker.patch("app.services.run_pipeline_service.update_idea_run_running")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()]},
    )

    assert response.status_code == 400
    running.assert_not_called()


def test_approve_low_signal_with_ack_proceeds(client, mocker):
    mocker.patch(
        "app.services.run_pipeline_service.get_idea_run",
        return_value=_row(status_="preflight_ready", category="b2b-saas",
                          signal_strength="low", signal_reasoning="thin"),
    )
    mocker.patch("app.services.run_pipeline_service.update_idea_run_running")
    mocker.patch("app.services.run_pipeline_service.run_pipeline")

    response = client.post(
        "/runs/11111111-1111-1111-1111-111111111111/approve",
        json={"competitors": [_competitor_body()], "acknowledged_low_signal": True},
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

    response = client.post("/runs", json={"idea": "x", "target_gap": None})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "busy"
    assert int(response.headers["Retry-After"]) > 0


def test_post_runs_rate_limited_429_after_hourly_limit(client, mocker):
    from app.config.constants import RATE_LIMIT_PER_HOUR
    from app.services import rate_limit_service

    # TestClient's socket peer is "testclient"; seed it to the hourly ceiling.
    for _ in range(RATE_LIMIT_PER_HOUR):
        rate_limit_service.record_run("testclient")

    response = client.post("/runs", json={"idea": "x", "target_gap": None})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "rate_limited"
    assert int(response.headers["Retry-After"]) > 0


def test_post_runs_budget_exhausted_429(client, mocker):
    mocker.patch(
        "app.services.rate_limit_service.openai_client.is_budget_exhausted",
        return_value=True,
    )

    response = client.post("/runs", json={"idea": "x", "target_gap": None})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "budget_exhausted"


def test_post_runs_records_run_against_client_ip_on_success(client, mocker):
    from app.services import rate_limit_service

    _mock_create_run_success(mocker)

    response = client.post(
        "/runs",
        json={"idea": "note-taking app with better offline sync", "target_gap": None},
        headers={"X-Forwarded-For": "203.0.113.42"},
    )

    assert response.status_code == 200
    # The first X-Forwarded-For hop is the recorded client, not the socket peer.
    assert "203.0.113.42" in rate_limit_service._ip_runs
    assert "testclient" not in rate_limit_service._ip_runs


# --- POST /runs/:id/feedback (slice 2 §7, issue #62) ------------------------

_RUN_ID = "11111111-1111-1111-1111-111111111111"


def test_feedback_on_done_run_appends_event_and_returns_ok(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="done"),
    )
    mocker.patch(
        "app.services.idea_run_service.list_gaps_for_run",
        return_value=[{"gap_id": "gap_001"}],
    )
    insert = mocker.patch(
        "app.services.idea_run_service.insert_feedback_event",
        return_value={"id": "fe1"},
    )

    response = client.post(
        f"/runs/{_RUN_ID}/feedback",
        json={"new_to_me_gap_ids": ["gap_001"], "direction": "continue",
              "time_saved_estimate_minutes": 30},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    insert.assert_called_once()


def test_feedback_resubmit_appends_another_row(client, mocker):
    """Append-only: a second submission inserts a second row (PRD §9)."""
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="done"),
    )
    insert = mocker.patch(
        "app.services.idea_run_service.insert_feedback_event",
        return_value={"id": "fe"},
    )

    client.post(f"/runs/{_RUN_ID}/feedback", json={"direction": "continue"})
    client.post(f"/runs/{_RUN_ID}/feedback", json={"direction": "drop"})

    assert insert.call_count == 2


def test_feedback_on_non_done_run_returns_409(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="running"),
    )
    insert = mocker.patch("app.services.idea_run_service.insert_feedback_event")

    response = client.post(f"/runs/{_RUN_ID}/feedback", json={"direction": "continue"})

    assert response.status_code == 409
    insert.assert_not_called()


def test_feedback_unknown_gap_ids_returns_400(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="done"),
    )
    mocker.patch(
        "app.services.idea_run_service.list_gaps_for_run",
        return_value=[{"gap_id": "gap_001"}],
    )
    insert = mocker.patch("app.services.idea_run_service.insert_feedback_event")

    response = client.post(
        f"/runs/{_RUN_ID}/feedback", json={"new_to_me_gap_ids": ["ghost"]},
    )

    assert response.status_code == 400
    insert.assert_not_called()


def test_feedback_invalid_direction_returns_422(client):
    response = client.post(f"/runs/{_RUN_ID}/feedback", json={"direction": "maybe"})

    assert response.status_code == 422


def test_feedback_negative_minutes_returns_422(client):
    response = client.post(
        f"/runs/{_RUN_ID}/feedback", json={"time_saved_estimate_minutes": -5},
    )

    assert response.status_code == 422


# --- POST /runs/:id/report (slice 2 §7, US-S7, issue #62) -------------------


def test_report_hides_run_and_returns_ok(client, mocker):
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="done"),
    )
    update = mocker.patch(
        "app.services.idea_run_service.update_idea_run_reported",
        return_value=_row(run_id=_RUN_ID, status_="reported"),
    )

    response = client.post(f"/runs/{_RUN_ID}/report", json={"reason": "abusive content"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    update.assert_called_once_with(_RUN_ID, "abusive content")


def test_report_empty_reason_returns_422(client):
    response = client.post(f"/runs/{_RUN_ID}/report", json={"reason": ""})

    assert response.status_code == 422


def test_reported_run_returns_404_from_get(client, mocker):
    """After a report, GET /runs/:id 404s while the row is retained (Q5)."""
    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="reported"),
    )

    response = client.get(f"/runs/{_RUN_ID}")

    assert response.status_code == 404


def test_report_is_per_ip_rate_limited(client, mocker):
    from app.config.constants import RATE_LIMIT_PER_HOUR
    from app.services import rate_limit_service

    # Exhaust the shared per-IP window (TestClient socket peer is "testclient").
    for _ in range(RATE_LIMIT_PER_HOUR):
        rate_limit_service.record_run("testclient")
    report = mocker.patch("app.services.idea_run_service.report_run")

    response = client.post(f"/runs/{_RUN_ID}/report", json={"reason": "spam"})

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Reason"] == "rate_limited"
    report.assert_not_called()


def test_report_counts_against_shared_per_ip_budget(client, mocker):
    from app.services import rate_limit_service

    mocker.patch(
        "app.services.idea_run_service.get_idea_run",
        return_value=_row(run_id=_RUN_ID, status_="done"),
    )
    mocker.patch(
        "app.services.idea_run_service.update_idea_run_reported",
        return_value=_row(run_id=_RUN_ID, status_="reported"),
    )

    response = client.post(f"/runs/{_RUN_ID}/report", json={"reason": "spam"})

    assert response.status_code == 200
    # An accepted report consumes a slot in the same bucket as POST /runs (Q6).
    assert "testclient" in rate_limit_service._ip_runs
