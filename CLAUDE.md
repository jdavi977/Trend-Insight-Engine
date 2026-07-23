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

Run and deploy from the [Makefile](Makefile); there is no `ops` workspace.

## ICM Workspaces
Staged, gated workflows under `/icm` — *not* code domains. Each is a sequence of
stages with review gates producing artifacts into the domains above.

- /icm/feature-planning — frame → spec → architecture map → issues → TDD plan.
  Enter it to take a feature from "this is friction" to grabbable issues. Read
  [icm/feature-planning/CONTEXT.md](icm/feature-planning/CONTEXT.md).

Routing-table rows are **one task, one artifact**; the workspace is the
**sequenced, gated** version of the same skills, plus the stage-01 kill gate.

## Routing Table
| Task                             | Go to     | Read               | Skills                       |
|----------------------------------|-----------|--------------------|------------------------------|
| Plan a feature end-to-end (gated)| /icm/feature-planning | icm/feature-planning/CONTEXT.md | (stages sequence the rows below) |
| Stress-test a design (one-off)   | /planning | planning/CONTEXT.md| grill-me                     |
| Map a component or data flow     | /planning | planning/CONTEXT.md| map-architecture             |
| Record a decision                | /planning | planning/CONTEXT.md| write-adr                    |
| Break a spec into issues         | /planning | planning/CONTEXT.md| to-issues                    |
| Write or refactor backend code   | /app      | app/CONTEXT.md     | tdd, python-code-review      |
| Debug a pipeline failure         | /app      | app/CONTEXT.md     | triage, python-code-review   |
| Find refactoring opportunities   | /app      | app/CONTEXT.md     | improve-codebase-architecture|
| Modify LLM prompts               | /app/llm  | app/CONTEXT.md     | python-code-review           |
| Build frontend feature           | /frontend | frontend/CONTEXT.md| frontend-component-standards |
| Write API or user docs           | /docs     | docs/CONTEXT.md    | —                            |

`grill-with-docs` is the domain-aware grill (challenges terminology, updates
`CONTEXT.md` / ADRs inline); it is explicit-invoke only, so ask for it by name.
Deliberately unrouted: `caveman`, `write-a-skill` — invoke by name.

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