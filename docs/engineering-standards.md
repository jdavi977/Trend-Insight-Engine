# Engineering Standards

> **Status:** authoritative as of 2026-07-22. Derived from
> [planning/specs/engineering-standards-alignment_spec.md](../planning/specs/engineering-standards-alignment_spec.md) §5.
> **Scope:** how this repo's code, layout, tooling, and documentation should
> look. Product behaviour is [docs/PRD.md](PRD.md)'s job, not this file's.

This is the single engineering-standard authority for Trend Insight Engine. It
is a **reference**, not a procedure — it says what "correct" looks like; skills
say how to get there.

## How to use this file

- **Cite it, do not copy it.** Root [CLAUDE.md](../CLAUDE.md), the four domain
  `CONTEXT.md` files, and the `python-code-review` skill point at this path
  rather than restating its rules. A second copy is a drift surface; that drift
  is why this file exists.
- **What lives elsewhere.** Domain facts (module map, endpoint list, run
  lifecycle, gap-display rules) belong in the relevant `CONTEXT.md`. Procedures
  (red-green-refactor, review order, how to run a grill) belong in
  `.claude/skills/`. If a rule here starts restating either, delete it here.
- **Every rule names its enforcement.** Either a tool that can mechanically
  catch a violation, or the explicit words *reviewer judgment*. A rule nobody
  and nothing checks is a wish.
