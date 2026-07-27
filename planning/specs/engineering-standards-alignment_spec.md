# Spec: Engineering standards + context-system alignment

> Status: grilled (2026-07-22). Author: audit of the context system on 2026-07-21.
> Related: [feature-planning-workspace_spec.md](feature-planning-workspace_spec.md)
> §5 (the previous, one-time drift fix this spec supersedes the approach of).
>
> **Grilled 2026-07-22** via the feature-planning workspace (stages 01–02).
> Scoped to **Slices 0–4**: tooling, CI, and the code-conformance dive (former
> Slices 5–6) split into a follow-on spec, `engineering-standards-tooling` (N6).
> §9's five open questions are resolved or relocated: OQ1's rule is settled
> (rename deferred), OQ2 is decided, OQ3–OQ5 moved to the follow-on.

## 1. Context / why now

Two months after v1 shipped (2026-06-11), the repo's **context system** — root
`CLAUDE.md`, four domain `CONTEXT.md` files, twelve skills, one ICM workspace —
has drifted from the filesystem it describes. A 2026-07-21 audit found 13
defects across four classes: routes that dead-end, sources that contradict each
other, redundant routing rows, and skills nothing points at (§4).

**Why this matters now, concretely:** this repo is driven *through* Claude. A
routing table that sends an agent to `prompt-engineering`, `doc-authoring`, or
`/ops` — none of which exist — or a `python-code-review` skill describing the
deleted `/analyze/youtube` endpoint, is a tax on *every* session, including the
pipeline work in NOTES.md. Fixing the context system is the cheapest lever on
all other work; it is not a detour from it.

The [feature-planning workspace spec](feature-planning-workspace_spec.md) §5
already fixed three drift items (U1–U3) on 2026-07-20. **Four new ones appeared
within a day**, and the audit found nine more that the U1–U3 sweep never looked
for. That is the actual lesson: a one-time sweep does not hold, because there is
no written standard for the sweep to check *against*. `python-code-review` — the
skill routed from 3 of 10 rows — still describes the **v1 codebase**, including a
worked example built on the deleted `/analyze/youtube` endpoint.

So this spec does three things in order, and the order matters:

1. **Write the standard** (§5) — one authority for how this project's code,
   layout, tooling, and docs should look, grounded in the actual stack and in
   current (2026) practice.
2. **Fix the map** (§4) — the 13 audit defects, resolved *against* that standard
   rather than ad-hoc.
3. **Conform the territory** — a whole-project dive bringing code, config, CI,
   and skills into line with §5.

Step 1 first is the load-bearing choice. Steps 2 and 3 are mechanical once the
standard exists, and undecidable before it: the audit's sharpest finding (F6,
camelCase vs snake_case) is a contradiction *no existing document can settle*,
because there is no document that says what the naming rule is derived from.

This audit is itself a one-time sweep — and it already missed things. `app/rag/`
and `app/lib/` are empty vestigial directories the audit never flagged, and F5's
layer list understates the real 14-directory module graph. That is not a reason
to distrust the findings; it is the sharpest possible argument for **A2's
automated checker**, which must catch what a human read-through cannot.

## 2. Goals / non-goals

**Goals**
- **G1.** One written engineering standard at `docs/engineering-standards.md`,
  covering backend, frontend, testing, tooling, and documentation — with every
  rule marked as already-true, a delta, or an open decision.
- **G2.** Every dead-end route, contradiction, and redundancy in §4 resolved.
- **G3.** `python-code-review` rewritten against the v2 codebase, **citing** the
  standard rather than restating it.
- **G4.** The **context system** — routing table, four `CONTEXT.md` files,
  skills, and the ICM workspace — verified consistent with §5, and that
  verification is a **demonstrated clean pass**: an agent runs a real task
  end-to-end through the fixed routing with zero dead-ends, *plus* the A2 script.
  Not a grep alone. *(Code/CI/config conformance is the follow-on spec's job —
  see N6.)*
- **G5.** The standard is *checkable*, so conformance can be re-verified later
  rather than re-audited by hand.

**Non-goals**
- **N1.** No behaviour change to the idea→gaps pipeline. This is layout,
  tooling, naming, and documentation. If a rename breaks a test, the rename is
  wrong, not the test.
