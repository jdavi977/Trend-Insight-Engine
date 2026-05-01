"""Contract tests for the `create_app()` factory introduced in PR 4.

`main.py` was a 109-line script mixing app construction, request models, and
endpoint bodies. PR 4 splits routers into `app/api/` and reduces `main.py` to
a factory that wires middleware, routers, and exception handlers.

These tests guard the factory's public contract: it returns a configured
FastAPI app exposing the four documented endpoints, with the documentation
visibility flags preserved.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.main import create_app


def test_create_app_returns_fastapi_instance():
    app = create_app()
    assert isinstance(app, FastAPI)


def test_create_app_registers_all_four_endpoints():
    app = create_app()
    routes = {(r.path, tuple(sorted(r.methods))) for r in app.routes if hasattr(r, "methods")}
    assert ("/analyze/youtube", ("POST",)) in routes
    assert ("/analyze/appStore", ("POST",)) in routes
    assert ("/get/homePage", ("GET",)) in routes
    assert ("/data/send", ("POST",)) in routes


def test_create_app_hides_internal_routes_from_schema():
    app = create_app()
    by_path = {r.path: r for r in app.routes if hasattr(r, "include_in_schema")}
    assert by_path["/data/send"].include_in_schema is False
    assert by_path["/"].include_in_schema is False


def test_create_app_returns_independent_instances():
    assert create_app() is not create_app()
