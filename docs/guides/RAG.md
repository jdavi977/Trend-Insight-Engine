# RAG Layer

The RAG (Retrieval-Augmented Generation) layer gives the engine memory across analyses. Before each LLM extraction, similar problems from past analyses are retrieved and injected into the system prompt as context. After extraction, each new problem is embedded and stored so future analyses can reference it.

---

## How It Works

```
Query (video title or app name)
       │
       ▼
  OpenAI Embeddings API
  model: text-embedding-3-small
  1536-dimensional vector
       │
       ▼
  match_insights RPC (Supabase pgvector)
  cosine similarity search
  threshold: 0.35
  top-k: 5
       │
       ▼
  Prior insights returned to service
       │
       ▼
  Injected into LLM system prompt
  as numbered context bullets
       │
       ▼
  gpt-4o extraction
       │
       ▼
  embed_and_store() for each new problem
  SHA256 ID → upsert to insights table
```

---

## Write Path

**Function:** `app/rag/rag.py::embed_and_store(extraction, source_url)`

**Triggered when:** `RAG_WRITE_ENABLED=true` (set in `.env`)

**When it runs:**
- Manual analysis — after `extract_insights()` returns in `youtube_service` / `appstore_service`
- Automatic pipeline — in the `post_extract()` hook, after LLM extraction, when `RAG_WRITE_ENABLED=true`

**Process per problem:**

1. Build embedding text: `f"{problem.problem}\n(type: {problem.type})"`
2. Embed with `text-embedding-3-small` via `clients/openai.py::create_embedding()`
3. Generate deterministic ID: `UUID(SHA256(source_url + embedding_text)[:32])`
4. Upsert the row to the `insights` table via `clients/pgvector.py::upsert_embedding()`

Errors are logged but never raised to the caller — a RAG write failure does not fail the analysis.

---

## Read Path

**Function:** `app/rag/rag.py::retrieve_similar(query, k=5)`

**Triggered when:** `RAG_READ_ENABLED=true` (set in `.env`)

**When it runs:**
- Manual: `youtube_service.youtube_manual()` — query is the video title
- Manual: `appstore_service.app_store_manual()` — query is the app name
- Automatic pipeline: `automaticYoutube._build_prompt()` / `automaticAppStore._build_prompt()` — query is `item["Title"]`, gated by `RAG_READ_ENABLED=true`

**Process:**

1. Embed the query string with `text-embedding-3-small`
2. Call `clients/pgvector.py::query_similar(embedding, threshold, k)`
3. Internally calls the `match_insights` Supabase RPC with:
   - `query_embedding` — the embedded query vector
   - `match_threshold` — `RAG_MIN_SIMILARITY` (default `0.35`)
   - `match_count` — `k`
4. Returns results sorted by cosine similarity, highest first

Results are passed to `build_youtube_prompt()` or `build_appstore_prompt()`, which render them as numbered context bullets in the LLM system prompt.

---

## Supabase Schema

**Table: `insights`**

```sql
CREATE TABLE insights (
    id           UUID         PRIMARY KEY,
    problem      TEXT         NOT NULL,
    type         TEXT         NOT NULL,
    severity     INTEGER      NOT NULL,    -- 1-5
    frequency    INTEGER      NOT NULL,    -- 1-5
    source       TEXT         NOT NULL,    -- 'youtube' | 'app_store'
    source_url   TEXT         NOT NULL,
    title        TEXT,                     -- video title or app name (nullable)
    extracted_at TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    embedding    vector(1536) NOT NULL
);
```

**Index:**

```sql
CREATE INDEX ON insights USING hnsw (embedding vector_cosine_ops);
```

HNSW supports incremental inserts — no index rebuild needed when new rows are added.

**RPC function: `match_insights`**

```sql
-- Called by pgvector client; returns rows above the similarity threshold
RETURNS TABLE (
    id, problem, type, severity, frequency,
    source, source_url, title, extracted_at, similarity
)
WHERE 1 - (embedding <=> query_embedding) >= match_threshold
ORDER BY similarity DESC
LIMIT match_count;
```

The migration that creates all of the above is `ops/migrations/001_insights_table.sql`. It is idempotent (`IF NOT EXISTS`) and must be run before enabling RAG.

---

## Configuration

All RAG constants are in `app/config/constants.py`:

| Constant | Value | Description |
|----------|-------|-------------|
| `RAG_TOP_K` | `5` | Max results returned per retrieval |
| `RAG_MIN_SIMILARITY` | `0.35` | Cosine similarity threshold |
| `RAG_COLLECTION` | `"insights"` | Supabase table name |

Both feature flags are read from `.env`:

| Env var | Default | Effect |
|---------|---------|--------|
| `RAG_READ_ENABLED` | `false` | Enables retrieval before LLM extraction |
| `RAG_WRITE_ENABLED` | `false` | Enables embedding storage after extraction |

The two flags are independent — you can write without reading (build up the store first) or read without writing (read-only mode).

---

## Similarity Threshold

The current threshold of `0.35` is intentionally low. The vector store has limited data while the project is early-stage, and a higher threshold would miss useful cross-source patterns that share semantic meaning but different phrasing.

As the `insights` table grows, consider raising this value toward `0.5–0.6` to reduce noise in the retrieved context. Change `RAG_MIN_SIMILARITY` in `app/config/constants.py`.

---

## API Endpoint

The RAG store is also queryable directly:

```
GET /insights/similar?query=<str>&k=<int>
```

| Parameter | Required | Default | Constraints |
|-----------|----------|---------|-------------|
| `query` | yes | — | min_length=1 |
| `k` | no | 5 | 1–50 |

Returns a `SimilarInsightsResponse` with the query string and a list of matching insight objects with their similarity scores. Handled by `app/api/insights.py::get_similar_insights()` via `rag_service.similar()`.

---

## Backfilling Historical Data

If the pipeline ran before `RAG_WRITE_ENABLED` was set, use the backfill script to embed all existing rows retroactively:

```bash
RAG_WRITE_ENABLED=true python -m ops.scripts.backfill_embeddings
```

The script reads all rows from `automatic_table` and `automatic_apple_table`, embeds each problem, and upserts into `insights`. It is safe to run multiple times — deterministic IDs mean no duplicates are created.

---

## Design Notes

**One embedding per problem, not per comment or analysis.**

Each `ProblemItem` (a clustered, LLM-extracted insight) gets its own vector. This means:

- A query for "crash on startup" retrieves the specific past insight about crashes, not an entire video's worth of problems
- The same insight can surface in retrieval regardless of what source it came from
- Deterministic IDs (`SHA256(source_url + problem_text)`) make upserts idempotent and avoid duplicates across re-runs