- **N2.** No migration to TypeScript, no new frontend framework, no component
  library. The frontend stays React 19 + JSX + Vite.
- **N3.** Do not adopt a standard because it is fashionable. Every rule in §5
  must justify itself against *this* repo's size, stage, and constraints — a
  repository-pattern layer or an OpenTelemetry stack is correct for a company
  and wrong here (see D3).
- **N4.** Do not restate the standard inside skills or `CONTEXT.md` files. Cite
  by path. A second copy is the drift surface this spec exists to remove.
- **N5.** No rewrite of `docs/PRD.md`. It is the product authority and stays
  intact.
- **N6.** No tooling adoption, CI changes, or code/config conformance edits **in
  this spec**. The standard still *documents* the ⚠️ tooling deltas, but
  *executing* them — `ruff`, the type checker, `pytest-cov`, CI jobs, the
  conformance dive, and the camelCase renames — is a separate follow-on spec,
  **`engineering-standards-tooling`** (former Slices 5–6). This spec delivers the
  standard plus the map/skill/workspace fixes and stops at a coherent,
  independently-mergeable state.
- **N7.** The empty `app/rag/` + `app/lib/` directories and the "RAG surface
  deleted" contradiction in `planning/CONTEXT.md` (finding **F14**) are known and
  deliberately left to the follow-on conformance dive. Seen here, not fixed here.

## 3. Cross-cutting design decisions (with rationale)

- **D1 — The standard is one file, `docs/engineering-standards.md`, and it is
  the authority.** Not a section of root `CLAUDE.md` (which is always-loaded and
  must stay ~450 tokens), and not a skill (skills are *procedures*; this is a
  *reference*). Root `CLAUDE.md` and `python-code-review` cite it by path. This
  follows the workspace spec's own D4: cite, don't copy.

- **D2 — Standards are derived from an external authority wherever one exists,
  and the citation is recorded inline.** F6 (camelCase) is unresolvable as long
  as two internal documents disagree with equal standing. Rooting the rule in
  PEP 8 makes it settleable and stops the next person re-litigating it. Where no
  external authority exists, the rule says "project choice" and gives the reason.

- **D3 — Adopt the parts of 2026 practice this repo is actually big enough for,
  and record what was deliberately declined.** The research (§5 sources) is
  consistent on a layered `api/services/repositories/` structure, DI via
  `Depends`, structured JSON logging with request-ID propagation, and
  feature-based organisation once a product has many domains. This repo is a
  single-domain pipeline with one active run per instance. Blanket adoption
  would add seams with one adapter each — a hypothetical seam, not a real one,
  by `improve-codebase-architecture`'s own test. The standard therefore has a
  **"Declined, and why"** section (§5.7) that is as load-bearing as the rules.

- **D4 — Every rule is tagged ✅ / ⚠️ / ❓.** ✅ = the code already does this
  (the rule records it so it does not erode). ⚠️ = a delta with known work. ❓ =
  a decision the standard cannot make on its own; it goes to §9. This tagging is
  what makes the §3 conformance dive mechanical instead of another audit.

- **D5 — Prefer rules a tool can enforce over rules a reviewer must remember.**
  A `ruff` rule in `pyproject.toml` beats a bullet in a skill, because the
  bullet is what drifted. Where a rule is mechanisable, the standard names the
  tool and the config; where it is not, it says so explicitly.

- **D6 — Fix the CI gap before the conformance dive, not after.** Adding lint +
  type-check + frontend jobs to CI *first* means the dive's work is verified as
  it lands rather than asserted. Today CI runs `pytest` only: `eslint` is
  installed and has **never run in CI**, and no type checker or linter exists at
  all for Python. **→ Relocated:** CI and the conformance dive both moved to the
  follow-on `engineering-standards-tooling` spec (N6); D6 governs *its* internal
  ordering, not this spec's. This spec's one enforcement artifact — the A2
  reference-checker script (§6 Slice 2) — ships without CI wiring; the follow-on
  wires it in as its first item.

## 4. The audit — what is broken

