---
name: Weekly App Store Insights on Insights Page
description: Surface the weekly App Store insights persisted in automatic_apple_table on the Insights page via a source toggle (YouTube / App Store), a sibling /get/homePageAppStore endpoint, and a parallel browse-by-genre filter.
type: spec
---

# Weekly App Store Insights on Insights Page — Spec

## Goal
Make the rows landing in `automatic_apple_table` from the weekly App
Store pipeline ([planning/specs/automatic-appstore-supabase_spec.md](planning/specs/automatic-appstore-supabase_spec.md))
visible to a human on [frontend/src/InsightsPage.jsx](frontend/src/InsightsPage.jsx).
Today the data writes successfully every Sunday but has no read path —
this spec adds the API endpoint and the UI surface that closes that
loop.

## Scope
- In:
  - New sibling endpoint `GET /get/homePageAppStore` in
    [app/api/home.py](app/api/home.py) (or a new
    `app/api/homeAppStore.py` if the YouTube handler is left untouched
    — see Decisions).
  - A source toggle (YouTube / App Store) at the top of
    [frontend/src/InsightsPage.jsx](frontend/src/InsightsPage.jsx).
  - When App Store is selected: a parallel "Browse by Genre" pill row
    (Games / Social Networking / Utilities / All) and an app-row list
    that mirrors the existing video-row layout.
  - Apple deep-link per app: `https://apps.apple.com/us/app/id{app_id}`.
  - Per-problem `average_rating` rendered as a small badge on each
    problem bullet.
- Out:
  - Changes to [frontend/src/HomePage.jsx](frontend/src/HomePage.jsx) —
    Home stays YouTube-only for now. Adding Apple to the marketing
    surface is a separate decision.
  - Modifying the existing `/get/homePage` endpoint shape (additive
    sibling endpoint instead — see Decisions).
  - Manual `/analyze/appStore` rendering changes in
    [frontend/src/AppStorePage.jsx](frontend/src/AppStorePage.jsx).
  - Backfill or historical browsing — current-week Sunday only,
    matching the YouTube path.
  - Per-genre keyword/prompt UI configuration (the NOTES.md May-5 idea
    about consolidating per-genre prompts is its own future spec).
  - Routing changes (no new page; toggle lives inside InsightsPage).

## Decisions

### Surface: Insights page, not Home
Confirmed with the user. Home stays the marketing top-3 surface and
keeps its "Weekly YouTube Insights" hero. The Insights page is the
exhaustive browse surface and is the right place to add a second
source — its existing pill-filter pattern generalizes cleanly to a
second axis (source) above the existing axis (category).

### Layout: source toggle that swaps the whole list
A two-button toggle (YouTube / App Store) sits above the existing
"Browse by Category" section. Switching to App Store **replaces** the
category pills with genre pills (Games / Social Networking /
Utilities / All) and replaces the video rows with app rows. The two
sources are not interleaved. Rationale:
- Apple rows have fields YouTube doesn't (`average_rating`,
  `genre_id`, `app_id`, `country`) and YouTube rows have fields Apple
  doesn't (`thumbnail` shape, video-specific link). A merged grid
  would force symmetry the data doesn't have — same trap the
  persistence ADR flagged for the Supabase schema.
- The genre filter and the category filter share a UX (pills) but
  not a value space. Showing both simultaneously would imply a
  cross-product filter that doesn't exist.

The page title and section copy generalize: "Weekly Insights" /
"Browse by Category" → "Browse by Genre" when toggled.

