# Backend Context — app/

## Module Map
| Folder         | Role                                              |
|----------------|---------------------------------------------------|
| config/        | Keywords, prompts, regex, API settings, category IDs |
| ingestion/     | YouTube API client + iTunes RSS scraper           |
| preprocessing/ | commentClean.py, reviewClean.py, validateUrl.py   |
| llm/           | extractInsights.py (OpenAI call), validateOutput.py |
| schemas/       | Pydantic model: llm_insights.py                   |
| scripts/       | automaticYoutube.py (weekly cron pipeline)        |
| utilities/     | Text helpers, YouTube response helpers, date utils |
| main.py        | FastAPI app — 4 endpoints, CORS, routing          |

## API Endpoints
- POST /analyze/youtube   → manual YouTube analysis
- POST /analyze/appStore  → manual App Store analysis
- GET  /get/homePage      → fetch weekly Supabase insights
- POST /data/send         → save JSON to local filesystem

## Code Patterns (Follow These)
- Each pipeline stage returns data to the caller — no side effects
- All config (keywords, prompts, regex) lives in config/, never hardcoded
- Pydantic models for ALL external data (API requests + LLM responses)
- Use python-dotenv for all secrets — never hardcode keys
- Logging via Python's logging module at appropriate levels

## Patterns to Avoid
- Do NOT add business logic to main.py — it only routes
- Do NOT write to Supabase from manual analysis endpoints
- Do NOT add new dependencies without updating requirements/setup docs
- Do NOT skip validateOutput.py after LLM calls

## LLM Output Schema (llm_insights.py)
Each insight has: problem (str), type (enum), severity (1-5),
frequency (1-5), total_likes (int)
Problem types: feature_request, complaint, usability, performance, pricing