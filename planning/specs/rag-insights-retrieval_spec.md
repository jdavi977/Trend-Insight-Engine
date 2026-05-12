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
    """Embed each problem in `extraction` and upsert into pgvector.
    Errors are swallowed and logged — never fails the caller."""

def retrieve_similar(query: str, k: int = 5) -> list[RetrievedInsight]:
    """Return up to K past insights with similarity >= RAG_MIN_SIMILARITY, ordered by score."""
```

Behind that interface:
1. `clients/pgvector.py` — single pgvector adapter over Supabase (upsert vector row, cosine similarity query via SQL). Matches the one-file-per-external-service pattern in `clients/`. Uses the existing Supabase connection string — no new credentials. Upsert key: `sha256(source_url + problem_text)` as a deterministic UUID — re-running the same analysis updates in place rather than duplicating vectors.
2. `clients/openai.py` — extend with `create_embedding(text: str) -> list[float]` using `text-embedding-3-small`. Same vendor adapter, separate function.
3. `clients/youtube.py` — extend with `get_video_title(video_id: str) -> str` via `videos().list(part="snippet")`. Needed by `youtube_service` for the `retrieve_similar` query before extraction.
4. `clients/appstore.py` — extend with `get_app_name(app_id: str) -> str` via `https://itunes.apple.com/lookup?id={app_id}`. Needed by `appstore_service` for the same reason.
5. `rag/rag.py` — orchestrates embed + store and query + format. No HTTP, no business logic outside RAG concerns.

Pipeline integration points (only two):
- **Write path:** services + jobs call `embed_and_store(result, url)` after a successful `extract_insights(...)` call. Gated on `RAG_WRITE_ENABLED`. Errors are caught, logged, and swallowed — a failed embed never fails the analysis response.
- **Read path:** services call `retrieve_similar(query=<video title or app name>)` *before* `extract_insights`, and pass the list into the prompt builder. Gated on `RAG_READ_ENABLED`. Returns `[]` when disabled or when no results meet the similarity threshold.

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
| Storage scope | Manual + weekly flows both write | Weekly jobs are the volume driver; manual runs add diversity. Write path gated behind `RAG_WRITE_ENABLED`; read path gated behind `RAG_READ_ENABLED`. Separate flags allow populating the store while retrieval is still being validated. |
| Upsert key | `sha256(source_url + problem_text)` as deterministic UUID | Re-running the same analysis updates the vector in place rather than duplicating it. Backfill script is idempotent for the same reason. |
| Similarity threshold | `RAG_MIN_SIMILARITY = 0.75` (tunable constant) | Prevents low-relevance context from being injected into prompts when the store is sparse. `similarity` score is returned on `RetrievedInsight` for empirical tuning in milestone 8. |
| Prompt injection format | Compact: `- [type] severity:{n} freq:{n} — "{problem}"` per insight | ~20–40 tokens per insight; K=5 adds ~100–200 tokens total. Structured enough for the LLM, cheap enough not to crowd out the comments. |
| pgvector index | HNSW via `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` | Handles incremental inserts without rebuild; works on an empty table; better recall than IVFFlat for real-time single-query workloads. |
| Title fetch for retrieval query | `get_video_title` / `get_app_name` added to respective clients | Manual services don't receive titles from ingestion. Title is available post-extraction but retrieval must happen pre-extraction. One extra API call per manual run. |

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
- `app/config/constants.py` — `RAG_TOP_K = 5`, `RAG_MIN_SIMILARITY = 0.75`, `RAG_COLLECTION = "insights"`.
- `app/config/secrets.py` — read `RAG_WRITE_ENABLED` (default False) and `RAG_READ_ENABLED` (default False). Supabase URL/key already present; no new credentials needed.
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

```python
# app/schemas/api.py — additive subclasses; LLMExtraction is unchanged
class YoutubeAnalysisResponse(LLMExtraction):
    retrieved_context: list[RetrievedInsight] = []

class AppStoreAnalysisResponse(LLMExtraction):
    retrieved_context: list[RetrievedInsight] = []
```

All existing fields (`source`, `title`, `problems`) remain at the top level — no nesting change. v1 consumers that read `response.problems` are unaffected. `retrieved_context` defaults to `[]` when `RAG_READ_ENABLED=False`.

`LLMExtraction` is unchanged — RAG reads/writes around it, not inside it.

## Caller Changes

