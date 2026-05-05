---
name: Genre Config Registry
description: Replace per-genre prompt/keyword constants with a single declarative genre registry plus a templated prompt builder, so adding a new YouTube category or App Store genre is a one-place change.
type: spec
---

# Genre Config Registry — Spec

## Goal
Adding a new YouTube category or App Store genre should be **one entry
in one file**. Today it requires editing
[app/config/keywords.py](app/config/keywords.py),
[app/config/prompts.py](app/config/prompts.py),
[app/config/constants.py](app/config/constants.py), and the matching
weekly script under [ops/scripts/](ops/scripts/) — and the prompts
themselves duplicate ~80% of their text across genres.

This spec replaces the current sprawl with:
1. A **genre registry** (`app/config/genres.py`) holding a `GenreConfig`
   per category/genre — id, name, keywords, and the unique
   prompt fragment.
2. A **prompt builder** that composes a system prompt from shared parts
   (intro, input shape, scoring rubric, output rules) plus the
   genre-specific theme list. No more 100-line copy-paste per genre.
3. Weekly scripts that iterate `GENRES` directly — no per-genre imports.

## Scope
- In:
  - New `app/config/genres.py` defining `GenreConfig` and the registries
    (`YOUTUBE_GENRES`, `APPSTORE_GENRES`).
  - New `app/config/promptTemplates.py` (or extend `prompts.py`) with the
    shared scaffolding + `build_youtube_prompt(fragment)` /
    `build_appstore_prompt(fragment)` functions.
  - Migrate the four YouTube prompts and four App Store prompts to
    `(theme_list, exclusion_list)` fragments under each `GenreConfig`.
  - Move keyword lists into the matching `GenreConfig.keywords` field.
  - Update [ops/scripts/weeklyYoutube.py](ops/scripts/weeklyYoutube.py)
    and [ops/scripts/weeklyAppStore.py](ops/scripts/weeklyAppStore.py)
    to iterate the registry instead of hand-assembled tuples.
  - Keep the manual analysis paths
    ([app/services/youtube_service.py](app/services/youtube_service.py),
    [app/services/appstore_service.py](app/services/appstore_service.py))
    working — they use the generic prompts, which become a "default"
    `GenreConfig` (or stay as a base prompt the builder produces with
    no genre fragment).
  - Snapshot tests verifying built prompts match current ones
    semantically (see Acceptance).
- Out:
  - Changing what the prompts *say* — this is a structural refactor.
    Wording differences caught by snapshot tests should be reconciled
    to the existing prompt as the source of truth.
  - Changing keyword contents (no curation pass — same words, new home).
  - Per-source schema changes in `automatic_table` /
    `apple_automatic_table`.
  - Frontend changes.
  - Dynamic/AI-generated keyword expansion (out — possible follow-up
    once the registry exists).

## Current State
**Keywords** ([app/config/keywords.py](app/config/keywords.py)):
- `YOUTUBE_KEYWORDS` — generic YouTube list (manual `/analyze/youtube`).
- `APPLE_KEYWORDS` — generic Apple list (manual `/analyze/appStore` AND
  all three weekly App Store genres).
- `GAME_KEYWORDS`, `SCIENCE_TECH_KEYWORDS`, `HOWTO_STYLE_KEYWORDS` —
  per-category YouTube lists (used only by the weekly job).

**Prompts** ([app/config/prompts.py](app/config/prompts.py), ~390 lines):
- `youtubeSystemPrompt` (generic) + `youtubeGameSystemPrompt`,
  `youtubeScienceTechSystemPrompt`, `youtubeHowtoStyleSystemPrompt`.
- `appStoreSystemPrompt` (generic) + `appStoreGamesSystemPrompt`,
  `appStoreSocialSystemPrompt`, `appStoreUtilitiesSystemPrompt`.
- `youtubePromptOutput`, `appStorePromptOutput` (output-format rules).
- The four YouTube genre prompts share an identical intro
  ("You will receive a JSON array..."), task numbering, and rules
  block. Only the **theme bullets** and the **non-genre exclusion
  bullet** differ. Same pattern on the App Store side.