Full detail is in the 2026-07-21 audit. Summarised, with the §5 rule or §6 slice
that resolves each.

### 4.1 Dead-end routes (an agent following these hits nothing)

| ID | Location | Defect | Resolved by |
|----|----------|--------|-------------|
| F1 | [CLAUDE.md:23](../../CLAUDE.md), [:52](../../CLAUDE.md) | `/ops` workspace + `ops/CONTEXT.md` do not exist; `ops/scripts/` was deleted in the v1→v2 teardown | Slice 2 |
| F2 | [CLAUDE.md:49](../../CLAUDE.md) | Skill `prompt-engineering` does not exist | Slice 2 |
| F3 | [CLAUDE.md:51](../../CLAUDE.md) | Skill `doc-authoring` does not exist | Slice 2 |
| F4 | [frontend/CONTEXT.md:38-39,53](../../frontend/CONTEXT.md) | Cites "ADR 2026-06-01" twice as the authority lifting the no-router rule; `planning/decisions/` holds only `.gitkeep` | Slice 2 |

### 4.2 Contradictions (two sources, opposite instructions)

| ID | Defect | Resolved by |
|----|--------|-------------|
| F5 | `python-code-review` is written against the v1 codebase: its layer list omits `api/`, `services/`, `clients/`, `config/`, `jobs/`, `eval/`; it says "adding a FastAPI endpoint in main.py" while routers live in `api/`; its worked example is `@app.post("/analyze/youtube")`, a **deleted** endpoint; its test convention (`tests/test_commentClean.py`) contradicts the mirrored tree in [app/CONTEXT.md](../../app/CONTEXT.md); and it never mentions the two rules that matter most — `resolve(stage)` routing and idea-blinded extraction | §5.1 + Slice 4 |
| F6 | [CLAUDE.md:58](../../CLAUDE.md) mandates `camelCase.py`; `python-code-review` enforces it with an explicit `❌ comment_clean.py`; but every v2 module is snake_case (`per_source_extraction_service.py`, `run_pipeline_service.py`, `idea_match.py`, `json_response.py`, `preflight_smoke.py`). **The review skill would flag the newest, correct code as a violation.** | §5.1 + **OQ1** |
| F7 | ADRs have two homes: `write-adr` → `planning/decisions/`; `grill-with-docs` and `improve-codebase-architecture` → `docs/adr/`. grill-with-docs **creates `docs/adr/` lazily**, and it *is* stage 02 of the feature-planning workspace — so running the workspace can spawn a second ADR directory | §5.6 + Slice 4 |

### 4.3 Redundancy

| ID | Defect | Resolved by |
|----|--------|-------------|
| F8 | `tdd` is invoked by ICM stage 05 *and* the `/app` rows. Not duplicate skills — **duplicate entry with no exit marker**. The skill's [§1 Planning](../../.claude/skills/tdd/SKILL.md) produces the plan stage 05 wants; §2–4 are the red-green-refactor loop. Nothing in [icm/feature-planning/CONTEXT.md:44](../../icm/feature-planning/CONTEXT.md) says "stop after planning", so an agent runs the loop and starts implementing inside the *planning* workspace | Slice 3 |
| F9 | [CLAUDE.md:46](../../CLAUDE.md) "Write backend code" and [:48](../../CLAUDE.md) "Refactor a module" — identical destination, identical skills. Two rows, one answer | Slice 2 |
| F10 | `grill-me` ⊂ `grill-with-docs` (same opening paragraph verbatim; the latter adds domain awareness, glossary challenge, inline `CONTEXT.md` updates). "Stress-test a design" routes to the strictly weaker tool | Slice 2 + **OQ2** |
| F11 | "Plan a new feature" vs "Plan a feature end-to-end" are near-synonyms as labels; the one-off/sequenced distinction lives only in prose below the table | Slice 2 |

### 4.4 Orphans and staleness

| ID | Defect | Resolved by |
|----|--------|-------------|
| F12 | `map-architecture`, `write-adr`, `improve-codebase-architecture` appear in **no routing row**. `write-adr` is the sharp case: [CLAUDE.md:57](../../CLAUDE.md) documents the naming convention for its output but nothing routes to the tool producing it — plausibly why F4's ADR was never written | Slice 2 |
| F13 | [feature-planning-workspace_spec.md §9](feature-planning-workspace_spec.md) lists OQ1/OQ2 as open; [CONTEXT.md](../../icm/feature-planning/CONTEXT.md) already decided both. §4.2 still names `impl-plan.md` as the stage-05 artifact; CONTEXT.md says issue body | Slice 3 |

**Also true, and worth stating:** `planning/architecture/` and `planning/decisions/`
are empty and no `<slug>_spec.md` from a real run exists — **the feature-planning
workspace has never been run.** Every finding above comes from reading it, not
using it. Slice 3 of that spec (first real run) remains outstanding.

## 5. The standard

This section is the content of `docs/engineering-standards.md`. Tags per D4:
**✅** already true · **⚠️** delta · **❓** decision needed (→ §9).

### 5.1 Python: naming and layout

- **✅ Layer rule stands as written** in [app/CONTEXT.md](../../app/CONTEXT.md):
  `api/ → services/` only; pipeline modules (`ingestion`, `preprocessing`,
  `llm`) never import each other; `jobs/` are thin shells. This matches the
  layered structure the research converges on, at this repo's scale.
