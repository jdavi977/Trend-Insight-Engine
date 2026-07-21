# ICM Comparison — Current AI Workflow vs. Interpretable Context Methodology

> Date: 2026-07-20. Compares the Trend Insight Engine's existing AI/context
> setup against Van Clief & McDermott's Interpretable Context Methodology (ICM,
> arXiv Mar 2026). Reference impl: github.com/RinDig/Interpretable-Context-Methodology-ICM-

## TL;DR

There are **two distinct "workflows"** in this repo, and conflating them is the
main risk when reasoning about ICM:

1. **The dev/meta workflow** — how *Claude* is steered while working on the
   codebase: root `CLAUDE.md` + per-workspace `CONTEXT.md` + skills + a routing
   table. **This is genuinely ICM-adjacent in spirit** and already nails several
   ICM principles. But it is organized by codebase *domain/layer* (planning, app,
   frontend, docs, ops) and by *task type* (skills), **not** by sequential
   pipeline *stage* — so it has no numbered stage folders and no
   Inputs/Process/Outputs stage contracts. Call it "ICM-lite for a codebase."

2. **The product/runtime pipeline** — the actual idea→gaps data flow, implemented
   in Python under `app/` (`services/` orchestrates stages, Supabase holds state).
   **This is exactly the code-orchestrated approach ICM positions itself against**
   — and it *should* be, because ICM explicitly excludes high-concurrency,
   multi-user, real-time pipelines, which is precisely what this product is.

So the honest verdict: the dev workflow *could* move closer to ICM if desired;
the runtime pipeline correctly should not. Most of ICM's ideas apply to #1.

---

## What the current AI workflow actually is (inventory)

| Piece | Where | Role |
|-------|-------|------|
| `CLAUDE.md` (root, ~450 tok) | / | Project identity, tech stack, **Workspaces** list, **Routing Table**, naming conventions |
| `CONTEXT.md` ×4 | planning/ app/ frontend/ docs/ | Per-domain contract: what this area does, patterns, patterns-to-avoid, authority pointer to PRD |
| Skills ×9+ | `.claude/skills/`, `.agents/skills/` | Task-scoped instruction bundles (code-review, tdd, write-adr, map-architecture, to-issues, triage, grill-me…). Each has frontmatter `name` + `description` + "Use when…" |
| Routing Table | in `CLAUDE.md` | Maps `Task → Workspace → Read → Skills`. This is the dispatcher. |
| `PRD.md` (~11k tok, 44 KB) | docs/ | The de-facto reference/"factory" constraint doc; every CONTEXT.md cites it as "Authority" |
| `NOTES.md` | / | Running hand-run lab journal (friction, bugs, lessons) |
| Local scripts / CI | `app/jobs/`, `app/eval/`, `Makefile`, `.github/workflows/` | Non-AI mechanical work: entrypoints, eval harness, tests, (stale) weekly crons |

Funnel in practice: **CLAUDE.md → Routing Table picks a workspace + skill →
that workspace's CONTEXT.md → the skill → (PRD when needed)**. That is a real,
working layered-context system — it just routes by domain, not by stage.

---

## Against ICM's five context layers

| ICM layer | "Question" | In this repo | Match |
|-----------|-----------|--------------|-------|
| **L0** CLAUDE.md (~800 tok) | Where am I? | Root `CLAUDE.md`, ~450 tok, folder map + routing table | ✅ Strong (even lean vs. the 800 target) |
| **L1** workspace CONTEXT.md (~300 tok) | Where do I go? | Split: the **Routing Table in CLAUDE.md** does dispatch; per-domain `CONTEXT.md` files are the destinations | ⚠️ Present but reorganized — routing lives one layer up |
| **L2** stage CONTEXT.md (200–500 tok) | What do I do? (the **stage contract**, the control point) | **No stage contracts exist.** Closest analog = **skills**, but they're keyed to *task type*, not *pipeline stage*, and declare no Inputs/Process/Outputs | ❌ Missing in ICM form |
| **L3** reference material (500–2k tok) | What rules apply? (voice/style/design — "the factory") | Scattered: CONTEXT "Patterns" sections + skills + ADRs + the 11k-tok PRD. No consolidated `_config/` | ⚠️ Exists but diffuse & partly oversized |
| **L4** working artifacts | What am I working with? | Source code files + Supabase rows — **not** markdown edit-surfaces handed stage→stage | ⚠️ Fundamentally different medium (see runtime section) |

**Token economics:** the CONTEXT.md files are well-behaved (450–1100 tok each;
root ~450). The weak spot is **L3**: pointing every CONTEXT.md at a ~11k-token
PRD as "Authority" invites the agent to load a monolith — the exact 30k–50k
"cluttered context" failure mode ICM warns about. ICM would say: extract the
stable constraints the agent actually needs into small `_config/` files and let
the PRD be a human reference, not an agent input.

---

## Against ICM's five design principles (dev workflow)

1. **One stage, one job** — N/A as literal stages; the analog is "one CONTEXT
   per domain, one skill per task." Mostly clean, but some skills bundle several
   jobs (e.g. `python-code-review` = module structure + layering + error handling
   + endpoint shape + tests). ⚠️
2. **Plain text as the interface** — ✅ Strong. All markdown/JSON, no proprietary
   serialization for the *context* system.
