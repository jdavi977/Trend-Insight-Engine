# Docs Context — docs/

> Authority: [PRD.md](PRD.md) is the v2.2 product spec (idea-in → gaps-out) and
> the source of truth for product behaviour. API/guide docs describe the `/runs`
> surface; the v1 single-URL + weekly-trending surface is removed.

## Audiences
- api/      → developers integrating or extending the backend (the `/runs` API)
- guides/   → new contributors setting up locally
- changelog → version history of features and fixes

## Standards
- API docs follow endpoint → method → params → response format.
- Document the v2 run lifecycle endpoints: `POST /runs`, `POST /runs/:id/approve`,
  `POST /runs/:id/feedback`, `POST /runs/:id/report`, `GET /runs/:id`, `GET /runs`.
  Do NOT document the removed `/analyze/youtube`, `/analyze/appStore`,
  `/get/homePage`.
- Output shape: gaps grounded in quote IDs (PRD §7.4) — document `GapItem`,
  `Quote`, `Coverage`, run lifecycle states, and the severity 1–5 rubric.
- Guides use numbered steps with code blocks.
- Changelog entries: YYYY-MM-DD | feature/fix | one-line description. Record the
  v1→v2 pivot (removed weekly pipeline + single-URL endpoints).
