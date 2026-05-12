# RAG: Insight Embedding + Retrieval

## Problem

The LLM extraction step is memoryless. Every `/analyze/youtube` and `/analyze/appStore` run starts from zero — it has no awareness of patterns surfaced by prior analyses of similar content. Two videos about the same game produce overlapping problems, but the model never sees the overlap. The system can't answer "have we seen this complaint before?" and can't reuse past structured insights to sharpen new ones.

Concretely:
- [app/llm/extractInsights.py](app/llm/extractInsights.py) returns `LLMExtraction` and discards it from the system's perspective the moment the HTTP response is sent (manual flows) or written to Supabase (weekly jobs).
- There is no path from "prior insight" → "current LLM prompt."
- There is no endpoint that exposes semantic search over historical insights.

This spec is v2 of the project: add a retrieval-augmented generation layer that **persists** every extracted insight as an embedding, **retrieves** the top-K most similar past insights when a new analysis runs, and **injects** them into the extraction prompt. No breaking changes to v1.

## Solution

A new `rag/` layer with two responsibilities behind one interface:

```python
# app/rag/rag.py
def embed_and_store(extraction: LLMExtraction, source_url: str) -> None:
    """Embed each problem in `extraction` and upsert into ChromaDB."""

def retrieve_similar(query: str, k: int = 5) -> list[RetrievedInsight]:
    """Return top-K semantically similar past insights with metadata."""
```

Behind that interface:
1. `clients/pgvector.py` — single pgvector adapter over Supabase (upsert vector row, cosine similarity query via SQL). Matches the one-file-per-external-service pattern in `clients/`. Uses the existing Supabase connection string — no new credentials.
2. `clients/openai.py` — extend with `create_embedding(text: str) -> list[float]` using `text-embedding-3-small`. Same vendor adapter, separate function.
3. `rag/rag.py` — orchestrates embed + store and query + format. No HTTP, no business logic outside RAG concerns.

Pipeline integration points (only two):
- **Write path:** services + jobs call `embed_and_store(result, url)` after a successful `extract_insights(...)` call. One line added per caller.
- **Read path:** services call `retrieve_similar(query=<title or first comment>)` *before* `extract_insights`, and pass the list into the prompt builder.

Prompt builders (`build_youtube_prompt`, `build_appstore_prompt` in [app/config/promptTemplates.py](app/config/promptTemplates.py)) gain an optional `prior_insights: list[RetrievedInsight] = []` argument and append a "Previously observed problems in similar content" block when non-empty.

## Architectural Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Vector DB | pgvector via Supabase | Co-located with relational data; one connection string, one backup strategy, hybrid SQL queries (metadata filter + cosine similarity) in a single call. ChromaDB was the zero-infra alternative but pgvector removes a second storage dependency. |
| Embedding model | `text-embedding-3-small` | Already using OpenAI; cost negligible at this scale; `large` not justified for ~hundreds of docs. |
| Embedding granularity | One vector per `ProblemItem` | Each problem is already a clean discrete unit (problem text + type + severity + frequency). Embedding raw comments would return noise. |
| Retrieval k | 5 | ~500–800 tokens of context; tunable constant in `app/config/constants.py`. |
| Metadata stored alongside vector | `source` ("youtube"\|"app_store"), `type`, `severity`, `frequency`, `source_url`, `title`, `extracted_at` | Enough to filter, display, and trace provenance. No raw comments stored. |
| Embedding text | `f"{problem}\n(type: {type})"` | Keeps the embedded text focused on the semantic content, not the metrics. Metrics are filterable metadata, not signal for cosine similarity. |
| Storage scope | Manual + weekly flows both write | Weekly jobs are the volume driver; manual runs add diversity. Both gated behind `RAG_ENABLED` env flag for safe rollout. |

## New Modules

```
app/
  clients/pgvector.py          # Supabase pgvector adapter (upsert, cosine similarity query)
  rag/
    __init__.py
    rag.py                     # embed_and_store, retrieve_similar
  schemas/
    rag.py                     # RetrievedInsight (Pydantic boundary model)
  api/
    insights.py                # GET /insights/similar?query=...&k=5
  services/
    rag_service.py             # thin orchestration for /insights/similar
```

Extensions to existing files:
- `app/clients/openai.py` — add `create_embedding(text: str) -> list[float]`.
- `app/config/promptTemplates.py` — `build_youtube_prompt` and `build_appstore_prompt` accept `prior_insights` and append a context block when present.
- `app/config/constants.py` — `RAG_TOP_K = 5`, `RAG_COLLECTION = "insights"`.
- `app/config/secrets.py` — read `RAG_ENABLED` (default False). Supabase URL/key already present; no new credentials needed.
- `app/main.py` — register `insights` router.

## Schema

```python
# app/schemas/rag.py
class RetrievedInsight(BaseModel):
    problem: str
    type: str
    severity: int
    frequency: int
    source: Literal["youtube", "app_store"]
    source_url: str
    title: Optional[str] = None
    extracted_at: str               # ISO timestamp
    similarity: float               # cosine; surfaced for debugging/UI

class SimilarInsightsResponse(BaseModel):
    query: str
    results: list[RetrievedInsight]
```

`LLMExtraction` is unchanged — RAG reads/writes around it, not inside it.

## Caller Changes

