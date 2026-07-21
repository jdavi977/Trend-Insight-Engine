# Core-feature questions — stage 01 (Frame)

The six questions every core feature must answer before any spec work starts.
Source: [NOTES.md](../../../NOTES.md), May 11.

Answer them **in order** with the user, one at a time. Q6 is a kill question —
if it fails, stop; there is no spec to write.

1. **Why are we building this feature?**
   Anchor the feature to business value. "Because it's missing" is not an answer.

2. **What are we actually building?**
   Functional requirements. What the feature does, stated so that "done" is
   checkable.

3. **How well should it work?**
   Non-functional requirements — latency, cost, failure behaviour, limits.
   Existing budgets live in [planning/CONTEXT.md](../../../planning/CONTEXT.md)
   ("Known Constraints"); a new feature either fits them or says why not.

4. **How do the systems talk to each other?**
   Integration complexity — which layers and external APIs are involved. The
   layer rule (`api/ → services/` only, pipeline modules don't import each
   other) is in [app/CONTEXT.md](../../../app/CONTEXT.md); do not restate it
   here, check the answer against it.

5. **What data is involved?**
   Data decisions are the hardest to reverse — new tables/columns, retention,
   PII exposure, what gets persisted vs. derived. Table names follow root
   [CLAUDE.md](../../../CLAUDE.md) "Naming Conventions".

6. **Should this feature be built at all?**
   Is this solving a user need, or an engineering problem? Answer honestly
   against the PRD's framing and the current phase in
   [planning/CONTEXT.md](../../../planning/CONTEXT.md) ("Current Priorities").
   A "no" here ends the workflow — record why in the friction note and stop.

## What the answers become

Q1 + Q6 → `§1 Context / why now` of the spec.
Q2 + Q6 → `§2 Goals / non-goals`.
Q3–Q5 are **not** written up at stage 01. Carry them into the stage-02 grill;
they are the material the interview sharpens.
