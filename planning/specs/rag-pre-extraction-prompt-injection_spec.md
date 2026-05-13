# RAG Pre-Extraction Context Injection

## Problem

The vector store is populated and per-problem enrichment runs after extraction, but the LLM never sees past insights when it generates new ones. The prompt builders (`build_youtube_prompt`, `build_appstore_prompt`) already accept a `prior_insights: list[RetrievedInsight]` argument and have a `_prior_insights_block` formatter — but both services always pass `[]`. The infrastructure exists; the wiring does not.

Concretely: when a user analyzes a new batch of comments, the LLM has no awareness of problems already discovered — whether from the same app analyzed previously, or from a different app where users reported the same pattern. The model can't consolidate, confirm, or refine known patterns — it starts cold every time. Problems that recur across analyses are only connected after the fact via `enrich_problems`, not used to influence extraction quality.

This spec adds a pre-extraction `retrieve_similar` call to both manual services, using a sample of the cleaned comments as the query, and threads the results into the prompt. The `enrich_problems` post-extraction enrichment is **kept as-is** — the two mechanisms are complementary. Pre-extraction gives the LLM context; post-extraction annotates each problem with provenance.

## Solution

Before calling `extract_insights`, each manual service builds a query from the cleaned comment corpus, fetches the top-K most semantically similar past insights from across all stored problems, then passes the results into the prompt builder.

The stored vectors are **problem descriptions**. To retrieve semantically similar ones, the query must be in the same space. Cleaned comments like *"the app crashes every time I go offline"* have high cosine similarity to stored problems like *"Offline mode crashes on iOS 17"* — regardless of which app or source those problems came from. This enables **cross-app pattern recognition**, which is the primary value of pre-extraction RAG.

```
URL
 ↓
fetch + clean comments/reviews      ← already happens
 ↓
sample cleaned_data → query_text    ← NEW: first RAG_QUERY_MAX_CHARS of joined corpus
 ↓
retrieve_similar(query_text)        ← NEW, gated on RAG_READ_ENABLED
 ↓
build_prompt(genre, prior_insights) ← prior_insights was always []
 ↓
extract_insights(cleaned, prompt)   ← LLM now sees cross-app patterns
 ↓
enrich_problems(result)             ← unchanged: per-problem provenance
 ↓
embed_and_store(result, link)       ← unchanged: write new problems
 ↓
return response
```

No new modules. No new schemas. No new endpoints. Changes are confined to the two service files and one config constant.

## Query Text

`retrieve_similar` takes a free-text query. The correct query is a **sample of the cleaned comments** — the same text the LLM will read. A video title or app name (e.g. `"Spotify App Review 2024"`) is categorically different from a problem description, so title-based queries produce poor retrieval regardless of vector quality.

To avoid embedding an unbounded corpus, the query is capped at a fixed character budget:

```python
RAG_QUERY_MAX_CHARS = 2000  # ~500 tokens; enough for semantic signal, safe for embedding models
query_text = " ".join(cleaned_data)[:RAG_QUERY_MAX_CHARS]
```

| Source | Query |
|---|---|
| YouTube | First 2000 chars of `cleaned_data` (joined comment strings) |
| App Store | First 2000 chars of `cleaned_data` (joined review strings) |

If `cleaned_data` is empty or the join produces a blank string, skip the pre-extraction call and pass `[]`.

## Caller Changes

### `app/services/youtube_service.py`

```python
# Before extract_insights:
prior_insights = []
if RAG_READ_ENABLED and cleaned_data:
    try:
        query_text = " ".join(cleaned_data)[:RAG_QUERY_MAX_CHARS]
        prior_insights = retrieve_similar(query_text)
    except Exception:
        logger.exception("Pre-extraction retrieve_similar failed; continuing without context")

prompt = build_youtube_prompt(default, prior_insights)
result = extract_insights(cleaned_data, prompt, youtubePromptOutput, source="youtube")
```

`enrich_problems` and `embed_and_store` calls remain unchanged.

### `app/services/appstore_service.py`

