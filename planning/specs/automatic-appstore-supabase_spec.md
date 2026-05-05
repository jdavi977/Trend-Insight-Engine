---
name: Automatic App Store Pipeline with Supabase Persistence
description: Mirror the weekly YouTube job for App Store reviews — fetch top apps per Apple genre, run reviews through clean → extract → persist into a new automatic_apple_table in Supabase.
type: spec
---

# Automatic App Store → Supabase — Spec

## Goal
Stand up a weekly App Store equivalent of `automaticYoutube.py` so top
apps per Apple genre are pulled, their reviews cleaned, insights
extracted via OpenAI, and persisted to a new `automatic_apple_table` in
Supabase — without a human in the loop. This unblocks the App Store
half of the RAG pipeline (PRD §3.1) by giving the embedder a relational
source of truth to read from.

## Scope
- In:
  - New iTunes RSS top-apps client call in [app/clients/appstore.py](app/clients/appstore.py).
  - New `app/jobs/automaticAppStore.py` modeled on
    [app/jobs/automaticYoutube.py](app/jobs/automaticYoutube.py).
  - New Supabase table `automatic_apple_table` and matching writer/idempotency
    helpers in [app/clients/supabase.py](app/clients/supabase.py).
  - New genre-ID constants and a per-genre system-prompt set.
  - New orchestration wrapper `ops/scripts/weeklyAppStore.py`.
  - New scheduled GitHub Actions workflow
    `.github/workflows/weekly-appstore.yml`.
  - Genres in v1: **Games (6014)**, **Social Networking (6005)**,
    **Utilities (6002)**.
- Out:
  - Wiring the manual `/analyze/appStore` endpoint to persist — explicitly
    deferred. Manual analysis stays ephemeral for now.
  - Frontend changes (Insights page rendering of Apple rows comes under a
    separate spec).
  - Backfill of historical Apple data.
  - The RAG embedder itself — this spec only produces the rows the
    embedder will read.
  - YouTube path changes.

## Decisions

### Persistence target: new `automatic_apple_table` (Option 1 of the ADR)
Hard assumption coming out of [planning/decisions/2026-05-05-app-store-insight-persistence.md](planning/decisions/2026-05-05-app-store-insight-persistence.md):
Apple insights write to Supabase, not Chroma-as-truth. A **separate**
table — `automatic_apple_table` — rather than overloading the existing
`automatic_table`, because:
- Apple rows have fields YouTube doesn't (`average_rating`,
  `example_reviews`, `app_id`, `country`) and YouTube rows have fields
  Apple doesn't (`thumbnail`, `total_likes`). Sharing a table forces
  both into nullable columns and a `source` discriminator that every
  read has to filter on.
- The existing `check_youtube_id` / `update_automatic_video_date` /
  `get_weekly_ids` helpers in [app/clients/supabase.py](app/clients/supabase.py)
  hardcode `"automatic_table"` and a `category` column shaped for
  YouTube category IDs; reusing them means broadening their semantics
  for both sources, which is exactly the kind of "force symmetry"
  trap the ADR's tradeoffs section flagged.
- Apple genre IDs (4-digit, e.g. 6014) collide visually but not
  numerically with YouTube category IDs (2-digit, e.g. 20). A single
  `category` column with mixed namespaces is a future-bug magnet.

The ADR's "Closes off" implication still holds: any *future* source
(Reddit, Amazon) follows this same pattern — its own table, its own
client helpers, no shared discriminator column.

### Top-apps source: legacy `itunes.apple.com` RSS, with sibling ADR for the deprecation risk
The endpoint
`https://itunes.apple.com/{country}/rss/topfreeapplications/limit={N}/genre={genreId}/json`
is the only public surface that gives **per-genre** top apps today.
The newer `rss.applemarketingtools.com` feed dropped per-genre
slicing and is mostly Apple Music/Books/Podcasts — unusable for this
pipeline. We build on the legacy feed knowing it's officially
deprecated.

