# Backend Context — app/

> Authority: [docs/PRD.md](../docs/PRD.md) (v2.2) §7.1–§7.5, §7.7–§7.9, §8, §9,
> §10.1, §15 (read those sections, not the whole file).
> v2 = **idea-in → cross-competitor gaps-out**. The legacy v1 single-URL +
> weekly surface (routers, jobs, RAG) was deleted in slice 3 (issue #72).

## Module Map
| Folder         | Role                                                                 |
|----------------|---------------------------------------------------------------------|
| config/        | Constants/tunables, prompts, regex, secrets. `constants.py` holds `MODEL_ROUTING` (§10.1) + engagement filters |
| clients/       | One file per external service — `appstore.py`, `youtube.py`, `openai.py`, `supabase.py` |
| ingestion/     | YouTube comment fetch + App Store review fetch                       |
| preprocessing/ | `reviewPipeline.py`, `redact.py` (regex + NER PII strip)             |
| llm/           | `preflight.py`, `synthesis.py`, `idea_match.py`, `router.py` (stage→model resolver). Per-source extraction lives in `services/per_source_extraction_service.py` |
| schemas/       | Pydantic boundary models — `runs.py` (v2 domain) |
| api/           | One router per resource. `runs.py`, `health.py` (`GET /` liveness). Plus `errors.py` |
| services/      | Orchestration — `idea_run_service`, `run_pipeline_service`, `preflight_service`, `per_source_extraction_service` |
| jobs/          | Runnable entrypoints. `preflight_smoke.py` |
| eval/          | PRD §7.9 measurement: `harness.py` drives the real pipeline on a `seed/` idea; `metrics.py` = the four pure scorers; reports → gitignored `reports/`. Outside the request path |
| utilities/     | Cross-cutting helpers only                                           |
| main.py        | App factory: `create_app()`, CORS, X-Robots-Tag middleware, routers, exception handlers |

## Layer Boundaries
- `api` (main.py / routers) → `services/` only. Never imports `ingestion/`,
  `preprocessing/`, `llm/` directly.
- `services/` orchestrate pipeline stages and return data. No HTTP, no `__main__`.
- Pipeline modules (`ingestion`, `preprocessing`, `llm`) don't import each other.
- `jobs/` are thin shells: parse args/env, call a service, handle exit.

## v2 API Endpoints (PRD §7.2)
- `POST /runs` — `{ idea, target_gap? }`. Runs pre-flight synchronously (≤10s),
  returns `preflight_ready` + candidate competitors. Per-IP rate-limited.
- `POST /runs/:id/approve` — `{ competitors[], acknowledged_low_signal? }`.
  `preflight_ready → running`; enqueues background pipeline. Low-signal without
  ack → 400.
- `POST /runs/:id/feedback` — `{ new_to_me_gap_ids?, direction?, time_saved? }`.
  Append-only; valid only when `done`. *(not yet implemented)*
- `POST /runs/:id/report` — `{ reason }`. Hides run pending admin. *(not yet impl.)*
- `GET /runs/:id` — current state + (when `done`) full results. Public.
- `GET /runs` — paginated public feed of completed runs (drives Home).

All `/runs` responses get `X-Robots-Tag: noindex, nofollow` (main.py middleware).
Legacy `/analyze/*`, `/get/homePage`, `/data/send`, `/insights/similar` are
**deleted** (slice 3, issue #72); `GET /` returns a tiny static health payload.

## Run Lifecycle
`pending → preflight_ready → running → done | failed` (+ `reported`).
`failed` terminal with structured `failure_reason` (e.g. `server_restart`).

## Code Patterns (Follow These)
- Each pipeline stage returns data to the caller — no side effects.
- All config (prompts, regex, model routing, filters) in `config/`, never hardcoded.
- Pydantic models for ALL external data (API requests + LLM responses).
- **Every LLM call resolves config via `llm/router.py` `resolve(stage)`** —
  never hardcode model/temperature/max_tokens at a call site (§10.1).
- **Idea-blinded extraction:** per-source extractor takes `SourceMetadata`, never
  `idea`/`target_gap`. Only synthesis + idea-match see the idea (§7.8).
- Synthesis output validated for quote-ID grounding: every `GapItem` cites ≥2
  `quote_id`s from the retrieval pool; uncited / unknown-ID gaps rejected (§7.7).
- PII redacted at persist time (`redact.py`); raw text never persisted.
- Use `python-dotenv` for secrets; logging via stdlib `logging`.

## Patterns to Avoid
- Do NOT add business logic to `main.py` — it only wires the app.
- Do NOT let `idea`/`target_gap` reach per-source extraction prompts.
- Do NOT emit a gap citing <2 quotes or a `quote_id` outside the pool.
- Do NOT hardcode model selection — route through `resolve(stage)`.
- Do NOT add new dependencies without updating requirements/setup docs.

## Reliability / Limits (PRD §8)
- Pre-flight ≤10s; full run ≤5 min p50; cap 5 concurrent OpenAI calls.
- Sources fan out ≤10 concurrently, sequential within a source; retry once with
  backoff. ≥70% sources succeed → `done` + `partial_sources`; below → `failed`.
- Rate limits: per-IP 3/hr, 10/day; daily OpenAI budget cap → `429 budget_exhausted`.
- Single active run per instance; 2nd submission → `429 busy` (queue UX is v1.1).

## Testing
- Test tree at top-level `/tests/`, mirroring `app/` (`tests/api/`,
  `tests/services/`, `tests/llm/`, `tests/preprocessing/`).
- Tooling: `pytest` + `pytest-mock` + `httpx.TestClient`.
- Mock external services (YouTube, App Store, OpenAI, Supabase). Hit pure modules
  (preprocessing, redact, schemas, llm/router) for real.
- Eval harness (PRD §7.9): runner scores pipeline output (gap recall,
  hallucination rate, citation ratio, severity calibration) against a 5-idea
  hand-labelled seed set. Manual in v1; CI gate is v1.1.

## v2 Domain Schema (schemas/runs.py)
- `GapItem`: `gap_id`, `gap`, `severity` (1–5 rubric), `frequency` (raw count),
  `spread` (distinct competitors), `competitors_present[]`, `evidence_quote_ids[]`
  (≥2).
- `Quote` (keyed by `quote_id`): `source`, `source_id`, `text_redacted`, `like_count`.
- `Coverage`: `quotes_retrieved`, `quotes_cited`, `citation_ratio`.
- `RunResult` = strict terminal view; `RunStateResponse` = permissive any-stage view.
- `Competitor`, `PainItem`, `SourceMetadata` (idea-blinded extractor input),
  `IdeaMatch`, `PreflightResult`.

## Model Routing (config/constants.py + llm/router.py)
v1 maps every stage to `gpt-4o`. Stages: `preflight_classify`, `preflight_rank`,
`per_source_extract`, `synthesis`, `idea_match`. Swapping a model per stage is a
one-line config change validated against the eval harness — no pipeline edits.
