from supabaseClient import supabase_client

def update_automatic_trend(data,):
    supabase_client.table("automatic_table").insert(data).execute()

row = {
  "source": "youtube",
  "data": {
    "captured_at": "2025-12-16T14:05:00Z",
    "top_problems": [
      {"problem": "Too many ads", "severity": 4, "frequency": 3}
    ]
  }
}

update_automatic_trend(row)