- **❓ Module and function names are `snake_case`, per PEP 8** — *"Modules
  should have short, all-lowercase names. Underscores can be used in the module
  name if it improves readability"*; *"mixedCase is allowed only in contexts
  where that's already the prevailing style … to retain backwards
  compatibility."* v2 code is already snake_case; the camelCase survivors are v1
  leftovers (`commentClean.py`, `reviewPipeline.py`, `validateUrl.py`,
  `appStoreReviews.py`, `youtubeComments.py`, `promptTemplates.py`,
  `textCleaning.py`, `json_response.py`'s neighbours) plus the function
  `keyChecker()` in `config/secrets.py`. **→ OQ1** decides rename-now vs.
  snake_case-for-new-code-only.
- **✅ Modern type-hint syntax** — `from __future__ import annotations`,
  builtin generics (`list[str]`), PEP 604 unions (`float | None`). Already the
  dominant style.
- **⚠️ One union syntax, not two.** `api/runs.py` mixes `Optional[datetime]`
  with `float | None` elsewhere. Standardise on `X | None`; `ruff` rule `UP007`
  enforces it.
- **✅ One file per external source.** `clients/{appstore,youtube,openai,supabase}.py`,
  `ingestion/{appStoreReviews,youtubeComments}.py`. Keep.
- **✅ Docstrings and comments explain *why*, citing the PRD/spec section.**
  `api/runs.py`'s module docstring and the CORS `expose_headers` comment in
  `main.py` are the model. This is a genuine strength of the codebase; the
  standard records it so it survives.

### 5.2 Python: configuration and secrets

- **⚠️ Config must not raise at import time.** `config/secrets.py` calls
  `keyChecker()` at module scope, so importing it fails without a full
  environment — which is why `.github/workflows/test.yml` must set four fake
  secrets just to collect tests. Move validation behind a callable or a settings
  object so import is side-effect-free.
- **⚠️ `pydantic-settings` is installed and unused.** It is already in
  `requirements.txt` (2.13.1). The research is unanimous that typed
  `BaseSettings` + `@lru_cache` is the production pattern, and it fixes the
  import-time problem in the same change. **→ OQ3** (adopt now, or keep
  `os.getenv` and only fix the import-time raise).
- **✅ All tunables in `config/`, never inline.** `MODEL_ROUTING`, engagement
  filters, prompts, regex. Keep, and keep it enforced.
- **✅ Secrets from `.env` via `python-dotenv`, never from `config/` files.**

### 5.3 Python: errors, logging, and the request path

- **✅ Per-module `logging.getLogger(__name__)`.** Already consistent across
  services, clients, and llm modules.
- **✅ Centralised exception handlers** via `api/errors.register_exception_handlers`.
  Matches the research's "global exception handlers, structured responses".
- **⚠️ `logging.basicConfig` runs at import time in `main.py`.** Move into
  `create_app()` so importing the module does not configure global logging —
  the same class of defect as 5.2's first bullet.
- **⚠️ Specific exceptions only; never bare `except:` or `except Exception: pass`.**
  Carried forward from `python-code-review` (this rule was always correct).
  `ruff` rules `E722` + `BLE001` enforce it.
- **✅ Pipeline stages raise upward rather than returning `None`/`[]` to signal
  failure.** The caller decides. Keep.
- **⚠️ Async discipline.** Research: `async def` for I/O-bound work, plain `def`
  only for CPU-bound or sync-library calls — a sync `def` handler runs in a
  threadpool, which is correct for the current blocking clients but should be a
  *stated* choice rather than an accident. Document which endpoints are sync and
  why (they call blocking SDKs).

### 5.4 Frontend: React 19 + Vite

- **✅ PascalCase components, flat pages in `src/`, shared UI in `components/`.**
  Already documented in [frontend/CONTEXT.md](../../frontend/CONTEXT.md) and
  matches the research's "PascalCase components". Keep — including the explicit
  *no* `src/pages/` rule.
- **✅ Hooks-only state, no Redux/Zustand; `react-router-dom` for routing
  (ADR 2026-06-01).** Keep. Note F4: **that ADR must actually be written.**
- **✅ Backend calls lifted to page level; base URL from
  `import.meta.env.VITE_API_BASE`.**
- **⚠️ The frontend has no tests and no test runner.** `frontend/package.json`
  has no `test` script and no Vitest. The research's standard shape is Vitest +
  React Testing Library for unit/component tests, Playwright for E2E of critical
  flows. **→ OQ4** — at minimum, Vitest + RTL on the run-lifecycle state
  machine; Playwright is likely over-scoped for now.
- **⚠️ `eslint` is configured but never runs in CI.** Add a frontend CI job.
- **⚠️ No formatter.** Add Prettier (or `eslint --fix` only) so formatting stops
  being a review topic. Project choice; no external authority compels Prettier.
- **⚠️ Stray root `package.json`** declaring only `dotenv` — vestigial, and it
  makes the repo look like an npm workspace it is not. Delete or justify.

### 5.5 Testing

- **✅ Test tree mirrors `app/`** (`tests/api/`, `tests/services/`, `tests/llm/`,
  …). Already true and already correct — and it is `python-code-review` that is
  wrong about this (F5), not the tests.
- **✅ Mock external services; run pure modules for real.** Keep.
- **✅ Behaviour over implementation, vertical slices over horizontal** — the
  `tdd` skill's philosophy. The standard cites it rather than restating it.
- **⚠️ No coverage measurement.** Add `pytest-cov`. Report a number; do **not**
  set a failing threshold initially — a threshold picked before you know the
  baseline is a number people game.
- **⚠️ Test-file naming inherits OQ1** (`test_appStoreReviews.py` vs
  `test_app_store_reviews.py`).

### 5.6 Documentation and decision records

- **⚠️ ADRs live in `planning/decisions/`, one home, full stop** (F7). Root
  `CLAUDE.md` already names the convention. `write-adr` is correct;
  `grill-with-docs` and `improve-codebase-architecture` must be pointed at
  `planning/decisions/` so neither creates `docs/adr/`.
- **✅ Naming conventions** in root `CLAUDE.md` — specs `feature-name_spec.md`,
  architecture/decisions `YYYY-MM-DD-topic.md`. Keep (F6's backend-module line
  is the only one changing).
- **⚠️ Every `CONTEXT.md` "Authority" line names PRD *sections*, not the file.**
  Already applied to all four (U3, 2026-07-20) — the standard records it so the
  next `CONTEXT.md` inherits it.
- **⚠️ A citation to a document that does not exist is a defect, not a TODO.**
  This is the rule F1–F4 all violate, and the one the standard most needs.

### 5.7 Tooling and CI

> Every ⚠️ in this subsection is *documented* by this spec (Slice 1) but
> *executed* by the follow-on `engineering-standards-tooling` spec (N6). The
> standard names the target; the follow-on lands it.

- **⚠️ Adopt `ruff` for lint + format.** The research is unanimous: one Rust
  binary replacing black + isort + flake8 + pyupgrade, one config block in
  `pyproject.toml`. The repo has **no Python linter or formatter today.**
  Highest value-per-effort item in this spec.
- **⚠️ Adopt a type checker.** `mypy` is the reference implementation and most
  compatible with third-party libraries; `ty`/`pyrefly` are faster but newer.
  Recommend `mypy` in non-strict mode first, tightened per-module. **→ OQ5.**
- **❓ `pyproject.toml` has no `[project]` table** — only `[tool.pytest.ini_options]`
  — yet `uv.lock` exists alongside a 144-line flat `pip freeze`
  `requirements.txt`, and CI installs with `pip`. The repo is **half-migrated to
  uv**. The research's migration path is `uv init --bare` then
  `uv add -r requirements.txt`. **→ OQ5** decides whether to finish the uv
  migration or drop `uv.lock` and stay on pip.
- **⚠️ CI runs `pytest` only.** No lint, no type check, no frontend job, no
  coverage. Add all four (D6).
- **⚠️ `filterwarnings` ignores `PydanticDeprecatedSince20`** in
  `pyproject.toml`, which means Pydantic-v1-style code is still present and
  silenced. Find it and fix it rather than suppressing it.

### 5.8 Declined, and why (per D3)

Recorded so nobody re-proposes these without new evidence:

- **Repository layer** (`repositories/` between services and Supabase). The
  research recommends it; here there is exactly one persistence target and
  `clients/supabase.py` is already the seam. One adapter = hypothetical seam.
- **Feature/domain-based restructuring** (`app/features/<domain>/`). Recommended
  "once the product has many domains". This product has one: idea → gaps.
- **`Depends()` dependency injection throughout.** The codebase uses direct
  module imports with monkeypatched tests, which works. Revisit if a second
  concrete implementation of anything appears — or sooner if test setup starts
  hurting.
- **Structured JSON logging + request-ID propagation + OpenTelemetry.** Correct
  for a multi-instance service; this is single-instance with one active run.
  Revisit at the v1.1 queue work, where correlating concurrent runs becomes real.
- **TypeScript migration** (N2) and a component library. Out of scope.

## 6. Build sequence (tracer-bullet slices)

This spec is **Slices 0–4 plus a final Prove-it slice**. Order honors §1's
"write the standard first" thesis: the standard is the authority Slices 2–4
resolve against. Slices 2, 3, 4 are independent of each other and parallelise
once Slice 1 lands. **Former Slices 5–6 (tooling, CI, the conformance dive) are
out of scope — see N6 and the follow-on `engineering-standards-tooling` spec.**

- **Slice 0 — Decide.** No code. Two decisions, both now made (see §9):
  **OQ1** — the *rule* is snake_case per PEP 8 (settled); the rename migration
  is deferred to the follow-on spec. **OQ2** — keep both `grill-me` and
  `grill-with-docs`, and make the routing table document the split. OQ3–OQ5 are
  tooling and relocate to the follow-on.
- **Slice 1 — Write the standard.** `docs/engineering-standards.md` from §5,
  with every ❓ resolved to ✅ or ⚠️. ⚠️ tooling deltas (§5.7, and the tooling
  bullets in 5.2/5.4/5.5) are *documented* here but tagged **"executed in
  `engineering-standards-tooling`"** — the standard is the reference; the
  follow-on is the work. Root `CLAUDE.md` cites it. Verifiable by reading
  top-to-bottom.
- **Slice 2 — Fix the routing table, dead ends, and build the ref-checker.**
  F1, F2, F3, F4, F9, F10, F11, F12: rewrite the routing table (drop the
  duplicate row, relabel the two planning rows, route the three orphan skills,
  and document the `grill-me`/`grill-with-docs` split per OQ2), **delete the
  `/ops` row and all references** (`CLAUDE.md`, `docs/guides/SETUP.md`,
  `feature-planning-workspace_spec.md`; run/deploy stays in the `Makefile`), and
  **scaffold** the missing ADR 2026-06-01 via `write-adr` into
  `planning/decisions/` (headers + prompts; the author fills in the reasoning).
  **New deliverable:** `scripts/check_context_refs.py` + a `make check-refs`
  target that verifies every path/skill/doc referenced by `CLAUDE.md` and the
  four `CONTEXT.md` files resolves on disk (A2). No CI wiring (N6) — the
  follow-on wires it in. This slice is the keeper: it stops the bleeding and the
  checker guards every later edit.
- **Slice 3 — Fix the ICM workspace seams.** F8 (stage-05 "plan only, do not
  enter red-green" + a handoff line stating implementation re-enters via the
  routing table) and F13 (close OQ1/OQ2 in the workspace spec, correct §4.2's
  stage-05 artifact). Add a note that a *complete* spec arriving from outside the
  workflow still enters at stage 01 (confirm-pass), not stage 03 — the resume
  table's completeness heuristic gives a false positive otherwise (surfaced by
  this very run; sibling of F13).
