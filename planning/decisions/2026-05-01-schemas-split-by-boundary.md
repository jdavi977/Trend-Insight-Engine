# ADR: schemas/ split by boundary direction (api.py vs llm.py)
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Target Layout, §PR 2)

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

Hints to draw from:
- Current state: `schemas/` only holds `llm_insights.py` (LLM output shape); the three request models (`YoutubeAnalyzeRequest`, `AppStoreAnalyzeRequest`, `DataSave`) live inline at `main.py:39-46`.
- Pain point: request bodies are co-located with the FastAPI app construction, so `main.py` mixes app wiring + CORS + schema definitions + endpoints + handlers (109 lines, growing).
- Trigger: PR 4 of the refactor splits `main.py` into `api/{youtube,appstore,home,internal}.py` routers — those routers need a stable home to import request models *from*, otherwise each router file would either redefine its model or import from a sibling.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **schemas/ split by boundary direction** — one file per boundary: `schemas/api.py` (inbound HTTP requests), `schemas/llm.py` (LLM output). Every Pydantic boundary model lives under `schemas/`.
2. **Per-feature schema files** — `schemas/youtube.py`, `schemas/appstore.py`, `schemas/home.py`, etc. — group request + LLM models by the feature they belong to.
3. **Co-locate schemas with their consumers** — request models live in `api/youtube.py` next to the route that uses them; LLM models live in `llm/` next to the extractor.

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Chose **[Option ?]** because …

Hints to draw from when picking the "single primary reason":
- Boundary clarity: split-by-direction makes the *kind* of contract (HTTP request vs LLM output) the organizing axis, which matches how the validation rules differ (request = client trust boundary, LLM = model trust boundary).
- Discoverability: one obvious place to look for "what does the API accept" vs "what does the LLM return."
- Reuse: the same request model could in principle be used by more than one route, and the same LLM output shape is used by both YouTube and App Store services — per-feature splitting would force duplication or cross-feature imports.
- Test seam: `tests/llm/test_validateOutput.py` already validates against `llm.py`-shaped dicts (spec §Pytest Bootstrap) — a single `schemas/llm.py` is the natural target.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

Hints — concrete costs of the chosen option:
- `schemas/api.py` will accumulate every request model in the app — as the API surface grows, this file grows linearly and becomes a grab-bag.
- A reader working on the YouTube feature must hop between `api/youtube.py`, `services/youtube_service.py`, and `schemas/api.py` to see the full flow — vertical-slice locality is lost.
- Needs a discipline rule: no Pydantic boundary model defined outside `schemas/` (otherwise the layout silently degrades back to the current state).
- By rejecting per-feature: lose the ability to delete a feature by deleting one folder.
- By rejecting co-location: lose the "everything for this route is in one file" ergonomics that FastAPI tutorials default to.

-
-

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

Hints to draw from:
- Closes off: defining `BaseModel` subclasses inline in `main.py` or in any `api/*.py` router file; importing request models from anywhere other than `schemas/api.py`.
- Closes off: importing schemas across feature boundaries (e.g. `services/appstore_service.py` reaching into `api/youtube.py` for a model).
- Enables: PR 4's router split — each `api/*.py` file imports its request model from `schemas/api.py` with no circular-import risk.
- Enables: a single test target for LLM-output validation (`tests/llm/test_validateOutput.py`) that doesn't need to know which feature produced the dict.
- Enables: future schema versioning (e.g. `schemas/api_v2.py`) along the same axis without restructuring.

- Closes off:
- Enables:
