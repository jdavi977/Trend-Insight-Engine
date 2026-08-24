# Spec: ICM Workspaces (eval-corpus + feature-planning) + existing-workspace update

> **⚠️ SUPERSEDED (2026-07-21) — do not plan from this file.** Replaced by
> [feature-planning-workspace_spec.md](feature-planning-workspace_spec.md),
> the post-grill version, which specs the `feature-planning` workspace only and
> **defers** the `eval-corpus` workspace to its Appendix A. This file is kept
> for history; the two-workspace scope below is no longer the plan.

> Status: draft (2026-07-20), superseded. Authority for ICM structure: the reference repo
> [RinDig/Interpreted-Context-Methdology](https://github.com/RinDig/Interpreted-Context-Methdology)
> `_core/CONVENTIONS.md` + arXiv 2603.16021 v2. Companion analysis:
> [../2026-07-20-icm-workflow-comparison.md](../2026-07-20-icm-workflow-comparison.md).
> This spec covers building two ICM workspaces and updating the repo's existing
> context system so it routes to them and stops contradicting itself.

## 1. Context / why now

v1 (v2.2) shipped 2026-06-11. The repo is now in a **reliability-hardening /
scope-down** phase (see [NOTES.md](../../NOTES.md), Jul 10–12): filter
miscalibration, empty quote pools, grounding-bar rejections, and a recurring
"is this change better or worse?" question that has no objective answer today.
The eval harness existed at the time of writing (`app/eval/harness.py`,
`metrics.py`) but the labelled seed set was only 5 ideas and labelling was
manual — the harness was deleted outright on 2026-07-27 (#87), which is part of
why this spec is superseded. Two sequential, reviewable, repeatable authoring
loops are worth turning into ICM workspaces; the live idea→gaps pipeline is
**not** (it is concurrent/real-time — ICM-excluded, stays as service code).

## 2. Goals / non-goals

**Goals**
- G1. An `eval-corpus` ICM workspace that grows the golden seed set 5 → 15–20
  ideas, one idea per run, with a human labelling gate, producing fixtures that
  `harness.py`/`metrics.py` and the (v1.1) CI regression gate consume.
- G2. A `feature-planning` ICM workspace that sequences the existing planning
  skills (grill → spec → arch-map → issues → TDD plan) with review gates,
  writing outputs into the existing `planning/` tree.
- G3. Update the **currently-created workspace** (root `CLAUDE.md` + domain
  `CONTEXT.md` + skills + routing table) to (a) route to the two new workspaces
  and (b) fix the map/territory drift the new workspaces depend on.

**Non-goals**
- N1. Do **not** ICM-ify the runtime idea→gaps pipeline.
- N2. Do **not** duplicate existing skills into the workspaces — invoke them.
- N3. No new orchestration framework, no new runtime deps. Filesystem + one agent.

## 3. Cross-cutting design decisions (with rationale)

- **D1 — Container folder is `icm/`, not `workspaces/`.** Root `CLAUDE.md`
  already uses "Workspaces" to mean code domains (`/planning`, `/app`, …).
  A top-level `workspaces/` would collide with that meaning. Use `icm/` to
  disambiguate: `icm/eval-corpus/`, `icm/feature-planning/`. Kept out of `app/`.
- **D2 — Follow the repo conventions verbatim, hyphens not underscores.** Stage
  folders `NN-name` (`01-select-idea`), everything `lowercase-with-hyphens`.
  (The arXiv prose shows `01_research`; the repo `_core/CONVENTIONS.md` mandates
  hyphens — the repo wins. This is the documented "off by a third" trap.)
- **D3 — Each workspace is self-contained** with root `CLAUDE.md` (L0) +
  routing `CONTEXT.md` (L1) + `stages/NN-*/` (each = `CONTEXT.md` + `references/`
  + `output/`) + `_config/` (L3 factory) + `shared/` + `skills/` + `setup/`.
- **D4 — Layer 3 is the human-facing authority, code is the enforcement.** e.g.
  `_config/rubric.md` states the severity 1–5 rubric a human labeller applies; it
  points to `config/constants.py` as the enforced source. Drift risk is real —
  see Open Question OQ1.
- **D5 — Scripts do the mechanical work, agent stages do judgment.** `harness.py`
  is wired in as a stage *script* (no AI); labelling/scoring/framing are agent
  stages. This is the ICM split, not new code.
- **D6 — Stage contract = the verified 3-section format** (Inputs table /
  Process steps / Outputs table), with each stage's Inputs pointing at the prior
  stage's `output/` to enforce the path.

## 4. Workspace A — `icm/eval-corpus/`

**Purpose:** add one labelled idea to the golden corpus per run; make "is this
pipeline change better or worse?" an objective, reviewable question.

### 4.1 Tree
```
icm/eval-corpus/
  CLAUDE.md                      # L0: identity, folder map, hyphen conventions, routing table
  CONTEXT.md                     # L1: task routing → which stage for "add an idea" / "re-score"
  stages/
    01-select-idea/CONTEXT.md    # + references/ output/
    02-run-capture/CONTEXT.md    # SCRIPT stage (harness.py); no AI
    03-label-gaps/CONTEXT.md     # AI; HUMAN edit gate (heavy)
    04-score/CONTEXT.md          # metrics.py vs gold labels
    05-commit-to-corpus/CONTEXT.md
  _config/
    rubric.md                    # severity 1–5 (human-facing; cites config/constants.py)
    grounding-rules.md           # ≥2 citations, quote_id-in-pool (PRD §7.7)
    metrics.md                   # the 4 scorers (PRD §7.9): recall, hallucination, citation, calibration
    corpus-coverage-goals.md     # target 15–20 ideas across categories + signal levels
  shared/harness-usage.md        # how to invoke app/eval/harness.py + metrics.py
  setup/questionnaire.md
```

### 4.2 Stages (job → key input → output → gate)
| Stage | Job | Key input | Output | Human gate |
|-------|-----|-----------|--------|------------|
| `01-select-idea` | Pick + frame an idea the corpus is missing (a signal level / category not yet covered) | `_config/corpus-coverage-goals.md`, current corpus index | `idea-brief.md` | **Heavy** (directional) |
| `02-run-capture` | **Script:** run `harness.py` on the idea; freeze raw gaps + full quote pool + coverage | `01/output/idea-brief.md` | `run-output.json` + `run-output.md` | none (mechanical) |
| `03-label-gaps` | **AI:** propose gold labels — genuine vs noise gaps, correct severity, grounding quote_ids, and gaps the pipeline *missed* | `02/output/*`, `_config/rubric.md`, `_config/grounding-rules.md` | `gold-labels.md` | **Heavy** (the corpus's whole value) |
| `04-score` | Run `metrics.py`: pipeline output vs approved gold labels; narrate divergences | `02/output/run-output.json`, `03/output/gold-labels.md`, `_config/metrics.md` | `scorecard.md` | Light-verify |
| `05-commit-to-corpus` | Normalise gold labels into the `seed/` fixture format; append; update corpus index | `03/output/gold-labels.md` | `seed/<slug>.json`, updated `corpus-index.md` | Light-verify |

### 4.3 Representative stage contract — `stages/03-label-gaps/CONTEXT.md`
```markdown
## Inputs
| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| L4 working | ../02-run-capture/output/run-output.md | full | the pipeline's candidate gaps + quote pool to judge |
| L4 working | ../02-run-capture/output/run-output.json | gaps[], quotes[] | machine-readable for exact quote_id refs |
| L3 reference | ../../_config/rubric.md | full | severity 1–5 definitions to label against |
| L3 reference | ../../_config/grounding-rules.md | full | a gap is valid only if ≥2 quote_ids from the pool cite it |

## Process
1. For each candidate gap, mark genuine | noise | duplicate, with a one-line reason.
2. Assign the correct severity per rubric.md (do not copy the pipeline's).
3. List the quote_ids that legitimately ground each genuine gap.
4. Add any REAL gaps the pipeline missed (these drive the recall metric).
5. Write gold-labels.md. Stop for human review before stage 04.

## Outputs
| Artifact | Location | Format |
|----------|----------|--------|
| gold-labels.md | output/ | markdown, one block per gap |
```

## 5. Workspace B — `icm/feature-planning/`

**Purpose:** turn a friction note / idea into a reviewed spec, architecture map,
and tracer-bullet issues — by **sequencing existing skills**, not replacing them.

### 5.1 Tree
```
icm/feature-planning/
  CLAUDE.md
  CONTEXT.md
  stages/
    01-frame/CONTEXT.md
    02-spec/CONTEXT.md
    03-architecture-map/CONTEXT.md
    04-issues/CONTEXT.md
    05-implementation-plan/CONTEXT.md
  _config/
    feature-questions.md         # the 6 core-feature questions from NOTES.md (May 11)
    layer-boundaries.md          # api→services rule etc. (cites app/CONTEXT.md)
    naming-conventions.md        # cites root CLAUDE.md
  skills/registry.md             # pointers to the repo skills each stage INVOKES
  shared/  setup/questionnaire.md
```

### 5.2 Stages
| Stage | Job | Invokes | Output (lands in) | Human gate |
|-------|-----|---------|-------------------|------------|
| `01-frame` | Friction/idea → framed problem (value, in/out) | `_config/feature-questions.md` | `problem-frame.md` | **Heavy** (directional) |
| `02-spec` | Grill the frame into a spec | `grill-with-docs` skill | `feature-name_spec.md` → `planning/specs/` | Review |
| `03-architecture-map` | Data-flow / dependency / failure map | `map-architecture` skill | `…map.md` → `planning/architecture/` | Light |
| `04-issues` | Break spec into tracer-bullet vertical slices | `to-issues` skill | issues (tracker or `issues.md`) | **Review** (plan vs spec) |
| `05-implementation-plan` | Per-issue TDD red-green-refactor + layer touchpoints | `tdd` skill, `_config/layer-boundaries.md` | `impl-plan.md` | Light-verify |

**Key contract detail:** stage `02`–`05` Process sections say "invoke the `<skill>`
skill" — the skills stay single-source in `.agents/skills/`; the workspace only
*sequences* them and adds the review gates between. Outputs deliberately land in
the existing `planning/` tree (which is why §6 must create those dirs first).

## 6. Update the currently-created workspace

The existing repo context system (root `CLAUDE.md` + domain `CONTEXT.md` +
skills + routing table) must change in two ways.

### 6.1 Integration (make the orchestrating agent aware)
- **U1.** Add an `## ICM Workspaces` section to root `CLAUDE.md`, distinct from
  the code-domain `## Workspaces` list, describing `icm/eval-corpus` and
  `icm/feature-planning` and when to enter each.
- **U2.** Add routing-table rows: `Grow the eval corpus → icm/eval-corpus → its
  CONTEXT.md`; `Plan a feature end-to-end → icm/feature-planning → its CONTEXT.md`.
- **U3.** Note the relationship: the routing table stays for **one-off** tasks;
  the ICM workspaces are for the **sequenced, gated** versions of those tasks.

### 6.2 Drift fixes (prerequisites — the map must match the territory)
- **U4.** Create `planning/specs/`, `planning/decisions/`, `planning/architecture/`.
  They are referenced by `planning/CONTEXT.md`, the `write-adr` and
  `map-architecture` skills, and `frontend/CONTEXT.md`'s ADR citation, but don't
  exist. **feature-planning writes its outputs here — load-bearing.** (Writing
  this spec already created `planning/specs/`.)
- **U5.** Resolve the stale weekly CI: `.github/workflows/weekly-youtube.yml` +
  `weekly-appstore.yml` are still cron-scheduled though the weekly pipeline was
  removed in the v1→v2 pivot. Delete or disable. (The factory contradicts docs.)
- **U6 (optional).** Extract a sub-2k-token L3 from the 44 KB `PRD.md` (severity
  rubric, model-routing table, layer rule, PII policy) so workspaces/skills stop
  pointing at a monolith. Shared by `eval-corpus/_config/` and code alike.

## 7. Build sequence (tracer-bullet slices, ready for `to-issues`)

- **Slice 0 — drift fix:** U4 + U5. Small, unblocks everything, map matches
  territory. No ICM content yet.
- **Slice 1 — scaffold `icm/` + eval-corpus skeleton:** full tree, `CLAUDE.md`,
  routing `CONTEXT.md`, all five stage `CONTEXT.md` contracts written, `_config/`
  populated. Empty `output/`. Verifiable by reading top-to-bottom.
- **Slice 2 — eval-corpus vertical slice (one idea end-to-end):** wire
  `harness.py` into `02`, real `03` labelling with the human gate, `04` score,
  `05` commit → a valid `seed/` fixture `metrics.py` accepts. Proves the pipeline.
- **Slice 3 — feature-planning workspace:** scaffold + `skills/registry.md`, run
  once on a real friction note from `NOTES.md` → spec in `planning/specs/`.
- **Slice 4 — integrate:** U1–U3 into root `CLAUDE.md`; validate a cold agent
  can enter each workspace from `CLAUDE.md` alone and follow the path.

## 8. Acceptance criteria

- **A1 (eval-corpus):** given only `icm/eval-corpus/CLAUDE.md`, a fresh agent
  runs all five stages on a new idea, pausing for human edit at `03`, and emits a
  `seed/` fixture `harness.py` consumes + `metrics.py` scores. Corpus index
  reflects the addition. Per-stage context stays within 2–8k tokens.
- **A2 (feature-planning):** given a friction note, a fresh agent produces a spec
  in `planning/specs/`, a map in `planning/architecture/`, and tracer-bullet
  issues — by invoking existing skills, not duplicating them.
- **A3 (existing workspace):** root `CLAUDE.md` routes to both; the three
  `planning/` subdirs exist; no weekly CI scheduled; a new contributor reading
  `CLAUDE.md` can find the ICM workspaces and know when to use them.

## 9. Open questions / risks

- **OQ1 — L3 duplication (rubric/metrics live in both `_config/` and code).**
  Proposal: `_config/` is the human-labelling authority and cites the code
  constant; revisit generating one from the other. Decide before Slice 1.
- **OQ2 — Does eval-corpus `02` hit live APIs?** Live YouTube/AppStore/OpenAI =
  cost + nondeterminism. Proposal: `02` runs live **once** and freezes the
  capture; `03`/`04` and CI replay the frozen fixture, never live. Decide before
  Slice 2. (Biggest risk.)
- **OQ3 — Does `feature-planning/04` create real tracker issues** (`to-issues`
  behaviour) or just `issues.md`? Depends on tracker setup. Decide before Slice 3.
- **OQ4 — PRD extraction (U6) scope.** Optional; skip if it balloons.

## 10. Next step in your own workflow

Per the routing table this spec is now grill-able (`grill-me` / `grill-with-docs`)
and sliceable (`to-issues`). Recommend grilling OQ1–OQ2 first, then `to-issues`
on §7 to generate the build tickets.