- **Rules are derived from an external authority wherever one exists**, and the
  citation is inline (see [Sources](#sources)). Where none exists, the rule says
  *project choice* and gives the reason. This is what makes a rule settleable
  instead of re-litigable.

### Tag legend

| Tag | Meaning |
|-----|---------|
| ✅ | The codebase already does this. The rule records it so it does not erode. |
| ⚠️ | A known delta between this rule and the code. Work is outstanding. |

There are no open decisions in this file. The two that were open — module
naming and the two grill skills — are resolved in the spec's §9 and folded in
below.

### Where the ⚠️ work happens

Tooling adoption, CI changes, and code/config conformance edits are **not** part
of the spec that produced this file (its N6). Each such rule is tagged
**"executed in `engineering-standards-tooling`"** — the follow-on spec that owns
that work. The target is named here regardless of when it lands; a rule may name
a tool that does not run yet.

---

## 1. Python: naming and layout

- **✅ The layer rule stands as written in [app/CONTEXT.md](../app/CONTEXT.md)
  §Layer Boundaries** — `api/ → services/` only; pipeline modules (`ingestion`,
  `preprocessing`, `llm`) never import each other; `jobs/` are thin shells. That
  file is the authority for the layer list; this one only affirms it is the
  rule. *Enforced by: reviewer judgment (`python-code-review`).*

- **✅ Module and function names are `snake_case`, per PEP 8.** *"Modules should
  have short, all-lowercase names. Underscores can be used … if it improves
  readability"*; *"mixedCase is allowed only in contexts where that's already the
  prevailing style … to retain backwards compatibility."* All v2 code complies
  (`per_source_extraction_service.py`, `run_pipeline_service.py`,
  `idea_match.py`, `json_response.py`). This supersedes the `camelCase.py` line
  that root `CLAUDE.md` carried before 2026-07-22.
  *Enforced by: `ruff` `N999`/`N802` (adoption executed in
  `engineering-standards-tooling`); reviewer judgment until then.*

- **⚠️ Six v1 modules and one function are still camelCase** —
  `config/promptTemplates.py`, `ingestion/appStoreReviews.py`,
  `ingestion/youtubeComments.py`, `preprocessing/reviewPipeline.py`,
  `preprocessing/validateUrl.py`, `utilities/textCleaning.py`, and
  `keyChecker()` in `config/secrets.py`. The **rule** above is settled; the
  **rename migration** (modules, imports, and the matching test files) is
  deferred so it can land in one pass while nothing else is in flight.
  *Enforced by: `ruff` `N999`. **Rename executed in
  `engineering-standards-tooling`.***

- **✅ Modern type-hint syntax** — `from __future__ import annotations`, builtin
  generics (`list[str]`), PEP 604 unions (`float | None`). Already the dominant
  style. *Enforced by: `ruff` `UP` rules (adoption executed in
  `engineering-standards-tooling`).*

- **⚠️ One union syntax, not two.** `X | None`, never `Optional[X]`.
  `services/idea_run_service.py` and `eval/{harness,metrics}.py` still import
  `typing.Optional` while the rest of the codebase uses `|`.
  *Enforced by: `ruff` `UP007`. **Executed in
  `engineering-standards-tooling`.***

- **✅ One file per external source.** `clients/{appstore,youtube,openai,
  supabase}.py`; `ingestion/{appStoreReviews,youtubeComments}.py`. A new
  external service gets a new file, not a branch in an existing one.
  *Enforced by: reviewer judgment.*

- **✅ Docstrings and comments explain *why*, citing the PRD or spec section.**
  The module docstring in `api/runs.py` and the CORS `expose_headers` comment in
  `main.py` are the model: they say what breaks without the line, and name the
  section that requires it. This is a real strength of this codebase; the rule
  exists so it survives contributor turnover. *Enforced by: reviewer judgment.*

## 2. Python: configuration and secrets

- **⚠️ Importing a module must not raise.** `config/secrets.py` calls
  `keyChecker()` at module scope, so `import app.config.secrets` fails without a
  full environment — which is why `.github/workflows/test.yml` sets four fake
  secrets merely to collect tests. Validation moves behind a callable or a
  settings object; import becomes side-effect-free.
  *Enforced by: reviewer judgment (a test that imports the module with an empty
  environment is the mechanical version). **Executed in
  `engineering-standards-tooling`.***

- **⚠️ Typed settings via `pydantic-settings`.** It is already in
  `requirements.txt` (2.13.1) and unused. A `BaseSettings` object behind
  `@lru_cache` is the production pattern and fixes the import-time raise above in
  the same change. *Enforced by: `pydantic-settings` itself (validation at
  first access). **Executed in `engineering-standards-tooling`** (spec OQ3).*

- **✅ All tunables live in `config/`, never inline.** `MODEL_ROUTING`,
  engagement filters, prompts, regex, genre/keyword lists. A magic number at a
  call site is a defect. *Enforced by: reviewer judgment
  (`python-code-review`).*

- **✅ Secrets come from `.env` via `python-dotenv`, and never from a `config/`
  module's literals.** `config/` holds tunables; `config/secrets.py` holds the
  *reader*, not the values. *Enforced by: reviewer judgment; secret-scanning on
  the remote.*

## 3. Python: errors, logging, and the request path

- **✅ Per-module `logging.getLogger(__name__)`.** Consistent across services,
  clients, and llm modules today. No module-level `print`.
  *Enforced by: `ruff` `T201` (adoption executed in
  `engineering-standards-tooling`); reviewer judgment until then.*

- **✅ Centralised exception handling** via
  `api/errors.register_exception_handlers`. Handlers do not each format their own
  error body. *Enforced by: reviewer judgment.*

- **⚠️ Logging is configured by the app factory, not at import.**
  `logging.basicConfig` currently runs at `main.py` module scope, so importing
  the module reconfigures global logging for whatever imported it. It belongs in
  `create_app()` — same class of defect as §2's first rule.
  *Enforced by: reviewer judgment. **Executed in
  `engineering-standards-tooling`.***

- **⚠️ Catch specific exceptions.** Never bare `except:`, never
  `except Exception: pass`. Carried forward from the v1 review skill, where it
  was always correct. *Enforced by: `ruff` `E722` + `BLE001`. **Adoption
  executed in `engineering-standards-tooling`.***

- **✅ Pipeline stages raise upward rather than returning `None` or `[]` to
  signal failure.** The caller decides what a failure means; a stage that
  swallows one hides it from the run's `failure_reason`.
  *Enforced by: reviewer judgment (`python-code-review`).*

- **✅ Async discipline is a stated choice, not an accident.** `async def` for
  genuinely awaitable I/O; plain `def` for handlers that call blocking SDKs, so
  FastAPI runs them in its threadpool instead of stalling the event loop. In this
  repo that means: **every `/runs` handler in `api/runs.py` is sync `def`**,
  because its call path reaches the blocking Supabase and OpenAI clients;
  `api/health.py` is `async def` because it returns a static payload and awaits
  nothing. A new handler picks a side on that test and says which in its
  docstring. *Enforced by: reviewer judgment (`python-code-review`).*

## 4. Frontend: React 19 + Vite

The stack is settled: React 19 + JSX + Vite. No TypeScript migration, no second
framework, no component library (see [Declined](#8-declined-and-why)).

- **✅ PascalCase components; pages flat in `src/`; shared UI in
  `components/`.** Including the explicit *no `src/pages/` directory* rule.
  [frontend/CONTEXT.md](../frontend/CONTEXT.md) is the authority for which pages
  exist. *Enforced by: reviewer judgment (`frontend-component-standards`).*

- **✅ Hooks-only state — no Redux, no Zustand.** `react-router-dom` is the one
  sanctioned routing library, authorised by ADR 2026-06-01, which supersedes the
  original no-router rule. *Enforced by: reviewer judgment
  (`frontend-component-standards`).*

- **✅ Backend calls are lifted to page level; child components do not fetch.
  The base URL comes from `import.meta.env.VITE_API_BASE`, never a literal.**
  *Enforced by: reviewer judgment (`frontend-component-standards`).*

- **⚠️ The frontend has no tests and no test runner.** `frontend/package.json`
  has no `test` script. The target is Vitest + React Testing Library, aimed
  first at the run-lifecycle state machine (`pending → preflight_ready → running
  → done | failed`) — the logic most likely to break silently. Playwright E2E is
  deliberately not adopted yet: over-scoped for one flow.
  *Enforced by: `vitest`. **Executed in `engineering-standards-tooling`**
  (spec OQ4).*

- **⚠️ `eslint` is configured and has never run in CI.** `frontend/eslint.config.js`
  exists and `npm run lint` works locally; nothing runs it on a push.
  *Enforced by: `eslint` in a CI job. **Executed in
  `engineering-standards-tooling`.***

- **⚠️ Formatting is a tool's job, not a review topic.** Adopt Prettier, or
  `eslint --fix` alone. Project choice — no external authority compels either;
  the requirement is that *something* mechanical owns formatting.
  *Enforced by: the formatter chosen. **Executed in
  `engineering-standards-tooling`.***

- **⚠️ There is one npm project, `frontend/`, not two.** The root
  `package.json` declares only `dotenv` and makes the repo look like an npm
  workspace it is not. Delete it or justify it in a comment.
  *Enforced by: reviewer judgment. **Executed in
  `engineering-standards-tooling`.***

## 5. Testing

- **✅ The test tree mirrors `app/`** — `tests/api/`, `tests/services/`,
  `tests/llm/`, `tests/preprocessing/`, and so on. This is already true and
  already correct; where the v1 `python-code-review` skill said otherwise, the
  skill was wrong, not the tests. *Enforced by: reviewer judgment
  (`python-code-review`).*

- **✅ Mock external services; run pure modules for real.** YouTube, App Store,
  OpenAI, and Supabase are mocked; `preprocessing`, `redact`, `validateUrl`,
  `schemas`, and `llm/router` are exercised directly. A test that mocks a pure
  module is testing the mock. *Enforced by: reviewer judgment.*

- **✅ Behaviour over implementation; vertical slices over horizontal layers.**
  The `tdd` skill owns this philosophy and the red-green-refactor procedure; this
  file cites it rather than restating it. *Enforced by: reviewer judgment
  (`tdd`).*

- **⚠️ No coverage measurement.** Adopt `pytest-cov` and report a number. Do
  **not** set a failing threshold initially — a threshold picked before the
  baseline is known is a number people game.
  *Enforced by: `pytest-cov`. **Executed in `engineering-standards-tooling`.***

- **⚠️ Test-file names follow the module rename.** `test_appStoreReviews.py`
  becomes `test_app_store_reviews.py` when §1's rename wave lands, not before —
  renaming tests ahead of their modules just moves the inconsistency.
  *Enforced by: `ruff` `N999`. **Executed in
  `engineering-standards-tooling`.***

## 6. Documentation and decision records

- **✅ ADRs live in `planning/decisions/`, one home, full stop.** All three
  skills that touch ADRs agree: `write-adr` scaffolds there, and
  `grill-with-docs` (plus its `ADR-FORMAT.md`) and
  `improve-codebase-architecture` were repointed there in the alignment spec's
  Slice 4 — each now carries an explicit *never create `docs/adr/`*. That
  mattered because `grill-with-docs` created the directory lazily *and* is stage
  02 of the feature-planning workspace, so running the workspace could spawn a
  second ADR home. Filenames follow root `CLAUDE.md`'s
  `YYYY-MM-DD-<subject>.md`; the sequential `0001-slug.md` scheme
  `ADR-FORMAT.md` carried is gone.
  *Enforced by: reviewer judgment; `scripts/check_context_refs.py` catches
  citations of ADRs that do not exist.*

- **✅ Naming conventions are root `CLAUDE.md`'s** — specs
  `feature-name_spec.md`; architecture docs and decision records
  `YYYY-MM-DD-topic.md`. That file is the authority; this one does not duplicate
  the list. *Enforced by: reviewer judgment.*

- **✅ Every `CONTEXT.md` "Authority" line names PRD *sections*, not the whole
  file.** All four already do. Pointing at a 1,000-line PRD is the same as
  pointing at nothing; the next `CONTEXT.md` inherits the narrower form.
  *Enforced by: reviewer judgment.*

- **✅ A citation to a document that does not exist is a defect, not a TODO.**
  This is the rule the whole 2026-07-21 audit was written about: a dead route
  costs every future session, and "we'll write it later" is how four of them
  survived a sweep. Either the target exists or the citation comes out.
  *Enforced by: `scripts/check_context_refs.py` (`make check-refs`) over root
  `CLAUDE.md` and the four domain `CONTEXT.md` files. CI wiring is **executed in
  `engineering-standards-tooling`**.*

## 7. Tooling and CI

> Every rule in this section is *documented* here and *executed* in
> `engineering-standards-tooling`. Nothing below is adopted by the spec that
> produced this file (its N6).

- **⚠️ `ruff` for lint and format.** One binary replacing black + isort + flake8
  + pyupgrade, one config block in `pyproject.toml`. The repo has **no Python
  linter or formatter today**, which makes this the highest value-per-effort item
  on the list. Start narrow — `E`, `F`, `UP`, `B`, `BLE` — get to clean, then
  widen. Do not start from `ALL`.
  *Enforced by: `ruff`. **Executed in `engineering-standards-tooling`.***

- **⚠️ A type checker, `mypy`, non-strict first and tightened per module.**
  `mypy` is the reference implementation and the most compatible with
  third-party stubs; `ty` and `pyrefly` are faster but newer, and this repo has
  no throughput problem to solve.
  *Enforced by: `mypy`. **Executed in `engineering-standards-tooling`**
  (spec OQ5).*

- **⚠️ One dependency manager. Finish the uv migration.** The repo is
  half-migrated: `uv.lock` exists but holds only a header, `pyproject.toml` has
  no `[project]` table (only `[tool.pytest.ini_options]`), dependencies live in a
  117-line flat `pip freeze` `requirements.txt`, and CI installs with `pip`. The
  path is `uv init --bare` then `uv add -r requirements.txt`.
  *Enforced by: `uv` + `uv.lock` in CI. **Executed in
  `engineering-standards-tooling`** (spec OQ5).*

- **⚠️ CI runs lint, type check, tests with coverage, the frontend job, and
  `make check-refs`.** Today it runs `pytest` only. Land the CI jobs *before* the
  conformance work they verify, so that work is checked as it arrives rather than
  asserted. *Enforced by: `.github/workflows/`. **Executed in
  `engineering-standards-tooling`.***

- **⚠️ Do not silence a deprecation you can fix.** `pyproject.toml`'s
  `filterwarnings` ignores `PydanticDeprecatedSince20`, which means Pydantic-v1-
  style code is still present and muted. Find it, fix it, drop the ignore. The
  `supabase`/`postgrest` ignores are legitimate — they are third-party and not
  ours to fix. *Enforced by: `pytest` `filterwarnings` (removing the entry is
  the enforcement). **Executed in `engineering-standards-tooling`.***

## 8. Declined, and why

Recorded so nobody re-proposes these without new evidence. Each is genuinely
recommended by current practice — and wrong for *this* repo's size and stage. A
seam with one implementation behind it is a hypothetical seam.

- **A repository layer** (`repositories/` between services and Supabase). There
  is exactly one persistence target, and `clients/supabase.py` is already the
  seam. Revisit if a second store appears.

- **Feature/domain-based restructuring** (`app/features/<domain>/`). The
  standard advice is to adopt this *once a product has many domains*. This
  product has one: idea → gaps.

- **`Depends()` dependency injection throughout.** Direct module imports with
  monkeypatched tests work today. Revisit when a second concrete implementation
  of anything appears — or sooner, if test setup starts hurting.

- **Structured JSON logging + request-ID propagation + OpenTelemetry.** Correct
  for a multi-instance service. This is single-instance with one active run at a
  time. Revisit at the v1.1 queue work, where correlating concurrent runs
  becomes a real problem.

- **TypeScript migration and a component library.** The frontend stays React 19 +
  JSX + Vite. Out of scope by the alignment spec's N2.

- **Playwright E2E.** Deferred, not declined — see §4. Vitest + RTL on the run
  lifecycle first; revisit E2E when there is more than one critical flow.

---

## Sources

Naming and layout rules are rooted in PEP 8 (the alignment spec's D2). The
remaining rules draw on a 2026-07-21 survey of current Python/FastAPI/React
practice; the full source list is in
[the spec's Sources section](../planning/specs/engineering-standards-alignment_spec.md).

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/) — module and function naming (§1)
- [PEP 604 — Allow writing union types as `X | Y`](https://peps.python.org/pep-0604/) — union syntax (§1)
- FastAPI production-structure guidance, 2026 — layering, centralised handlers, async discipline (§3)
- Modern Python tooling surveys, 2026 — `uv`, `ruff`, `mypy`, `pyproject.toml` (§7)
- React folder-structure and Vitest/RTL guidance, 2026 — component naming, test runner (§4, §5)
