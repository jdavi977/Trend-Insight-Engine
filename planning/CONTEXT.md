# Planning Context — Trend Insight Engine

## What This App Does
Ingests user-generated content (YouTube comments, App Store reviews),
runs a 3-stage pipeline (ingest → preprocess → LLM extract), and
returns structured JSON insights with severity/frequency scores.

## Current Pipeline Flow
URL Input → validateUrl.py → Ingestion (YouTube API / iTunes RSS)
→ Preprocessing (commentClean / reviewClean) → LLM (extractInsights)
→ validateOutput.py → JSON response to frontend

## Active Features
- Manual YouTube analysis (/analyze/youtube)
- Manual App Store analysis (/analyze/appStore)
- Weekly Youtube pipeline (scripts/automaticYoutube.py)
- Home page weekly insights from Supabase (/get/homePage)
- Category filtering: Games, Science & Tech, How-to & Style

## Architectural Principles
- Each pipeline stage is a separate module (ingestion, preprocessing, llm)
- No stage knows about the other — data flows top to bottom
- Pydantic validates all input (API requests) and all output (LLM responses)
- Supabase is ONLY used for automated/weekly data, not manual analysis
- Config is centralized in app/config/ (keywords, prompts, patterns, IDs)

## Current Priorities
- Using youtube api thumbnail url to display an image for weekly insights

## Known Constraints
- YouTube Data API v3 quota limits per day
- iTunes RSS is paginated and rate-sensitive
- OpenAI calls are synchronous — long videos = long wait time
- Engagement filter: YouTube ≥50 likes, App Store >5 votes