from app.lib.supabaseClient import supabase_client
from app.utilities.getDate import getSundayDate

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
  print(response.data)

  
if __name__ == "__main__":
  get_weekly_ids(20)