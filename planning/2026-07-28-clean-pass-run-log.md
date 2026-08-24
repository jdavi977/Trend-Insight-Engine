# Run log: demonstrated clean pass (G4 / A8)

> Evidence for [#85](https://github.com/jdavi977/Trend-Insight-Engine/issues/85),
> the exit gate of
> [engineering-standards-alignment_spec.md](specs/engineering-standards-alignment_spec.md)
> (§6 Slice 5, A8). The same run satisfies
> [#79](https://github.com/jdavi977/Trend-Insight-Engine/issues/79), Slice 3 of
> [feature-planning-workspace_spec.md](specs/feature-planning-workspace_spec.md) —
> both specs ask for one real task routed cold from root `CLAUDE.md`, so it was run
> once and cross-referenced rather than dogfooded twice. That covers A1; A2 (the
> resume path) is a separate check, added as Step 5.
>
> Verdict: **pass.** Zero dead-end routes, contradictions, or missing skills on the
> route taken. Four drift findings filed off-route as #91–#94.

## Step 1 — static check (`engineering-standards-alignment` A2)

```
$ make check-refs
venv/bin/python scripts/check_context_refs.py
check-refs: 5 file(s) checked, every reference resolves.
```

Green. Necessary but not sufficient — A2 proves the graph *resolves*, A8 proves it
is *usable*.

> **Two different A2s.** Unqualified "A2" in this log means
> `engineering-standards-alignment`'s A2 (the reference check above).
> `feature-planning-workspace`'s A2 — *a fresh agent determines the correct next
> stage from the §4.3 disk checks alone* — is a separate criterion, covered in
> Step 5.

## Step 2 — the task

[#76](https://github.com/jdavi977/Trend-Insight-Engine/issues/76), "Scope down to
the core pipeline." Non-trivial by construction: subtractive, cross-layer
(`app/`, `frontend/`, `docs/`, Supabase), and on the declared critical path, so the
first output of the workspace was a plan that was needed anyway. A removal also
stresses the workflow usefully — *what breaks if I cut this* is what an
architecture map is for.

## Step 3 — the route taken

Entered cold at root [CLAUDE.md](../CLAUDE.md) → Routing Table → row *"Plan a
feature end-to-end (gated)"* → `/icm/feature-planning` → read
[icm/feature-planning/CONTEXT.md](../icm/feature-planning/CONTEXT.md).

| Stage | Invoked | Artifact landed | Resolved? |
|---|---|---|---|
| 01 Frame | [`_config/feature-questions.md`](../icm/feature-planning/_config/feature-questions.md) (6 questions) | [`specs/scope-down-core-pipeline_spec.md`](specs/scope-down-core-pipeline_spec.md) §1–§2, status draft | ✅ |
| 01 gate (heavy) | HITL kill gate, Q6 *"should this be built?"* | approved — recorded in the spec's status banner as a **subtractive engagement** | ✅ |
| 02 Spec | `grill-with-docs` skill | same file filled to §9, status **grilled (2026-07-26)** | ✅ |
| 03 Map | `map-architecture` skill | [`architecture/2026-07-26-scope-down-core-pipeline.md`](architecture/2026-07-26-scope-down-core-pipeline.md) | ✅ |
| 04 Issues | `to-issues` skill | #86–#90, titled `[spec: scope-down-core-pipeline]`, parent #76 (2026-07-27 03:38Z) | ✅ |
| 05 Impl plan | `tdd` skill, Workflow §1 Planning only | TDD plan folded into all five issue bodies — no separate `impl-plan.md` | ✅ |

Stage 04 exercised the workspace's *"when stage 04 disagrees with the spec"* rule
as designed: the slice breakdown was patched back into the spec in place as
[§10 Issue slices](specs/scope-down-core-pipeline_spec.md), without bouncing to
stage 02 to re-grill.

**Handoff back through the routing table.** Stage 05 ends the workspace;
implementation re-entered at root `CLAUDE.md` per domain — `/app` (`tdd` red-green,
`python-code-review`), `/frontend` (`frontend-component-standards`), `/docs`.
Commits `a2d33a2..74f23ef` on `scope-down`; #86–#90 and #76 all closed
2026-07-27/28. Suite green afterwards: **253 passed**.

The workspace's *"invoke skills, never copy them"* rule held — `git diff
--name-only a2d33a2~1..74f23ef` touches no path under `.claude/`.

## Step 4 — findings

**On the route: zero.** Every routing-table row, every stage's skill, and every
artifact path resolved. Naming conventions agreed end to end (`feature-name_spec.md`,
`YYYY-MM-DD-topic.md`, `[spec: <slug>]`), and no two documents contradicted each
other on where an artifact belongs.

**Off the route, filed not fixed** (#85's fourth acceptance criterion — silent
fixes break the audit trail):

| # | Finding | Class |
|---|---|---|
| [#91](https://github.com/jdavi977/Trend-Insight-Engine/issues/91) | `to-issues:10` sends the agent to `/setup-matt-pocock-skills`; no such command | dangling command |
| [#92](https://github.com/jdavi977/Trend-Insight-Engine/issues/92) | `tdd:47`, `to-issues:20`, `triage:63`, `improve-codebase-architecture:35` all cite a "project domain glossary" that has no home | dangling doc (F4 class, prose) |
| [#93](https://github.com/jdavi977/Trend-Insight-Engine/issues/93) | `triage:63` reads `.out-of-scope/*.md`; the directory does not exist | dangling path |
| [#94](https://github.com/jdavi977/Trend-Insight-Engine/issues/94) | `check-refs` stops at the five `DEFAULT_ROOTS` and never follows the routing table into `icm/feature-planning/` | gap in A2's guard |

None blocked the run. #91 sits on a conditional branch the run never took (this
repo's label vocabulary *is* provided); #92 was worked around by reading
`planning/CONTEXT.md` for domain vocabulary; #93 and #94 are off the planning
route entirely. All four share a shape: **prose pointers a link-checker cannot
see** — which is the argument for A8 existing alongside A2.

Checked by hand, clean, and therefore not filed:

```
$ venv/bin/python scripts/check_context_refs.py \
    icm/feature-planning/CONTEXT.md icm/feature-planning/_config/feature-questions.md
check-refs: 2 file(s) checked, every reference resolves.
```

One cosmetic imprecision, recorded rather than filed: `icm/feature-planning/CONTEXT.md`
cites the `tdd` skill as "§1 planning only" and "§2–4", which are subsections of
that skill's `## Workflow`, not top-level sections. Unambiguous in practice — the
subsections are numbered 1–4 and named *Planning, Tracer Bullet, Incremental Loop,
Refactor* — so it misdirects nobody, but it is a citation that does not match the
cited file's structure. Fold into #92's pass over skill call sites if that issue is
taken up.

## Step 5 — the resume path (`feature-planning-workspace` A2)

Steps 1–4 cover A1 — the route *forward*. A2 asks a different question: dropped into
a feature already in progress, with no conversation history, does an agent land on the
right stage from disk alone? Run 2026-07-28, after implementation had already handed
back.

Applied the "How to resume" ladder in
[icm/feature-planning/CONTEXT.md](../icm/feature-planning/CONTEXT.md) to slug
`scope-down-core-pipeline`:

| Check | Result |
|---|---|
| spec absent | ✗ — `specs/scope-down-core-pipeline_spec.md` exists |
| only §1–§2 filled | ✗ — all 10 sections written |
| complete ⇒ 03 | ✗ — `architecture/2026-07-26-scope-down-core-pipeline.md` exists |
| map exists ⇒ 04 | ✗ — #86–#90 published |
| issues exist ⇒ 05 | ✗ — all five carry `## TDD plan (stage 05 — plan only)` |
| issues carry a TDD plan | ✅ ⇒ **done** |

Correct answer, from `ls` + `gh issue list` + the issue bodies, with no memory of the
run. The agent also correctly *declined* the
*"specs authored outside this workflow enter at 01, not 03"* confirm-pass, reading the
spec's status banner (`framed + grilled via the feature-planning workspace (stages
01–02)`) as proof the kill gate had already fired. That branch existing and being
skipped on the right evidence is the useful part — the trap it guards is a spec that
*looks* complete to the ladder but never passed a gate.

**Deviation from the wording, recorded not re-run.** #79 specifies dropping the agent
in *"partway through"*; this ran at the terminal state. It therefore evaluated all six
rows to exhaustion rather than stopping at the first match — broader coverage of the
ladder, but not literally the mid-run drop-in asked for. A mid-run instance comes free
on the next feature routed through the workspace.

## What this pass proves, and what it does not

Proves the routing graph is *usable*: one real task, cold entry, five stages, an
implementable handoff, zero dead-ends — the dynamic half of the verification that
a grep cannot give. Step 5 adds the other direction: the graph is also *re-enterable*
mid-feature, from disk, with no memory.

Does not prove code/CI/config conformance to
[docs/engineering-standards.md](../docs/engineering-standards.md); that is the
`engineering-standards-tooling` follow-on spec's job (N6), and A5's CI wiring is
explicitly relocated there. Nor does it prove the routing table is complete for
tasks nobody has tried yet — one clean pass is evidence, not a proof of totality.