3. **Layered context loading** — ✅ Strongest match. On-demand funnel, nothing
   irrelevant loaded up front (PRD size caveat aside).
4. **Every output is an edit surface** — ⚠️ Partial. The human edits CONTEXT.md
   and code directly (good), but there's no *staged* output→review→next-stage
   handoff, because there are no stages.
5. **Configure the factory, not the product** — ⚠️ Partial. Naming conventions,
   patterns, ADRs, PRD *are* factory config, but they're diffuse and some are
   **stale** (see findings).

---

## The runtime pipeline vs. ICM — why it's correctly NOT ICM

The product flow (idea → pre-flight → concurrent per-source ingest → idea-blinded
extract → quote-then-claim synthesis → gaps → Supabase) is orchestrated in
`services/run_pipeline_service` with concurrency caps, per-source retries, and
DB-held state. That's "framework-level orchestration" (hand-rolled, not
LangChain) — the thing ICM argues against for *reviewable sequential* work.

But ICM's own "where it doesn't fit" list rules this pipeline out of ICM:
- **High-concurrency, many users hitting the same pipeline** — yes (API-triggered
  background runs, per-IP rate limits, ≤10 concurrent sources).
- **Real-time / tight loops** — the Result page polls every 5s while running.
- **Not a per-run human-in-the-loop file review** — runs go idea→gaps unattended
  after approval.

So keeping the runtime pipeline as code is the *right* call. ICM is the wrong
tool for the product's hot path.

## The one place the product already has an ICM-shaped gate

The **pre-flight review** is a textbook ICM breakpoint: the pipeline surfaces an
editable plan (category, signal_strength, candidate competitors) and **stops for
the human to edit before the expensive stages run** (`preflight_ready → approve
→ running`). That is exactly ICM's "surface the structural plan as an editable
artifact at the point where an error is cheapest to catch." The difference is
purely medium: this project implements that gate as API + UI + DB rather than as
a markdown file on disk — appropriate, given the concurrency constraints above.

---

## Concrete findings (the "verify against reality" warning, made real)

The ICM writeup's closing warning — *an unverified ICM setup is "coherent,
confident, and off by a third: wrong folder pattern, wrong instruction format,
token use over budget"* — shows up here not as a bad build but as **drift
between the context files and the filesystem**:

1. **Dangling output/reference folders.** `planning/CONTEXT.md` links to
   `specs/…` and `decisions/…`; the `map-architecture` skill writes to
   `planning/architecture/`; `write-adr` writes to `planning/decisions/`;
   `frontend/CONTEXT.md` cites ADR
   `planning/decisions/2026-06-01-frontend-routing-state-vs-router.md`. **None of
   `planning/specs`, `planning/decisions`, `planning/architecture` exist** — git
   tracks only `planning/CONTEXT.md`. In ICM terms, the stages promise output
   folders that aren't on disk, and cite reference artifacts that are missing.
2. **Stale factory config (CI).** `.github/workflows/weekly-youtube.yml` and
   `weekly-appstore.yml` are still present and cron-scheduled (`0 8 * * 0`), even
   though `planning/CONTEXT.md` and `app/CONTEXT.md` state the weekly pipeline was
   **removed** in the v1→v2 pivot / slice 3. The "factory" contradicts the
   documented product state. ICM's *edit-the-source* rule: fix this at the CI
   source, not per-run.
3. **L3 monolith.** Every CONTEXT.md routes to an 11k-token PRD as "Authority"
   with no smaller extracted constraints — over ICM's 2–8k per-stage budget if
   loaded.

These are cheap to fix and would make the dev workflow materially more
ICM-faithful (interpretable = the map matches the territory).

---

## What the user already does that IS core ICM

- **"Run it by hand first / friction has information in it."** `NOTES.md` is a
  months-long hand-run journal of doing the pipeline manually and cataloguing
  where friction lives (`youtube comments returning []`, `quote_pool quite low`,
  `inconsistent retrieved quotes cited despite the same prompt`). The May 4 entry
  — Claude "performed the task but missed functions from other layers" — is
  literally the ICM lesson that manual runs are the research. **Practice already
  aligns with ICM's most-quoted principle even though the file structure doesn't.**
- **Layered navigation intent.** The July 12 note "reorganize my AI Workflow
  files for better context hopping" is the ICM layered-loading instinct stated in
  the user's own words.

---

## Optional next steps (only if moving the *dev* workflow toward ICM)

- **Fix the map/territory drift first** (findings 1–2): create the missing
  `planning/{specs,decisions,architecture}/` or update the pointers; delete or
  de-schedule the weekly workflows. Highest interpretability-per-effort.
- **Extract a small `_config/`-style L3** from the PRD: the handful of stable
  constraints agents actually need (severity rubric, model-routing table, layer
  rule, PII policy) as sub-2k-token files, leaving the PRD as human reference.
- **If (and only if) an authoring workflow is genuinely sequential + reviewable +
  repeatable** — e.g. PRD→spec→issues→implementation, or the eval-corpus buildout
  — that is a legitimate candidate for a real numbered-stage ICM workspace with
  Inputs/Process/Outputs contracts. The runtime pipeline is not.
- **Don't ICM-ify the runtime pipeline.** It fails ICM's fit test on concurrency
  and real-time; leave it as service code.
