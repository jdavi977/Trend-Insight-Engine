# ADR: RAG Vector Database Selection

Date: 2026-05-11
Status: Draft

Related spec: planning/specs/rag-insights-retrieval_spec.md

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

Need a storage for embedding vectors to enable semantic search for previously recorded insights. Project is designed for single-user operation, with a weekly most popular data source pull.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **pgvector** - Use existing Supabase connection to store vectors alongside insights
2. **ChromaDB local** - file-based vector store with no external infrastructure
3. **Pinecone** - Fully managed cloud vector DB with built-in scaling and filtering

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Chose **pgvector** because pgvector is a postgres extension offered in our existing supabase database. This lets me co-locate vectors with the relational data, use one connection string, one backup strategy, and run hybrid queries with a single SQL query.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

- Gained: pgvector's integration with Supabase infrastructure
- Gained: Hybrid SQL queries combining metadata filters + semantic similarity in one call
- Lost: Pinecone's managed scalaing and uptime guarantees
- Lost: ChromaDB's zero-config local setup 

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

- Enables: Direct SQL queries combining insight metadata and vectors 
- Enables: Shared vector store across multiple deployments without manual file sync
- Closes: ChromaDB fast iteration and testing without cloud service latency