- **Slice 4 — Rewrite `python-code-review` against v2.** F5 and F7. The skill
  cites `docs/engineering-standards.md` for rules and keeps only the *procedure*:
  which layer, which checks, in what order. Use the **real 14-directory module
  graph** (`api, clients, config, data, eval, ingestion, jobs, lib, llm,
  preprocessing, rag, schemas, services, utilities`) — F5's list is understated.
  Add the two v2 rules it is missing (`resolve(stage)`, idea-blinded extraction).
  Point `grill-with-docs` and `improve-codebase-architecture` at
  `planning/decisions/`.
- **Slice 5 — Prove it (G4 exit).** After Slices 1–4 land: run
  `make check-refs` to green, **and** drive one real task end-to-end through the
  fixed routing table with zero dead-ends hit. This is the demonstrated clean
  pass — the dynamic half of A2 that a grep alone cannot give. Depends on 2, 3,
  4.

## 7. Acceptance criteria

- **A1.** `docs/engineering-standards.md` exists, and every rule is either
  enforced by a tool named in the file or explicitly marked as reviewer-judgment.
  (A rule may name a tool whose *adoption* is the follow-on spec's job — it is
  named here regardless of when it runs.)
- **A2.** Every path, skill name, and document referenced by root `CLAUDE.md`
  and the four `CONTEXT.md` files **resolves on disk**, verified by
  `scripts/check_context_refs.py` (`make check-refs`) exiting clean. That script
  is the durable answer to why F1–F4 recurred.
