from datetime import datetime, timezone
from typing import Optional

from supabase import create_client, Client

from app.config.secrets import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
from app.utilities.getDate import getSundayDate

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def update_automatic_trend(data):
    supabase_client.table("automatic_table").insert(data).execute()


def update_automatic_video_date(id, date):
    current_video_date = supabase_client.table("automatic_table").select("date").eq("key", id).execute()
    if current_video_date.data[0] != date:
        supabase_client.table("automatic_table").update({"date": date}).eq("key", id).execute()


def check_youtube_id(key: str):
    response = supabase_client.table("automatic_table").select().eq("key", key).execute()
    if response.data:
        return response.data
    else:
        return []


def get_weekly_ids(category: int):
    date = getSundayDate()
    response = supabase_client.table("automatic_table").select().eq("date", date).eq("category", category).execute()
    return response.data


def update_automatic_apple_trend(data):
    supabase_client.table("automatic_apple_table").insert(data).execute()


def update_automatic_app_date(app_id: int, date):
    current_app_date = supabase_client.table("automatic_apple_table").select("date").eq("app_id", app_id).execute()
    if current_app_date.data[0] != date:
        supabase_client.table("automatic_apple_table").update({"date": date}).eq("app_id", app_id).execute()


def check_appstore_id(app_id: int):
    response = supabase_client.table("automatic_apple_table").select().eq("app_id", app_id).execute()
    if response.data:
        return response.data
    else:
        return []


def get_weekly_apple_ids(genre_id: int):
    date = getSundayDate()
    response = supabase_client.table("automatic_apple_table").select().eq("date", date).eq("genre_id", genre_id).execute()
    return response.data


def delete_youtube_id(key: str) -> None:
    supabase_client.table("automatic_table").delete().eq("key", key).execute()


def delete_appstore_id(app_id: int) -> None:
    supabase_client.table("automatic_apple_table").delete().eq("app_id", app_id).execute()


def get_all_ids(category: int):
    response = supabase_client.table("automatic_table").select().eq("category", category).execute()
    return response.data


def get_all_apple_ids(genre_id: int):
    response = supabase_client.table("automatic_apple_table").select().eq("genre_id", genre_id).execute()
    return response.data


def get_insights_count() -> int:
    response = supabase_client.table("insights").select("id", count="exact").limit(0).execute()
    return response.count or 0


def insert_idea_run(idea: str, target_gap: Optional[str]) -> dict:
    response = supabase_client.table("idea_runs").insert({
        "idea": idea,
        "target_gap": target_gap,
        "status": "pending",
        "competitors_json": [],
        "quotes_json": {},
    }).execute()
    return response.data[0]


def update_idea_run_preflight(
    run_id: str,
    category: str,
    signal_strength: str,
    signal_reasoning: str,
    candidates: list[dict],
) -> dict:
    response = supabase_client.table("idea_runs").update({
        "status": "preflight_ready",
        "category": category,
        "signal_strength": signal_strength,
        "signal_reasoning": signal_reasoning,
        "competitors_json": candidates,
    }).eq("id", run_id).execute()
    return response.data[0]


def get_idea_run(run_id: str) -> Optional[dict]:
    response = supabase_client.table("idea_runs").select("*").eq("id", run_id).execute()
    if response.data:
        return response.data[0]
    return None


def _one_updated_row(response, run_id: str) -> dict:
    """Return the single updated row, or raise if the update matched nothing.

    A Supabase update that matches zero rows returns an empty `data` list;
    indexing it blindly raises an opaque IndexError. Surface a descriptive
    error instead — the row was deleted, filtered by RLS, or lost a race.
    """
    rows = response.data or []
    if not rows:
        raise RuntimeError(f"idea_runs update matched no row for run_id={run_id}")
    return rows[0]


def update_idea_run_running(run_id: str, competitors: list[dict]) -> Optional[dict]:
    """Atomically transition preflight_ready → running, persisting the competitors.

    The `status='preflight_ready'` precondition makes the transition the gate:
    a second concurrent approve finds no matching row and gets `None`, so the
    pipeline is enqueued exactly once. Returns the updated row, or `None` when
    the run was no longer `preflight_ready`.
    """
    response = supabase_client.table("idea_runs").update({
        "status": "running",
        "competitors_json": competitors,
    }).eq("id", run_id).eq("status", "preflight_ready").execute()
    rows = response.data or []
    return rows[0] if rows else None


