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


def get_all_ids(category: int):
    response = supabase_client.table("automatic_table").select().eq("category", category).execute()
    return response.data


def get_all_apple_ids(genre_id: int):
    response = supabase_client.table("automatic_apple_table").select().eq("genre_id", genre_id).execute()
    return response.data


def get_insights_count() -> int:
    response = supabase_client.table("insights").select("id", count="exact").limit(0).execute()
    return response.count or 0
