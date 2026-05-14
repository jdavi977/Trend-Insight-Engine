# RAG v3: From Calibration Layer to Product Intelligence System

## Problem

RAG today is defensive. The pipeline writes embeddings, retrieves similar problems, and uses them in two narrow places:

1. **Refinement prompt** — prior insights nudge severity/frequency upward for recurring issues ([promptTemplates.py:69-93](app/config/promptTemplates.py#L69-L93)).
2. **Post-extraction enrichment** — each problem is tagged `recurrence: "known" | "new"` and decorated with `similar_insights` ([rag.py:66-77](app/rag/rag.py#L66-L77)).

Plus a thin search endpoint at `/insights/similar`.

That is the floor of what RAG can do here, not the ceiling. The first extraction pass still sees zero history. Recurrence is a per-run tag, not a stable identity — there is no notion of *"this is the same problem we've seen 47 times since January"*. YouTube and App Store insights live in the same table but are never correlated. Raw source text isn't stored, so the system cannot cite the exact comment behind a claim. There is no trend view, no emerging-problem detection, and no way to empirically tune `RAG_MIN_SIMILARITY` or `RAG_TOP_K` because retrievals aren't logged or scored.

The shift this spec proposes: stop treating the vector store as a per-request side-channel and start treating it as the **canonical problem ledger** — a longitudinal record of every issue users have raised, with provenance, recurrence counts, cross-source links, and a query layer rich enough to power a real product-insight UI.

## Goals

- Every extracted problem links to a stable canonical problem ID with a recurrence count and source list.
- The LLM sees relevant prior context on the **first** extraction pass, not only during refinement.
- A problem raised on YouTube and on App Store is recognized as the same problem.
- Retrieval supports metadata filters (type, severity, time window) — not just cosine similarity.
- Every canonical problem can be traced back to the raw comments/reviews that produced it.
- New problem clusters that don't fit existing categories are surfaced weekly.
- Retrieval quality and refinement quality are measurable, not vibe-checked.

## Non-Goals

- Replacing the LLM extraction step. RAG augments extraction; it does not extract.
- Multi-tenant or per-user partitioning of the ledger. Single-tenant for v3.
- Real-time streaming. Weekly job cadence is unchanged.
- LLM fine-tuning. All gains come from retrieval + prompting.
- Conversational UI / chat over the corpus. Deferred; this spec is about the data layer.

## Solution Overview

Seven additions, sequenced so each phase produces user-visible value and each phase's plumbing is reused by the next.

### 1. Few-shot the first extraction pass

Today's first extraction pass passes `prior_insights=[]` ([youtube_service.py:28](app/services/youtube_service.py#L28)). It retrieves history *between* pass 1 and pass 2 only. Inject the top-K most similar past problems into the pass-1 prompt as well, using a sample of the cleaned comment corpus as the query (same approach as the existing pre-extraction injection spec, but applied to the actual pass-1 call).

**Why this is first:** zero new infrastructure. The retrieval, prompt builder, and prior-insights formatter all exist. This is a one-line wiring fix that immediately improves extraction quality and surfaces whether retrieval is noisy enough to need #4 (hybrid filters) sooner rather than later.

### 2. Canonical problem ledger

Today, every extracted problem gets a row keyed by `sha256(source_url + problem_text)` ([rag.py:18-20](app/rag/rag.py#L18-L20)). Two videos describing the same issue produce two rows. The `recurrence` tag is computed per-request and discarded.

Introduce a **canonical problem** abstraction: a stable record that owns identity, recurrence count, first/last seen timestamps, and a list of source occurrences. Each new extraction either (a) merges into an existing canonical via high-similarity match, or (b) creates a new canonical. The existing per-source embedding table becomes the occurrences table; canonicals are a new layer on top.

**Output**: when the user analyzes a video, the response shows "this problem has been raised 47 times across 12 videos and 3 App Store reviews since 2026-01-04" — not just `recurrence: "known"`.

**Why this is the keystone:** every later item (cross-source, trends, citations, evaluation) needs stable identity to be useful. Without it, you can answer "have we seen something similar?" but not "what's actually happening with problem X over time?"

### 3. Cross-source correlation

Once canonicals exist, a single canonical can own occurrences from `source: youtube` and `source: app_store`. Surface this in the response: a canonical with occurrences in both sources ranks higher in retrieval and displays both source counts in the UI.

**Why now:** cross-source is essentially free once #2 lands — it's a query that already works against the canonical table. The work is mostly UI: showing the multi-source badge and weighting in retrieval ordering.

### 4. Hybrid retrieval (metadata + vector)

Today `retrieve_similar` is pure cosine with a single similarity floor ([rag.py:80-97](app/rag/rag.py#L80-L97)). Add structured filters: `type`, `severity >= N`, `extracted_at` window, `source` subset. pgvector supports this in a single SQL query.

**Use cases this unlocks:**
- Refinement prompt only sees recent (last 90 days) prior insights — old data doesn't pollute calibration for a fast-moving product.
- `/insights/similar` accepts filter params for a real search UI.
- Trend detection (#6) needs time-windowed queries.

### 5. Embed raw source text alongside extracted problems

Today only the LLM's summary is embedded ([rag.py:31](app/rag/rag.py#L31)). The raw comments and reviews are dropped after extraction. This means the system can claim "47 mentions" but cannot show the 47 quotes.

Store the cleaned source text (comment/review body + author + likes/votes + URL with timestamp anchor where applicable) linked to each occurrence. Two reasons:

- **Citations**: each canonical can be expanded to show actual user quotes. This is what makes the UI trustworthy to a PM or exec.
- **Re-extraction**: if the prompt or model changes, the raw text can be re-embedded and re-extracted without re-fetching from the YouTube API (quota matters).

### 6. Trend and emergence detection

A weekly job that runs over canonicals and surfaces:

- **Rising**: canonicals whose occurrence rate over the last 4 weeks is significantly higher than the prior 12 weeks.
- **Emerging**: clusters of recent occurrences (last 4 weeks) that don't merge into any existing canonical above the similarity threshold — candidate new canonicals.
- **Dormant**: previously frequent canonicals with no new occurrences in 8+ weeks.

Output goes to a new home-page panel and/or a `/trends` endpoint. This is the feature that turns the app from "summarize a video" into "tell me what's changing."

**Why this slot:** needs canonicals (#2), needs time filters (#4), benefits from raw text for "show me examples of this new cluster" (#5).

### 7. Evaluation harness

Today `RAG_MIN_SIMILARITY = 0.75` and `RAG_TOP_K = 5` are guesses. The system has no way to know if 0.75 is too tight or too loose, or whether the refinement prompt actually improves output.

Build a lightweight eval loop:

- **Retrieval logging**: every `retrieve_similar` call writes the query, results, and similarity scores to a log table.
- **Sampled review**: a weekly script samples N retrievals and presents them for thumbs-up/thumbs-down. (Manual at first; LLM-as-judge later.)
- **A/B prompting**: a flag to run refinement with and without prior insights on the same input, log both outputs side-by-side, and let the maintainer compare.

**Why last:** earlier items move the needle whether or not you measure them. But once 1–6 are live, you cannot keep tuning by feel — the surface area is too large. This is the discipline layer.

## Sequencing

| Phase | Items | Ships |
|---|---|---|
| **v3.1** | #1 few-shot pass 1 | Better first-pass extractions, validates retrieval quality on real prompts. One PR. |
| **v3.2** | #2 canonical ledger | Recurrence count + cross-extraction identity. Migration of existing rows into canonicals. |
| **v3.3** | #3 cross-source + #4 hybrid filters | Multi-source badges, filterable `/insights/similar`. |
| **v3.4** | #5 raw text storage + citations | Quote-level provenance in the UI. Backfill of weekly-job raw text where retainable. |
| **v3.5** | #6 trends + emergence | Home-page "what's changing" panel. |
| **v3.6** | #7 eval harness | Tunable thresholds backed by data, A/B comparison flag. |

Phases are sized so each ships independently and rolls back cleanly. Phase v3.2 is the largest and the only one that requires a data migration.

## Success Criteria

End state — what's true when v3.6 lands:

- Re-analyzing the same video twice produces the same canonical problem IDs.
- The home page shows a "rising problems" section sourced from #6.
- Each canonical in the UI lists the source videos/apps and at least one raw quote.
- Refinement prompt context is filterable by recency and severity (default: last 90 days, severity ≥ 3).
- A maintainer can answer "is RAG making refinement better?" by pulling the eval log, not by re-reading prompts.
- `/insights/similar?query=...&type=complaint&since=2026-02-01` returns filtered results.
- A YouTube canonical that also appears in App Store shows both source counts in the response.

## Architectural Decisions to Make in Phase Specs

Captured here as open questions; each phase spec resolves the ones relevant to it.

| Decision | Phase | Notes |
|---|---|---|
| Canonical merge policy | v3.2 | Similarity threshold for auto-merge; manual review queue for borderline matches? |
| Canonical ID format | v3.2 | Deterministic hash of seed problem text, or UUID assigned at creation? |
| Raw text retention | v3.4 | All raw comments, or only those cited by a canonical? Storage cost vs. completeness. |
| Trend window sizes | v3.5 | 4w/12w is the starting heuristic — needs validation against actual data volume. |
| Eval review cadence | v3.6 | Manual weekly vs. LLM-as-judge continuous. Manual is cheaper to build, scales worse. |

## Deferred (explicitly post-v3)

- Conversational Q&A interface over the canonical ledger.
- Multi-tenant partitioning.
- LLM fine-tuning on canonicalized data.
- Real-time webhook ingestion.
- Embedding model upgrade / re-embedding migrations.
- Sentiment-aware retrieval (separating complaints from feature requests at the embedding level).

## Open Questions

1. **Migration of existing weekly data**: the `automatic_table` rows were never canonicalized. Phase v3.2 needs a one-shot script that clusters existing problems into seed canonicals — does this run before or after v3.2 cutover? (Recommendation: before, as part of the PR, similar to the v2 backfill pattern.)
2. **Raw text and the App Store source**: iTunes RSS reviews are short and self-contained. YouTube comments can be long threads — do we store the parent comment only, or include replies?
3. **Trend panel placement**: new home-page section, or a new `/trends` route? Affects scope of v3.5.