Default tab on first load: **YouTube** (preserves current behavior;
nobody's muscle memory breaks). Toggle state is component-local React
state — no URL param, no localStorage in v1. If users start asking
for shareable links to a specific tab, add a query param later.

### API: sibling endpoint, not a shape change
New endpoint `GET /get/homePageAppStore` returning a
`list[list[dict]]` shaped identically to `/get/homePage`'s outer
shape — one inner list per Apple genre, in fixed order
(Games → Social Networking → Utilities). Reasons:
- Additive: the existing YouTube fetch on InsightsPage and on
  HomePage stays byte-identical. No coordinated frontend/backend
  deploy.
- Mirrors the per-source separation already established by the
  separate Supabase tables and the persistence ADR's "no shared
  discriminator" principle. The frontend has two fetches, two
  loading states, two error states — same pattern the backend has.
- Parallel-fetchable: when the toggle is added, both endpoints can
  be kicked off in `useEffect` simultaneously so flipping the toggle
  is instant after first load.

Implementation: place the new endpoint alongside the existing one in
[app/api/home.py](app/api/home.py) — the file is already named for
the home/insights read path and adding a second handler keeps the
two read paths colocated. Do **not** generalize
`get_home_data` to take a source param; the small duplication is
preferable to a parameterized handler that obscures which table is
being read.

The handler calls `get_weekly_apple_ids(genre_id)` (already exists in
[app/clients/supabase.py:54](app/clients/supabase.py#L54)) once per
genre, with the same per-genre `try/except` → `HTTPException 503`
shape the YouTube handler uses. Genre IDs come from
`app/config/constants.py` (`APPLE_GAMES_GENRE_ID`,
`APPLE_SOCIAL_GENRE_ID`, `APPLE_UTILITIES_GENRE_ID`).

### Card content per Apple row
Mirroring the existing YouTube `insights-row` structure:

- **Header (left):** thumbnail (the `im:image` URL stored in
  `automatic_apple_table.thumbnail`, falling back to the existing
  `--empty` placeholder when null), wrapped in an `<a>` to
  `https://apps.apple.com/{country}/app/id{app_id}` (target="_blank").
  `country` comes from the row (`"us"` in v1) so the link stays
  correct when more locales are added.
- **Title:** `app_title`.
- **Subtitle line:** genre label ("Games" / "Social Networking" /
  "Utilities") — replaces the date line, since every row shares the
  same Sunday `date` and the genre is the more useful at-a-glance
  field. Date can move into a tooltip or be dropped; v1 drops it.
- **Body:** "Common Issues Highlighted" heading (reuse existing
  copy), then a bulleted list of `problems.problem`. Each bullet gets
  a small inline rating badge sourced from `problems.average_rating`
  (e.g. `★ 2.3`). Use the existing `insights-detail-bullets` styles;
  the badge is a new `<span class="insights-rating-badge">` rendered
  only when `average_rating` is present.

`severity` and `frequency` are **not** rendered in v1 to keep the
visual delta vs. the YouTube row small. The frontend CONTEXT.md
"Insight Display Rules" call for severity/frequency 1–5 visual
scales — that's a follow-up spec covering both YouTube and App
Store rows together (they currently aren't shown for YouTube either,
so adding them only on Apple would be inconsistent).

### CSS reuse, no new design system
Reuse the existing `insights-row` / `insights-row-title` /
`insights-row-detail` classes verbatim — the layout is identical.
New classes added to [frontend/src/InsightsPage.css](frontend/src/InsightsPage.css):
- `insights-source-toggle` + `insights-source-button` (the
  YouTube/App Store toggle, styled similarly to `insights-pill` but
  visually distinct enough to read as a primary axis).
- `insights-rating-badge` (the per-problem star badge).

No new image assets — Apple thumbnails come from the RSS-provided
URL. If a row has a null thumbnail (early rows from the dry-run
that pre-dated the `Thumbnail` field), the existing
`insights-detail-thumb--empty` placeholder applies unchanged.

### Data shape contract (frontend)
The toggle-aware InsightsPage holds two pieces of fetched data:
`youtubeData` (the existing `weeklyData`, renamed for clarity) and
`appStoreData`. Both are fetched on mount in parallel; each has its
own loading and error state. Switching the toggle is purely a render
decision — no refetch.

App-row grouping: rows in `automatic_apple_table` are one-per-
`(app_id, problem)` (mirror of the YouTube schema), so the frontend
groups by `app_id` the same way `getAllVideoEntries` groups by
`key`. A new `getAllAppEntries(appStoreData)` helper is added next
to it.

Genre filter: when an Apple genre pill is selected, filter on
`genre_id`. The "All" pill shows every Apple row across the three
genres.

### Empty / partial-data behavior
- Both endpoints fail → page-level error (preserve current
  behavior, just gated to whichever source is selected).
- One source fails, the other succeeds → the failed source's tab
  shows its own error; the working tab stays usable. This is why
  the two sources have separate loading/error state.
- A Sunday where the App Store job ran but produced zero rows for
  a genre → empty-state copy ("No insights yet. Check back after
  the next run.") inside that genre's filtered view, identical to
  the YouTube empty state.

## Verification
- Local: with the dev backend pointed at the production Supabase
  (or a seeded local instance), confirm the toggle swaps the row
  list, the genre pills filter correctly, and the deep-links open
  the right App Store page in a new tab.
- Visual regression: take before/after screenshots of the YouTube
  view to confirm zero visual change when the toggle defaults to
  YouTube.
- Network: confirm both `/get/homePage` and
  `/get/homePageAppStore` fire on mount in parallel (DevTools
  waterfall).
- Failure isolation: temporarily break
  `get_weekly_apple_ids` (e.g. wrong table name) and confirm the
  YouTube tab still renders.
- A Sunday with zero Apple rows for a single genre: confirm the
  per-genre empty state and that "All" still shows the other two
  genres' rows.

## Acceptance
- [ ] `GET /get/homePageAppStore` exists in
      [app/api/home.py](app/api/home.py), returns
      `[games_rows, social_rows, utilities_rows]` in fixed order,
      raises 503 with a per-genre detail on Supabase failure.
- [ ] [frontend/src/InsightsPage.jsx](frontend/src/InsightsPage.jsx)
      has a source toggle (YouTube default) above the browse
      section.
- [ ] Selecting App Store swaps the category pills for genre pills
      (All / Games / Social Networking / Utilities) and the video
      rows for app rows.
- [ ] Each app row renders thumbnail, App Store deep link
      (`apps.apple.com/{country}/app/id{app_id}`), app title, genre
      label, and a bulleted problem list with per-problem rating
      badges.
- [ ] Both endpoints are fetched in parallel on mount; switching
      the toggle does not refetch.
- [ ] YouTube source/category/category-filter behavior is byte-
      identical to pre-spec (visual regression check passes).
- [ ] One-source-failure case verified: breaking the Apple endpoint
      does not break the YouTube tab, and vice versa.
- [ ] Empty per-genre state renders the existing empty-state copy.
- [ ] No new env vars, no new routes, no new dependencies.
