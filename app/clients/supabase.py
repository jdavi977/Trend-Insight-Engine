from datetime import datetime
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
) -> dict:
    """Write the terminal happy-path result. `status='done'` is set last (spec §8)."""
    response = supabase_client.table("idea_runs").update({
        "status": "done",
        "quotes_json": quotes,
        "coverage_json": coverage,
        "idea_match_json": idea_match,
    }).eq("id", run_id).execute()
    return _one_updated_row(response, run_id)


def update_idea_run_failed(run_id: str, failure_reason: str) -> dict:
    """Mark a run failed with a freeform reason (spec §8 happy-path-only failure mode)."""
    response = supabase_client.table("idea_runs").update({
        "status": "failed",
        "failure_reason": failure_reason,
    }).eq("id", run_id).execute()
    return _one_updated_row(response, run_id)


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
