# ADR: App Store Insight Persistence
Date: 2026-05-05
Status: Draft

Related spec: PRD_Trend_Insight_Engine_v2.md (§3.1 RAG Pipeline)

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

The project only has weekly Youtube job write insights to Supabase, manual `analyze/appStore` results are returned to the caller but then dropped. This means that there is no appStore data being saved. A new feature being implemented includes RAG work which embeds insights into ChromaDB on extraction, since we dont have any saved appStore data, re-running an analysis would re-embed and re-extract from scratch everytime.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **Write App Store insights to Supabase**: have appStore insights write to Supabase `automatic_apple_table`, have the RAG embedder read from Supabase as source of truth.
2. **Treat ChromaDB as source of truth for App Store**: embed and store directly into the App Store ChromaDB collection on `/analyze/appStore` and rely on the vector store's metadata fields to hold insight payload.

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Currently choosing, will try to implement option 1 first, depends if we are able to using the iTunes RSS field.

Chose **[Option ?]** because …

Hints to draw from when picking the "single primary reason":
- Symmetry with YouTube: do both sources benefit from going through the same Supabase → embedder pipeline, or is forcing symmetry premature?
- Source-of-truth clarity: where does an insight "live" — the relational store, the vector store, or both? Which one is authoritative if they disagree?
- Re-embeddability: if you change embedding models or chunking later, can you rebuild ChromaDB from Supabase, or is Chroma the only copy?
- Query shape: what reads do you actually need on App Store insights — relational filters (severity, date) or semantic search? Picking the store that matches the dominant read pattern.
- Cost of the simpler path now vs. the migration cost later if the simpler path turns out wrong.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

Hints — concrete costs of the chosen option:
- If Supabase: an extra write on every `/analyze/appStore` call (latency + a Supabase row per run), plus a schema decision about whether App Store insights share `automatic_table` or get their own table.
- If Supabase: dual-write discipline — every place that creates an App Store insight must remember to write Supabase *and* embed to Chroma, and the two can drift.
- If ChromaDB-as-truth: no relational query path for App Store insights (no SQL filters, no joins, no Supabase dashboard view) — anything non-semantic has to go through Chroma's metadata filtering.
- If ChromaDB-as-truth: rebuilding the vector store after an embedding-model change means re-running every original analysis (LLM cost) instead of re-embedding existing rows.
- Either way: asymmetry between YouTube and App Store paths if you don't also revisit YouTube — two ingestion shapes to maintain.

-
-

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

Hints to draw from:
- Closes off: under Option 1, "ephemeral analyze endpoints" become disallowed — every `/analyze/*` endpoint is expected to persist. Under Option 2, "Supabase as the single relational store of insights" stops being true.
- Enables: under Option 1, a uniform embedder that reads from Supabase and writes to Chroma works for both sources; the `/insights/similar` endpoint (PRD §3.1) has one backing query path. Under Option 2, App Store can ship without touching the Supabase schema at all, unblocking Week 1 faster.
- Either way: this decision sets the precedent for any *future* source (Reddit, Amazon reviews) — they'll follow whichever pattern wins here.

- Closes off:
- Enables:
