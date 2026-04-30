---
name: Weekly Insights Thumbnails
description: Display YouTube video thumbnails for each row in the weekly insights page using thumbnail data already captured by the automatic pipeline.
type: spec
---

# Weekly Insights Thumbnails — Spec

## Goal
Render the YouTube thumbnail next to each video card on the Insights page
(`/insights`) so weekly entries are visually identifiable. The thumbnail
URL is already fetched from the YouTube API by `getMostPopularVideos` and
written into `automatic_table` by `youtube_automatic`; this feature
finishes the path: Supabase → `/get/homePage` → `InsightsPage.jsx`.

## Scope
- In:
  - Confirm/fix the thumbnail field in `automatic_table` rows.
  - Surface the thumbnail through `/get/homePage` (already implicit via
    `select()` — verify).
  - Replace the empty `.insights-detail-thumb` placeholder with an
    `<img>` showing the video thumbnail.
  - Fallback styling when a row has no thumbnail (older pre-feature
    rows, or future videos missing the `medium` size).
- Out:
  - Manual `/analyze/youtube` flow (no Supabase persistence, separate
    UI path).
  - App Store reviews (no thumbnail concept).
  - Backfill of historical `automatic_table` rows written before
    thumbnails were added (treat as missing → fallback).

## Current State
- `app/ingestion/youtubeComments.py:58–63` returns
  `{"Title", "Id", "Thumbnail": item["snippet"]["thumbnails"]["medium"]}`
  where `medium` is `{url, width, height}` (320×180).
- `app/scripts/automaticYoutube.py:56` writes
  `"thumbnail": id["Thumbnail"]` per row.
- `app/lib/db.py:get_weekly_ids` does `select()` (all columns) → already
  returns `thumbnail` to the API.
- `frontend/src/InsightsPage.jsx:127` renders an empty
  `<div className="insights-detail-thumb" />` for every entry.

## Data Contract
Decision: **store the thumbnail as an object** matching the YouTube API
shape — `{url, width, height}` — so width/height are available for
`<img>` attributes (prevents CLS) without a second API call.

`automatic_table.thumbnail` (jsonb, nullable):
```json
{ "url": "https://i.ytimg.com/vi/<id>/mqdefault.jpg", "width": 320, "height": 180 }
```

`/get/homePage` response: each item gains an optional `thumbnail` object
of the same shape. Existing consumers that ignore unknown fields are
unaffected.

## Backend Changes
- **None expected** if the column already exists and accepts jsonb. To
  verify before frontend work:
  - Inspect `automatic_table` schema in Supabase — confirm `thumbnail`
    column exists and is `jsonb` (or `json`). If missing, add it via
    Supabase SQL editor; document the migration under
    `ops/supabase/` per existing conventions.
  - Spot-check a recent row from a Sunday run to confirm
    `row["thumbnail"]["url"]` is populated.

`update_automatic_video_date` does **not** refresh the thumbnail. That is
acceptable: YouTube `mqdefault.jpg` URLs are stable for a video's
lifetime. No code change needed.

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

## Failure Modes
- **Row missing `thumbnail`** (pre-feature row, or `medium` size absent):
  fall back to the empty grey block. Page never crashes on null.
- **Image 404 / network error**: browser shows broken-image icon. Out of
  scope for v1; revisit only if it occurs in practice.
- **Mixed-content / CSP**: YouTube serves `i.ytimg.com` over HTTPS, no
  CSP changes anticipated.

## Acceptance
- [ ] `automatic_table.thumbnail` column confirmed (or added) as jsonb.
- [ ] One Sunday cron run produces rows where
      `row["thumbnail"]["url"]` is a valid `i.ytimg.com` URL.
- [ ] `/get/homePage` response includes `thumbnail` on populated rows.
- [ ] Insights page renders the correct thumbnail per video card across
      all three categories.
- [ ] Rows without a thumbnail render the grey fallback, no console
      errors.
- [ ] Lighthouse: no new CLS regression on the Insights page (the
      width/height attrs reserve space).

## Open Questions
- Do we want a one-shot backfill script for pre-feature rows, or let
  them age out as new Sunday runs replace them? (Default: age out.)
- Which thumbnail size is right long-term — `medium` (320×180),
  `high` (480×360), or `maxres` when present? `medium` is what we store
  today; revisit if cards visibly look low-res on wide screens.
- Should the card become a clickable link to the YouTube video? Out of
  scope here, but the thumbnail is the natural affordance — track as a
  follow-up.
