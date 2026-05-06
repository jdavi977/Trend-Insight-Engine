# Deep Module: extract_insights

## Problem

The LLM seam is split across two shallow modules and four duplicated post-processing recipes.

- **`extractInsights.py` is a 4-line pass-through.** [app/llm/extractInsights.py:4-9](app/llm/extractInsights.py#L4-L9) just forwards to `create_response`. Deletion test: remove it, callers import `create_response` directly — nothing concentrates, nothing duplicates.
- **`validateOutput.py` is only wired to one of four callers.** Used at [app/services/youtube_service.py:15](app/services/youtube_service.py#L15). Not used by `appstore_service.py`, `jobs/automaticYoutube.py`, or `jobs/automaticAppStore.py`. The App Store manual flow returns unvalidated LLM output — silent contract gap.
- **Latent bug in validateOutput.** [app/llm/validateOutput.py:31](app/llm/validateOutput.py#L31) calls `mkdir(..., exist_ok=False)` and crashes on the second invalid run within the same second. The `except:` at line 18 also swallows the `validated`-undefined path on line 22.
- **Duplicated post-processing.** Both jobs run the same recipe after `extractInsights`: `json.loads` → `isinstance(data, list)` shape repair → `if not data["problems"]: skip` ([automaticYoutube.py:36-50](app/jobs/automaticYoutube.py#L36-L50), [automaticAppStore.py:41-54](app/jobs/automaticAppStore.py#L41-L54)). That recipe is the actual leverage point — it's currently copy-pasted, untyped, and unvalidated.

## Solution

Replace `extractInsights.py` and `validateOutput.py` with one deep module whose interface returns a typed, normalized, validated result.

```python
# app/llm/extractInsights.py
def extract_insights(
    data: list,
    system_prompt: str,
    output_prompt: str,
) -> LLMExtraction | None:
    """
    Returns a validated LLMExtraction, or None if the model returned
    no usable problems. Caller handles None as 'skip this item'.
    Per-problem validation drops malformed entries and quarantines them.
    """
```

Behind that interface:
1. Call `clients.openai.create_response` (vendor adapter — unchanged).
2. `json.loads` the raw text.
3. Normalize list-vs-dict shape (today duplicated in two jobs).
4. `LLMExtraction.model_validate` the envelope.
5. Per-item `ProblemItem.model_validate`; quarantine failures to `data/invalid_data/<run_id>/run.json` with collision-safe writes.
6. Return `None` when `problems` is empty or envelope validation fails.

Vendor shape (`developer` role, `output_text`) stays inside [app/clients/openai.py](app/clients/openai.py) as the single adapter. Callers stop seeing `str` and `json.loads` — they see an `LLMExtraction`.

## Schema Tightening

[app/schemas/llm.py:18](app/schemas/llm.py#L18) currently types `problems: List` (untyped). Tighten to `List[ProblemItem]` so envelope validation does the per-item check Pydantic-natively. The current spec keeps a manual loop because `ProblemItem` doesn't yet model App Store fields (`average_rating`, `example_reviews`).

**Decision needed:** one `ProblemItem` with optional fields, or `YoutubeProblemItem` + `AppStoreProblemItem` discriminated by `LLMExtraction.source`? Recommendation: discriminated union — keeps each source's contract tight and surfaces type errors at the boundary.

## Caller Changes

| File | Before | After |
|------|--------|-------|
| [services/youtube_service.py](app/services/youtube_service.py) | `extractInsights` → `validateOutput` | `extract_insights` → return result or 404-equivalent on `None` |
| [services/appstore_service.py](app/services/appstore_service.py) | `extractInsights` → return raw str | `extract_insights` → return typed result (closes silent gap) |
| [jobs/automaticYoutube.py](app/jobs/automaticYoutube.py) | `extractInsights` + `json.loads` + list/dict repair + `data["problems"]` check | `extract_insights`, skip on `None`, iterate `result.problems` |
| [jobs/automaticAppStore.py](app/jobs/automaticAppStore.py) | same recipe as above | same as above |

## Benefits

- **Depth.** Small interface (`data`, `system_prompt`, `output_prompt` → `LLMExtraction \| None`); real work behind it.
- **Locality.** The `isinstance(data, list)` repair lives in one place.
- **Leverage.** All four callers get the same quality bar; App Store manual flow gains validation it currently lacks.
- **Testability.** One mock seam (`extract_insights`) replaces the `extractInsights` + `validateOutput` pair in service tests.
- **Bug fix.** `mkdir(exist_ok=False)` collision goes away; bare `except:` is replaced with explicit `ValidationError` handling.

## Test Plan

Real (not mocked):
- `tests/llm/test_extract_insights.py`
  - Happy path: valid LLM JSON → `LLMExtraction` with all problems intact (mock `create_response`).
  - List-shaped envelope: `[{...}]` → unwrapped to dict.
  - Empty problems: returns `None`.
  - Mixed valid/invalid problems: invalid quarantined, valid kept.
  - Envelope validation failure: returns `None`.
  - Quarantine collision: two invalid runs in same second both write without error.

Mocked at the new seam:
- `tests/services/test_youtube_service.py` — patch `app.llm.extractInsights.extract_insights`, assert orchestration on returned `LLMExtraction`.
- `tests/services/test_appstore_service.py` — new; same shape as youtube.

Out of scope: testing the OpenAI vendor call itself.

## Sequencing (three PRs)

### PR 1 — Schema tightening
- Decide on `ProblemItem` strategy (single optional vs discriminated union).
- Type `LLMExtraction.problems` as `List[ProblemItem]` (or union).
- Update existing `validateOutput` tests if any; otherwise scaffold `tests/llm/test_extract_insights.py` against the *current* `validateOutput` as the safety net.

### PR 2 — Introduce `extract_insights`, delete the two old modules
- Write `app/llm/extractInsights.py` with the new `extract_insights` function (replacing the existing pass-through).
- Delete `app/llm/validateOutput.py`.
- Migrate all four callers in one PR — atomic; no transitional dual-export.
- Fix `mkdir(exist_ok=False)` (use `exist_ok=True`, or append a counter on collision).
- Replace bare `except:` with `pydantic.ValidationError`.

### PR 3 — Caller cleanup
- Both jobs: remove `import json`, remove `isinstance(data, list)` repair, iterate typed `result.problems`.
- `appstore_service.py`: return validated result, update endpoint contract if response shape changes.
- `youtube_service.py`: remove `validateOutput` import.

## Acceptance

- `grep -r "json.loads" app/` returns no matches outside `app/llm/` and `app/clients/`.
- `grep -r "isinstance(data, list)" app/` returns no matches.
- `grep -r "validateOutput" app/` returns no matches.
- All four callers use `extract_insights` and consume an `LLMExtraction`.
- Tests green; quarantine collision test passes.

## Deferred

- Async OpenAI calls (separate concern from module shape).
- Retry/backoff inside `create_response` (lives in `clients/openai.py` if added).
- Streaming responses.
