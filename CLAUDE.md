# Trend Insight Engine

A full-stack app that takes a builder's **idea** and returns ranked,
evidence-backed **candidate gaps** drawn from real complaints across relevant
competitors (YouTube comments + App Store reviews). Every gap is grounded in
verbatim, PII-redacted quotes. v2 = **idea-in → cross-competitor gaps-out**;
see [docs/PRD.md](docs/PRD.md) (v2.2) — the source of truth.

## Tech Stack
- Frontend: React 19 + Vite (frontend/)
- Backend: FastAPI + Python 3.14 (app/)
- LLM: OpenAI API (gpt-4o); per-stage model routing via config (PRD §10.1)
- Validation: Pydantic (+ quote-ID grounding check on synthesis)
- Storage: Supabase (`idea_runs`, `gaps`, `feedback_events`)
- Data Sources: YouTube Data API v3, iTunes RSS / App Store Search API
- Server: Uvicorn (ASGI)

## Engineering Standards
How this repo's code, layout, tooling, and docs should look — naming, config,
errors/logging, frontend, testing, ADRs, tooling/CI, and what was deliberately
declined — is [docs/engineering-standards.md](docs/engineering-standards.md).
It is the authority; cite it by path, never restate it here or in a skill.

## Workspaces (code domains)
- /planning   — Feature specs, architecture decisions, pipeline design
- /app        — Backend pipeline code (ingestion, preprocessing, LLM, API)
- /frontend   — React SPA (Home, New Run, Pre-flight, Run/Result, My Runs)
- /docs       — API reference, guides, changelog
- /ops        — Deployment, Supabase setup, run execution

## ICM Workspaces
Staged, gated workflows under `/icm`. These are *not* code domains — each is a
sequence of stages with review gates that produces artifacts into the domains
above.

- /icm/feature-planning — Plan a feature end-to-end: frame → spec → architecture
  map → issues → TDD plan. Enter it when taking a feature from "this is
  friction" all the way to grabbable issues. Read
  [icm/feature-planning/CONTEXT.md](icm/feature-planning/CONTEXT.md).

The routing table below is for **one-off** tasks — a single grill, a single
architecture map, a single breakdown into issues. `/icm/feature-planning` is the
**sequenced, gated** version of that same work, invoking the same skills in
order. Same tools; the workspace adds ordering and the stage-01 kill gate.

## Routing Table
| Task                        | Go to     | Read               | Skills                                      |
|-----------------------------|-----------|--------------------|---------------------------------------------|
| Plan a feature end-to-end   | /icm/feature-planning | icm/feature-planning/CONTEXT.md | (sequences the skills below) |
| Plan a new feature          | /planning | planning/CONTEXT.md| grill-with-docs, to-issues                  |
| Stress-test a design        | /planning | planning/CONTEXT.md| grill-me                                    |
| Write backend code          | /app      | app/CONTEXT.md     | tdd, python-code-review                          |
| Debug a pipeline failure    | /app      | app/CONTEXT.md     | triage, python-code-review                          |
| Refactor a module           | /app      | app/CONTEXT.md     | tdd, python-code-review                          |
| Modify LLM prompts          | /app/llm  | app/CONTEXT.md     | prompt-engineering                          |
| Build frontend feature      | /frontend | frontend/CONTEXT.md| frontend-component-standards                |
| Write API or user docs      | /docs     | docs/CONTEXT.md    | doc-authoring                               |
| Deploy or run the pipeline  | /ops      | ops/CONTEXT.md     | —                                           |

## Naming Conventions
- Specs:            feature-name_spec.md
- Architecture:     YYYY-MM-DD-topic.md
- Decision records: YYYY-MM-DD-decision-title.md
- Backend modules:  snake_case.py per PEP 8 (e.g. run_pipeline_service.py); the
                    surviving v1 camelCase modules are a tracked delta
- Frontend comps:   PascalCase.jsx
- API endpoints:    resource-oriented run lifecycle (e.g. POST /runs, GET /runs/:id)
- Supabase tables:  idea_runs, gaps, feedback_events (v2; automatic_table removed)
- Env vars:         SCREAMING_SNAKE_CASE (YOUTUBE_API, OPENAI_KEY)