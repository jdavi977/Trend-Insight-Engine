# Architecture

## Overview

Trend Insight Engine is a full-stack application with two analysis modes:

- **Manual** — user pastes a YouTube or App Store URL, gets structured insights immediately
- **Automatic** — weekly GitHub Actions jobs fetch trending content, run the full pipeline, and store results for the Home and Insights pages

Both modes run the same core pipeline: ingest → preprocess → LLM → store. The RAG layer runs alongside: it reads similar past insights before LLM extraction and writes new insights after.

---

## High-Level Data Flow

```
                        MANUAL ANALYSIS
                        ───────────────
  User (browser)
       │  POST /analyze/youtube
       │  POST /analyze/appStore
       ▼
  ┌──────────────────────────────────────────────┐
  │              FastAPI  (app/main.py)           │
  │  ┌──────────────────────────────────────────┐ │
  │  │   Service Layer                          │ │
  │  │   youtube_service / appstore_service     │ │
  │  └─────────────┬────────────────────────────┘ │
  └────────────────│─────────────────────────────┘
                   │
       ┌───────────┼───────────────────────────┐
       │           │                           │
       ▼           ▼                           ▼
  [Ingestion]  [RAG Read]              [Preprocessing]
  fetch 100    retrieve_similar()       engagement filter
  comments /   embeds query (title)     emoji strip
  10 pages     returns top-k past       keyword filter
  reviews      insights                 dedup
       │           │                           │
       └───────────┴───────────────────────────┘
                           │
                           ▼
                    [LLM Extraction]
                    gpt-4o
                    system prompt = genre config
                                  + prior insights
                    returns structured problems
                    (severity, frequency, type)
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
          [RAG Write]           [API Response]
          embed_and_store()     JSON → frontend
          text-embedding-3-small
          upsert to insights table
          (pgvector / Supabase)
```

```
                        AUTOMATIC PIPELINE
                        ──────────────────
  GitHub Actions (Sunday)
       │
       ▼
  automaticYoutube.py / automaticAppStore.py
       │
       ▼
  automaticPipeline.run_automatic_pipeline()
       │
       ├── check_existing() — skip if already processed this week
       ├── ingest()         — fetch comments/reviews
       ├── clean()          — same preprocessing as manual
       ├── system_prompt()  — build_prompt() calls retrieve_similar(title)
       │                      if RAG_READ_ENABLED; injects prior insights
       ├── extract_insights() — LLM with genre prompt + RAG context
       ├── post_extract()   — embed_and_store() if RAG_WRITE_ENABLED
       └── persist_row()    — upsert to automatic_table / automatic_apple_table
       │
       ▼
  Supabase (Postgres)
       │
       ▼
  GET /get/homePage
  GET /get/homePageAppStore
       │
       ▼
  Home + Insights pages (React frontend)
```

---

## Components

### Frontend (`frontend/`)

React 19 SPA built with Vite. Four pages:

| Page | Route | Data source |
|------|-------|-------------|
| Home | `/` | `GET /get/homePage` + `GET /get/homePageAppStore` |
| Insights | `/insights` | same as Home |
| YouTube | `/youtube` | `POST /analyze/youtube` |
| App Store | `/appstore` | `POST /analyze/appStore` |

Frontend dev server runs on port 5173. Backend CORS is locked to that origin.

### API Layer (`app/api/`)

FastAPI route handlers. Thin — they validate the request and delegate to a service.

| File | Endpoints |
|------|-----------|
| `youtube.py` | `POST /analyze/youtube` |
| `appstore.py` | `POST /analyze/appStore` |
| `home.py` | `GET /get/homePage`, `GET /get/homePageAppStore` |
| `insights.py` | `GET /insights/similar` |
| `internal.py` | `POST /data/send` (hidden from OpenAPI schema) |
| `errors.py` | 422 and HTTP exception handlers |

### Service Layer (`app/services/`)

