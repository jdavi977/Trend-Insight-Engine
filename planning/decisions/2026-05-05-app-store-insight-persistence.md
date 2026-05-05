# ADR: App Store Insight Persistence
Date: 2026-05-05
Status: Accepted

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

Chose **Option 1 — write App Store insights to Supabase in a new `automatic_apple_table`** because Supabase needs to remain the single relational source of truth for insights so the RAG embedder can re-embed from it without re-running the LLM extraction. A separate table (rather than overloading `automatic_table`) keeps Apple-only fields (`app_id`, `country`, `average_rating`, `example_reviews`) and YouTube-only fields (`thumbnail`, `total_likes`) from collapsing into nullable columns behind a `source` discriminator, and avoids mixing 2-digit YouTube category IDs with 4-digit Apple genre IDs in one column.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

1. Extra write on every `/analyze/appstore` call, new schema table for AppStore insights in Supabase
2. Dual-write discipline: every place that creates an App Store insight must remember to write Supabase and embed to Chroma
3. Two ingestion shapes to maintain (Youtube and AppStore) 
4. Duplicated Supabase helpers — `update_automatic_apple_trend` / `check_appstore_id` / `get_weekly_apple_ids` parallel the YouTube versions. We accept the duplication instead of parameterizing the existing helpers because a `table_name` argument hides which table is read at the call site.

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

- Closes off: ChromaDB-as-source-of-truth for any insight stream. Every `/analyze/*` flow that produces persisted insights is now expected to land them in Supabase first; embedders read Supabase, not the LLM output directly. Also closes off the option of a single shared insights table — future sources (Reddit, Amazon) get their own table with their own helpers, no `source` discriminator column.
- Enables: a uniform embedder that reads from Supabase and writes to Chroma works for both YouTube and Apple with the same query shape; the `/insights/similar` endpoint (PRD §3.1) has one backing pattern. Re-embedding after an embedding-model change becomes a re-read of `automatic_apple_table` instead of re-running every LLM extraction. Unblocks the spec in [planning/specs/automatic-appstore-supabase_spec.md](../specs/automatic-appstore-supabase_spec.md) to begin implementation.
