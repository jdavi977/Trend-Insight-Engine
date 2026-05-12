# Trend Insight Engine

Turn YouTube comments and App Store reviews into clear, actionable product insights — automatically.

---

## What It Does

Paste a YouTube video URL or an App Store link. The engine fetches user feedback, filters out the noise, and uses an LLM to surface the most important problems users are reporting — ranked by severity and frequency.

Every insight includes:
- **Problem** — what users are complaining about or asking for
- **Type** — complaint, feature request, usability issue, performance, or pricing
- **Severity** — how serious (1–5)
- **Frequency** — how often it appears (1–5)

A weekly automated pipeline also pre-analyzes top trending YouTube videos across Games, Science & Tech, and How-to & Style — browse them without running a manual analysis.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite |
| Backend | FastAPI + Python 3.14 |
| LLM | OpenAI gpt-4o |
| Embeddings | text-embedding-3-small (pgvector via Supabase) |
| Data sources | YouTube Data API v3, iTunes RSS |

---

## Docs

| Guide | Description |
|-------|-------------|
| [Setup](docs/guides/SETUP.md) | Install dependencies, configure API keys, run the app |
| [Usage](docs/guides/USAGE.md) | How to analyze YouTube videos and App Store apps |
| [Architecture](docs/guides/ARCHITECTURE.md) | System design, pipeline layers, data flow |
| [RAG Layer](docs/guides/RAG.md) | How cross-analysis memory works (embeddings, retrieval) |
| [Pipeline](docs/guides/PIPELINE.md) | Weekly automated pipeline — how it runs and what it stores |
| [Data Sources](docs/guides/DATA_SOURCES.md) | YouTube and App Store ingestion details |
| [Contributing](docs/guides/CONTRIBUTING.md) | Branching strategy, conventions, PR process |
| [Changelog](docs/changelog/CHANGELOG.md) | Release history |

**API reference:** [YouTube](docs/api/youtube.md) · [App Store](docs/api/appstore.md) · [Home](docs/api/home.md) · [Insights](docs/api/insights.md) · [Errors](docs/api/errors.md)

---

## License

MIT — see [LICENSE](LICENSE) for details.
