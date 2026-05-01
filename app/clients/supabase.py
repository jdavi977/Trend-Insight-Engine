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
