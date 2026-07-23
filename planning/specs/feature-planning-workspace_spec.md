# Spec: feature-planning ICM workspace (+ context-system drift fixes)

> Status: draft (2026-07-20), post-grill. Tracker: GitHub issue
> [#75](https://github.com/jdavi977/Trend-Insight-Engine/issues/75).
> Authority for ICM structure: the reference repo
> [RinDig/Interpreted-Context-Methdology](https://github.com/RinDig/Interpreted-Context-Methdology)
> `_core/CONVENTIONS.md` + arXiv 2603.16021 v2. Companion analysis:
> [../2026-07-20-icm-workflow-comparison.md](../2026-07-20-icm-workflow-comparison.md).
>
> Supersedes the pre-grill `icm-workspaces_spec.md`, which specced two
> workspaces. The `eval-corpus` workspace is **deferred** — see Appendix A.

## 1. Context / why now

v1 (v2.2) shipped 2026-06-11. The repo is in a **reliability-hardening /
scope-down** phase ([NOTES.md](../../NOTES.md), Jul 10–12). Two things are true
at once:

1. The dev/meta workflow (root `CLAUDE.md` + per-domain `CONTEXT.md` + skills +
   routing table) is ICM-adjacent already, but routes by *domain*, not by
   *stage* — it has no notion of sequence and no review gates. Planning a
   feature means remembering to invoke grill → spec → map → issues → TDD in
   order, and nothing stops you skipping a step.
2. The context files have **drifted from the filesystem**: they cite output
   folders that don't exist and CI that runs deleted code. An ICM workspace
   whose outputs land in those folders can't work until that's fixed.

This spec builds the sequencing layer (§4) and fixes the drift it depends on
(§5). It does **not** touch the runtime idea→gaps pipeline.

## 2. Goals / non-goals

**Goals**
- G1. A `feature-planning` ICM workspace that sequences the existing planning
  skills with review gates, writing outputs into the existing `planning/` tree.
- G2. Fix the map/territory drift the workspace depends on (missing `planning/`
  subdirs, stale weekly CI, unscoped PRD citations).
- G3. Root `CLAUDE.md` routes to the workspace, distinct from the one-off
  routing table.

**Non-goals**
- N1. Do **not** ICM-ify the runtime idea→gaps pipeline. It fails ICM's own fit
  test on concurrency and real-time; it stays service code.
- N2. Do **not** duplicate existing skills into the workspace — invoke them.
  Skills stay single-source in `.agents/skills/`.
- N3. No new orchestration framework, no new runtime deps. Filesystem + one agent.
- N4. Do **not** build the `eval-corpus` workspace yet (Appendix A).

## 3. Cross-cutting design decisions (with rationale)

- **D1 — Container folder is `icm/`, not `workspaces/`.** Root `CLAUDE.md`
  already uses "Workspaces" to mean code domains (`/planning`, `/app`, …). A
  top-level `workspaces/` would collide with that meaning. `icm/` disambiguates
  and leaves room for `icm/eval-corpus/` when it revives.
- **D2 — Repo conventions verbatim, hyphens not underscores.** Everything
  `lowercase-with-hyphens`. (The arXiv prose shows `01_research`; the repo
  `_core/CONVENTIONS.md` mandates hyphens — the repo wins. The documented
  "off by a third" trap.)
- **D3 — One deep document, not five shallow ones.** Four of the five stages
  delegate to an existing skill (N2), and their outputs land in `planning/`,
  not in the workspace. Per-stage folders would therefore have ICM's *shape*
  (`CONTEXT.md` + `references/` + `output/`) with empty `output/` dirs and no
  edit-surface handoff — ICM's form without its mechanic. Five files that each
  say "invoke skill X" are shallow modules by [NOTES.md](../../NOTES.md):11's
  own test (*"interface is nearly as complex as the implementation"*). The
  workspace is one `CONTEXT.md` holding the stage table.
- **D4 — `_config/` holds only what the workflow owns.** One file. Layering
  (`app/CONTEXT.md`) and naming (root `CLAUDE.md`) are cited **by path**, never
  copied — a copy is a drift surface, and neither source is a token monolith
  (root `CLAUDE.md` is ~450 tok and always loaded).
- **D5 — State derives from artifacts on disk.** No progress file. Each stage
  has a checkable output path; which paths exist for a slug tells a resuming
  agent where it is. Nothing to fall out of sync, and it forces every stage to
  produce a real artifact.
- **D6 — The spec file is the maturing artifact.** Stage 01 opens it with §1–§2
  only; stage 02 fills it out. One artifact that matures across the gate, rather
  than a frame document the spec immediately supersedes.
- **D7 — A stage-04 mismatch patches the spec in place; the workflow stays at
  04.** (Closes OQ1.) It does not bounce back to 02 and re-grill. The spec is
  the maturing artifact (D6), and a mismatch surfacing that late is nearly
  always a spec gap rather than a bad frame.
- **D8 — Stage 05's plan lives in the issue body, and stage 05 is plan-only.**
  (Closes OQ2.) The `tdd` plan is per-issue anyway and issues are where an
  implementer looks, so there is no `impl-plan.md` and no new path convention.
  Stage 05 invokes `tdd` §1 (planning) only and stops; the red-green loop runs
  during implementation, which re-enters via root `CLAUDE.md`'s routing table.
  Without that exit marker an agent runs the loop inside the *planning*
  workspace.

## 4. The workspace — `icm/feature-planning/`

**Purpose:** turn a friction note into a reviewed spec, architecture map,
tracer-bullet issues, and a TDD plan — by **sequencing existing skills**, not
replacing them.

### 4.1 Tree
```
icm/feature-planning/
  CONTEXT.md              # the workflow: stage table + how-to-resume + gates
  _config/
    feature-questions.md  # the 6 core-feature questions (NOTES.md, May 11)
```

`feature-questions.md` is the only file whose content exists nowhere else in the
repo. Everything else the workflow needs is cited by path.

### 4.2 Stages

`<slug>` is the feature name in root `CLAUDE.md`'s convention
(`feature-name_spec.md`).

| # | Stage | Invokes | Artifact | Gate |
|---|-------|---------|----------|------|
| 01 | **Frame** | `_config/feature-questions.md` | `planning/specs/<slug>_spec.md`, **§1 Context + §2 Goals/non-goals only**, status draft | **Heavy** — directional. The workflow adds this gate. |
| 02 | **Spec** | `grill-with-docs` skill | same file, filled out | built into the skill (it is an interview) |
| 03 | **Map** | `map-architecture` skill | `planning/architecture/YYYY-MM-DD-<slug>.md` | light verify |
| 04 | **Issues** | `to-issues` skill | GitHub issues titled `[spec: <slug>]` | built into the skill (step 4 quizzes on the slice breakdown) |
| 05 | **Impl plan** | `tdd` skill (**§1 planning only**) | TDD plan folded into each `[spec: <slug>]` issue body | light verify |

There is no `impl-plan.md` — stage 05's plan goes where an implementer actually
looks, in the issue body (D8). Stage 05 is **plan-only**: it does not enter the
`tdd` red-green loop. Implementation re-enters via root `CLAUDE.md`'s routing
table once an issue is grabbed.

**Gate design.** Only stage 01 needs a gate the workflow itself enforces —
02 and 04 are interactive inside their skills, and 03/05 are verify-only. This
is why the workflow is thin: most of its value is *ordering* plus one gate the
routing table can't express.

The 6 questions at stage 01 (NOTES.md:17-23) — why build it, what are we
building, how well must it work, how do systems talk, what data is involved,
**should this be built at all** — make 01 a genuine kill gate, not a formality.

### 4.3 How to resume

`CONTEXT.md` carries a "how to resume" section stating the check, in order:

| Check | ⇒ next stage |
|-------|--------------|
| `planning/specs/<slug>_spec.md` absent | 01 |
| exists, only §1–§2 filled | 02 |
| complete | 03 |
| `planning/architecture/*-<slug>.md` exists | 04 |
| `gh issue list --search "[spec: <slug>]"` non-empty | 05 |

The "complete ⇒ 03" row is a heuristic on the artifact, and it cannot tell a
spec this workflow produced from one authored outside it. `CONTEXT.md`
therefore carries the exception: **a complete spec that stages 01–02 did not
produce enters at 01 as a confirm-pass** — the six questions walked against
what the spec already says, ending in explicit approval — because otherwise
the kill gate never fires. (Sibling of the F13 drift; surfaced by the
2026-07-22 run.)

## 5. Drift fixes (prerequisites)

- **U1 — Create `planning/decisions/` and `planning/architecture/`.**
  Referenced by `planning/CONTEXT.md`, the `write-adr` and `map-architecture`
  skills, and `frontend/CONTEXT.md`'s ADR citation — none exist. Stage 03 writes
  to `architecture/`, so this is load-bearing. (`planning/specs/` now exists.)
- **U2 — Delete `.github/workflows/weekly-youtube.yml` and
  `weekly-appstore.yml`.** Both invoke `python -m ops.scripts.weekly*`, and
  `ops/scripts/` was deleted in the v1→v2 teardown. Last successful run
  2026-05-24, before slice 3 shipped 2026-06-11. Dead CI pointing at dead code,
  still cron-scheduled `0 8 * * 0`. `test.yml` stays.
- **U3 — Scope the PRD citations.** All four `CONTEXT.md` files name the
  ~11k-token `docs/PRD.md` as "Authority" with no section pointer, so an agent
  following the citation loads a monolith — the exact 30k–50k cluttered-context
  failure ICM warns about, and stage 02 is the stage that would follow it.
  Change each Authority line to name the sections that file summarises (e.g.
  `PRD §7.5–7.9, §10.1`). Four one-line edits. **No extraction** — the PRD stays
  intact as human reference, and no constraint gets a second home.

## 6. Integration

- **I1.** Add an `## ICM Workspaces` section to root `CLAUDE.md`, distinct from
  the code-domain `## Workspaces` list, describing `icm/feature-planning` and
  when to enter it.
- **I2.** Add a routing-table row: `Plan a feature end-to-end → icm/feature-planning
  → its CONTEXT.md`.
- **I3.** State the relationship: the routing table is for **one-off** tasks; the
  workspace is for the **sequenced, gated** version of the same work.

## 7. Build sequence (tracer-bullet slices, ready for `to-issues`)

- **Slice 0 — drift fix:** U1 + U2 + U3. Small, unblocks everything, makes the
  map match the territory. No ICM content yet.
- **Slice 1 — build the workspace:** `icm/feature-planning/CONTEXT.md` +
  `_config/feature-questions.md`. Verifiable by reading top-to-bottom.
- **Slice 2 — integrate:** I1–I3 into root `CLAUDE.md`.
- **Slice 3 — first real run:** drive issue
  [#76](https://github.com/jdavi977/Trend-Insight-Engine/issues/76) ("Scope down
  to the core pipeline") through all five stages. Chosen because it is the
  declared critical path — `eval-corpus` is blocked on it — so the workflow's
  first output is a plan that was needed anyway, not dogfood. A removal also
  stresses the workflow usefully: "what breaks if I cut this" is exactly the
  question an architecture map answers.

## 8. Acceptance criteria

- **A1.** Given only root `CLAUDE.md`, a fresh agent finds the workspace, enters
  it, and plans issue #76 through all five stages — pausing at the 01 gate,
  invoking (not reimplementing) each skill, landing artifacts at the §4.2 paths.
- **A2.** Dropped into a half-finished feature, a fresh agent determines the
  correct next stage from the §4.3 disk checks alone.
- **A3.** `planning/{specs,decisions,architecture}/` all exist; no weekly CI is
  scheduled; every `CONTEXT.md` Authority line names PRD sections, not the file.
- **A4.** Workspace context stays within ICM's 2–8k token budget.

## 9. Open questions / risks

- ~~**OQ1 — Gate rejection loop.**~~ **Closed at Slice 1 → D7.** A stage-04
  mismatch patches the spec in place and stays at 04.
- ~~**OQ2 — Where does `impl-plan.md` live?**~~ **Closed at Slice 1 → D8.** It
  does not exist; the plan folds into each `[spec: <slug>]` issue body, and
  stage 05 is plan-only.
- **R1 — The stage table is shaped for additions; #76 is a removal.** Expected to
  expose a gap on the first run. That is a reason to run it, not to avoid it —
  but budget for amending `CONTEXT.md` after Slice 3.

---

## Appendix A — `eval-corpus` workspace (deferred)

**Status: deferred** until the pipeline scope-down (#76) lands. Recorded here so
the grilling isn't lost.

**Intent.** An ICM workspace that grows the golden seed set 5 → 15–20 ideas, one
idea per run, with a human labelling gate, producing fixtures that
[app/eval/harness.py](../../app/eval/harness.py) /
[metrics.py](../../app/eval/metrics.py) and the v1.1 CI regression gate consume —
making "is this pipeline change better or worse?" an objective question.

**Proposed stages.** `01-select-idea` → `02-run-capture` (script: `harness.py`,
no AI) → `03-label-gaps` (AI + heavy human gate) → `04-score` (`metrics.py`) →
`05-commit-to-corpus`.

**Decided during the grill:**

- **A-D1 — Stage 01 writes a stub seed.** `harness.load_seed(name)` requires
  `app/eval/seed/<name>.json` to exist *before* the run, but stage 05 is what
  authors the fixture — the sequence as originally specced cannot execute.
  Resolution: stage 01 emits a stub seed (`idea`, `target_gap`, `category`,
  `expected_gaps: []`) alongside the idea brief; stage 05 fills in
  `expected_gaps` and flips `label_status` to `human_reviewed`. **No code
  change** — `expected_gaps` is already `Field(default_factory=list)` and
  `label_status` already defaults to `agent_drafted`. Recall simply scores 0-of-0
  at stage 02, which is ignored there.
  (Caveat to handle: a stub in `seed/` is indistinguishable from a finished-but-empty
  fixture to anything that globs the directory. Consider `seed/_pending/`.)

**Unresolved — the blocking question:**

- **A-OQ1 — What should stage 03 label, and what should the fixture store?**
  As originally specced, the workspace's *heaviest* human gate spends most of its
  effort on output nothing consumes:

  | Labelled at 03 | Consumer today |
  |---|---|
  | genuine gaps + missed gaps (text) | `gap_recall` ✅ |
  | corrected severity | none — `severity_range` is *recorded in the report*, not scored; calibration is run-level from `quality_signals` |
  | grounding `quote_id`s | none — `hallucination_count` already checks pool membership mechanically, and production's synthesis validator rejects violations pre-persist |
  | noise / duplicate marks | none — there is no precision scorer |

  Options considered: (a) recall + precision, dropping the human `quote_id`
  re-check but keeping the one judgment a machine can't make — *do the cited
  quotes actually support the claim*; (b) recall only, zero code change, but
  blind to precision regressions; (c) full rich labels with an extended schema;
  (d) rich prose labels, distilling only the machine-scorable subset into `seed/`.

  Context for whoever decides: the July 10–12 friction is mostly **yield** —
  empty quote pools, gaps rejected under the 2-citation bar, comments filtering
  to `[]`. Those surface as *recall misses*, so recall is the right primary
  metric and (b) is not as weak as it looks.

- **A-OQ2 — Does `02` hit live APIs?** `harness.py` drives the real pipeline
  (real pre-flight, ingestion, extraction, synthesis; only the terminal Supabase
  writes are intercepted). Live = cost + nondeterminism. Proposal: `02` runs live
  **once** and freezes the capture; `03`/`04` and CI replay the frozen fixture.
  Note this **does** need code — the harness writes reports to a gitignored
  `reports/` dir and has no replay path — which conflicts with N3.