def update_idea_run_done(
    run_id: str,
    quotes: dict,
    coverage: dict,
    idea_match: Optional[dict],
    partial_sources: Optional[dict] = None,
) -> dict:
    """Write the terminal happy-path result. `status='done'` is set last (spec §8).

    `partial_sources` (slice 2 §5.1) is the partial-completion summary written to
    `partial_sources_json` — `None` on a fully-successful run, populated when the
    run completed `done` despite ≥1 source failing above the 70% threshold.
    """
    response = supabase_client.table("idea_runs").update({
        "status": "done",
        "quotes_json": quotes,
        "coverage_json": coverage,
        "idea_match_json": idea_match,
        "partial_sources_json": partial_sources,
    }).eq("id", run_id).execute()
    return _one_updated_row(response, run_id)


def update_idea_run_failed(run_id: str, failure_reason: str) -> dict:
    """Mark a run failed with a freeform reason (spec §8 happy-path-only failure mode)."""
    response = supabase_client.table("idea_runs").update({
        "status": "failed",
        "failure_reason": failure_reason,
    }).eq("id", run_id).execute()
    return _one_updated_row(response, run_id)


def update_idea_run_failed_if_running(
    run_id: str, failure_reason: str
) -> Optional[dict]:
    """Conditionally transition running → failed (spec §5.2, US-S4).

    The `status='running'` precondition makes this safe for read-time restart
    reconciliation: a row that a live pipeline already moved to `done`/`failed`
    on another code path matches no row and returns `None`, so a genuinely-live
    run can't be clobbered. Returns the updated row, or `None` when the run was
    no longer `running`.
    """
    response = supabase_client.table("idea_runs").update({
        "status": "failed",
        "failure_reason": failure_reason,
    }).eq("id", run_id).eq("status", "running").execute()
    rows = response.data or []
    return rows[0] if rows else None


def update_idea_run_reported(run_id: str, reason: str) -> dict:
    """Hide a run from the public surface (spec §7, US-S7, issue #62).

    Flips `status` → `reported`, stamps `reported_at`, and stores the report
    reason for manual admin review. The row is retained, not deleted (PRD §8 —
    "hidden pending decision"). Raises if the run_id matches no row.
    """
    response = supabase_client.table("idea_runs").update({
        "status": "reported",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "report_reason": reason,
    }).eq("id", run_id).execute()
    return _one_updated_row(response, run_id)


def insert_feedback_event(
    run_id: str,
    new_to_me_gap_ids: Optional[list[str]],
    direction: Optional[str],
    time_saved_estimate_minutes: Optional[int],
) -> dict:
    """APPEND-ONLY insert into `feedback_events` (spec §7, PRD §9).

    Every call adds a row — never an upsert, update, or delete. Multiple rows
    per `run_id` are expected (one per feedback submission). `submitted_at` is
    stamped server-side by the column default (migration 002).
    """
    response = supabase_client.table("feedback_events").insert({
        "run_id": run_id,
        "new_to_me_gap_ids_json": new_to_me_gap_ids,
        "direction": direction,
        "time_saved_estimate_minutes": time_saved_estimate_minutes,
    }).execute()
    return response.data[0]


def insert_gaps(gap_rows: list[dict]) -> list[dict]:
    """Insert the synthesised gaps for a run. No-op for an empty list."""
    if not gap_rows:
        return []
    response = supabase_client.table("gaps").insert(gap_rows).execute()
    return response.data or []


def list_gaps_for_run(run_id: str) -> list[dict]:
    """Return a run's gaps ordered by synthesis rank (ascending `ordinal`)."""
    response = (
        supabase_client.table("gaps")
        .select("*")
        .eq("run_id", run_id)
        .order("ordinal")
        .execute()
    )
    return response.data or []


def list_done_idea_runs(limit: int, before: Optional[datetime]) -> list[dict]:
    query = (
        supabase_client.table("idea_runs")
        .select("id, idea, updated_at")
        .eq("status", "done")
    )
    if before is not None:
        query = query.lt("updated_at", before.isoformat())
    response = query.order("updated_at", desc=True).limit(limit).execute()
    return response.data or []
