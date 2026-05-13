# Architecture: RAG Post-Extraction Per-Problem Enrichment
Date: 2026-05-12

## Overview
Replace the current title-based pre-extraction RAG query with per-problem similarity lookups that run after LLM extraction. Each extracted problem is individually compared against the stored insights vector, and matched past problems are attached inline. This applies to manual analysis only; the automatic pipeline is out of scope for this change.

## Data Flow

**Current (pre-extraction):**
URL → Metadata (title) → `retrieve_similar(title)` → inject into LLM prompt → `extract_insights()` → `embed_and_store()`

**New (post-extraction):**
URL → `extract_insights()` (no RAG context) → `enrich_problems()` → per-problem `retrieve_similar(problem.problem)` → tag recurrence → `embed_and_store()` → enriched response

## Components

| Component | File | Role |
|-----------|------|------|
| YouTube service | `app/services/youtube_service.py` | Remove pre-extraction `retrieve_similar(title)` call; call `enrich_problems()` after extraction |
| App Store service | `app/services/appstore_service.py` | Same removals and additions as YouTube service |
| RAG layer | `app/rag/rag.py` | Add `enrich_problems(extraction)` — loops each problem, calls `retrieve_similar(problem.problem)`, attaches matches and recurrence tag |
| Retrieve similar | `app/rag/rag.py::retrieve_similar` | Unchanged — called per-problem instead of once per analysis |
| Embed and store | `app/rag/rag.py::embed_and_store` | Unchanged — still runs after enrichment |
| LLM extraction | `app/llm/extractInsights.py` | Unchanged — no prior_insights injected |
| Prompt builders | `app/config/promptTemplates.py` | Remove `prior_insights` argument from `build_youtube_prompt` / `build_appstore_prompt` call sites; keep default `[]` signature to avoid breaking the API |
| Problem schemas | `app/schemas/llm.py` | Add `similar_insights: list[RetrievedInsight] = []` and `recurrence: Literal["new", "known"] = "new"` to `YoutubeProblemItem` and `AppStoreProblemItem` |
| Response schemas | `app/schemas/api.py` | Remove `retrieved_context` field from `YoutubeAnalysisResponse` and `AppStoreAnalysisResponse` |
| Automatic YouTube | `app/jobs/automaticYoutube.py` | Remove `retrieve_similar(item["Title"])` from `_build_prompt`; no enrichment added (automatic pipeline stores to Supabase, not an API response) |
| Automatic App Store | `app/jobs/automaticAppStore.py` | Same removal as automatic YouTube |

## Recurrence Tagging Logic

Inside `enrich_problems()`, after calling `retrieve_similar(problem.problem)` for each problem:

- `similar_insights` is empty → `recurrence = "new"`
- `similar_insights` has at least one match → `recurrence = "known"`

No resurging detection in this pass — that requires time-series reasoning and belongs in a later iteration.

## External Dependencies

| Service | Used For | Failure Impact |
|---------|----------|----------------|
| OpenAI Embeddings API (`text-embedding-3-small`) | Embed each problem text for retrieval | Enrichment skipped; analysis result still returned |
| Supabase pgvector (`match_insights` RPC) | Cosine similarity search per problem | Enrichment skipped; analysis result still returned |

**Call count change:** Current flow makes 1 embedding call per analysis (for the title). New flow makes N embedding calls per analysis where N = number of extracted problems (typically 3–10), plus the existing write-path calls. Peak cost: ~20 embedding calls per manual analysis.

## Failure Points

- **Enrichment failure must never fail the analysis.** `enrich_problems()` wraps all embedding and retrieval calls in try/except, same pattern as `embed_and_store()`. On any error, problems are returned with `similar_insights = []` and `recurrence = "new"`.
- **Empty vector store.** If the `insights` table has no rows (fresh install, `RAG_WRITE_ENABLED` was never set), every problem will be tagged `"new"` — correct behaviour, no special handling needed.
- **High problem count.** 10 problems = 10 serial embedding calls before the response returns. No parallelism in the current client. Acceptable at current scale; worth revisiting if P95 latency grows.
- **Removed `retrieved_context` is a breaking API change.** Frontend currently reads `retrieved_context` in `YoutubeAnalysisResponse` and `AppStoreAnalysisResponse`. Both frontend pages must be updated in the same PR.

## Diagram

```mermaid
flowchart TD
    A[URL input] --> B[Ingest comments / reviews]
    B --> C[Preprocess]
    C --> D[extract_insights — LLM\nno RAG context in prompt]
    D --> E{RAG_READ_ENABLED?}
    E -- yes --> F[enrich_problems\nfor each problem]
    F --> G[retrieve_similar\nproblem.problem text]
    G --> H[attach similar_insights\ntag recurrence new | known]
    H --> I{RAG_WRITE_ENABLED?}
    E -- no --> I
    I -- yes --> J[embed_and_store\nnew problems]
    I -- no --> K[Return enriched response]
    J --> K
```

## Known Issues

### Issue 1 — Duplicate rows on re-analysis

`_make_id` in `app/rag/rag.py:18–20` generates the row ID as `sha256(source_url + problem_text)`. The upsert is intended to deduplicate — but because the LLM is non-deterministic, re-running analysis on the same URL produces slightly different problem strings (e.g. `"Tab completion is unreliable"` vs `"Code completion frequently fails"`). Different text → different hash → brand new row, bypassing the upsert entirely. The `insights` table silently grows a duplicate entry per re-analysis rather than updating the existing one.

This issue exists in the current write path and is not introduced by this change, but per-problem enrichment makes it more visible: a re-analysed video will tag its problems as `"known"` (the old row is still there and will match at high similarity), yet a second near-duplicate row will be written for each problem. Resolution options belong in a follow-up ADR — candidates include semantic deduplication before upsert (query-first, skip write if similarity ≥ threshold) or a fuzzy-match step in `embed_and_store`.

## Files Changed Summary

| File | Change Type |
|------|-------------|
| `app/rag/rag.py` | Add `enrich_problems()` |
| `app/schemas/llm.py` | Add fields to both ProblemItem types |
| `app/schemas/api.py` | Remove `retrieved_context` |
| `app/services/youtube_service.py` | Remove pre-extraction read; add enrichment call |
| `app/services/appstore_service.py` | Remove pre-extraction read; add enrichment call |
| `app/config/promptTemplates.py` | Remove `prior_insights` from call sites |
| `app/jobs/automaticYoutube.py` | Remove `retrieve_similar` from `_build_prompt` |
| `app/jobs/automaticAppStore.py` | Remove `retrieve_similar` from `_build_prompt` |
| `frontend/src/YouTubePage.jsx` | Update to read per-problem `similar_insights` instead of `retrieved_context` |
| `frontend/src/AppStorePage.jsx` | Same update as YouTubePage |
