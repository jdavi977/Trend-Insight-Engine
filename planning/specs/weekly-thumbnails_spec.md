---
name: Weekly Insights Thumbnails
description: Display YouTube video thumbnails for each row in the weekly insights page using thumbnail data already captured by the automatic pipeline.
type: spec
---

# Weekly Insights Thumbnails — Spec

## Goal
Render the YouTube thumbnail next to each video card on the Insights page
(`/insights`) **and on the Home page Top Videos by Category section**
(`/`) so weekly entries are visually identifiable. The thumbnail URL is
already fetched from the YouTube API by `getMostPopularVideos` and
written into `automatic_table` by `youtube_automatic`; this feature
finishes the path: Supabase → `/get/homePage` → `InsightsPage.jsx` /
`HomePage.jsx`.

## Scope
- In:
  - Switch ingestion to capture the **highest-resolution thumbnail
    available** (prefer `maxres` → `standard` → `high` → `medium` →
    `default`) instead of the hard-coded `default` (120×90).
  - Confirm/fix the thumbnail field in `automatic_table` rows.
  - Surface the thumbnail through `/get/homePage` (already implicit via
    `select()` — verify).
  - Replace the empty `.insights-detail-thumb` placeholder on the
    Insights page with an `<img>` showing the video thumbnail.
  - Replace the empty `.top-video-card-thumb` placeholder on the
    Home page (`HomePage.jsx`, Top Videos by Category section) with an
    `<img>` using the same data shape.
  - Fallback styling when a row has no thumbnail (older pre-feature
    rows, or future videos missing every size).
- Out:
  - Manual `/analyze/youtube` flow (no Supabase persistence, separate
    UI path).
  - App Store reviews (no thumbnail concept).
  - Backfill of historical `automatic_table` rows written before
    thumbnails were added (treat as missing → fallback).

## Current State
- `app/ingestion/youtubeComments.py:58–63` returns
  `{"Title", "Id", "Thumbnail": item["snippet"]["thumbnails"]["default"]}`
  where `default` is `{url, width, height}` (120×90).
- `app/scripts/automaticYoutube.py:56` writes
  `"thumbnail": id["Thumbnail"]` per row.
- `app/lib/db.py:get_weekly_ids` does `select()` (all columns) → already
  returns `thumbnail` to the API.
- `frontend/src/InsightsPage.jsx:127` renders an empty
  `<div className="insights-detail-thumb" />` for every entry.
- `frontend/src/HomePage.jsx:142` renders an empty
  `<div className="top-video-card-thumb" />` for every top-video card,
  and `getTopVideoEntries` already projects fields off `items[0]` —
  thumbnail just needs to be added to that projection.

## Data Contract
Decision: **store the thumbnail as an object** matching the YouTube API
shape — `{url, width, height}` — so width/height are available for
`<img>` attributes (prevents CLS) without a second API call.

**Resolution selection (ingestion-side):** YouTube returns a
`thumbnails` map with up to five sizes. Pick the largest available in
this priority order: `maxres` (1280×720) → `standard` (640×480) →
`high` (480×360) → `medium` (320×180) → `default` (120×90). `maxres` is
not always present (older / less popular videos), so the fallback chain
is required.

`automatic_table.thumbnail` (jsonb, nullable):
```json
{ "url": "https://i.ytimg.com/vi/<id>/maxresdefault.jpg", "width": 1280, "height": 720 }
```

`/get/homePage` response: each item gains an optional `thumbnail` object
of the same shape. Existing consumers that ignore unknown fields are
unaffected.

## Backend Changes
- **`app/ingestion/youtubeComments.py:getMostPopularVideos`** — replace
  the hard-coded `thumbnails["default"]` lookup with a helper that
  picks the largest available size in the priority order above. Sketch:
  ```python
  def _pick_largest_thumbnail(thumbs):
      for size in ("maxres", "standard", "high", "medium", "default"):
          if size in thumbs:
              return thumbs[size]
      return None
  ```
  Then `"Thumbnail": _pick_largest_thumbnail(item["snippet"]["thumbnails"])`.
- **Schema**: confirm `automatic_table.thumbnail` exists as `jsonb` (or
  `json`). If missing, add it via Supabase SQL editor; document the
  migration under `ops/supabase/` per existing conventions.
- **Verification**: spot-check a recent row from a Sunday run to confirm
  `row["thumbnail"]["url"]` is populated and points at a high-res asset
  (e.g. `maxresdefault.jpg`) for popular videos.

`update_automatic_video_date` does **not** refresh the thumbnail. That is
acceptable: YouTube thumbnail URLs are stable for a video's lifetime.
No code change needed.

## Frontend Changes
File: `frontend/src/InsightsPage.jsx`

- Pull `thumbnail` off the first item of each grouped entry, same
  pattern as `title`/`category`:
  ```js
  thumbnail: items[0].thumbnail,  // {url, width, height} | null
  ```
- Replace the placeholder div with an image + fallback:
  ```jsx
  {entry.thumbnail?.url ? (
    <img
      className="insights-detail-thumb"
      src={entry.thumbnail.url}
      width={entry.thumbnail.width}
      height={entry.thumbnail.height}
      alt={entry.title}
      loading="lazy"
    />
  ) : (
    <div className="insights-detail-thumb insights-detail-thumb--empty" />
  )}
  ```

File: `frontend/src/InsightsPage.css`

- Style `.insights-detail-thumb` as an `<img>`: fixed aspect ratio
  (16:9), `object-fit: cover`, rounded corners matching existing card
  styling, responsive max-width.
- `.insights-detail-thumb--empty` keeps the current grey block for the
  fallback case.

File: `frontend/src/HomePage.jsx`

- Extend `getTopVideoEntries` to project the thumbnail off the first
  item of the group, mirroring `title`/`category`:
  ```js
  thumbnail: items[0].thumbnail,  // {url, width, height} | null
  ```
- Replace the empty `.top-video-card-thumb` div in the Top Videos by
  Category section with the same image + fallback pattern as the
  Insights page (different className):
  ```jsx
  {thumbnail?.url ? (
    <img
      className="top-video-card-thumb"
      src={thumbnail.url}
      width={thumbnail.width}
      height={thumbnail.height}
      alt={title}
      loading="lazy"
    />
  ) : (
    <div className="top-video-card-thumb top-video-card-thumb--empty" />
  )}
  ```

File: `frontend/src/HomePage.css`

- Style `.top-video-card-thumb` as an `<img>`: 16:9 aspect ratio,
  `object-fit: cover`, rounded corners matching the card. Keep the
  grey-block treatment under `.top-video-card-thumb--empty` for the
  fallback case.

## Failure Modes
- **Row missing `thumbnail`** (pre-feature row, or `medium` size absent):
  fall back to the empty grey block. Page never crashes on null.
- **Image 404 / network error**: browser shows broken-image icon. Out of
  scope for v1; revisit only if it occurs in practice.
- **Mixed-content / CSP**: YouTube serves `i.ytimg.com` over HTTPS, no
  CSP changes anticipated.

## Acceptance
- [ ] `automatic_table.thumbnail` column confirmed (or added) as jsonb.
- [ ] Ingestion picks the largest available size; popular-video rows
      from a Sunday cron run contain `maxresdefault.jpg` URLs.
- [ ] One Sunday cron run produces rows where
      `row["thumbnail"]["url"]` is a valid `i.ytimg.com` URL.
- [ ] `/get/homePage` response includes `thumbnail` on populated rows.
- [ ] Insights page renders the correct thumbnail per video card across
      all three categories.
- [ ] Home page Top Videos by Category section renders the correct
      thumbnail per top-video card.
- [ ] Rows without a thumbnail render the grey fallback on both pages,
      no console errors.
- [ ] Lighthouse: no new CLS regression on Insights or Home (the
      width/height attrs reserve space).

## Open Questions
- Do we want a one-shot backfill script for pre-feature rows, or let
  them age out as new Sunday runs replace them? (Default: age out.)
- Should the card become a clickable link to the YouTube video? Out of
  scope here, but the thumbnail is the natural affordance — track as a
  follow-up.