| File | Added |
|---|---|
| [services/youtube_service.py](app/services/youtube_service.py) | call `get_video_title(id)` for query; `retrieve_similar(query=title)` before `extract_insights`; pass into `build_youtube_prompt`; `embed_and_store(result, link)` after |
| [services/appstore_service.py](app/services/appstore_service.py) | call `get_app_name(id)` for query; same pattern |
| [jobs/automaticYoutube.py](app/jobs/automaticYoutube.py) | `embed_and_store` after successful extraction (write-only — weekly jobs don't need retrieval context for now) |
| [jobs/automaticAppStore.py](app/jobs/automaticAppStore.py) | same |
| [api/insights.py](app/api/insights.py) *(new)* | `GET /insights/similar` → `rag_service.similar(query, k)` |

`embed_and_store` is no-op when `RAG_WRITE_ENABLED=False`. `retrieve_similar` returns `[]` when `RAG_READ_ENABLED=False` or when no results meet `RAG_MIN_SIMILARITY` — both render to an empty prompt block, identical to v1 behavior.

## Frontend

Add a "Retrieved context" accordion to the YouTube and App Store result pages under `frontend/src/`. Collapsed by default; expands to show the K insights that were injected into the prompt. Renders `retrieved_context` from the analysis response — empty accordion when the list is empty.

Deferred (post-milestone-8): standalone `/similar` search page. The `/insights/similar` endpoint (PR 3) is available; the UI can be added once retrieval quality is validated in milestone 8.

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
- Add `clients/pgvector.py` (Supabase pgvector adapter: upsert with deterministic UUID key, cosine similarity query with `RAG_MIN_SIMILARITY` filter).
- Create `insights` table in Supabase with `vector(1536)` column and HNSW index (migration in `ops/`).
- Add `create_embedding` to `clients/openai.py`.
- Add `rag/rag.py` with `embed_and_store` / `retrieve_similar` working against a hardcoded test document.
- Tests for both.
- No integration with the extraction pipeline yet.

### PR 1b — Backfill existing insights (milestone 2, after PR 1)
- One-off script in `ops/scripts/backfill_embeddings.py` that reads `automatic_table` and `automatic_apple_table`, reconstructs embedding text + metadata, and calls `embed_and_store` for each row.
- Idempotent — safe to re-run (upsert key handles duplicates).
- YouTube `source_url` reconstructed as `https://www.youtube.com/watch?v={key}`; App Store as `https://apps.apple.com/app/id{app_id}`.
- `extracted_at` set from the row's `date` column (weekly Sunday date — acceptable approximation).

### PR 2 — Write path: persist insights as they're extracted (milestone 3)
- Add `embed_and_store` calls to both services and both jobs.
- Gated on `RAG_WRITE_ENABLED`. Default off.
- Add `get_video_title` to `clients/youtube.py` and `get_app_name` to `clients/appstore.py`.
- Run a few analyses locally with the flag on to populate the store.

### PR 3 — `/insights/similar` endpoint (milestone 4)
- `schemas/rag.py`, `services/rag_service.py`, `api/insights.py`.
- Register router in `main.py`.
- Tests for endpoint + service.

### PR 4 — Read path: inject retrieved context into prompts (milestone 5)
- Extend `build_youtube_prompt` / `build_appstore_prompt` to accept `prior_insights`; append compact block (`- [type] severity:{n} freq:{n} — "{problem}"`) when non-empty.
- Call `get_video_title` / `get_app_name` in both services; call `retrieve_similar(query=title)` and thread the result into the prompt. Gated on `RAG_READ_ENABLED`.
- Services return `YoutubeAnalysisResponse` / `AppStoreAnalysisResponse` (subclasses of `LLMExtraction`) with `retrieved_context` populated.

### PR 5 — Frontend surfacing (milestone 6)
- "Retrieved context" collapsed accordion on YouTube and App Store result pages.
- Renders `retrieved_context` from the analysis response; hidden when empty.

### PR 6 — Before/after writeup (milestone 7)
- Analyze the same video with and without RAG; document delta in README, including embedding model choice, chunking decision, and a screenshot of the retrieved-context panel.

Milestone 8 ("use it for a week on 5+ real videos/apps") is a gate before declaring v2 done, not a PR.

## Acceptance

- `RAG_WRITE_ENABLED=true` + run `/analyze/youtube` → row appears in `insights` table with correct metadata and a non-null embedding.
- `RAG_READ_ENABLED=true` + run `/analyze/youtube` twice on related videos → second run's response contains non-empty `retrieved_context` with `similarity >= 0.75` and the prompt visibly included those insights.
- `GET /insights/similar?query=<known phrase>&k=5` returns up to 5 ordered `RetrievedInsight`s (fewer if store has no results above threshold).
- `RAG_WRITE_ENABLED=false`, `RAG_READ_ENABLED=false` → all v1 behavior is byte-identical to current `master`. No new fields populated, no calls to pgvector or embeddings.
- README contains an "Architecture: RAG" section with the embedding-model choice, the insight-level chunking rationale, and a before/after example.
- All tests green.

## Deferred (explicitly post-v2)

- Evaluation framework / LLM-as-judge scoring.
- Agent-based routing.
- Async embedding writes (current write is synchronous after extraction — acceptable since extraction is already the long pole).
- Per-genre filtered retrieval (e.g. only retrieve from same `genre.id`). Worth doing once the store has >100 insights; cut from MVP.
- Re-embedding migrations when changing model.
- Cost / token logging for embedding calls.

## Resolved Decisions

1. **Backfill existing insights** — backfill from `automatic_table` and `automatic_apple_table` via `ops/scripts/backfill_embeddings.py` (PR 1b). Store doesn't start empty; past data seeds retrieval immediately.

2. **Query text for `retrieve_similar`** — video title (via `get_video_title`) for YouTube; app name (via `get_app_name`) for App Store. One extra API call per manual run. Revisit if retrieval quality is poor in milestone 8.

3. **Single collection** — one `insights` table with `source` metadata field. Cross-source retrieval (YouTube video surfacing App Store complaints) is possible later for free.