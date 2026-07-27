# Frontend Context — frontend/

> Authority: [docs/PRD.md](../docs/PRD.md) (v2.2) §6 (US-4, US-5), §7.1, §7.6,
> §7.8 — read those sections, not the whole file. v2 = **idea-in →
> gaps-out**. The old 4-page weekly-trending / single-URL SPA (Home, Insights,
> YouTube, App Store) is **replaced**. Legacy pages remain in `src/` pending the
> v2 rebuild.

## App Structure (v2)
React 19 + Vite SPA, organised around the run lifecycle:
- **Home** → public feed of recent completed runs (idea text, completed-at, link)
  + "Start a new run" CTA. Replaces old weekly-trending Home.
- **New Run** → submit form (idea — the only field) → pre-flight loading →
  **pre-flight review** (signal-strength panel + competitor list editor).
- **Run Status / Result** → in-session live progress while `running`, full
  result when `done`. Reached by approving a run or opening one from the feed,
  and addressable at `/runs/:id` — paste the URL into a fresh tab and the
  result loads directly (US-4 leave/return, US-5 share; see Patterns below).
- **My Runs** → frontend-only filter of the public feed against `localStorage`
  `run_id`s (no auth/accounts in v1).

Pages live **flat in `src/`** (`HomeV2.jsx`, `NewRun.jsx`, `RunResult.jsx`) —
there is no `src/pages/` directory. Legacy v1 pages (`HomePage`, `InsightsPage`,
`YouTubePage`, `AppStorePage`) stay mounted in `App.jsx` on `/legacy/*` routes
but are unlinked from nav; removal is slice 3.

## Run Lifecycle (what the UI polls)
`pending → preflight_ready → running → done | failed`. New Run drives
`pending → preflight_ready` (synchronous, ≤10s wait) then `approve` →
`running`; Result page polls `GET /runs/:id` every 5s while the status is
non-terminal (`pending` / `preflight_ready` / `running`) and stops on
`done` / `failed`.

## Patterns (Follow These)
- State via React hooks (useState, useEffect) — no Redux/Zustand.
- **Navigation uses `react-router-dom`** (routes: `/` Home feed, `/runs/new`,
  `/runs/:id`). Pages own their own navigation via `useNavigate()`; the Result
  page reads its run id from the route via `useParams()` — no `onOpenRun` /
  `runId` props, no `currentPage` state switch. This is the one sanctioned
  routing library; it supersedes the old "no router" rule to deliver US-4 / US-5
  ([docs/PRD.md](../docs/PRD.md) §6). A formal routing ADR is still to be
  recorded.
- All API calls use Fetch against the `/runs` endpoints; base URL from a config
  constant (`import.meta.env.VITE_API_BASE`), never hardcoded.
- Components are PascalCase.jsx. Each page is a top-level component; shared UI in
  `components/`.
- Lift backend calls to page level — child components don't fetch.

## Patterns to Avoid
- Do NOT add a state management library.
- Do NOT add a *second* routing library or replace `react-router-dom`; the
  single-router rule is settled. (The prior "no router at all" rule is lifted.)
- Do NOT create a `src/pages/` directory; pages are flat in `src/`.
- Do NOT call the backend from child components — lift to page level.
- Do NOT hardcode the backend URL.
- Do NOT index run pages — backend sets `X-Robots-Tag: noindex, nofollow` on
  `/runs`; don't build SEO around run content.

## Pre-flight Review Rules (PRD §7.6)
- **Signal-strength panel:** show `signal_strength` + `signal_reasoning`. If
  `low`, prominent: primary CTA *"Continue anyway — I understand the signal will
  be thin"*, secondary *"Cancel and refine"*. Acknowledgement gates `approve`
  (sends `acknowledged_low_signal: true`).
- **Competitor list editor:** add / remove / paste URL. Each candidate shows its
  search-API source ("found via App Store search for X").

## Result / Gap Display Rules (PRD §7.6, §7.8)
- **Signal-strength banner** at the top.
- **`partial_sources` banner** if any sources failed, naming them.
- **Ranked gap list** with **verbatim quotes prominent next to each claim** — not
  hidden in a drill-down (reinforces "decision support, not verdict").
- Per gap, show: `severity` (1–5 scale), `frequency` (raw count), `spread`
  (distinct competitors), and **citation count** (`len(evidence_quote_ids)`) —
  2 citations is visibly weaker than 12 (§7.8).
- **Coverage line:** render `coverage` as e.g. *"12 of 184 retrieved quotes were
  cited (6%)"*.
- **Thumbs-up control** per gap → `POST /runs/:id/feedback`
  (`new_to_me_gap_ids`).
- **Direction prompt** after the list — *"continuing / shifting / dropping / need
  more research?"* → `POST /runs/:id/feedback` (`direction`). Non-blocking,
  dismissible.
- **"Report this run"** link → `POST /runs/:id/report`.

## Not in v2
- No NPS / sentiment ratios (structured pain only).
- No severity/frequency *color-coded-by-type* grouping (that was the v1 insight
  view) — v2 ranks gaps, grounded in quotes, not typed insights.
- No accounts, no real-time/streaming, no multi-idea comparison UI.
