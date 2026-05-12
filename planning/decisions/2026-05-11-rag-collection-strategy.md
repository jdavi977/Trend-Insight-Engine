# ADR: RAG Collection Strategy

Date: 2026-05-11
Status: Draft

Related spec: planning/specs/rag-insights-retrieval_spec.md

## Context

The system needs a vector storage strategy that supports semantic retrieval across data sources.

## Options Considered

1. **Single collection with source metadata filter** — All insights (YouTube + App Store)
   in one insights collection

2. **One collection per source** — Separate `outube_insights and appstore_insights
   collections

## Decision

Chose **single collection with source metadata filter** because the same problem surfacing
in both YouTube and App Store for the same product becomes visible in a single query
without any client-side stitching.

## Tradeoffs Accepted

- Gained: Cross-source retrieval by default — a k=5 query can return a mix of YouTube
  and App Store insights, surfacing correlated pain points without extra logic
- Gained: Simpler `clients/chroma.py` and `rag_service.py` — no conditional branching
  on which collection to query
- Gained: Future product-level filtering (`product_id`, `source`, `category`) added as
  metadata without schema migration
- Lost: Source-level namespacing — no hard separation between YouTube and App Store
  vectors; client must explicitly filter by `source` metadata if isolated results
  are ever required
- Lost: Per-source collection tuning — cannot independently configure retrieval k,
  metadata schema, or vector dimensionality per source if sources diverge in the future
- Taken on: Metadata discipline — the shared schema must be valid for both YouTube and
  App Store insights from day one; a field present in one but absent in the other
  requires a nullable/optional convention enforced across all ingestion paths

## Consequences

- Closes off: Per-source collection management — there is no `youtube_insights` or
  `appstore_insights` collection; adding one later would require a data migration
- Closes off: Retrieval isolation by source without client-side filtering — raw queries
  return a cross-source mix by default

- Enables: Cross-source pain point correlation — the same problem appearing in both
  YouTube comments and App Store reviews for the same product surfaces in a single
  semantic query
- Enables: Product-scoped retrieval — filtering by `product_id` metadata returns all
  insights for one product across both sources, which is the primary use case
- Enables: Simpler test mocking — one collection to stub in tests, not two or three
- Enables: `source` as a discovery dimension — downstream features (e.g., "show me only
  App Store insights for this product") can be added as a metadata filter without
  touching the collection architecture