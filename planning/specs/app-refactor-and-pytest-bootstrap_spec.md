# app/ Structural Refactor & Pytest Bootstrap

## Problem
Three observed smells in the current `app/` layout:

- **`app/scripts/` is overloaded.** It holds one real cron entrypoint (`automaticYoutube.py`) alongside three orchestration modules (`youtubePipeline.py`, `appStorePipeline.py`, `data_save.py`) that are imported directly by `main.py:10-12`. Three of four "scripts" aren't scripts.
- **`main.py` is growing.** 109 lines mixing app construction, CORS, three request models, four endpoint bodies, and two exception handlers. `app/CONTEXT.md` already says "no business logic in main.py" — currently held together by thin wrappers. Latent bug: exception handlers at `main.py:88`/`100` reference `Request` but it's never imported.
- **No `services/` layer.** Pipelines double as services. `app/CONTEXT.md` doc and `app/scripts/` tree already disagree on what `scripts/` contains.

No tests exist (`app/tests/` is empty), so the refactor needs a safety net first.

## Target Layout
```
app/
  main.py                 # create_app() factory: middleware, include_router(), register exception handlers
  api/
    youtube.py            # POST /analyze/youtube
    appstore.py           # POST /analyze/appStore
    home.py               # GET  /get/homePage
    internal.py           # POST /data/send
    errors.py             # exception handlers (with the missing Request import fixed)
  services/
    youtube_service.py    # was scripts/youtubePipeline.py
    appstore_service.py   # was scripts/appStorePipeline.py
    persistence_service.py# was scripts/data_save.py
  jobs/                   # runnable __main__ entrypoints only
    automaticYoutube.py   # was scripts/automaticYoutube.py
  schemas/
    api.py                # request bodies (YoutubeAnalyzeRequest, AppStoreAnalyzeRequest, DataSave)
    llm.py                # was llm_insights.py — LLM output
  clients/                # one file per external service we wrap
    supabase.py           # merged lib/db.py + lib/supabaseClient.py
    youtube.py            # was utilities/youtubeApiHelper.py (drop __main__ scratch)
  ingestion/              # unchanged
  preprocessing/          # unchanged
  llm/                    # unchanged
  config/                 # unchanged (config.py vs settings.py rename DEFERRED)
  utilities/              # cross-cutting only — getDate.py, textCleaning.py
```

## Layer Boundaries
- `api/` → `services/` only. Never imports `ingestion/`, `preprocessing/`, `llm/` directly.
- `services/` orchestrate pipeline stages and return data. No HTTP, no `__main__`.
- `jobs/` are thin shells: parse args/env, call a service, handle persistence/exit code.
- `schemas/` is the single home for every Pydantic boundary model, split by direction.
- `clients/` wraps every external service in one file each.

## Pytest Bootstrap
- **Tree:** top-level `/tests/` mirroring `app/`. Delete empty `app/tests/`.
- **Tooling:** `pytest`, `pytest-mock`, `httpx.TestClient`. No `pytest-asyncio` (handlers are sync).
- **Mock vs real:**
  - Mock: YouTube Data API, iTunes RSS, OpenAI, Supabase.
  - Real: `preprocessing/`, `validateUrl.py`, `validateOutput.py`, schema models.
- **Pre-refactor safety net (write BEFORE any files move):**
  1. `tests/preprocessing/test_validateUrl.py` — table of valid/invalid YouTube + App Store URLs.
  2. `tests/preprocessing/test_commentClean.py` + `test_reviewClean.py` — fixed input → exact cleaned output.
  3. `tests/llm/test_validateOutput.py` — good + malformed `llm.py`-shaped dicts, assert pass/fail.
  4. `tests/services/test_youtube_service.py` — happy-path orchestration, all clients mocked.
  5. `tests/api/test_routes.py` — `TestClient` smoke tests for all four endpoints, services mocked.
- **Out of scope round 1:** ingestion modules (mock surface too large for value), `extractInsights.py` (testing OpenAI SDK), `automaticYoutube.py` (covered via service tests).

## Sequencing (six PRs)

### PR 1 — Pytest bootstrap, no code moves
- Add `pytest` + `pytest-mock` to requirements; configure `testpaths = ["tests"]`.
- Create `tests/` with `conftest.py` (mock client fixtures) and `tests/fixtures/` (sample JSON).
- Write the five safety-net tests **against the current layout**.
- Delete empty `app/tests/`.
- Wire `make test` (CI integration deferred to `ops/`).
- Result: green safety net, zero behavior change.

### PR 2 — Schemas split + main.py bug fix
- Rename `schemas/llm_insights.py` → `schemas/llm.py`.
- Create `schemas/api.py` with the three request models from `main.py:39-46`.
- Fix missing `Request` import in `main.py` exception handlers.
- Update imports.

### PR 3 — Carve out `services/`
- Move `app/scripts/{youtubePipeline, appStorePipeline, data_save}.py` → `app/services/{youtube_service, appstore_service, persistence_service}.py`.
- Update `main.py` imports; update `automaticYoutube.py` if it imports any.
- Update `tests/services/test_youtube_service.py` import path — that's the regression check.

### PR 4 — Carve out `app/api/` (HIGHEST RISK)
- Create `app/api/{youtube, appstore, home, internal, errors}.py`, each owning a router.
- `main.py` becomes `create_app()`: middleware, `include_router()` × 4, error handler registration.
- `tests/api/test_routes.py` is the load-bearing safety net for this PR. Should stay green without changes.
- Watch for: router prefix collisions, `include_in_schema=False` preserved on `/data/send` and `/`, exception handler registration order.

### PR 5 — Rename `lib/` → `clients/`, move YouTube helper
- Merge `lib/db.py` + `lib/supabaseClient.py` → `clients/supabase.py`.
- Move `utilities/youtubeApiHelper.py` → `clients/youtube.py`, drop `__main__` scratch.
- Delete `app/lib/`.

### PR 6 — Rename `scripts/` → `jobs/`
- Move `scripts/automaticYoutube.py` → `jobs/automaticYoutube.py`.
- Update cron / Makefile / `ops/` references.
- Cosmetic once PR 3 has pulled the orchestration out.

## Deferred (not in this refactor)
- `config/config.py` vs `config/settings.py` rename (cosmetic, post-refactor).
- Ingestion-module tests.
- OpenAI client wrapper extraction into `clients/openai.py`.
- CI wiring (lives in `ops/`).
