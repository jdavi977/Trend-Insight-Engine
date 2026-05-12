# Changelog

Format: `YYYY-MM-DD | feature/fix/refactor | description`

---

## 2026-05-12
2026-05-12 | feature | RAG read path added to automatic pipeline — YouTube and App Store jobs now retrieve similar past insights before LLM extraction when RAG_READ_ENABLED=true
2026-05-12 | feature | RAG integration into extraction pipeline; semantic similarity threshold set to 0.35
2026-05-12 | feature | Frontend displays retrieved RAG context alongside generated insights
2026-05-12 | feature | End-to-end RAG foundation — pgvector adapter, embedding client, rag.py module
2026-05-12 | feature | Semantic search endpoint over pgvector store
2026-05-12 | feature | Backfill script fixed for YouTube and App Store sources
2026-05-12 | fix     | YouTube service now includes video title in output
2026-05-12 | fix     | App Store missing source field in service and prompt template

## 2026-05-11
2026-05-11 | docs    | RAG spec and architecture decision records created

## 2026-05-06
2026-05-06 | feature | extract_insights deep module encapsulating LLM pass-through and validateOutput
2026-05-06 | feature | Split ProblemItem into clientProblemItem — separate fields for API response vs. internal schema

## 2026-05-05
2026-05-05 | feature | Unified reviewPipeline with per-source config driving both YouTube and App Store
2026-05-05 | feature | Centralized genre module and prompt template
2026-05-05 | feature | App Store insights added to the Insights page
2026-05-05 | feature | homePageAppStore endpoint for homepage data
2026-05-05 | feature | App Store weekly workflow extended to social networking and utilities genres
2026-05-05 | refactor| youtube.py and appstore.py refactored as single-wrapper entry points
2026-05-05 | fix     | App Store scheduling and import issues resolved

## 2026-05-04
2026-05-04 | feature | YouTube client wrapper refactor — single external-call boundary
2026-05-04 | feature | Thumbnails now link to YouTube; best-quality thumbnails shown on home page

## 2026-05-01
2026-05-01 | feature | CI: pytest workflow added via GitHub Actions
2026-05-01 | feature | OpenAI client wrapper extracted from extractInsights
2026-05-01 | refactor| Layered app architecture — clients/, routers/, services/, jobs/ directories
2026-05-01 | refactor| Routers created for appstore, home, internal, and error handling
2026-05-01 | refactor| Renamed scripts → jobs, lib → clients; youtube.py helpers extracted

## 2026-04-30
2026-04-30 | feature | Weekly YouTube cron automated via GitHub Actions
2026-04-30 | feature | Root CLAUDE.md context map: tech stack, workspaces, routing table, naming conventions
2026-04-30 | feature | Pytest bootstrap covering current pipeline logic

## 2026-03-25
2026-03-25 | feature | RequestValidationError and StarletteHTTPException error handling added

## 2026-02-25
2026-02-25 | feature | YouTube video thumbnails fetched from API and displayed on Insights page

## 2026-02-17
2026-02-17 | feature | Homepage fetches and displays backend weekly YouTube data
2026-02-17 | feature | Weekly YouTube data grouped by video ID with category scaling

## 2026-02-13
2026-02-13 | feature | Category and date fields added to database; automatic pipeline updates existing IDs by date

## 2026-02-11
2026-02-11 | feature | Automatic YouTube pipeline fetches from database and returns results; deduplication by key

## 2026-01-28
2026-01-28 | feature | Pydantic validation for LLM JSON output; invalid data saved to data/invalid_data/

## 2026-01-27
2026-01-27 | feature | config.py loading all env keys with failsafes

## 2025-12-17
2025-12-17 | feature | Automatic ingestion of most popular gaming videos; insights pushed to Supabase

## 2025-12-16
2025-12-16 | feature | Supabase integration with insert function

## 2025-12-08
2025-12-08 | feature | Separate pages for YouTube and App Store sources
2025-12-08 | feature | App Store reviews analysis end-to-end

## 2025-12-05
2025-12-05 | feature | React frontend connected to FastAPI via fetch POST and CORSMiddleware
2025-12-05 | feature | App Store URL validation and review scraper

## 2025-12-03
2025-12-03 | feature | extractInsights working with OpenAI; problems batched via LLM prompt

## 2025-11-30
2025-11-30 | feature | Initial project: YouTube comment fetching and comment-cleaning pipeline
