# ADR: clients/ wrapper layer for external SDKs
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Target Layout, §PR 5)

## Context

Current codebase has a layered structure (api -> services -> pipeline -> clients/schemas). Right now external SDK calls (Supabase writes, YouTube Data API fetches, OpenAI calls) are reached out in different layers of the code. Without a fixed wrapper layer, new integrations such as helper functions for external SDK calls would repeat auth/ config/error handling in different places of the project.

## Options Considered

1. Clients/<vendor>.py wrapper layer: includes one file per external service under `app/clients/`
2. Use SDKs directly in services: services and pipeline modules would make external calls whenever needed

## Decision

Chose **Clients/<vendor>.py** because it confines external calls to a single layer, gives one place to change auth/retries/SDK versions per vendor, and creates a single mock seam per vendor for tests.


## Tradeoffs Accepted

Creates one extra module per client, also creates one more hop when reading code

## Consequences

- Closes off:
    1. Vendor SDK imports outside of `clients/`
    2. Auth/config setup scattered across modules
    3. SDK helpers inside old lib/utilities folder
- Enables:
    1. A single mock point per vendor in tests
    2. A single place to change auth, retries, or SDK versions
    3. A folder specific for all data-source integrations
