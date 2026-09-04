# Trend Insight Engine

> [ONE-LINE HOOK — what it does, for whom, in plain language.]
> <!-- e.g. "Enter a product idea and get the recurring, evidence-backed gaps
>      users report about the competitors already in that space." Avoid buzzwords;
>      a non-technical reader should get it on the first pass. -->

[![Live Demo](https://img.shields.io/badge/demo-live-brightgreen)]([DEMO_URL])
[![Tests](https://github.com/[USER]/[REPO]/actions/workflows/test.yml/badge.svg)](https://github.com/[USER]/[REPO]/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
<!-- Delete any badge you can't back up. A broken/dead demo badge hurts more
     than no badge. -->

---

## Overview

**The problem.** 

Many ideas exist, and there is almost a definite certaintly that an idea is already being built upon.
Despite the many solutions there are for a problem, there are still complaints and requests real users need/want. To find these issues, builders would have to manually read hundreds of scattered reviews over different sources taking a long period of time.

**The approach.**

Submit an idea. A synchronous pre-flight classifies the idea and proposes competitors which the user will review and optionally edit before running. The pipeline would then pull real user feedback from different sources, extract painpoints, and synthesizes the pains that recure across multiple competitors into ranked gaps.

**Who it's for.** 

Solo founders and indie builders wanting to validate a product idea before commmiting to it.

---

## Why not just ask an AI chatbot?

> A chatbot gives you a plausible answer about your market. This gives you a
> falsifiable one — every gap traces back to two real user quotes, or it doesn't ship.

- **Idea-blinded.** In a chat, your idea is in context from token one, so the model
  finds gaps that flatter it. Here, extraction never sees the idea — only synthesis does.
- **Can return nothing.** Gaps that can't cite two verbatim quotes are rejected, so a
  thin result is real information, not a fluent paragraph.
- **Evidence is fetched, not recalled.** Real YouTube comments and App Store reviews per
  run, including ones written after any model's training cutoff — and recurrence is counted.
- **Runs persist.** Addressable at `GET /runs/:id`, so a result can be revisited and shared.

*Limits:* coverage is two sources (YouTube, iTunes RSS), and ranking/severity are still
model judgment.

---

## Demo

<!-- This is the highest-value section on the page. Put a GIF here, not a wall
     of text. Record with peek/asciinema/QuickTime, keep it under ~20s, and
     show the real happy path: idea in → pre-flight review → gaps out.
     Store media in docs/media/ and commit it. -->

![Demo]([docs/media/demo.gif])

**Try it:** [DEMO_URL] · **Example run:** [LINK TO A COMPLETED PUBLIC RUN]

<details>
<summary>Screenshots</summary>

| [Submit an idea] | [Pre-flight review] | [Gap results] |
|---|---|---|
| ![]([docs/media/new-run.png]) | ![]([docs/media/preflight.png]) | ![]([docs/media/results.png]) |

</details>

---

## Features

- **Pre-flight before you spend** — a run first classifies the idea and proposes
  competitors, with a signal-strength read, so you can edit the list or cancel
  before the pipeline runs.

- **Idea-blinded extraction** — pains come from what users actually said, not from your idea. 
  The per-source extractor receives only source metadata; only synthesis ever sees the idea.

- **Evidence-grounded gaps** — every gap cites at least two verbatim user
  quotes; gaps the model can't ground get rejected rather than shown.

---

## Architecture

```
[ React SPA ]
      |  POST /runs  { idea }
      v
[ FastAPI ] --> pre-flight (classify idea, rank competitors)  --(<=10s)--> user approves
      |
      v
[ Pipeline ] --> ingestion (YouTube comments, App Store reviews)
      |          --> preprocessing (filter, PII redaction)
      |          --> per-source extraction (idea-blinded)
      |          --> synthesis (cross-competitor gaps + quote grounding)
      v
[ Supabase / Postgres ] --> GET /runs/:id
```

**Run lifecycle:** `pending → preflight_ready → running → done | failed`

| Layer | What lives there |
|---|---|
| [`app/api/`](app/api/) | FastAPI routers — one per resource, calls services only |
| [`app/services/`](app/services/) | Orchestration: pre-flight, run pipeline, extraction, rate limiting |
| [`app/ingestion/`](app/ingestion/) | YouTube comment + App Store review fetching |
| [`app/preprocessing/`](app/preprocessing/) | Engagement filtering, PII redaction (regex + NER) |
| [`app/llm/`](app/llm/) | Prompting, stage→model routing, JSON response validation |
| [`app/schemas/`](app/schemas/) | Pydantic models for every external boundary |
| [`frontend/src/`](frontend/src/) | React 19 + Vite SPA (feed, new run, run result) |

---

## Tech Stack

| Layer | Technology |
|---|---|---|
| Frontend | React 19, Vite, React Router 7 |
| Backend | Python 3.x, FastAPI, Pydantic 2 |
| LLM | OpenAI `gpt-4o` (per-stage routing) |
| Data | Supabase (Postgres) |
| Sources | YouTube Data API v3, iTunes RSS |
| Testing | pytest, pytest-mock, httpx TestClient |



---

## Getting Started

### Prerequisites

- Python [3.X]+ and Node [20]+
- API keys: OpenAI, YouTube Data API v3
- A Supabase project (Postgres)

### Setup

```bash
git clone https://github.com/[USER]/[REPO].git
cd [REPO]

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && cd ..

# Secrets
cp .env.example .env   # then fill in the keys below
```

`.env`:

| Variable | Purpose |
|---|---|
| `OPENAI_KEY` | OpenAI API key |
| `YOUTUBE_API` | YouTube Data API v3 key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

### Run

```bash
uvicorn app.main:app --reload      # API  → http://localhost:8000
cd frontend && npm run dev         # SPA  → http://localhost:5173
```

### Test

```bash
pytest                             # backend
cd frontend && npm run lint        # frontend
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/runs` | Submit an idea; runs pre-flight, returns candidate competitors |
| `POST` | `/runs/:id/approve` | Confirm competitors and start the full pipeline |
| `GET` | `/runs/:id` | Run state, and full results once `done` |
| `GET` | `/runs` | Paginated feed of completed runs |

---


## Roadmap

1. Add more data sources
2. Keep testing and optimizing pipeline