**Prerequisite work for this spec:** a sibling ADR
`planning/decisions/YYYY-MM-DD-itunes-rss-top-apps-deprecation.md`
recording (a) why the deprecated feed was chosen, (b) what breaks if
Apple turns it off (the weekly job stops producing rows; manual
`/analyze/appStore` is unaffected since it uses the still-live reviews
RSS), and (c) the fallback options when that day comes (scrape the
public charts page, switch to the marketing-tools feed and lose genre
slicing, or pin a curated app-ID list per genre and abandon top-charts
entirely). Treat the ADR as a deliverable of this spec, not a
follow-up — the spec should not merge without it.

The client call lives in [app/clients/appstore.py](app/clients/appstore.py)
as `list_top_apps(genre_id: int, country: str = "us", limit: int = 5)`,
parallel in shape to the existing `fetch_reviews_page`. It returns a
list of `{Id, Title, Artist}` dicts so `automaticAppStore.py` can mirror
the YouTube job's `id['Id']` / `id['Title']` access pattern. No
thumbnail field — Apple's RSS does include `im:image`, but the
weekly-thumbnails feature is a YouTube-only spec and Apple thumbnails
are out of scope here. Add the field to the returned dict anyway
(`Thumbnail` set to the largest `im:image` URL) so downstream consumers
can opt in later without re-shaping the client.

### Job entrypoint: new `app/jobs/automaticAppStore.py`
A direct mirror of [app/jobs/automaticYoutube.py](app/jobs/automaticYoutube.py).
Signature:

```python
def appstore_automatic(
    apps: list[dict],   # [{Id, Title, Artist, Thumbnail}]
    genre_id: int,
    genre_prompt: str,
    keywords: list[str],
) -> list[dict]
```

Per-app loop:
1. `check_appstore_id(app['Id'])` — short-circuit + bump `date` if the
   app was already processed for this Sunday (mirror of
   `check_youtube_id` + `update_automatic_video_date`).
2. `getAppReviews(app['Id'], "mostrecent", APP_REVIEW_PAGES)` from
   [app/ingestion/appStoreReviews.py](app/ingestion/appStoreReviews.py).
3. `loadAndCleanReviews(reviews, APPLE_KEYWORDS)` (or whatever the
   review-clean entrypoint is — confirm naming during implementation;
   the YouTube job calls `loadAndClean` from `commentClean.py`, the
   Apple equivalent should already exist in `preprocessing/reviewClean.py`).
4. `extractInsights(cleaned, genre_prompt, appStorePromptOutput)` —
   reuse the existing `appStorePromptOutput` from
   [app/config/prompts.py](app/config/prompts.py).
5. For each problem in the LLM output, build a `trend_data` row and
   call `update_automatic_apple_trend(...)`.

The function returns the list of persisted rows (same convention as
`youtube_automatic`) so the orchestration wrapper can count them for
the job summary.

### `automatic_apple_table` schema
Columns (Supabase table created out-of-band by the user — schema
migration is a manual prerequisite, same posture the YouTube table was
created with):

| Column          | Type      | Notes                                              |
|-----------------|-----------|----------------------------------------------------|
| `key`           | text PK   | `app_id` (e.g. `"284882215"`). Idempotency key.    |
| `app_id`        | text      | Same value as `key` — kept for query ergonomics.   |
| `app_title`     | text      | App display name from RSS.                         |
| `country`       | text      | ISO country code (`"us"` in v1).                   |
| `genre_id`      | int       | Apple genre ID (6014 / 6005 / 6002).               |
| `date`          | date      | Sunday of the run (UTC).                           |
| `thumbnail`     | text      | `im:image` URL, largest size. Nullable.            |
| `problems`      | jsonb     | `{problem, type, average_rating, severity, frequency, example_reviews}` |

One row per `(app_id, problem)` — same shape as YouTube where each
problem becomes its own row. Idempotency handled by `key` PK plus the
`check_appstore_id` short-circuit; re-running the same Sunday is a
no-op for already-processed apps and bumps `date` for ones first seen
this week.

### Supabase helpers
Add to [app/clients/supabase.py](app/clients/supabase.py), parallel to
the existing YouTube helpers:

- `update_automatic_apple_trend(data)` — insert into
  `automatic_apple_table`.
- `update_automatic_app_date(app_id, date)` — bump `date` on existing
  rows (mirror of `update_automatic_video_date`).
