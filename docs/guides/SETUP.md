# Developer Setup

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | bundled with Node |

You'll also need API keys for three services:

| Service | Where to get it |
|---------|----------------|
| YouTube Data API v3 | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| OpenAI | [OpenAI Platform](https://platform.openai.com/api-keys) |
| Supabase | [supabase.com](https://supabase.com) — project URL + service role key |

---

## 1. Clone the repo

```bash
git clone <repo-url>
cd Trend-Insight-Engine
```

---

## 2. Backend

### Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### Install dependencies

```bash
pip install fastapi "uvicorn[standard]" pydantic python-dotenv \
  google-api-python-client openai requests supabase
```

### Configure environment variables

Create a `.env` file at the project root:

```bash
YOUTUBE_API=your_youtube_api_key_here
OPENAI_KEY=your_openai_api_key_here
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
LOG_LEVEL=INFO          # optional: DEBUG, INFO, WARNING, ERROR
```

### Run the backend

```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:5173` (Vite default).

> **Note:** the backend's CORS allowlist is set to `http://localhost:5173`. If Vite picks a different port, update `allow_origins` in `app/main.py`.

---

## 4. Supabase Setup

The RAG layer and the weekly pipeline both need a Supabase project with `pgvector` enabled.

1. Enable the `pgvector` extension in your Supabase project: **Database → Extensions → vector**
2. Run the migration scripts in `ops/` to create the `automatic_table` and `insights` tables (see `ops/CONTEXT.md` for details)
3. Make sure your `.env` has both `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` set

---

## 5. Weekly Pipeline (optional)

The Home and Insights pages are powered by pre-generated data. To populate them:

```bash
# YouTube (Games, Science & Tech, How-to & Style)
python app/jobs/automaticYoutube.py

# App Store (Games, Social, Utilities)
python app/jobs/automaticAppStore.py
```

Run these manually or schedule them weekly via cron or a task scheduler.

---

## Testing the App

**Manual analysis (YouTube or App Store):**
1. Open `http://localhost:5173`
2. Go to the YouTube or App Store tab
3. Paste a valid URL:
   - YouTube: `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`
   - App Store: `https://apps.apple.com/us/app/app-name/id123456789`
4. Click **Analyze** and wait for results

**Weekly home page:**
Run `automaticYoutube.py` (step 5 above) first, then visit the Home or Insights tab.

---

## Project Structure

```
app/
  api/          FastAPI route handlers
  clients/      External service clients (OpenAI, Supabase, pgvector)
  config/       Constants, prompt templates, keywords, secrets
  ingestion/    YouTube and App Store data fetching
  jobs/         Automated weekly pipeline scripts
  llm/          LLM extraction and output validation
  preprocessing/ Filtering, deduplication, text cleaning
  rag/          Embed-and-store + retrieve-similar
  schemas/      Pydantic models
  utilities/    Text helpers, date bucketing
frontend/
  src/
    components/ Reusable UI components
    pages/      Home, Insights, YouTube, AppStore
docs/           API reference, guides, changelog
ops/            Deployment scripts, Supabase migrations
planning/       Feature specs, architecture decisions
```
