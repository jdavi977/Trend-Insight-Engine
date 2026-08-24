"""Abuse / cost guards for `POST /runs` (slice 2 §6, issue #59).

Three guards make the run front door safe in front of a stranger, all rejecting
at the same chokepoint with `429`:

| Guard       | Check                                              | Response               |
|-------------|----------------------------------------------------|------------------------|
| Concurrency | a pipeline is already `running` on this instance   | 429 busy + Retry-After |
| Rate limit  | >3 runs/hour OR >10 runs/day for this client IP    | 429 rate_limited + R-A |
| Budget      | today's OpenAI spend ≥ OPENAI_DAILY_BUDGET_USD     | 429 budget_exhausted   |

Check order (`check_can_create_run`): concurrency → rate limit → budget —
cheapest / most-likely-to-reject first (spec §6). The router calls
`check_can_create_run` *before* `idea_run_service.create_run` does any work, then
`record_run` once the run is created. Layer rule holds: router → service.

**State is operational, not run data (spec §4).** Per-IP counters are in-process
TTL buckets (a single instance for v1, PRD §8); lost-on-restart resets the
window, which is lenient, not unsafe. The daily spend total lives in the OpenAI
transport (`app/clients/openai.py`). A multi-instance deploy moves both to a
shared store — noted, not built.

**Client-IP trust (open question Q4).** `client_ip` reads the first hop of
`X-Forwarded-For`, falling back to the socket peer. This is correct **only**
behind a single known proxy that sets/overwrites the header — the v1 deploy's
assumption (PRD §8). If the app is ever exposed without that proxy, or behind an
untrusted one, the header is client-spoofable and the per-IP limit is trivially
bypassed: re-pin this to the real proxy topology before changing the deploy.
"""
from __future__ import annotations

import threading
import time

from fastapi import HTTPException, Request, status

from app.clients import openai as openai_client
from app.config.constants import (
    BUSY_RETRY_AFTER_SECONDS,
    RATE_LIMIT_PER_DAY,
    RATE_LIMIT_PER_HOUR,
)
from app.services import run_pipeline_service

_HOUR_SECONDS = 3600
_DAY_SECONDS = 86_400

# client IP -> sorted list of POST /runs timestamps (epoch seconds), pruned to
# the trailing day on each access. In-process; see module docstring.
_ip_runs: dict[str, list[float]] = {}
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    """Derive the client IP: first `X-Forwarded-For` hop, else the socket peer.

    See the module docstring on the single-known-proxy trust assumption (Q4).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first_hop = forwarded.split(",")[0].strip()
        if first_hop:
            return first_hop
    if request.client is not None:
        return request.client.host
    return "unknown"


def _prune_locked(ip: str, now: float) -> list[float]:
    """Drop timestamps older than a day and return the surviving list. Locked."""
    cutoff = now - _DAY_SECONDS
    kept = [t for t in _ip_runs.get(ip, []) if t > cutoff]
    if kept:
        _ip_runs[ip] = kept
    else:
        _ip_runs.pop(ip, None)
    return kept


def _check_concurrency() -> None:
    if run_pipeline_service.has_running_pipeline():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A run is already in progress. Please try again shortly.",
            headers={
                "Retry-After": str(BUSY_RETRY_AFTER_SECONDS),
                "X-RateLimit-Reason": "busy",
            },
        )


def _check_rate_limit(ip: str, now: float) -> None:
    with _lock:
        runs = _prune_locked(ip, now)

    hour_runs = [t for t in runs if t > now - _HOUR_SECONDS]
    if len(hour_runs) >= RATE_LIMIT_PER_HOUR:
        retry_after = int(min(hour_runs) + _HOUR_SECONDS - now) + 1
        _raise_rate_limited(retry_after, "hourly")
    if len(runs) >= RATE_LIMIT_PER_DAY:
        retry_after = int(min(runs) + _DAY_SECONDS - now) + 1
        _raise_rate_limited(retry_after, "daily")


def _raise_rate_limited(retry_after: int, window: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            f"Rate limit reached ({RATE_LIMIT_PER_HOUR}/hour, "
            f"{RATE_LIMIT_PER_DAY}/day). Try again later."
        ),
        headers={
            "Retry-After": str(max(retry_after, 1)),
            "X-RateLimit-Reason": "rate_limited",
            "X-RateLimit-Window": window,
        },
    )


def _check_budget() -> None:
    if openai_client.is_budget_exhausted():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The daily analysis budget has been reached. Please try again tomorrow.",
            headers={"X-RateLimit-Reason": "budget_exhausted"},
        )


def check_can_create_run(ip: str) -> None:
    """Run all three guards in order; raise 429 on the first that rejects.

    Read-only: this never records the run. The router calls `record_run(ip)`
    after `create_run` succeeds so a budget rejection doesn't burn a rate-limit
    slot. Order is concurrency → rate limit → budget (spec §6).
    """
    _check_concurrency()
    _check_rate_limit(ip, time.time())
    _check_budget()


def record_run(ip: str) -> None:
    """Record one accepted POST /runs against the client IP's TTL bucket."""
    now = time.time()
    with _lock:
        _prune_locked(ip, now)
        _ip_runs.setdefault(ip, []).append(now)


def reset() -> None:
    """Test seam: clear all per-IP counters."""
    with _lock:
        _ip_runs.clear()