- `check_appstore_id(app_id)` — return existing rows or `[]` (mirror
  of `check_youtube_id`).
- `get_weekly_apple_ids(genre_id)` — for the future Insights-page
  reader (mirror of `get_weekly_ids`). Add now while the helpers are
  being touched; cheaper than a second round-trip.

Do **not** generalize the YouTube helpers to take a table name — the
small amount of duplication is preferable to a parameterized helper
that obscures which table is being read at the call site.

### Genre selection + per-genre prompts
v1 ships three genres, chosen to cover the breadth of complaint
patterns the existing [APPLE_KEYWORDS](app/config/keywords.py) list
already targets:

- **Games (6014)** — gameplay, monetization, progression complaints.
- **Social Networking (6005)** — moderation, privacy, notification
  fatigue.
- **Utilities (6002)** — reliability, sync, subscription friction.

Each genre gets its own system prompt (mirror of
`youtubeGameSystemPrompt` / `youtubeScienceTechSystemPrompt` /
`youtubeHowtoStyleSystemPrompt`):

- `appStoreGamesSystemPrompt`
- `appStoreSocialSystemPrompt`
- `appStoreUtilitiesSystemPrompt`

All three reuse `appStorePromptOutput` for output shape, identical to
how the YouTube prompts share `youtubePromptOutput`. The existing
generic `appStoreSystemPrompt` stays in place for the manual
`/analyze/appStore` endpoint — do not delete it, do not retrofit
manual analysis to use the genre prompts (out of scope).

New constants in [app/config/constants.py](app/config/constants.py):

```python
APPLE_GAMES_GENRE_ID = 6014
APPLE_SOCIAL_GENRE_ID = 6005
APPLE_UTILITIES_GENRE_ID = 6002
APPLE_TOP_APPS_LIMIT = 5
APPLE_COUNTRY = "us"
```

`APPLE_TOP_APPS_LIMIT = 5` matches the YouTube cap so the cost
envelope is symmetric: 5 apps × 3 genres × 10 review pages × 1 OpenAI
call = 15 OpenAI calls/run, same as YouTube.

### Orchestration: `ops/scripts/weeklyAppStore.py`
Direct mirror of [ops/scripts/weeklyYoutube.py](ops/scripts/weeklyYoutube.py).
A `GENRES` tuple list of `(name, genre_id, prompt, keywords)`,
per-genre `try/except` isolation, exit 1 if any genre raised, and the
same `$GITHUB_STEP_SUMMARY` Markdown table (columns: Genre / Status /
Apps / Rows / Error). Keywords list is `APPLE_KEYWORDS` for all three
genres in v1 — splitting per-genre keyword lists is a future tuning
knob, not a v1 requirement.

The 5/genre cap is enforced **upstream** in `list_top_apps` by passing
`limit=APPLE_TOP_APPS_LIMIT`, mirroring how `getMostPopularVideos`
enforces `maxResults=5`. No slice in the wrapper.

### Workflow: `.github/workflows/weekly-appstore.yml`
Direct copy of [.github/workflows/weekly-youtube.yml](.github/workflows/weekly-youtube.yml)
with these deltas:
- `name: Weekly App Store Pipeline`
- `concurrency.group: weekly-appstore` (so this workflow never blocks
  or gets blocked by the YouTube one).
- `cron: '30 8 * * 0'` — same Sunday, **30 minutes after** the YouTube
  job starts. Two reasons: (a) avoids both jobs hitting Supabase
  inserts and OpenAI rate limits at the same instant, (b) if both
  fail, the failure emails arrive in two distinguishable threads. The
  YouTube job's 30min timeout means the Apple job may briefly overlap
  it on a slow week, which is fine — they write to different tables
  and use different external APIs.