- **A3.** No two documents in the repo state contradictory rules for the same
  thing (naming, ADR location, test layout, layer list).
- **A4.** `python-code-review` contains no reference to a deleted endpoint,
  module, or layout, names the real module graph, and names the `resolve(stage)`
  and idea-blinded-extraction rules.
- **A5.** *(Relocated to `engineering-standards-tooling`.)* CI running pytest +
  ruff + type checker + frontend eslint is the follow-on spec's acceptance
  criterion. This spec ships the ref-checker script (A2) *unwired*; the follow-on
  adds it and the other jobs to CI.
- **A6.** Every skill in `.claude/skills/` is reachable from root `CLAUDE.md`,
  or is deliberately unrouted with a one-line note saying so.
- **A7.** The pipeline's behaviour is unchanged: the full test suite passes
  before and after, with no test edited except for renames (N1). *(Renames are
  themselves deferred to the follow-on; this spec should edit no test.)*
- **A8. (new)** The G4 **demonstrated clean pass**: after Slices 1–4 land, an
  agent drives one real task end-to-end through the fixed routing table hitting
  zero dead-ends. The dynamic proof that A2's static check cannot give — and the
  first time the feature-planning workspace's downstream is exercised on real
  routing (see §4's note that the workspace had never been run).

## 8. Risks

- **R1 — Slice 6 is a large diff touching files across every layer.** A rename
  wave plus a formatter pass will conflict with any in-flight branch. Land it
  when nothing else is open, and split formatting from renaming into separate
  commits so `git blame` survives.
- **R2 — The standard becomes the next thing that drifts.** A1/A2's tool
  enforcement is the mitigation; a standard that is only prose has exactly the
  failure mode this spec was written about.
- **R3 — `ruff`'s first pass on an unlinted 3k-line codebase will surface
  hundreds of findings.** Adopt a narrow rule set first (`E`, `F`, `UP`, `B`,
  `BLE`), get to clean, then widen. Do not start with `ALL`.
- **R4 — Scope.** This spec has six slices spanning docs, skills, tooling, CI,
  and code. Slices 0–2 deliver most of the value; if attention runs out, stopping
  after Slice 4 leaves the repo strictly better and coherent.

## 9. Decisions (formerly open questions)

Resolved in the 2026-07-22 grill (Slice 0). Two decided here; three relocated to
the follow-on `engineering-standards-tooling` spec, which owns the tooling work.

- **OQ1 — camelCase: DECIDED (rule) / DEFERRED (migration).** The *rule* is
  snake_case per PEP 8; v2 code already complies. The standard (§5.1) and the
  `python-code-review` rewrite (Slice 4) encode the rule now. The *rename
  migration* — six surviving modules (`promptTemplates`, `appStoreReviews`,
  `youtubeComments`, `reviewPipeline`, `validateUrl`, `textCleaning`; the audit's
  seventh, `commentClean.py`, is already gone) plus imports and test files —
  is a conformance-dive change and **moves to the follow-on** (N6). Recommendation
  there stands: rename in one pass while nothing is in flight.
  *Update 2026-07-27:* `scope-down-core-pipeline` (issue #86) deleted
  `validateUrl` and `textCleaning` as dead code, so the follow-on's rename scope
  is **four** modules — `promptTemplates`, `appStoreReviews`, `youtubeComments`,
  `reviewPipeline` — plus `keyChecker()`.

- **OQ2 — `grill-me` vs `grill-with-docs`: DECIDED — keep both.** `grill-with-docs`
  carries `disable-model-invocation: true`, so the model cannot auto-reach it;
  `grill-me` is the auto-invocable quick grill. Folding would lose that path.
  Slice 2's routing table keeps `grill-me` for "Stress-test a design" and
  documents `grill-with-docs` as the explicit-only, domain-aware version.
  Resolves F10 without deletion.

- **OQ3 / OQ4 / OQ5 — RELOCATED** to `engineering-standards-tooling` with their
  recommendations intact: adopt `pydantic-settings` (OQ3); Vitest + RTL on the
  run-lifecycle state machine, Playwright deferred (OQ4); finish the uv migration
  and adopt `mypy` non-strict (OQ5). They set the size of the follow-on's slices,
  not this spec's.

---

## Sources (§5 research, 2026-07-21)

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/) (naming authority, D2)
- [Modern Python Tooling in 2026: uv, Ruff, pyproject.toml](https://levelup.gitconnected.com/modern-python-tooling-in-2026-uv-ruff-pyproject-toml-and-a-cleaner-workflow-4d1f7872f7be)
- [Managing a Python project with uv in 2026](https://blog.bythewood.me/posts/managing-a-python-project-with-uv-in-2026/)
- [Modern Python Tooling 2026: uv, Ruff, mypy Complete Guide](https://softaims.com/blog/modern-python-tooling-uv-ruff-mypy-2026)
- [Migrate requirements.txt to pyproject.toml with uv](https://pydevtools.com/handbook/how-to/migrate-requirements.txt/)
- [Production-Ready FastAPI Project Structure (2026 Guide)](https://dev.to/thesius_code_7a136ae718b7/production-ready-fastapi-project-structure-2026-guide-b1g)
- [FastAPI Best Practices for Production: Complete 2026 Guide](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026)
- [FastAPI Best Practices (Auth0)](https://auth0.com/blog/fastapi-best-practices/)
- [Best Practices for FastAPI Dependency Injection](https://fastapi-patterns.com/core-architecture-routing-patterns/dependency-injection-strategies/best-practices-for-fastapi-dependency-injection/)
- [FastAPI for MLOps: Python Project Structure and API Best Practices](https://pyimagesearch.com/2026/04/13/fastapi-for-mlops-python-project-structure-and-api-best-practices/)
- [React Folder Structure Best Practices 2026 — Robin Wieruch](https://www.robinwieruch.de/react-folder-structure/)
- [Ultimate Guide: React, TypeScript, Vite & Vitest Setup for 2026](https://www.nandann.com/blog/react-typescript-vite-vitest-setup-guide-2026)
