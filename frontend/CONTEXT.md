# Frontend Context — frontend/

> Authority: [docs/PRD.md](../docs/PRD.md) §7.6 (v2.2). v2 = **idea-in →
> gaps-out**. The old 4-page weekly-trending / single-URL SPA (Home, Insights,
> YouTube, App Store) is **replaced**. Legacy pages remain in `src/` pending the
> v2 rebuild.

## App Structure (v2)
React 19 + Vite SPA, organised around the run lifecycle:
- **Home** → public feed of recent completed runs (idea text, completed-at, link)
  + "Start a new run" CTA. Replaces old weekly-trending Home.
- **New Run** → submit form (idea + optional target gap) → pre-flight loading →
  **pre-flight review** (signal-strength panel + competitor list editor).
- **Run Status / Result** → stable URL; live progress while `running`, full
  result when `done`.
- **My Runs** → frontend-only filter of the public feed against `localStorage`
  `run_id`s (no auth/accounts in v1).

## Run Lifecycle (what the UI polls)
`pending → preflight_ready → running → done | failed`. New Run drives
`pending → preflight_ready` (synchronous, ≤10s wait) then `approve` →
`running`; Result page polls `GET /runs/:id` until `done`.

## Patterns (Follow These)
- State via React hooks (useState, useEffect) — no Redux/Zustand.
- All API calls use Fetch against the `/runs` endpoints; base URL from a config
  constant (`import.meta.env.VITE_API_BASE`), never hardcoded.
- Components are PascalCase.jsx. Each page is a top-level component; shared UI in
  `components/`.
- Lift backend calls to page level — child components don't fetch.

## Patterns to Avoid
- Do NOT add a state management library.
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
