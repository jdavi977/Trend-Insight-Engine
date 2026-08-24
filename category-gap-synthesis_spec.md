# Spec: Category gaps over product gripes

> Status: **draft** (2026-08-23) — stage-01 frame only, via the feature-planning
> workspace. §1–§2 below are the stage-01 output and passed the kill gate
> (question 6, answered *"yes — and it carries its own validation"*).
> §3 onward is stage-02 grill work and is deliberately absent.
> Friction note: this session — *"help builders validate their idea by ... seeing
> if their issue aligns with the problems that real people are complaining
> about"*, followed by the framing decision to return the category's unfixed
> pain rather than adjudicate the builder's hypothesis.
>
> Carried into the stage-02 grill (framing answers Q3–Q5, not written up here):
> pool reaches synthesis **compressed** (all pain items + bounded quote sample);
> spread/frequency recomputed by a **deterministic Python back-mapping pass**;
> alignment tag emitted **inside the existing synthesis call**; **cited quotes +
> bounded sample** persisted; **tier derived, alignment stored** (one hand-run
> `ALTER TABLE`).

## 1. Context / why now

The tool's stated job is PRD §2 step 4 — *"does my idea address something all
competitors fail at?"* — the step the PRD says happens "in the user's head with
no structure." The v2 pipeline builds everything up to that step and then stops:
it returns a ranked gap list and leaves the cross-referencing to the builder.
The run does not end in a decision.

**Why now, concretely: the measured output does not support the claims the UI
makes about it.** Ten real `done` runs were read out of Supabase on 2026-08-23:

| Observation | Measurement |
|---|---|
| Runs returning nothing at all | **5 of 10** — including three separate attempts at the same idea |
| `frequency` across every persisted gap | always **2 or 3** |
| `spread` across every persisted gap | never above **2**; most are 1 |
| Dominant gap shape | one product's bugs — *"Habitica suffers from crashes"*, *"Office Mobile isn't optimized for iPad"* |

Both quantitative fields are degenerate, and the Result page presents them to
builders as evidence-strength signals. `frequency` is not a count of how many
people complained; it is the number of quote IDs the model chose to list, which
is always the minimum the grounding rule demands. And because
`spread = |distinct competitors among cited quotes|`, **spread is mathematically
capped by frequency** — at 2 citations, spread cannot exceed 2, regardless of how
much evidence was retrieved. Cross-competitor pain, the one output no adjacent
tool produces, is currently unreachable by construction.

Underneath sits an evidence funnel that starves the whole loop. On the
workflow-management run, ~2,300 ingested comments and reviews produced **24
quotes** at synthesis. The cause is measurable: the App Store engagement filter
gates on `vote_count`, which is 0 for **401 of 500** Asana reviews and 1 for
another 77, against a category threshold of 6. Meanwhile `rating` — the 1-star
flag, the strongest pain signal the feed carries — is fetched by
`app/clients/appstore.py` and never read, and the review `title` is discarded.
Re-gating the same run on `rating <= 2` yields **1,118 quotes instead of 22**.

The one run that works is instructive rather than reassuring: `2.5d survivor-like`
returned 7 gaps, several at spread=2, and genuinely category-level — ads
disrupting play, progression walls, pay-to-win, missing multiplayer. It is a
mobile game, the category where App Store review volume and vote counts are
highest. The pipeline is capable of the right output when enough evidence
survives; it usually does not.

**Why this is the right thing to build now.** planning/CONTEXT.md names the
current phase as the v1.1 roadmap, and the honest case against this spec was put
at the gate: the eval harness was deleted (#87), so four coupled changes — filter,
prompt, metrics, output shape — would ship with no instrument to prove they
helped, and the §2 workflow has still never been validated with a real user. The
gate resolved **yes** on the ground that this is the core loop rather than a
feature on top of it, that a tool failing half its runs is not a candidate for
further deferral, and that the acceptance bar chosen here is countable without
rebuilding the harness. The standing requirement in planning/CONTEXT.md — *"the
eventual engagement-filter retune must bring its own validation"* — is therefore
absorbed into this spec as a deliverable, not deferred past it.

## 2. Goals / non-goals

### Goals

- **G1 — Two-tier output.** A pain cited across N or more distinct competitors is
  a **category gap** and leads the Result page. Single-competitor pain is
  demoted to a clearly separated *"one product's problems"* section. The tier is
  a computed function of measured spread, so "done" is checkable without
  judgement.
- **G2 — Metrics that measure something.** `spread` and `frequency` are
  recomputed deterministically from the full evidence pool after synthesis, not
  read off the model's citation list. `spread` must be able to reach the number
  of approved competitors; `frequency` must reflect how many pain items and
  quotes actually carry the theme.
- **G3 — An evidence pool that can support G1–G2.** Gate App Store reviews on
  pain signal (star rating) rather than `vote_count`, read the review `title`
  alongside the body, and recalibrate the YouTube threshold. Success is
  structural, not a target number: cross-competitor patterns must become
  *reachable*.
- **G4 — No run returns an empty page.** Every completed run renders something
  actionable: category gaps when they exist, otherwise the demoted gripes plus
  an explicit statement that no category-wide pattern was found. The zero-gap
  case becomes a designed state, not a dead end.
- **G5 — Idea alignment as annotation.** Gaps overlapping what the builder
  described are marked as such. The mark never reorders, filters, or gates the
  gap list.
- **G6 — The change validates itself.** A fixed set of ~10 ideas is run before
  and after, reporting zero-gap-run count, maximum achieved spread, and the
  category-vs-gripe split. This is the acceptance gate and satisfies the
  standing validation requirement in planning/CONTEXT.md.

### Non-goals

- **A verdict on the builder's idea.** No confirmed/invalidated adjudication, no
  crowded/open judgement. A confident verdict off a thin pool is the costliest
  error this tool can make, and PRD §1 framing is decision support, not a
  verdict. G5's annotation is the deliberate ceiling.
- **Rebuilding the eval harness.** v1.1 item #1 stands on its own. G6 is a
  before/after count on a fixed idea set, not a scored corpus, and must not be
  filed as a partial delivery of the golden eval set.
- **Resurrecting a separate `idea_match` stage.** #88 deleted
  `app/llm/idea_match.py` and folded `target_gap` into `idea`. G5 is emitted by
  the existing synthesis call; this spec adds no pipeline stage and no new
  `resolve(stage)` routing entry.
- **A theme × competitor matrix.** Considered and declined at stage 01: it is
  information-dense but hands the cross-referencing back to the user, which is
  the thing G1 exists to fix.
- **New data sources.** Reddit and HN stay v1.1 item #6. This spec works the
  App Store and YouTube evidence already being retrieved and thrown away.
- **Pre-flight competitor relevance.** Off-target competitor selection is real —
  the screen-watching-AI run mined Microsoft Office and Otter — but it is a
  distinct failure with a distinct fix, and folding it in would make an already
  four-part change unreviewable. Recorded here as the most likely next spec.
- **User research on the §2 workflow.** v1.1 item #4 stands. This spec improves
  an output shape whose consumer is still a hypothesis, and accepts that risk
  explicitly rather than resolving it.
- **Queue UX, longitudinal tracking, per-run filter tuning.** Untouched v1.1 items.
