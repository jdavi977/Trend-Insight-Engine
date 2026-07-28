# Docs Context — docs/

> Authority: [PRD.md](PRD.md) (v2.2, idea-in → gaps-out) §7.1–§7.2, §7.4 — the
> run lifecycle, the `/runs` endpoints, and the output schema this folder
> documents. Read those sections, not the whole file. API/guide docs describe
> the `/runs` surface; the v1 single-URL + weekly-trending surface is removed.

## Audiences
- api/      → developers integrating or extending the backend (the `/runs` API)
- guides/   → new contributors setting up locally
- changelog → version history of features and fixes

## Standards
- API docs follow endpoint → method → params → response format.
- Document the v2 run lifecycle endpoints: `POST /runs`, `POST /runs/:id/approve`,
  `GET /runs/:id`, `GET /runs`. Do NOT document the removed `/analyze/youtube`,
  `/analyze/appStore`, `/get/homePage`, or the scope-down's `POST /runs/:id/feedback`
  and `POST /runs/:id/report` (#89).
- Output shape: gaps grounded in quote IDs (PRD §7.4) — document `GapItem`,
  `Quote`, `Coverage`, run lifecycle states, and the severity 1–5 rubric.
- Guides use numbered steps with code blocks.
- Changelog entries: YYYY-MM-DD | feature/fix | one-line description. Record the
  v1→v2 pivot (removed weekly pipeline + single-URL endpoints).
