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

## Workspaces
- /planning   — Feature specs, architecture decisions, pipeline design
- /app        — Backend pipeline code (ingestion, preprocessing, LLM, API)
- /frontend   — React SPA (Home, New Run, Pre-flight, Run/Result, My Runs)
- /docs       — API reference, guides, changelog
- /ops        — Deployment, Supabase setup, run execution

## Routing Table
| Task                        | Go to     | Read               | Skills                                      |
|-----------------------------|-----------|--------------------|---------------------------------------------|
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
- Backend modules:  camelCase.py (existing pattern, e.g. commentClean.py)
- Frontend comps:   PascalCase.jsx
- API endpoints:    resource-oriented run lifecycle (e.g. POST /runs, GET /runs/:id)
- Supabase tables:  idea_runs, gaps, feedback_events (v2; automatic_table removed)
- Env vars:         SCREAMING_SNAKE_CASE (YOUTUBE_API, OPENAI_KEY)