# Spec: Scope down to the core pipeline

> Status: **grilled** (2026-07-26) — framed + grilled via the feature-planning
> workspace (stages 01–02). §1–§2 passed the stage-01 kill gate; §3–§9 are the
> stage-02 grill output, with all four cut decisions resolved against the
> codebase and the user's calls.
> Source issue: [#76](https://github.com/jdavi977/Trend-Insight-Engine/issues/76).
> Friction note: [NOTES.md](../../NOTES.md) 2026-07-12 ("scope down as much as
> possible to make the pipeline simpler", Next steps #2).
>
> This is a **subtractive** engagement: the deliverable is *decisions and
> removals*, not new behaviour. Every named cut candidate gets an explicit
> remove / park / keep verdict, and the repo is swept beyond the named list.

## 1. Context / why now

The project drifted from its purpose by feature-piling. The author's own record
is explicit — *"I went away from what my intended purpose was for this project by
trying to add as many features as possible"* ([NOTES.md](../../NOTES.md) 05-16),
and *"Based on my current issues I want to scope down as much as possible to make
the pipeline simpler"* (07-12). This spec acts on that decision.

**Why now, concretely:** the core loop is *itself* unreliable, and the
non-essential surfaces are making that reliability work harder to do. The 07-10
and 07-12 notes catalogue real core-loop failures — `quote_pool` too low, many
YouTube comments filtering to `[]`, candidate gaps rejected under the ≥2-citation
grounding bar, synthesis receiving the idea but not using it to target gaps.
Layered on top of that failing loop are surfaces that serve no current user and
are only *partly* maintained: `feedback_events` (already decided "remove for
now"), backend-only `quality_signals` recording, dead columns
(`preflight_raw_json`, `partial_sources_json` NULL in Supabase), an
`idea_match` stage that only fires when a `target_gap` is supplied, and empty
shell directories left from the v1→v2 teardown (`app/rag/`, `app/lib/`,
`tests/rag/`, `tests/jobs/`). Each one is a place a debugging session can get
lost, and a line in the PRD/CLAUDE.md that no longer matches the filesystem.

The foundation we are scaling back to is one loop:

> **idea in → preflight competitors → ingest comments/reviews → idea-blinded
> per-source extraction → quote-then-claim synthesis → persisted, quote-grounded
> gaps.** Everything not serving that loop is a cut candidate.

Cutting first is the load-bearing choice. It shrinks the surface area a
debugging or hardening session has to hold in its head, and it removes the
half-maintained code that obscures where the loop actually breaks. It also has
**sequencing value**: the `quality_signals`/eval-harness decision is coupled to
the pipeline-reliability-hardening spec (deleted at HEAD, recover via
`git show d8ad4f9^:planning/specs/pipeline-reliability-hardening_spec.md`), whose
filter-retune validation *depends on the eval harness*. That keep/cut call must
be made here, **before** the retune issue is filed — decide the two together or
the retune loses its safety net.

The honest risk, surfaced at the stage-01 gate: scope-down engagements tend to
**over-cut**. The mitigation is a hard rule (§2): **park = recoverable from git
history, never half-maintained** — anything valuable but non-essential is
removed cleanly and logged, not left in a half-alive state.

## 2. Goals / non-goals

**Goals**

- **G1 — Write down the foundation.** The core loop (above) captured in one
  paragraph in `planning/CONTEXT.md` or the PRD, with everything else marked
  *opt-in-later*. This is the reference the rest of the cuts are judged against.
- **G2 — Every cut candidate gets an explicit verdict.** For each named
  candidate — `feedback_events`, `quality_signals` (coupled with the eval
  harness), `preflight_raw_json`, the `idea_match` stage, the empty shells,
  `app/preprocessing/validateUrl.py`, `app/jobs/preflight_smoke.py`,
  `app/data/invalid_data`, `app/utilities/textCleaning.py` — a **remove / park /
  keep** decision with a one-line reason, logged as a comment on #76.
- **G3 — Sweep the whole repo, not just the named list.** The mandate is broader
  than the candidates above; anything else cut is logged in the same #76 comment.
- **G4 — Remove the `feedback_events` surface** (endpoints + frontend), and
  update the PRD + CLAUDE.md, both of which still list it as a v2 table.
- **G5 — Resolve `preflight_raw_json`** — add the writer or drop the column, with
  the reason recorded. (Same disposition question applies to `partial_sources_json`.)
- **G6 — Delete the empty shell directories** left from the v1 teardown.
- **G7 — Decide `quality_signals` + eval-harness together, before the retune
  issue is filed** (keep both minimal or cut both — not separately), so the
  hardening spec's retune validation has a known safety net.
- **G8 — Prune the test tree.** After the cuts land, no test file references a
  removed surface, and the full suite passes. Core-loop and grounding-contract
  tests stay green — they are the foundation's safety net, not cut candidates.

**Non-goals**

- **N1 — No behaviour change to the core loop.** This is removal, documentation,
  and decisions. If a cut changes idea→gaps output, the cut is wrong.
- **N2 — No reliability *fixes* here.** The `quote_pool`, `[]`-filtering,
  grounding-rejection, and synthesis-ignores-idea problems are the
  pipeline-reliability-hardening spec's job. This spec only *decides* the
  `quality_signals`/harness question that hardening depends on, and clears the
  surface so hardening is easier. It does not retune filters or touch synthesis.
- **N3 — Park, don't half-maintain.** Nothing valuable is left in a partially
  working state. Cut cleanly (recoverable from git) or keep and maintain — there
  is no third state. This is the mitigation for the over-cut risk.
- **N4 — No new features, no new surfaces.** The whole point is fewer moving
  parts. Building back up happens *after* the core loop is reliable, in later
  work, not here.
- **N5 — No PRD rewrite.** The PRD stays the product authority; the only edits
  here are the removals a cut forces (e.g. dropping `feedback_events` from the v2
  table list, marking parked surfaces opt-in-later).
- **N6 — Supabase table *drops* are decided but executed with care.** Slice-1
  tables have **no checked-in migration** (they were made via the dashboard), so
  any DB change must be additive/idempotent and its physical-drop-vs-leave-orphan
  disposition stated explicitly rather than assumed. Deciding "remove the
  surface" does not automatically mean "drop the table this run."

## 3. Cross-cutting decisions (with rationale)

- **D1 — Park = clean, git-recoverable removal; never half-maintained** (N3).
  This is the one rule every cut obeys. A parked surface is deleted in a single
  coherent commit with the decision logged, so `git revert`/`git show` brings it
  back whole. There is no "left partly wired" state — that is the exact dead
  weight this spec removes.

- **D2 — All four grilled decisions took the deepest cut.** Resolved 2026-07-26
  against the codebase and the user's calls (§5 is the table): **cut** the eval
  harness *and* `quality_signals` together; **fold** `target_gap` into `idea` and
  remove the `idea_match` stage; **remove both** the feedback *and* report
  surfaces; **drop** the dead `preflight_raw_json` column.

- **D3 — Cutting the harness voids the reliability spec's safety net; that is a
  cross-spec consequence and must be recorded before the retune issue is filed.**
  The pipeline-reliability-hardening spec (deleted at HEAD, `git show
  d8ad4f9^:planning/specs/pipeline-reliability-hardening_spec.md`) has exit
  criterion 5 — *"eval harness green post-retune, all 5 seed categories, recall
  not worse"* — and extends `quality_signals` with `quotes_dropped_for_budget`.
  Both assume artifacts this spec deletes. Consequence: **the engagement-filter
  retune must establish its own validation** (a fresh harness, a manual
  before/after on a fixed idea set, or a golden-corpus check) and can no longer
  cite exit-criterion-5. #76's sequencing clause exists precisely to force this
  call *before* the retune issue is written — it is now made: cut. **→ ADR
  candidate** (§9): hard-ish to reverse, surprising to a future reader of the
  reliability spec, a real trade-off (simplicity now vs. rebuild-the-harness
  later).

- **D4 — Docs follow code, in the same slice — never ahead of it.** Each cut's
  edits to `planning/CONTEXT.md`, the PRD, and root `CLAUDE.md` land *in the
  slice that removes the surface*, not up front. Rewriting CONTEXT.md to say
  "no `idea_match`" while the code still runs it would make the doc lie about the
  running system — the precise drift the engineering-standards work fights. The
  one exception is the **foundation paragraph** (G1), which describes the core
  loop that already exists today and is true immediately (Slice 1).

- **D5 — "Fold `target_gap` into `idea`" is a redesign, not a pure removal, and
  is scoped as its own slice.** It changes the `POST /runs` contract (drops the
  `target_gap` field), the `synthesize(idea, target_gap, …)` call signature, and
  the frontend form — beyond deleting `idea_match`. Its semantics carry a live
  design question (§9 Q1): does synthesis keep receiving anything gap-shaped, or
  just the single `idea` string? This spec removes the *separate* surface;
  making synthesis actually *use* the idea to target gaps is reliability-spec
  work (N2), not this one.

## 4. Inventory — what each surface is, and its blast radius

Concise map of decision → touched files. The full import graph and the
data-flow diagram are the stage-03 architecture map's job
(`planning/architecture/2026-07-26-scope-down-core-pipeline.md`); this table is
enough to slice against.

| Surface | Backend | Frontend | DB | Tests |
|---|---|---|---|---|
| **Eval harness + quality_signals** | `app/eval/` (harness, metrics, seed/, reports/); `quality_signals` in `schemas/runs.py` (`QualitySignals`), `services/idea_run_service.py`, `services/run_pipeline_service.py`, `clients/supabase.py` | — | `idea_runs.quality_signals_json` | `tests/eval/*`, refs in `test_run_pipeline_service.py`, `test_runs_schemas.py`, `test_idea_run_service.py` |
| **idea_match + target_gap (fold)** | `llm/idea_match.py`, `llm/router.py` (stage), `config/constants.py`, `services/run_pipeline_service.py` (call + `_set_stage`), `llm/synthesis.py` (signature), `schemas/runs.py` (`target_gap` ×3, idea_match fields), `clients/supabase.py`, `services/idea_run_service.py` | `NewRun.jsx` (targetGap field), `RunResult.jsx` (`IdeaMatchCard`) | `idea_runs.target_gap`, `idea_runs.idea_match_json` | `tests/llm/test_idea_match.py`, refs in `test_runs.py`, service/schema tests |
| **feedback + report (remove both)** | `api/runs.py` (`POST /feedback`, `POST /report`), `schemas/runs.py` (`RunFeedback`, `RunReport`, `reported` status), `services/idea_run_service.py` (`submit_feedback`, `report_run`), `services/rate_limit_service.py` (`check_can_report`), `clients/supabase.py` (feedback_events writes) | `RunResult.jsx` (feedback + report UI) | `feedback_events` table (drop); `reported` status value | `tests/api/test_runs.py`, `tests/services/*` |
| **preflight_raw_json (drop)** | none (zero refs) | — | `idea_runs.preflight_raw_json` (drop) | — |
| **dead weight (sweep)** | `preprocessing/validateUrl.py`, `utilities/textCleaning.py`, empty `app/rag/`, `app/lib/`, `app/data/` | — | — | `tests/preprocessing/test_validateUrl.py`, empty `tests/rag/`, `tests/jobs/` |

**Kept, explicitly** (so a later sweep doesn't re-flag them): `partial_sources_json`
(live — written + read), `preprocessing/redact.py` (live PII),
`preprocessing/reviewPipeline.py` (live cleaning; camelCase is a tracked rename
delta, not dead code), `jobs/preflight_smoke.py` (manual dev tool guarding the
≤10s preflight budget).

## 5. The cuts — decision log

This table *is* the source for #76 G2/G3's required issue comment (posted when
Slice 1 lands). Verdict ∈ remove / park / keep; every row has a one-line reason.

| # | Surface | Verdict | Reason |
|---|---|---|---|
| 1 | Eval harness (`app/eval/`) | **remove** | Manual dev tool, not in CI/Makefile; its only downstream (the reliability retune) is being decoupled (D3). |
| 2 | `quality_signals` | **remove** | Backend-only, never surfaced in UI; the harness was its only real consumer (cut together per #76). |
| 3 | `idea_match` stage + card | **remove** | Optional add-on that does not serve the core loop; folded away with `target_gap`. |
| 4 | `target_gap` field | **fold into `idea`** | Separate field is extra contract + UI surface; one idea input carries gap intent (NOTES 07-12). Redesign slice (D5). |
| 5 | `POST /feedback` + `feedback_events` | **remove** | Already decided "remove for now" (NOTES 07-12); no current consumer. |
| 6 | `POST /report` + `reported` state | **remove** | User chose the wider cut; moderation is not core-loop and adds a lifecycle state to maintain. |
| 7 | `preflight_raw_json` column | **drop** | Dead column, zero code refs; drop via Supabase dashboard (no checked-in migration exists — N6). |
| 8 | `app/rag/`, `app/lib/`, `app/data/`, `tests/rag/`, `tests/jobs/` | **remove** | Empty shells from the v1 teardown (only `__pycache__`). |
| 9 | `validateUrl.py` (+ test), `textCleaning.py` | **remove** | v1 URL-in flow / unused utility; only importer is the module's own test. |
| — | `partial_sources_json`, `redact.py`, `reviewPipeline.py`, `preflight_smoke.py` | **keep** | Live or actively useful (see §4). |

## 6. Build sequence (tracer-bullet slices)

Ordered safest-first; each slice is independently shippable, prunes its own
tests, and leaves the suite green (G8 is verified per-slice, not deferred). Doc
edits ride inside the slice that makes them true (D4). Stage 04 turns these into
`[spec: scope-down-core-pipeline]` issues.

- **Slice 1 — Foundation + dead-weight sweep.** Write the G1 foundation
  paragraph into `planning/CONTEXT.md` (true today), post the §5 decision log as
  the #76 comment (G2/G3), and delete the empty shells + dead modules
  (`validateUrl`, `textCleaning`, `app/data/`, `app/rag/`, `app/lib/`) with their
  tests. Pure-safe: no runtime behaviour touched. Ships the reference the rest
  are judged against.
- **Slice 2 — Cut eval harness + `quality_signals`.** Delete `app/eval/` +
  `tests/eval/`; strip `quality_signals` from schemas/services/supabase and their
  tests; drop `idea_runs.quality_signals_json`. Record the D3 cross-spec
  consequence where the reliability spec will look for it (a note in
  `planning/CONTEXT.md` or the recovered spec's future home).
- **Slice 3 — Fold `target_gap` into `idea`, remove `idea_match`.** Drop the
  `target_gap` field from `POST /runs` + `NewRun.jsx`, delete `llm/idea_match.py`,
  the stage routing, the `IdeaMatchCard`, and the `idea_match`/`target_gap`
  schema+DB columns; simplify `synthesize(…)` to drop `target_gap`. Resolve §9 Q1
  before coding. Vertical (frontend + backend + schema + tests).
- **Slice 4 — Remove feedback + report surface.** Delete both endpoints, the
  `RunFeedback`/`RunReport` schemas, the service methods, `check_can_report`, the
  feedback_events writes, the `reported` lifecycle state, and the frontend UI;
  drop the `feedback_events` table (dashboard); update the run-lifecycle
  description in `planning/CONTEXT.md` + PRD + `CLAUDE.md`.
- **Slice 5 — Drop `preflight_raw_json`.** Dashboard column drop + a one-line
  note. Tiny; can piggyback on Slice 2's DB touch if batching dashboard changes.
- **Verification gate (G8).** After the slices: no test references a removed
  surface, and `make test` (full suite) is green. This is a gate on the branch,
  not a separate slice.

## 7. Acceptance criteria

Mirrors #76's checklist, sharpened by the grill.

- **A1.** The core-loop foundation is written in one paragraph in
  `planning/CONTEXT.md`; every removed/parked surface is marked opt-in-later.
- **A2.** Every §5 row is logged as a #76 comment with its one-line reason, and
  any surface cut beyond §5 during the repo sweep is logged in the same comment.
- **A3.** `app/eval/` and all `quality_signals` references are gone; the
  reliability-spec consequence (D3) is recorded before any retune issue is filed.
- **A4.** `POST /runs` no longer accepts `target_gap`; `idea_match` is gone from
  backend, frontend, schema, and DB; synthesis runs on `idea` alone.
- **A5.** `POST /feedback` and `POST /report` are gone; `feedback_events` is
  dropped; the `reported` status is removed from the lifecycle and the docs.
- **A6.** `preflight_raw_json` is dropped (or its retention is documented — here,
  dropped).
- **A7.** The empty shell directories and dead modules (§5 rows 8–9) are deleted.
- **A8.** No test file references a removed surface; the full suite passes.
- **A9.** PRD + `CLAUDE.md` + `planning/CONTEXT.md` no longer list
  `feedback_events`, `quality_signals`, `idea_match`/`target_gap`, or the
  `reported` state as live; each is marked removed or opt-in-later.

## 8. Risks

- **R1 — Over-cut.** The deepest option was taken on all four decisions.
  Mitigation: D1 (clean git-recoverable park) + the §5 log make every cut a
  one-command restore. If a cut surface turns out load-bearing, revert its slice.
- **R2 — The harness cut strands the reliability retune (D3).** The retune's
  only planned validation is being deleted. Mitigation: the retune issue must
  *not* be filed citing exit-criterion-5; it owns its own validation. This spec
  blocks that ordering explicitly (§6 Slice 2 records the consequence).
- **R3 — Removing `reported` is a state-machine change with reach.** The lifecycle
  is documented in the PRD, `planning/CONTEXT.md`, schemas, and admin-hidden
  filtering. Slice 4 must find every reader of the state, not just the endpoint.
- **R4 — Fold `target_gap` is a contract change (D5).** Any client or test
  sending `target_gap` breaks. Mitigation: it is a single vertical slice; grep
  for `target_gap` across both trees is the completeness check.
- **R5 — DB drops have no migration to revert (N6).** `feedback_events`,
  `quality_signals_json`, `target_gap`, `idea_match_json`, `preflight_raw_json`
  are dashboard changes. Mitigation: document each drop in the slice; treat
  "drop the column" and "stop writing the column" as separable — code stops
  first, physical drop can lag safely.

## 9. Decisions (formerly open questions)

Resolved at stage 04 (2026-07-26).

- **Q1 — Fold semantics: DECIDED — `idea` alone.** `synthesize(…)` drops
  `target_gap` and runs on `idea` only. Making synthesis actually *use* the idea
  to target gaps is a *reliability* improvement (NOTES 07-12), out of scope here
  (N2). This resolution makes Slice 3 **AFK** rather than HITL.
- **Q2 — ADR for the harness cut: DECIDED — no ADR.** The cross-spec consequence
  is already captured in §D3 here and in the `pipeline-reliability-hardening`
  memory (updated 2026-07-26); a separate `planning/decisions/` record was judged
  redundant. If the reliability spec is re-filed, it inherits D3 from this spec.
- **Q3 — The recovered reliability spec is left deleted**, not amended now; its
  eventual re-file inherits D3. Recorded, not acted on here.

## 10. Issue slices (stage 04)

Published as `[spec: scope-down-core-pipeline]` issues, parent #76. Manual
Supabase drops are isolated in one HITL slice (5) that lags the code slices, per
R5/N6 ("stop writing" in code first; physical drop after).

| Slice | Type | Blocked by |
|---|---|---|
| 1 — Foundation write-down + dead-weight sweep | AFK | none |
| 2 — Cut eval harness + `quality_signals` (code) | AFK | none |
| 3 — Fold `target_gap` into `idea`, remove `idea_match` (code) | AFK | none |
| 4 — Remove feedback + report surface (code) | AFK | none |
| 5 — Supabase dashboard drops (`feedback_events` + 4 dead columns) | HITL | 2, 3, 4 |