**Wiring** ([ops/scripts/weeklyYoutube.py:24-28](ops/scripts/weeklyYoutube.py#L24-L28),
[ops/scripts/weeklyAppStore.py:19-23](ops/scripts/weeklyAppStore.py#L19-L23)):
```python
CATEGORIES = [
    ("Games", GAME_CATEGORY_ID, youtubeGameSystemPrompt, GAME_KEYWORDS),
    ("Science & Tech", SCIENCE_TECH_ID, youtubeScienceTechSystemPrompt, SCIENCE_TECH_KEYWORDS),
    ("How-to & Style", HOW_TO_STYLE_ID, youtubeHowtoStyleSystemPrompt, HOWTO_STYLE_KEYWORDS),
]
```
Adding "Music" requires four imports plus a tuple here, plus new
constants and prompt and keyword list elsewhere.

**Job signatures** ([app/jobs/automaticYoutube.py:11](app/jobs/automaticYoutube.py#L11),
[app/jobs/automaticAppStore.py:15](app/jobs/automaticAppStore.py#L15))
already accept `(category, categoryPrompt, keywords)` — the registry
fits the existing call shape with zero job-internal refactor.

## Data Contract

### `GenreConfig` dataclass
File: `app/config/genres.py`
```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class GenreConfig:
    name: str                    # e.g. "Games", "Social Networking"
    source: str                  # "youtube" | "appstore"
    id: int                      # YouTube categoryId or Apple genreId
    keywords: tuple[str, ...]    # filter list for preprocessing
    theme_bullets: str           # genre-specific themes (Markdown bullets)
    exclusion_hint: str          # one-line "ignore X about the creator/dev" rider
    severity_hint: str           # one-line severity-5 anchor for this genre
```

The `theme_bullets` field is the *only* part that varied meaningfully
between today's prompt strings. The shared scaffolding (intro, input
fields, task numbering, scoring rubric, output rules) lives in the
template module.

### Registries
```python
YOUTUBE_GENRES: tuple[GenreConfig, ...] = (
    GenreConfig(name="Games", source="youtube", id=GAME_CATEGORY_ID, ...),
    GenreConfig(name="Science & Tech", source="youtube", id=SCIENCE_TECH_ID, ...),
    GenreConfig(name="How-to & Style", source="youtube", id=HOW_TO_STYLE_ID, ...),
)

APPSTORE_GENRES: tuple[GenreConfig, ...] = (
    GenreConfig(name="Games", source="appstore", id=APPLE_GAMES_GENRE_ID, ...),
    GenreConfig(name="Social Networking", source="appstore", id=APPLE_SOCIAL_GENRE_ID, ...),
    GenreConfig(name="Utilities", source="appstore", id=APPLE_UTILITIES_GENRE_ID, ...),
)
```

A lookup helper for any code that has only an id:
```python
def get_genre(source: str, id: int) -> GenreConfig: ...
```

### Prompt builder
File: `app/config/promptTemplates.py`
```python
def build_youtube_prompt(genre: GenreConfig) -> str:
    return YOUTUBE_PROMPT_TEMPLATE.format(
        themes=genre.theme_bullets,
        exclusion=genre.exclusion_hint,
        severity_anchor=genre.severity_hint,
    )

def build_appstore_prompt(genre: GenreConfig) -> str: ...
```

`YOUTUBE_PROMPT_TEMPLATE` is the shared scaffold (intro, input shape,
numbered task list, output fields, rules) with `{themes}`,
`{exclusion}`, `{severity_anchor}` placeholders. Same for App Store.

The generic (non-genre) prompts used by manual analysis become either
(a) a "default" `GenreConfig` with broad theme_bullets, or
(b) the result of `build_*_prompt(None)` which skips the theme section.
Pick (a) — keeps the codepath uniform and lets manual analysis benefit
from the same scoring rubric updates.

## Backend Changes

### New files
- **`app/config/genres.py`** — `GenreConfig` dataclass, `YOUTUBE_GENRES`,
  `APPSTORE_GENRES`, `get_genre()`. Imports
  `GAME_CATEGORY_ID` / `SCIENCE_TECH_ID` / `HOW_TO_STYLE_ID` /
  `APPLE_*_GENRE_ID` from `constants.py`.
- **`app/config/promptTemplates.py`** — `YOUTUBE_PROMPT_TEMPLATE`,
  `APPSTORE_PROMPT_TEMPLATE`, `build_youtube_prompt()`,
  `build_appstore_prompt()`, plus the existing
  `youtubePromptOutput` / `appStorePromptOutput` (move them here too,
  or re-export from `prompts.py` for compatibility).

### Modified files
- **`app/config/keywords.py`** — delete the per-genre lists once they're
  inlined into `GenreConfig.keywords`. Keep `YOUTUBE_KEYWORDS` and
  `APPLE_KEYWORDS` only if the manual paths still need them as a
  default; otherwise also fold those into a "default" `GenreConfig`
  and delete the file.
- **`app/config/prompts.py`** — delete the eight bespoke prompt strings.
  Keep the file only if `youtubePromptOutput` / `appStorePromptOutput`
  stay here. Otherwise delete.
- **`app/services/youtube_service.py`** — replace
  `youtubeSystemPrompt` + `YOUTUBE_KEYWORDS` imports with a call to
  the default-genre helper, e.g.:
  ```python
  default = get_default_genre("youtube")
  cleaned = loadAndClean(items, default.keywords)
  insights = extractInsights(cleaned, build_youtube_prompt(default), youtubePromptOutput)
  ```
- **`app/services/appstore_service.py`** — same shape.
- **`ops/scripts/weeklyYoutube.py`** — replace the `CATEGORIES` tuple
  with iteration over `YOUTUBE_GENRES`:
  ```python
  for genre in YOUTUBE_GENRES:
      videos = getMostPopularVideos(genre.id)
      rows = youtube_automatic(videos, genre.id, build_youtube_prompt(genre), genre.keywords)
  ```
- **`ops/scripts/weeklyAppStore.py`** — same shape with
  `APPSTORE_GENRES` and `build_appstore_prompt`.

### Untouched
- `app/jobs/automaticYoutube.py`, `app/jobs/automaticAppStore.py` —
  signatures already take `(prompt, keywords)`. No change.
- `app/llm/extractInsights.py` — receives the built prompt as before.
- Supabase clients, ingestion, preprocessing — unaffected.

## Migration Strategy
1. Land `genres.py` and `promptTemplates.py` alongside the existing
   constants. Build prompts and assert they match the existing strings
   (modulo whitespace) via a test (see Acceptance).
2. Switch `ops/scripts/weeklyYoutube.py` and `weeklyAppStore.py` to the
   registry. Run both manually (or wait for the next Sunday cron) and
   confirm the output rows match the prior week's shape.
3. Switch the manual services. Smoke-test `/analyze/youtube` and
   `/analyze/appStore`.
4. Delete the now-unused constants from `keywords.py` and `prompts.py`.
5. Update [planning/CONTEXT.md](planning/CONTEXT.md) "Architectural
   Principles" line about config to reference the registry.

Each step is independently mergeable; step 4 is the only destructive
one and should land after one full Sunday run on the registry path.

## Failure Modes
- **Prompt drift after templating**: built prompt subtly differs from
  hand-written original (extra newline, missing rule). Mitigated by the
  snapshot test in step 1 — diff must be inspected and either the
  template or the fragment adjusted before deletion in step 4.
- **Forgotten import in weekly script**: caught immediately on next run
  (ImportError fails the GitHub Action and shows in the summary).
- **Manual analysis path regression**: covered by the smoke test in
  step 3; both endpoints exercise `extractInsights` end-to-end.
- **New genre added without keywords**: `GenreConfig` is `frozen` and
  `keywords` is required — adding a genre without keywords fails at
  module-import time, not at runtime mid-cron.

## Acceptance
- [ ] `app/config/genres.py` exists with `GenreConfig`,
      `YOUTUBE_GENRES`, `APPSTORE_GENRES`, `get_genre()`.
- [ ] `app/config/promptTemplates.py` exists with
      `build_youtube_prompt` and `build_appstore_prompt`.
- [ ] Snapshot test under `tests/config/test_prompt_templates.py`
      asserts that
      `build_youtube_prompt(GAMES_GENRE) == youtubeGameSystemPrompt`
      (whitespace-normalized) for all six existing genre prompts.
      This test is added *before* deletion in step 4 and stays as a
      regression guard against future template edits.
- [ ] `ops/scripts/weeklyYoutube.py` imports only `YOUTUBE_GENRES` +
      `build_youtube_prompt` + `youtube_automatic` (no per-genre
      prompt or keyword imports).
- [ ] Same shape on `weeklyAppStore.py`.
- [ ] Manual `/analyze/youtube` and `/analyze/appStore` continue to
      return the existing JSON shape on a fixture URL.
- [ ] One Sunday run on the registry path produces the same number of
      `automatic_table` and `apple_automatic_table` rows as the prior
      week (±expected drift from new top videos/apps).
- [ ] `app/config/keywords.py` and `app/config/prompts.py` either
      deleted or reduced to only the output-format constants.
- [ ] Adding a hypothetical "Music" YouTube category requires editing
      *only* `genres.py` and `constants.py` (verified by grep — no
      changes to `prompts.py`, `keywords.py`, or `weeklyYoutube.py`).

## Open Questions
- Should the keyword list itself be templated (shared base + per-genre
  additions), or kept as a flat per-genre list? Today
  `APPLE_KEYWORDS` is shared across all three App Store genres — this
  is either an oversight or an intentional default. **Decision needed
  before step 1**: keep flat (simpler, current behavior), or introduce
  `keywords = BASE_APPLE_KEYWORDS + GAMES_EXTRAS` composition.
- Where do `youtubePromptOutput` / `appStorePromptOutput` live —
  `promptTemplates.py` or a small remaining `prompts.py`? Lean toward
  folding them into `promptTemplates.py` and deleting `prompts.py`.
- Should manual `/analyze/youtube` accept an optional category and
  route to the matching `GenreConfig`? Out of scope here, but the
  registry makes it a one-line change later.
- Future: dynamic keyword expansion (LLM-suggested additions per
  genre) — the registry is the natural seam for this. Track as
  follow-up.
