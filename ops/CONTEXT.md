# Ops Context — ops/

## Infrastructure
- Backend: Uvicorn on port 8000 (local), deployable to any ASGI host
- Frontend: Vite dev server port 5173, builds to static dist/
- Database: Supabase (automatic_table) — managed cloud Postgres
- Automation: automaticYoutube.py runs weekly (cron or manual trigger)

## Weekly Pipeline
1. Run app/jobs/automaticYoutube.py
2. Fetches top videos across 3 category IDs (Games, Science & Tech, How-to)
3. Runs full pipeline on each video
4. Writes results to Supabase automatic_table keyed by (video_id, date, category)
5. Frontend /get/homePage reads from this table

## Required Env Vars
YOUTUBE_API, OPENAI_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

## Deploy Checklist (deploy/checklist.md)
- [ ] .env populated with all 4 keys
- [ ] CORS allow_origins updated for production domain
- [ ] Supabase RLS policies reviewed
- [ ] Weekly pipeline scheduled via .github/workflows/weekly-youtube.yml
      (runs Sundays 08:00 UTC; secrets set in repo settings)
- [ ] OpenAI dashboard hard usage limit configured (~$25/month) so a
      runaway pipeline cannot drain billing