from app.lib.supabaseClient import supabase_client

def update_automatic_trend(data):
  supabase_client.table("automatic_table").insert(data).execute()

def check_youtube_id(id: str) -> bool:
  

