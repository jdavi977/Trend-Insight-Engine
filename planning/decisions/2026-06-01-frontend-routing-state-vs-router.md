# ADR: Frontend Routing — State-Based Nav Now, Router in Slice 2

Date: 2026-06-01
Status: Accepted

Related spec: planning/specs/v2-slice-1-end-to-end_spec.md (§10)
Related PRD: docs/PRD.md §7.6, §15; US-4, US-5

## Context

The slice-1 spec described the v2 frontend with `react-router` and browser routes
(`/runs/new`, `/runs/:id`). The three run-lifecycle pages (NewRun #51, RunResult
#52, HomeV2 #53) were actually built on the pre-existing state-based navigation in
`frontend/src/App.jsx` — a `currentPage` switch plus an `activeRunId` set by an
`openRun(runId)` callback. `frontend/CONTEXT.md` also forbids new state/routing
libraries. So the merged code and the spec disagreed: no router was introduced.

The question is whether to retrofit `react-router-dom` now, keep state-based nav
permanently, or schedule the migration deliberately.

## Options Considered

1. **Retrofit react-router into slice 1** — convert all three already-merged pages
   immediately to `/`, `/runs/new`, `/runs/:id`.

2. **Keep state-based nav permanently** — never introduce a router; accept that
   runs are only reachable in-session.

3. **State-based nav for slice 1, router migration in slice 2** — ship slice 1 on
   the existing pattern; do the `react-router-dom` conversion as the first slice-2
   frontend task, before slice 2's new feedback/report UI.

## Decision

Chose **option 3**. Slice 1 stays on state-based navigation (it was already merged
that way and the slice-1 exit criteria don't require URLs). The router migration is
pulled into **slice 2** — the "make it real-user-ready before public exposure"
slice — and sequenced *first*, ahead of the slice-2 feedback/report controls, so
that UI is built once on the routed pages rather than twice.

## Tradeoffs Accepted

- Gained: Slice 1 shipped without re-opening two merged PRs or fighting the
  CONTEXT.md "no new libraries" rule mid-slice.
- Gained: A single coherent frontend refactor in slice 2 — introduce the router and
  build feedback/report UI on the routed pages in one pass.
- Gained: US-4 (leave/return via a saved URL) and US-5 (share a result) get real
  delivery in slice 2, gated to the same point public users first arrive.
- Lost: For all of slice 1, a run can't be bookmarked, shared, or reopened across a
  reload — only revisited in-session via the feed or "My Runs."
- Lost: The slice-1 spec's literal `/runs/:id` wording; reconciled in this ADR and
  in the updated spec/PRD/CONTEXT docs.
- Taken on: A second touch of the three run pages in slice 2 (the conversion). Cost
  is bounded — the pages already centralize navigation through `App.jsx` callbacks,
  so the change is mostly swapping `currentPage`/`openRun` for route params.

## Consequences

- Closes off: Treating in-session state nav as the permanent v2 model. The
  `currentPage` switch is explicitly interim; slice 3's removal of the legacy v1
  pages also removes the bulk of that switch.
- Enables: Deep-linkable, shareable, reload-safe run URLs as a slice-2 deliverable.
- Requires: Slice 2 frontend work to start with the router migration; the
  feedback/report UI (PRD §7.6) is built on routed pages, not on `currentPage`.
- Backend is unaffected: `GET /runs/:id` already addresses a run server-side and
  sets `X-Robots-Tag: noindex, nofollow`; only client navigation changes.