- Env vars: `OPENAI_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.
  **No `YOUTUBE_API` and no Apple-side credential** — the iTunes RSS
  endpoints are unauthenticated, which is also the reason the
  deprecation risk is real (Apple has no business relationship to
  preserve).
- Entrypoint: `python -m ops.scripts.weeklyAppStore`.
- Same `permissions: contents: read`, same `cancel-in-progress: false`,
  same `timeout-minutes: 30`, same `ubuntu-24.04`, same Python 3.14
  pin.

The public-repo secret-leak warning in [planning/specs/weekly-cron_spec.md](planning/specs/weekly-cron_spec.md)
applies identically here — re-read that section before adding any
PR-triggered workflow that touches secrets.

### Failure handling, observability, concurrency
Inherit verbatim from the YouTube spec:
- `print` stays for v1 — the logging migration is a separate cleanup.
- Per-genre `try/except` in the wrapper, exit code propagates, default
  GitHub scheduled-workflow failure email is the alerting channel.
- `$GITHUB_STEP_SUMMARY` markdown block per run.
- Concurrency group `weekly-appstore` with `cancel-in-progress: false`
  for the same partial-state-on-Supabase reason.

### Cost & quota
- Hard cap: 5 apps × 3 genres × 1 OpenAI call/app = 15 calls/run.
  Identical envelope to YouTube. Combined weekly OpenAI envelope after
  this lands: ~30 calls/Sunday, well inside the existing $25/month
  dashboard hard cap.
- iTunes RSS has no documented quota but is rate-sensitive; the
  per-app review fetch already loops `APP_REVIEW_PAGES = 10` pages
  with no sleep. If the weekly run starts hitting non-200s mid-loop
  (visible in the run log), a `time.sleep(0.5)` between pages is the
  first knob to tune — but do not pre-emptively add it in v1.

## Verification

Pre-merge dry-run: push the workflow on a feature branch, trigger via
`workflow_dispatch` against that branch with the real production
secrets. Writes go to the real `automatic_apple_table`; this is
acceptable because `check_appstore_id` makes the eventual scheduled
run a no-op on those rows (same rationale as the YouTube spec).

Post-merge: manually trigger the workflow once on `master` before the
first scheduled Sunday so the first cron firing isn't the first real
run.

## Acceptance

- [ ] Sibling ADR `planning/decisions/YYYY-MM-DD-itunes-rss-top-apps-deprecation.md`
      written and Status: Accepted before this spec merges.
- [ ] Persistence ADR [2026-05-05-app-store-insight-persistence.md](planning/decisions/2026-05-05-app-store-insight-persistence.md)
      moved from Draft → Accepted with Option 1 selected.
- [ ] `automatic_apple_table` created in Supabase with the schema
      above.
- [ ] `app/clients/appstore.py` exposes
      `list_top_apps(genre_id, country, limit)` against the legacy
      `topfreeapplications/genre={id}/json` endpoint.
- [ ] `app/clients/supabase.py` exposes
      `update_automatic_apple_trend`, `update_automatic_app_date`,
      `check_appstore_id`, `get_weekly_apple_ids`.
- [ ] `app/config/constants.py` has the three Apple genre IDs +
      `APPLE_TOP_APPS_LIMIT` + `APPLE_COUNTRY`.
- [ ] `app/config/prompts.py` has `appStoreGamesSystemPrompt`,
      `appStoreSocialSystemPrompt`, `appStoreUtilitiesSystemPrompt`.
- [ ] `app/jobs/automaticAppStore.py` exists with
      `appstore_automatic(apps, genre_id, prompt, keywords)`.
- [ ] `ops/scripts/weeklyAppStore.py` exists and runs all 3 genres
      with per-genre failure isolation + GITHUB_STEP_SUMMARY block.
- [ ] `.github/workflows/weekly-appstore.yml` exists with
      `cron: '30 8 * * 0'` + `workflow_dispatch`,
      `permissions: contents: read`, `concurrency.group: weekly-appstore`
      with `cancel-in-progress: false`, `timeout-minutes: 30`,
      `actions/setup-python@v5` pinned to 3.14, runner pinned to
      `ubuntu-24.04`.
- [ ] Branch dry-run via `workflow_dispatch` produced a green Action
      and rows landed in `automatic_apple_table`.
- [ ] Per-genre failure isolation verified (deliberately break one
      genre — bad genre id or bad prompt — and confirm the wrapper
      continues to the next genre, exits 1 at the end).
- [ ] Post-merge manual `workflow_dispatch` on `master` succeeds
      before the first scheduled Sunday.
- [ ] First scheduled Sunday at 08:30 UTC lands rows in
      `automatic_apple_table` for all 3 genres.
