from app.lib.supabaseClient import supabase_client

def update_automatic_trend(data):
  supabase_client.table("automatic_table").insert(data).execute()

def check_youtube_id(key: str):
  response = supabase_client.table("automatic_table").select().eq("key", key).execute()
  if response.data:
    return response.data
  else:
    return []
  
if __name__ == "__main__":
  check_youtube_id("i")