```python
# Before extract_insights:
prior_insights = []
if RAG_READ_ENABLED and cleaned_data:
    try:
        query_text = " ".join(cleaned_data)[:RAG_QUERY_MAX_CHARS]
        prior_insights = retrieve_similar(query_text)
    except Exception:
        logger.exception("Pre-extraction retrieve_similar failed; continuing without context")

prompt = build_appstore_prompt(default, prior_insights)
result = extract_insights(cleaned_data, prompt, appStorePromptOutput, source="app_store")
```

`enrich_problems` and `embed_and_store` calls remain unchanged.

## Automatic Pipeline

No changes. `automaticPipeline.py` calls `enrich_problems` (post-extraction) but not pre-extraction injection. Weekly jobs process dozens of items in a loop — adding an embedding call per item would meaningfully extend runtime and quota usage. Pre-extraction injection is scoped to manual (single-item, user-triggered) flows only.

## What the LLM Prompt Looks Like

`_prior_insights_block` in [app/config/promptTemplates.py](app/config/promptTemplates.py#L29) already produces:

```
Previously observed problems (use as context, do not repeat verbatim):
- [complaint] severity:4 freq:3 — "Offline mode crashes on iOS 17"
- [feature_request] severity:2 freq:5 — "No dark mode support"
...
```

This block is appended to the base system prompt. `RAG_TOP_K` (currently 5) controls how many lines appear. At ~20–40 tokens per line, 5 insights adds ~100–200 tokens — negligible against the comment corpus.

Retrieved insights may come from any previously analyzed source. The LLM is expected to:
- Confirm known patterns if comments still mention them (higher confidence)
- Consolidate similar phrasing into a single canonical problem description
- Identify genuinely new problems the prior context doesn't cover

## Failure Handling

The pre-extraction call uses the same try/except pattern as `enrich_problems` — fall back to `[]` on any exception and continue. A retrieval failure must never fail the analysis.

If `cleaned_data` is empty, the pre-extraction call is skipped entirely; no exception path is needed.

## Files Changed

| File | Change |
|---|---|
| `app/services/youtube_service.py` | Add pre-extraction `retrieve_similar` call using cleaned comments; pass result into `build_youtube_prompt` |
| `app/services/appstore_service.py` | Same |
| `app/config/settings.py` (or equivalent) | Add `RAG_QUERY_MAX_CHARS = 2000` alongside existing `RAG_TOP_K` |

No other files change.

## Known Limitations

**Query truncation.** The 2000-char cap means only the first portion of the comment corpus influences retrieval. If the most diagnostically rich comments appear later in the list, they won't affect the query. If retrieval quality is poor after milestone 8, consider shuffling or sampling comments rather than taking the head.

**Cold start.** When the vector store is empty, `retrieve_similar` returns `[]` and behavior is identical to today. Pre-extraction injection only activates once the store has relevant content.

**Non-determinism.** The LLM may still paraphrase retrieved problems differently, causing near-duplicate rows on the write path. That's a known issue documented in the architecture doc and out of scope here.

## Test Plan

Mocked:
- `tests/services/test_youtube_service.py` — patch `retrieve_similar`; assert it is called with the first 2000 chars of joined `cleaned_data` when `RAG_READ_ENABLED=True`; assert `build_youtube_prompt` is called with the returned list; assert it is NOT called when `RAG_READ_ENABLED=False` or `cleaned_data` is empty.
- `tests/services/test_appstore_service.py` — same pattern.
- Exception path: patch `retrieve_similar` to raise; assert service returns a valid result with `prior_insights=[]` (no crash).
- Empty corpus path: pass `cleaned_data=[]`; assert `retrieve_similar` is never called.

No new integration tests — the retrieval and prompt formatting paths are already covered by existing tests.

## Acceptance

- `RAG_READ_ENABLED=true`, vector store populated with problems from at least one prior source → `POST /analyze/youtube` (or `/analyze/appstore`) response contains problems that align with or refine retrieved cross-source insights; LLM output visibly shaped by retrieved context (manually verified on 2+ analyses).
- Retrieved insights come from a different app than the one being analyzed → confirms cross-app retrieval is working.
- `RAG_READ_ENABLED=false` → behavior byte-identical to current; `retrieve_similar` never called.
- `retrieve_similar` raises → analysis completes successfully with `prior_insights=[]`.
- All existing tests green; new service tests green.

## Sequencing

Single PR. Both service files change together — the logic is identical and the diff is small (~10 lines per service). No schema changes, no new modules, no migration.
