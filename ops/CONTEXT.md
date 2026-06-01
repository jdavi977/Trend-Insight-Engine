# Ops Context — ops/

> Authority: [docs/PRD.md](../docs/PRD.md) §8, §9 (v2.2). The weekly YouTube
> pipeline is **removed** in v2; runs are on-demand. Legacy weekly automation
> remains in tree pending cleanup.

## Infrastructure
- Backend: Uvicorn on port 8000 (local), deployable to any ASGI host.
- Frontend: Vite dev server port 5173, builds to static dist/.
- Database: Supabase (managed cloud Postgres) — see Data Model below.
- Background work: in-process FastAPI background tasks (v1). No external queue;
  single active run per server instance (queue UX deferred to v1.1).

## Run Execution (replaces the weekly pipeline)
Runs are on-demand, one per submission, driven by `POST /runs` → `approve` →
background pipeline. There is **no cron**. The old weekly
`automaticYoutube.py` job and `automatic_table` / `automatic_apple_table`
stores are removed in v2.

## Data Model (PRD §9)
| Store | Used for |
|-------|----------|
| Supabase `idea_runs` | One row per run (source of truth): idea, status, category, signal, competitors_json, quotes_json, partial_sources_json, failure_reason, reported_at, timestamps |
| Supabase `gaps` | One row per surfaced gap (FK run_id) — promoted out of the run blob for cross-run analytics |
| Supabase `feedback_events` | Append-only feedback log (FK run_id) — never overwritten |
| In-memory job state | Background progress for active runs; lost on restart → run → `failed` |

## Operational Limits & Guardrails (PRD §8)
- Pre-flight ≤10s; full run ≤5 min p50; cap **5 concurrent OpenAI calls**.
- Rate limiting: per-IP 3 runs/hr, 10 runs/day. **Daily OpenAI spend cap**
  (env-configurable) → `429 budget_exhausted`.
- Partial completion: ≥70% sources succeed → `done` + `partial_sources` banner;
  below 70% → `failed`.
- Reliability: server restart while `running` → `failed`
  (`failure_reason: server_restart`) on next read. No silent partial `done`.
- Abuse: `POST /runs/:id/report` immediately hides a run pending admin review
  (hidden, not deleted).
- SEO: `/runs/:id` set `X-Robots-Tag: noindex, nofollow`; Home feed indexable but
  lists only idea text + timestamp, not gap content.

## Required Env Vars
`YOUTUBE_API`, `OPENAI_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
plus v2 guardrail config (daily OpenAI budget cap, per-IP rate limits).
App Store Search API needs no key.

## CI
- `.github/workflows/test.yml` runs `pytest` on every push to `master` and on
  PRs. Env vars stubbed (external services mocked in tests).
- The weekly-youtube workflow is obsolete in v2 — remove once the weekly job is
  deleted from the tree.

## Deploy Checklist (deploy/checklist.md)
- [ ] .env populated with all keys + v2 guardrail config (budget cap, rate limits)
- [ ] CORS allow_origins updated for production domain
- [ ] Supabase tables created: `idea_runs`, `gaps`, `feedback_events`; RLS reviewed
- [ ] `X-Robots-Tag: noindex, nofollow` confirmed on `/runs` responses
- [ ] Daily OpenAI budget cap configured (env) AND OpenAI dashboard hard usage
      limit set so a runaway cannot drain billing
- [ ] Per-IP rate limits verified (3/hr, 10/day)
- [ ] Admin path for reviewing `reported` runs in place
