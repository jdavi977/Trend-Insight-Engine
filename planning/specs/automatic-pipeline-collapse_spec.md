---
name: Collapse Automatic YouTube + App Store Jobs into One Pipeline Module
description: Replace the two near-identical automatic_* job bodies with a single jobs/automaticPipeline.py that owns the per-item loop, empty-data guards, list/dict normalization, and per-problem fan-out, driven by a small per-source adapter.
type: spec
---

# Automatic Pipeline Collapse — Spec

## Goal
Replace the two near-line-identical job bodies in
[app/jobs/automaticYoutube.py](app/jobs/automaticYoutube.py) and
[app/jobs/automaticAppStore.py](app/jobs/automaticAppStore.py) with a
single deep `app/jobs/automaticPipeline.py` that owns the loop and the
recurring guard logic, driven by a per-source adapter. The two
existing job files become ~10-line shells that build their adapter and
delegate.

This is a structural refactor: behavior on the wire is unchanged. What
changes is where the logic lives, and as a side effect the loop
becomes testable without mocking five SDK boundaries.

## Scope
- In:
  - New `app/jobs/automaticPipeline.py` containing the shared loop,
    guards, normalization, and per-problem fan-out.
  - New adapter contract (a small dataclass or `Protocol`) that
    captures the six per-source seams listed in **Decisions →
    Adapter shape** below.
  - Rewrite [app/jobs/automaticYoutube.py](app/jobs/automaticYoutube.py)
    as a thin shell that wires the YouTube adapter and calls the
    pipeline. Public signature
    `youtube_automatic(ids, category, categoryPrompt, keywords)` is
    preserved — `ops/scripts/weeklyYoutube.py` keeps working unchanged.
  - Rewrite [app/jobs/automaticAppStore.py](app/jobs/automaticAppStore.py)
    as a thin shell that wires the App Store adapter and calls the
    pipeline. Public signature
    `appstore_automatic(apps, genre_id, genre_prompt, keywords)` is
    preserved — `ops/scripts/weeklyAppStore.py` keeps working unchanged.
  - New `tests/jobs/test_automaticPipeline.py` exercising the loop
    against a fake adapter (existing-id short-circuit, empty-clean
    skip, list-vs-dict normalization, empty-problems skip,
    per-problem fan-out, return value shape).
  - Fix the always-truthy `if trend_data:` guard at
    [app/jobs/automaticYoutube.py:67](app/jobs/automaticYoutube.py#L67) /
    [app/jobs/automaticAppStore.py:74](app/jobs/automaticAppStore.py#L74)
    by deleting it — the row is built unconditionally inside the
    per-problem loop, so the check has never gated anything.
- Out:
  - Behavior changes to ingestion, cleaning, LLM extraction, or
    Supabase writes. This spec moves code, it does not change what
    the pipeline produces.
  - Parameterizing the Supabase helpers
    (`update_automatic_trend` / `update_automatic_apple_trend` stay
    distinct functions called via the adapter — see ADR check below).
  - Generalizing the adapter for a third source (Reddit/Amazon).
    Two adapters is the seam; three would be the validation. Build
    for two, leave the third as a future spec.
  - Replacing `print` with structured logging — separate cleanup, not
    blocked by this refactor.
  - Touching the `automatic_table` / `automatic_apple_table` schemas.
  - Touching the GitHub Actions workflows or `ops/scripts/weekly*.py`
    wrappers. Their import paths and the entrypoint function names
    are preserved.

## Decisions

### Why one module, not two
Both job files implement the same loop:
`for each item → check_*_id() → if hit, bump date and skip; if miss,
ingest → *Clean() → extractInsights() → json.loads → list-vs-dict
normalization → empty-problems guard → fan out per-problem rows →
call update_automatic_*_trend()`.

[app/jobs/automaticYoutube.py:11-71](app/jobs/automaticYoutube.py#L11-L71)
and
[app/jobs/automaticAppStore.py:15-78](app/jobs/automaticAppStore.py#L15-L78)
are nearly line-identical conditionals. Two shallow jobs sitting in
front of two near-identical bodies. Apply the deletion test: delete
one of them, and the same ~50 lines of guard logic reappear elsewhere
— that complexity wants one home.

Three concrete bugs the duplication is currently hiding or doubling:

- The `if trend_data:` check at
  [automaticYoutube.py:67](app/jobs/automaticYoutube.py#L67) and
  [automaticAppStore.py:74](app/jobs/automaticAppStore.py#L74) is
  always truthy — `trend_data` is built unconditionally one line
  above with `trend_data.append({...})`. The check has never gated a
  write. A fix has to land twice today.
- The `isinstance(data, list)` normalization is duplicated character-
  for-character. Any change to LLM output handling has to be
  remembered in two places.
- The `len(cleaned_data) <= 0` guard prints a misleading
  `"no problems found"` (problems aren't extracted yet at that
  point) — duplicated. Fixable in one place once collapsed.

### Adapter shape
The adapter is the seam. It captures everything that differs between
YouTube and App Store; the pipeline keeps everything that doesn't.

```python
# app/jobs/automaticPipeline.py
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class SourceAdapter:
    item_id: Callable[[dict], Any]              # item -> id used for check_* + logging
    check_existing: Callable[[Any], list | dict | None]  # already-persisted? returns rows or falsy
    bump_date: Callable[[Any, str], None]       # update *_date(id, today)
    ingest: Callable[[dict], list]              # raw comments / reviews
    clean: Callable[[list, list[str]], list]    # cleaned text list
    system_prompt: str                          # per-source/per-category system prompt
    output_prompt: str                          # per-source output-shape prompt
    build_row: Callable[[dict, dict, str], dict] # (item, problem, today) -> trend_data row
    persist_row: Callable[[list[dict]], None]   # update_automatic_*_trend(trend_data)
```

The choice of a frozen dataclass of callables (vs. an ABC subclass
per source) is deliberate: the adapters are wiring, not behavior with
state. A dataclass keeps the call sites in the shell modules
declarative — the YouTube shell reads as a list of "here's how
YouTube does each step," not as a class hierarchy. Mirrors the same
posture as the per-source Supabase helpers in the persistence ADR:
keep the call site explicit.

`keywords` stays a runtime argument to the pipeline (not baked into
the adapter) because it varies per category/genre within a single
source — the YouTube shell threads `GAME_KEYWORDS` /
`SCIENCE_TECH_KEYWORDS` / `HOWTO_STYLE_KEYWORDS` through the same
adapter. Same for App Store: one adapter, three genre prompts and
keyword lists wired by `ops/scripts/weeklyAppStore.py`.

### Pipeline signature
```python
def run_automatic_pipeline(
    items: list[dict],
    keywords: list[str],
    adapter: SourceAdapter,
) -> list[dict]:
    today = str(getCurrentDate())
    page_data = []
    for item in items:
        item_id = adapter.item_id(item)
        existing = adapter.check_existing(item_id)
        if existing:
            adapter.bump_date(item_id, today)
            page_data.append(existing)
            continue

        raw = adapter.ingest(item)
        cleaned = adapter.clean(raw, keywords)
        if not cleaned:
            continue

        insights = extractInsights(cleaned, adapter.system_prompt, adapter.output_prompt)
        data = json.loads(insights)
        if isinstance(data, list):
            if not data:
                continue
            data = data[0]
        if not data.get("problems"):
            continue

        for problem in data["problems"]:
            row = [adapter.build_row(item, problem, today, data)]
            adapter.persist_row(row)
            page_data.append(row)
    return page_data
```

Notes on the signature:
- `extractInsights` stays imported by the pipeline directly. It is
  the one piece of behavior that is genuinely identical across
  sources (same OpenAI client, same JSON-mode call). Hiding it
  behind the adapter would be ceremony, not a seam.
- `getCurrentDate()` lives in the pipeline, not the adapter. Date
  source is a global concern, not a per-source one.
- `build_row` takes `(item, problem, today, data)` — the YouTube row
  needs `data["title"]` (from the LLM), the App Store row does not.
  Pass the full `data` dict and let each adapter pick what it needs.
  This is the smallest contract that covers both call sites without
  forcing a synthetic field on Apple.

### What the YouTube shell looks like after
```python
# app/jobs/automaticYoutube.py — full file, ~25 lines
from app.jobs.automaticPipeline import run_automatic_pipeline, SourceAdapter
from app.ingestion.youtubeComments import getYoutubeComments
from app.preprocessing.commentClean import loadAndClean
from app.config.prompts import youtubePromptOutput
from app.clients.supabase import (
    update_automatic_trend,
    check_youtube_id,
    update_automatic_video_date,
)

def youtube_automatic(ids, category, categoryPrompt, keywords):
    adapter = SourceAdapter(
        item_id=lambda item: item["Id"],
        check_existing=check_youtube_id,
        bump_date=update_automatic_video_date,
        ingest=lambda item: getYoutubeComments(item["Id"], "relevance", item["Title"]),
        clean=loadAndClean,
        system_prompt=categoryPrompt,
        output_prompt=youtubePromptOutput,
        build_row=lambda item, problem, today, data: {
            "key": item["Id"],
            "thumbnail": item["Thumbnail"],
            "date": today,
            "category": category,
            "title": data["title"],
            "problems": {
                "problem": problem["problem"],
                "type": problem["type"],
                "total_likes": problem["total_likes"],
                "severity": problem["severity"],
                "frequency": problem["frequency"],
            },
        },
        persist_row=update_automatic_trend,
    )
    return run_automatic_pipeline(ids, keywords, adapter)
```

The App Store shell is the same shape with `check_appstore_id`,
`update_automatic_app_date`, `getAppReviews`/`appReviewClean`,
`appStorePromptOutput`, the Apple `build_row`, and
`update_automatic_apple_trend`.

### ADR check — persistence helpers stay separate
[planning/decisions/2026-05-05-app-store-insight-persistence.md](planning/decisions/2026-05-05-app-store-insight-persistence.md)
tradeoff #4 explicitly rejected parameterizing the Supabase helpers
because a `table_name` argument hides which table is read at the
call site. This spec respects that: `update_automatic_trend` and
`update_automatic_apple_trend` remain distinct functions. The
adapter wires them by reference; the pipeline never sees a table
name. Same for `check_youtube_id` / `check_appstore_id` and
`update_automatic_video_date` / `update_automatic_app_date`.

The ADR did not speak to the job-loop logic, only to the
helpers. Collapsing the loop is orthogonal to its conclusion.

### What gets fixed along the way
- `if trend_data:` deleted (always truthy — see Why one module
  above). One-line behavior change, captured here so it doesn't
  surprise a reviewer who diffs the shells against the originals.
- `cleaned_data` empty-skip log message rewritten from
  `"due to no problems found"` to `"due to empty cleaned data"` —
  the old message is wrong (problems haven't been extracted yet).
  Trivial, but worth doing while the line is moving.
- Print statements stay verbatim otherwise. The logging migration
  is a separate cleanup and should not get smuggled in here.

### What about a third source
The PRD hints at Reddit/Amazon. Resist the urge to design for them
in this spec. The adapter contract above covers the two real call
sites. If Reddit lands and exposes a meaningfully different shape
(streaming ingestion, multi-pass extraction, whatever), that's the
moment to evolve the contract — with the third call site in hand to
validate the change. Two-instance generalizations are exactly the
right size; three-instance generalizations done in advance are how
the ABC hierarchy gets ahead of reality.

## Verification

Pre-merge checks (run from repo root):
- `pytest tests/jobs/test_automaticPipeline.py` — new tests pass.
- `pytest tests/jobs/test_automaticYoutube_layout.py` — existing
  layout test still passes (`youtube_automatic` still importable
  from `app.jobs.automaticYoutube`, `ops.scripts.weeklyYoutube.main`
  still callable).
- `pytest` — full suite green.
- `python -m ops.scripts.weeklyYoutube` against a scratch
  `automatic_table` (or with the Supabase writes mocked at the
  client boundary) — produces the same row shape as before. Diff
  the rows against the pre-refactor output for at least one video.
- Same for `python -m ops.scripts.weeklyAppStore`.

Post-merge: the next scheduled Sunday cron firings (08:00 UTC
YouTube, 08:30 UTC App Store) land rows in the same tables with the
same shape. The `check_*_id` short-circuits make a same-day re-run
safe, so a manual `workflow_dispatch` on `master` immediately after
merge is the cheapest live confirmation.

## Acceptance

- [ ] `app/jobs/automaticPipeline.py` exists with
      `run_automatic_pipeline(items, keywords, adapter)` and a
      `SourceAdapter` dataclass exposing the six callables + two
      prompt strings listed in Decisions → Adapter shape.
- [ ] `app/jobs/automaticYoutube.py` is reduced to a shell that
      builds the adapter and calls `run_automatic_pipeline`. Public
      signature `youtube_automatic(ids, category, categoryPrompt,
      keywords)` unchanged.
- [ ] `app/jobs/automaticAppStore.py` is reduced to a shell that
      builds the adapter and calls `run_automatic_pipeline`. Public
      signature `appstore_automatic(apps, genre_id, genre_prompt,
      keywords)` unchanged.
- [ ] The always-truthy `if trend_data:` guard is gone from both
      shells (and not present in the pipeline).
- [ ] `tests/jobs/test_automaticPipeline.py` exists and exercises,
      against a fake adapter:
      - existing-id short-circuit calls `bump_date` and appends the
        existing rows to the return value;
      - empty `clean()` output skips the item with no
        `extractInsights` call;
      - `data` returned as a single-element list is normalized to
        `data[0]`;
      - `data` returned as an empty list skips the item;
      - `data["problems"]` empty/missing skips the item;
      - non-empty problems trigger one `build_row` + one
        `persist_row` call per problem;
      - return value is the list of persisted rows in order.
- [ ] `tests/jobs/test_automaticYoutube_layout.py` still passes
      unchanged.
- [ ] `pytest` full suite green.
- [ ] No call site imports `update_automatic_trend` /
      `update_automatic_apple_trend` /  `check_youtube_id` /
      `check_appstore_id` /
      `update_automatic_video_date` /
      `update_automatic_app_date` with a `table_name` argument or
      from a parameterized helper. The ADR's "no table-name arg"
      constraint holds.
- [ ] Manual `workflow_dispatch` on `master` after merge: both
      `weekly-youtube` and `weekly-appstore` workflows produce green
      runs and land rows in their respective tables.
