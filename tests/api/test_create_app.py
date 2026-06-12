"""Contract tests for the `create_app()` factory.

Slice 3 (issue #72) tears down the v1 surface: the factory mounts only the
health and runs routers. These tests pin that contract — the v2 run-lifecycle
endpoints exist, `GET /` is a tiny static health payload, and every retired v1
endpoint 404s.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_create_app_returns_fastapi_instance():
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_registers_only_v2_routes():
    app = create_app()
    routes = {(r.path, m) for r in app.routes if hasattr(r, "methods") for m in r.methods}
    assert ("/", "GET") in routes
    assert ("/runs", "POST") in routes
    assert ("/runs", "GET") in routes
    assert ("/runs/{run_id}", "GET") in routes
    assert ("/runs/{run_id}/approve", "POST") in routes
    assert ("/runs/{run_id}/feedback", "POST") in routes
    assert ("/runs/{run_id}/report", "POST") in routes
    v1_paths = {"/analyze/youtube", "/analyze/appStore", "/get/homePage", "/data/send", "/insights/similar"}
    assert v1_paths.isdisjoint({path for path, _ in routes})


def test_root_returns_health_payload(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "trend-insight-engine", "status": "ok"}


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/analyze/youtube"),
        ("post", "/analyze/appStore"),
        ("get", "/get/homePage"),
        ("post", "/data/send"),
        ("get", "/insights/similar"),
    ],
)
def test_retired_v1_endpoints_return_404(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 404


def test_create_app_returns_independent_instances():
    assert create_app() is not create_app()