Orchestrates pipeline stages. One service per analysis type.

- `youtube_service.youtube_manual(link)` — full YouTube manual flow
- `appstore_service.app_store_manual(link)` — full App Store manual flow
- `rag_service.similar(query, k)` — RAG retrieval endpoint wrapper
- `persistence_service.data_save(data)` — saves JSON to filesystem

Services never import from `app/api/` and never call HTTP endpoints.

### Ingestion (`app/ingestion/`)

- `youtubeComments.py` — fetches up to 100 comments via YouTube Data API v3
- `appStoreReviews.py` — paginates iTunes RSS Feed (up to 10 pages)

### Preprocessing (`app/preprocessing/`)

- `reviewPipeline.clean()` — single pipeline for both sources:
  1. Engagement filter (likes ≥ 50 for YouTube; vote_count ≥ 6 for App Store)
  2. Normalize content (lowercase, strip whitespace)
  3. Strip emojis
  4. Keyword filter (App Store only — genre-specific keyword list)
  5. Deduplicate by content
- `validateUrl.py` — regex validation for YouTube and App Store URLs

### LLM Extraction (`app/llm/`)

- `extractInsights.extract_insights()` — sends cleaned data to gpt-4o, parses and validates the response
- Invalid problems quarantined to `data/invalid_data/` (not raised to caller)
- Returns `LLMExtraction` (source, title, list of validated `ProblemItem`s)

### RAG Layer (`app/rag/`)

See [RAG.md](RAG.md) for full detail.

- `embed_and_store(extraction, source_url)` — embeds and upserts each problem
- `retrieve_similar(query, k=5)` — embeds query, calls pgvector RPC, returns top-k

### Clients (`app/clients/`)

One file per external service. No business logic.

| File | Service | Key operations |
|------|---------|----------------|
| `youtube.py` | YouTube Data API v3 | list comments, list popular, get title |
| `appstore.py` | iTunes RSS Feed | list reviews, list top apps, get app name |
| `openai.py` | OpenAI API | `gpt-4o` completions, `text-embedding-3-small` embeddings |
| `supabase.py` | Supabase Postgres | CRUD for `automatic_table`, `automatic_apple_table` |
| `pgvector.py` | Supabase pgvector | upsert and query `insights` table |

### Config (`app/config/`)

| File | What it holds |
|------|--------------|
| `constants.py` | Numeric constants (comment counts, category IDs, RAG thresholds) |
| `genres.py` | Per-genre metadata: keywords, LLM prompt fragments, category IDs |
| `promptTemplates.py` | LLM system prompt builders — inject genre config + RAG context |
| `preprocessing.py` | Preprocessing config structs for each source |
| `secrets.py` | `keyChecker()` — loads and validates env vars |
| `regex.py` | URL and emoji regex patterns |

### Jobs (`app/jobs/`)

See [PIPELINE.md](PIPELINE.md) for full detail.

- `automaticYoutube.py` — processes 3 YouTube categories weekly
- `automaticAppStore.py` — processes 3 App Store genres weekly
- `automaticPipeline.py` — shared `run_automatic_pipeline()` with `SourceAdapter` pattern

### Storage (Supabase)

| Table | Key | Purpose |
|-------|-----|---------|
| `automatic_table` | video ID | Weekly YouTube insights |
| `automatic_apple_table` | app ID | Weekly App Store insights |
| `insights` | SHA256(source_url + problem) | RAG vector store |

---

## External Dependencies

| Service | Used for |
|---------|---------|
| YouTube Data API v3 | Fetching comments and trending videos |
| iTunes RSS Feed | Fetching reviews and top apps |
| OpenAI API (gpt-4o) | LLM insight extraction |
| OpenAI API (text-embedding-3-small) | RAG embeddings |
| Supabase Postgres | Persistent storage for all data |
| Supabase pgvector | Vector similarity search for RAG |
| GitHub Actions | Weekly pipeline automation |
