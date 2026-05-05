# ADR: clients/ wrapper layer for external SDKs
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Target Layout, §PR 5)

## Context

Current codebase has a layered structure (api -> services -> pipeline -> clients/schemas). Right now exteral SDK calls (Supabase writes, Youtube data API fetches, OpenAI calls) are reached out in different layers of the code. Without a fixed wrapper layer, new integerations such as helper functions for exteral SDK calls would repeat auth/ config/error handling in different places of the project.

## Options Considered

1. Clients/<vendor>.py wrapper layer: includes one file per external service under `app/clients/`
2. Use SDKs directly in services: services and pipeline modules would make external calls whenever needed

## Decision

Chose **Clients/<vendor>.py** because it makes sure external calls are organized in one place and not called in different layers of the code. This also helps with tests.


## Tradeoffs Accepted

Creates one extra module per client, also creates one more hop when reading code

## Consequences

- Closes off: vendor SDK imports outside of clients/, auth/config setup scattered across modules, SDK helpers inside old lib/utilties folder
- Enables: a single mock point per vendor in tests, a single place to change auth, retries, or SDK versions, a folder specific for all data-source integrations
