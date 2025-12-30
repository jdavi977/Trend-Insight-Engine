from lib.supabaseClient import supabase_client

def update_automatic_trend(data):
  print(1)
  supabase_client.table("automatic_table").insert(data).execute()
