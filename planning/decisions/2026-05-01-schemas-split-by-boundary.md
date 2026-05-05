# ADR: schemas/ split by boundary direction (api.py vs llm.py)
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Target Layout, §PR 2)

## Context

Current state: schemas/ hold the LLM output shape only. There are three request models YoutubeAnalyzeRequest, AppstoreAnalyzeRequest, and DataSave inside main.py.

## Options Considered

1. schema/ split by boundary direction: one file per boundary including `schemas/api.py` and `schemas/llm.py`. All Pydantic boundary models live under `schemas/`.
2. Per-feature schema files: `schemas/youtube.py`, `schemas/appstore.py`, `schemas/home.py`

## Decision

Chose **boundary direction split** easy to reuse the same request model, same LLM output shape is used by both Youtube and App store services, by having the shape in one folder we remove duplication or cross-feature imports.

## Tradeoffs Accepted

1. `schemas/api.py` will accumulate every request model in the app, so as we add more APIs, this file will grow


## Consequences

- Closes off: 
    1. Defining `BaseModel` subclasses in `main.py` or in any `api/*.py` file
    2. Importing request models must be from `schemas/api.py` only.
- Enables:
    1. Reduces the amount of imports as each `api/*.py` file imports its request model from `schemas/api.py`
    2. Single test target for LLM-output validation
