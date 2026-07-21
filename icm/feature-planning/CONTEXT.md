# Workspace: feature-planning

Turns a friction note into a reviewed spec, an architecture map, tracer-bullet
issues, and a TDD plan — by **sequencing skills that already exist**, with one
review gate the routing table can't express.

Authority: [planning/specs/feature-planning-workspace_spec.md](../../planning/specs/feature-planning-workspace_spec.md)
(§4, §6). That spec governs; this file is the operating procedure.

## When to enter this workspace

Enter when planning a feature **end-to-end** — from "this is friction" to issues
someone can grab. For one-off planning work (just a grill, just an architecture
map, just breaking an existing spec into issues), use root
[CLAUDE.md](../../CLAUDE.md)'s routing table and invoke the skill directly.
This workspace is the sequenced, gated version of the same work, not a
different set of tools.

`<slug>` throughout is the feature name in root `CLAUDE.md`'s convention —
the `feature-name` in `feature-name_spec.md`.

## Rules

- **Invoke skills, never copy them.** Each stage below names a skill; read it
  from `.claude/skills/<name>/SKILL.md` and follow it as written. Nothing in
  this workspace restates a skill's instructions, and no stage edits
  `.claude/skills/`.
- **Cite, don't duplicate.** Layering rules live in
  [app/CONTEXT.md](../../app/CONTEXT.md), naming conventions and the tech stack
  in root [CLAUDE.md](../../CLAUDE.md), pipeline flow and constraints in
  [planning/CONTEXT.md](../../planning/CONTEXT.md). Read them by path. A second
  copy is a drift surface.
- **Every stage leaves an artifact on disk (or on the tracker).** That artifact
  *is* the progress record — see "How to resume".

## Stages

| #  | Stage         | Invokes                        | Artifact                                                                              | Gate                                       |
|----|---------------|--------------------------------|---------------------------------------------------------------------------------------|--------------------------------------------|
| 01 | **Frame**     | [`_config/feature-questions.md`](_config/feature-questions.md) | `planning/specs/<slug>_spec.md` — **§1 Context + §2 Goals/non-goals only**, status draft | **Heavy** — directional. Enforced here (below). |
| 02 | **Spec**      | `grill-with-docs` skill        | the same file, filled out                                                             | built into the skill — it is an interview  |
| 03 | **Map**       | `map-architecture` skill       | `planning/architecture/YYYY-MM-DD-<slug>.md`                                          | light verify                               |
| 04 | **Issues**    | `to-issues` skill              | GitHub issues titled `[spec: <slug>]`                                                 | built into the skill — its step 4 quizzes on the breakdown |
| 05 | **Impl plan** | `tdd` skill                    | TDD plan folded into each `[spec: <slug>]` issue body                                 | light verify                               |

The spec file is the maturing artifact: stage 01 opens it with §1–§2 only,
stage 02 fills it out. There is no separate frame document, and no
`impl-plan.md` — stage 05's plan goes where an implementer actually looks, in
the issue body.

Run stages in order. The value of this workspace is the ordering plus the 01
gate; skipping a stage forfeits both.

### Stage 01 gate (heavy)

Work through all six questions in
[`_config/feature-questions.md`](_config/feature-questions.md) with the user,
one at a time. Then **stop and present** the drafted §1 + §2 and wait for
explicit approval before writing anything further.

This is a real kill gate. Question 6 — *should this feature be built at all?* —
is allowed to end the workflow: if the answer is no, record why in
[NOTES.md](../../NOTES.md) and stop. Do not soften a "no" into a smaller
feature without the user saying so.

### Stage 03 and 05 verify

Light: confirm the artifact exists at the path in the table, that it names real
files/paths, and that it doesn't contradict the spec. No user gate.

### When stage 04 disagrees with the spec

If the slice breakdown at stage 04 doesn't match the spec, **patch the spec in
place and stay at 04.** Do not bounce back to stage 02 and re-grill. The spec is
the maturing artifact, and a mismatch surfacing this late is nearly always a
spec gap rather than a bad frame — amend `planning/specs/<slug>_spec.md`, note
what changed, and continue slicing.

## How to resume

There is no progress file. State derives from what exists on disk. Run these
checks in order and stop at the first one that matches:

| Check                                                            | ⇒ next stage |
|------------------------------------------------------------------|--------------|
| `planning/specs/<slug>_spec.md` absent                            | 01           |
| exists, only §1–§2 filled                                         | 02           |
| complete (all sections written)                                   | 03           |
| `planning/architecture/*-<slug>.md` exists                        | 04           |
| `gh issue list --search "[spec: <slug>]"` returns issues          | 05           |
| those issues carry a TDD plan section                             | done         |

```bash
ls planning/specs/<slug>_spec.md planning/architecture/*-<slug>.md 2>/dev/null
gh issue list --search "[spec: <slug>]"
```

Stage 05 has no file artifact by design — its resume check is "the
`[spec: <slug>]` issues carry a plan section", not a path on disk.
