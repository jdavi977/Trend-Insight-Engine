# Backend Context — app/

> Structural refactor in flight — see [planning/specs/app-refactor-and-pytest-bootstrap_spec.md](../planning/specs/app-refactor-and-pytest-bootstrap_spec.md). The Module Map below describes the **target** layout; current tree may differ until PRs 1–6 land.


## Module Map
| Folder         | Role                                              |
|----------------|---------------------------------------------------|
| config/        | Keywords, prompts, regex, API settings, category IDs |
| clients/       | One file per external service we wrap — `supabase.py`, `youtube.py`, (future) `openai.py` |
| ingestion/     | YouTube comment fetch + iTunes RSS scraper        |
| preprocessing/ | reviewPipeline.py, reviewClean.py, validateUrl.py   |
| llm/           | extractInsights.py (OpenAI call), validateOutput.py |
| schemas/       | All Pydantic boundary models — `api.py` (HTTP request bodies), `llm.py` (LLM output) |
| api/           | One router per resource (youtube, appstore, home, internal) + request schemas + exception handlers |
| services/      | Orchestration called by API/jobs (youtube, appstore, persistence) |
| jobs/          | Runnable entrypoints with `__main__` (cron-invoked, e.g. automaticYoutube.py) |
| utilities/     | Cross-cutting helpers only — `getDate.py`, `textCleaning.py` (YouTube API helper moved to `clients/youtube.py`) |
| main.py        | App factory: create_app(), middleware, include_router(), register exception handlers |

## Layer Boundaries
- `api` (main.py / routers) → `services/` only. Never imports `ingestion/`, `preprocessing/`, `llm/` directly.
- `services/` orchestrate pipeline stages and return data. No HTTP, no `__main__`.
- `jobs/` are thin shells: parse args/env, call a service, handle persistence/exit code.

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

## Testing
- Test tree lives at top-level `/tests/`, mirroring `app/` (`tests/api/`, `tests/services/`, `tests/preprocessing/`, `tests/llm/`). The empty `app/tests/` is removed.
- Tooling: `pytest` + `pytest-mock` + `httpx.TestClient`.
- Mock external services: YouTube Data API, iTunes RSS, OpenAI, Supabase. Hit pure modules (preprocessing, validateUrl, validateOutput, schemas) for real — mocking deterministic functions tests nothing.
- Pre-refactor safety net (write these BEFORE moving files):
  1. `tests/preprocessing/test_validateUrl.py`
  2. `tests/preprocessing/test_reviewPipeline.py` + `test_reviewClean.py`
  3. `tests/llm/test_validateOutput.py`
  4. `tests/services/test_youtube_service.py` (happy path, all clients mocked)
  5. `tests/api/test_routes.py` (TestClient smoke tests, services mocked)

## LLM Output Schema (schemas/llm.py)
Each insight has: problem (str), type (enum), severity (1-5),
frequency (1-5), total_likes (int)
Problem types: feature_request, complaint, usability, performance, pricing