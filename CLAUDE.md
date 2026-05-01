# Trend Insight Engine

A full-stack app that ingests YouTube comments and App Store reviews,
cleans/filters them, and uses OpenAI to extract structured product
insights (problems, feature requests, usability issues) with severity
and frequency metrics.

## Tech Stack
- Frontend: React 19 + Vite (frontend/)
- Backend: FastAPI + Python 3.14 (app/)
- LLM: OpenAI API (gpt-4o)
- Validation: Pydantic
- Storage: Supabase (automatic_table)
- Data Sources: YouTube Data API v3, iTunes RSS Feed
- Server: Uvicorn (ASGI)

## Workspaces
- /planning   — Feature specs, architecture decisions, pipeline design
- /app        — Backend pipeline code (ingestion, preprocessing, LLM, API)
- /frontend   — React SPA (Home, Insights, YouTube, App Store pages)
- /docs       — API reference, guides, changelog
- /ops        — Deployment, Supabase setup, automation scripts

## Routing Table
| Task                        | Go to     | Read               | Skills                                      |
|-----------------------------|-----------|--------------------|---------------------------------------------|
| Plan a new feature          | /planning | planning/CONTEXT.md| grill-with-docs, to-issues                  |
| Stress-test a design        | /planning | planning/CONTEXT.md| grill-me                                    |
| Write backend code          | /app      | app/CONTEXT.md     | tdd                                         |
| Debug a pipeline failure    | /app      | app/CONTEXT.md     | triage                                      |
| Refactor a module           | /app      | app/CONTEXT.md     | tdd                                         |
| Modify LLM prompts          | /app/llm  | app/CONTEXT.md     | prompt-engineering                          |
| Build frontend feature      | /frontend | frontend/CONTEXT.md| react-component                             |
| Write API or user docs      | /docs     | docs/CONTEXT.md    | doc-authoring                               |
| Deploy or run weekly pipeline| /ops     | ops/CONTEXT.md     | —                                           |

## Naming Conventions
- Specs:            feature-name_spec.md
- Architecture:     YYYY-MM-DD-topic.md
- Decision records: YYYY-MM-DD-decision-title.md
- Backend modules:  camelCase.py (existing pattern, e.g. commentClean.py)
- Frontend comps:   PascalCase.jsx
- API endpoints:    /verb/resource (e.g. /analyze/youtube)
- Supabase table:   automatic_table (weekly YouTube insights)
- Env vars:         SCREAMING_SNAKE_CASE (YOUTUBE_API, OPENAI_KEY)