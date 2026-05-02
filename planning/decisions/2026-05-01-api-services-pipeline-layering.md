# ADR: api → services → (ingestion|preprocessing|llm) layering
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Layer Boundaries)

## Context
Previous app/ is flat, containing route handlers, ingestion modules, preprocessing, and LLM sitting next to each other with no enforced direction of imports. Due to no layered approach, every route test in pytest bootstrap would have to mock ingestion + OpenAI + Supabase directly instead of mocking one service at a time.

## Options Considered
1. Strict Layering (api -> services -> pipeline stages) - Route handlers can only import from services/ and services orchestrate ingestion/, preprocessing/, llm/, and clients/
2. Flat layout - Keep app/ flat, routes import whatever module they need directly
3. Hybrid approach - routes call ingestion directly for "simple" endpoints. Servies layer exists for Youtube analysis flow, but trivial endpoints such as single Youtube or iTunes fetch would skill the service and call ingestion from the handler.

## Decision
Chose **Strict Layering** because it provides a cleaner code structure, having each endpoint follow the same shape. It also provides a scalable environment for route tests.

## Tradeoffs Accepted
1. One extra module per endpoint flow
2. One more hop to read when looking at code top-down


## Consequences
- Closes off:
    1. Closes off api modules importing from ingestion/, preprocessing/, llm/, or clients/ directly.
    2. jobs/ containing business logic instead of being thin shells
- Enables:
    1. Route tests mock a single service function
    2. Reusing the same service from both a HTTP route and a jobs/ cron entry point
    3. When swapping a client (iTunes to Youtube) the API surface would not be touched, instead only one ingestion module would need to be changed.