| File | Added |
|---|---|
| [services/youtube_service.py](app/services/youtube_service.py) | `retrieve_similar(query=...)` before `extract_insights`; pass into `build_youtube_prompt`; `embed_and_store(result, link)` after |
| [services/appstore_service.py](app/services/appstore_service.py) | same pattern |
| [jobs/automaticYoutube.py](app/jobs/automaticYoutube.py) | `embed_and_store` after successful extraction (write-only — weekly jobs don't need retrieval context for now) |
| [jobs/automaticAppStore.py](app/jobs/automaticAppStore.py) | same |
| [api/insights.py](app/api/insights.py) *(new)* | `GET /insights/similar` → `rag_service.similar(query, k)` |

The `embed_and_store` call is no-op when `RAG_ENABLED=False`. The `retrieve_similar` call returns `[]` when disabled, which renders to an empty prompt block — same behavior as before.

## Frontend

Add a "Retrieved context" panel to the YouTube and App Store result pages under `frontend/src/`. Renders the `RetrievedInsight[]` returned alongside the analysis. Two display modes:
1. Inline on the analysis result page — collapsed accordion showing the K insights that were injected.
2. Standalone `/similar` page — search box → calls `/insights/similar?query=...` → list view.

The backend must return retrieved context in the analysis response (additive field, doesn't break v1 consumers). Add `retrieved_context: list[RetrievedInsight] = []` to the analysis response envelope.

## Test Plan

Real:
- `tests/rag/test_rag.py` — embed_and_store writes vectors with expected metadata; retrieve_similar returns ordered results; k is respected; empty store returns `[]`.
- `tests/schemas/test_rag.py` — `RetrievedInsight` validation.

Mocked:
- `tests/clients/test_openai.py` — `create_embedding` shape (mock the SDK call, assert the request).
- `tests/services/test_youtube_service.py` — patch `retrieve_similar` and `embed_and_store`; assert both are called and the prompt builder receives the list.
- `tests/api/test_insights.py` — TestClient against `/insights/similar` with `rag_service.similar` mocked.

Out of scope: testing ChromaDB's correctness, testing OpenAI's embedding quality.

## Sequencing (PRs map to milestones)

### PR 1 — Walking skeleton for embeddings (milestone 2)
- Add `clients/pgvector.py` (Supabase pgvector adapter: upsert vector row, cosine similarity query).
- Create `insights` table in Supabase with `vector(1536)` column (migration in `ops/`).
- Add `create_embedding` to `clients/openai.py`.
- Add `rag/rag.py` with `embed_and_store` / `retrieve_similar` working against a hardcoded test document.
- Tests for both.
- No integration with the extraction pipeline yet.

### PR 2 — Write path: persist insights as they're extracted (milestone 3)
- Add `embed_and_store` calls to both services and both jobs.
- Gated on `RAG_ENABLED`. Default off.
- Run a few analyses locally with the flag on to populate the store.

### PR 3 — `/insights/similar` endpoint (milestone 4)
- `schemas/rag.py`, `services/rag_service.py`, `api/insights.py`.
- Register router in `main.py`.
- Tests for endpoint + service.

### PR 4 — Read path: inject retrieved context into prompts (milestone 5)
- Extend `build_youtube_prompt` / `build_appstore_prompt` to accept `prior_insights`.
- Call `retrieve_similar` in both services (not jobs, for now) and thread the result into the prompt.
- Return `retrieved_context` in the analysis response envelope.

### PR 5 — Frontend surfacing (milestone 6)
- "Retrieved context" panel on analysis result pages.
- Standalone `/similar` search page.

### PR 6 — Before/after writeup (milestone 7)
- Analyze the same video with and without RAG; document delta in README, including embedding model choice, chunking decision, and a screenshot of the retrieved-context panel.

Milestone 8 ("use it for a week on 5+ real videos/apps") is a gate before declaring v2 done, not a PR.

## Acceptance

- `RAG_ENABLED=true` + run `/analyze/youtube` twice on related videos → second run's response contains non-empty `retrieved_context` and the prompt visibly included those insights.
- `GET /insights/similar?query=<known phrase>&k=5` returns 5 ordered `RetrievedInsight`s.
- `RAG_ENABLED=false` → all v1 behavior is byte-identical to current `master`. No new fields populated, no calls to pgvector or embeddings.
- README contains an "Architecture: RAG" section with the embedding-model choice, the insight-level chunking rationale, and a before/after example.
- All tests green.

## Deferred (explicitly post-v2)

- Evaluation framework / LLM-as-judge scoring.
- Agent-based routing.
- Async embedding writes (current write is synchronous after extraction — acceptable since extraction is already the long pole).
- Per-genre filtered retrieval (e.g. only retrieve from same `genre.id`). Worth doing once the store has >100 insights; cut from MVP.
- Re-embedding migrations when changing model.
- Cost / token logging for embedding calls.

## Open Questions

1. **Embed weekly Supabase insights retroactively?** The store starts empty on PR 2. Option A: backfill from `automatic_table` in a one-off script. Option B: let the store grow organically from new runs. Recommendation: B for MVP; backfill script lives in `ops/` if needed.

Answer: Option A, we want past insights to be stored since we dont have as much data right now

2. **Query text for `retrieve_similar` in services?** Options: (a) video title / app name, (b) concatenated first N cleaned comments, (c) both. Recommendation: (a) for PR 4 — cheapest, fastest, semantically meaningful. Revisit if retrieval quality is poor in milestone 8.

Answer: video title / app name

3. **Single collection or one per source?** Single collection with `source` metadata filter. Simpler; cross-source retrieval (a YouTube video about an app surfacing App Store complaints) becomes possible later for free.

Answer: single collection