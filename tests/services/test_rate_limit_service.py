"""Tests for app/services/rate_limit_service.py — the POST /runs guards (issue #59).

Covers client-IP derivation, the concurrency / rate-limit / budget 429 paths,
their `Retry-After` headers, and the check order. The guard state singletons are
reset between tests by the autouse `_reset_guard_state` fixture (tests/conftest).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.config.constants import (
    BUSY_RETRY_AFTER_SECONDS,
    RATE_LIMIT_PER_DAY,
    RATE_LIMIT_PER_HOUR,
)
from app.services import rate_limit_service


def _request(forwarded: str | None = None, peer: str | None = "10.0.0.9"):
    headers = {"x-forwarded-for": forwarded} if forwarded is not None else {}
    client = SimpleNamespace(host=peer) if peer is not None else None
    return SimpleNamespace(headers=headers, client=client)


class TestClientIp:
    def test_uses_first_x_forwarded_for_hop(self):
        req = _request(forwarded="203.0.113.7, 70.41.3.18, 150.172.238.178")
        assert rate_limit_service.client_ip(req) == "203.0.113.7"

    def test_falls_back_to_socket_peer_when_no_header(self):
        req = _request(forwarded=None, peer="198.51.100.4")
        assert rate_limit_service.client_ip(req) == "198.51.100.4"

    def test_falls_back_to_peer_when_header_blank(self):
        req = _request(forwarded="   ", peer="198.51.100.5")
        assert rate_limit_service.client_ip(req) == "198.51.100.5"

    def test_unknown_when_no_header_and_no_peer(self):
        req = _request(forwarded=None, peer=None)
        assert rate_limit_service.client_ip(req) == "unknown"


class TestConcurrencyGuard:
    def test_busy_429_when_a_pipeline_is_running(self, mocker):
        mocker.patch.object(
            rate_limit_service.run_pipeline_service,
            "has_running_pipeline",
            return_value=True,
        )
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run("1.2.3.4")
        assert exc.value.status_code == 429
        assert exc.value.headers["X-RateLimit-Reason"] == "busy"
        assert exc.value.headers["Retry-After"] == str(BUSY_RETRY_AFTER_SECONDS)

    def test_passes_when_no_pipeline_running(self, mocker):
        mocker.patch.object(
            rate_limit_service.run_pipeline_service,
            "has_running_pipeline",
            return_value=False,
        )
        mocker.patch.object(
            rate_limit_service.openai_client, "is_budget_exhausted", return_value=False
        )
        # Should not raise.
        rate_limit_service.check_can_create_run("1.2.3.4")


class TestRateLimitGuard:
    @pytest.fixture(autouse=True)
    def _no_other_guards(self, mocker):
        mocker.patch.object(
            rate_limit_service.run_pipeline_service,
            "has_running_pipeline",
            return_value=False,
        )
        mocker.patch.object(
            rate_limit_service.openai_client, "is_budget_exhausted", return_value=False
        )

    def test_allows_up_to_the_hourly_limit(self):
        ip = "5.5.5.5"
        for _ in range(RATE_LIMIT_PER_HOUR):
            rate_limit_service.check_can_create_run(ip)
            rate_limit_service.record_run(ip)
        # The next one is over the hourly limit.
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run(ip)
        assert exc.value.status_code == 429
        assert exc.value.headers["X-RateLimit-Reason"] == "rate_limited"
        assert exc.value.headers["X-RateLimit-Window"] == "hourly"
        assert int(exc.value.headers["Retry-After"]) > 0

    def test_hourly_retry_after_is_within_the_hour(self):
        ip = "5.5.5.6"
        for _ in range(RATE_LIMIT_PER_HOUR):
            rate_limit_service.record_run(ip)
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run(ip)
        assert 0 < int(exc.value.headers["Retry-After"]) <= 3600 + 1

    def test_daily_limit_rejects_after_hour_windows_age_out(self, mocker):
        ip = "6.6.6.6"
        now = 1_000_000.0
        mocker.patch.object(rate_limit_service.time, "time", return_value=now)
        # Seed RATE_LIMIT_PER_DAY runs all older than an hour but within a day,
        # so the hourly window is clear but the daily ceiling is hit.
        two_hours_ago = now - 7200
        rate_limit_service._ip_runs[ip] = [
            two_hours_ago + i for i in range(RATE_LIMIT_PER_DAY)
        ]
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run(ip)
        assert exc.value.headers["X-RateLimit-Window"] == "daily"
        assert int(exc.value.headers["Retry-After"]) > 0

    def test_counters_are_per_ip(self):
        a, b = "7.7.7.7", "8.8.8.8"
        for _ in range(RATE_LIMIT_PER_HOUR):
            rate_limit_service.record_run(a)
        # `a` is now at the limit, but `b` is untouched.
        with pytest.raises(HTTPException):
            rate_limit_service.check_can_create_run(a)
        rate_limit_service.check_can_create_run(b)  # no raise

    def test_old_timestamps_are_pruned(self, mocker):
        ip = "9.9.9.9"
        now = 2_000_000.0
        mocker.patch.object(rate_limit_service.time, "time", return_value=now)
        # All timestamps older than a day → pruned → bucket clears.
        rate_limit_service._ip_runs[ip] = [now - 86_401 - i for i in range(20)]
        rate_limit_service.check_can_create_run(ip)  # no raise
        assert ip not in rate_limit_service._ip_runs


class TestBudgetGuard:
    def test_budget_exhausted_429(self, mocker):
        mocker.patch.object(
            rate_limit_service.run_pipeline_service,
            "has_running_pipeline",
            return_value=False,
        )
        mocker.patch.object(
            rate_limit_service.openai_client, "is_budget_exhausted", return_value=True
        )
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run("1.1.1.1")
        assert exc.value.status_code == 429
        assert exc.value.headers["X-RateLimit-Reason"] == "budget_exhausted"


class TestCheckOrder:
    def test_concurrency_checked_before_rate_limit_and_budget(self, mocker):
        # A running pipeline rejects first, even if budget would also reject —
        # cheapest/most-likely-to-reject first (spec §6).
        mocker.patch.object(
            rate_limit_service.run_pipeline_service,
            "has_running_pipeline",
            return_value=True,
        )
        budget = mocker.patch.object(
            rate_limit_service.openai_client, "is_budget_exhausted", return_value=True
        )
        with pytest.raises(HTTPException) as exc:
            rate_limit_service.check_can_create_run("1.1.1.1")
        assert exc.value.headers["X-RateLimit-Reason"] == "busy"
        budget.assert_not_called()
