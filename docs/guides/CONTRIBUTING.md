# Contributing

## Branching Strategy

| Branch | Purpose |
|--------|---------|
| `master` | Stable, production-ready code. Direct pushes are rare — use PRs. |
| `<feature>` | All development work. Branch off `master`, open a PR back to it. |

Branch names should mirror what they do: `rag`, `youtube-backfill`, `fix-appstore-pagination`.

---

## Commit Style

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short imperative description>
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

**Scope:** the module or area changed — `rag`, `youtube`, `appstore`, `llm`, `frontend`, `pipeline`

```
feat(rag): add similarity threshold env override
fix(appstore): handle missing source field in service
docs(pipeline): add backfill instructions
```

- Keep the first line under 72 characters
- Use imperative mood: "add" not "added", "fix" not "fixed"
- No period at the end

---

## Pull Request Process

1. Branch off `master` with a descriptive name
2. Keep PRs focused — one concern per PR
3. Run tests locally before opening (see below)
4. Title should match the commit style: `feat(scope): description`
5. The PR description should answer: what changed, why, and how to test it

CI runs automatically on every PR and push to `master` (see `.github/workflows/test.yml`).

---

## Running Tests

**Setup:** make sure the virtual environment is active and dependencies are installed (see [SETUP.md](SETUP.md)).

```bash
# Run the full suite
python -m pytest -q

# Run a specific directory
python -m pytest tests/preprocessing/

# Run a single file, verbose
python -m pytest tests/rag/test_rag.py -v
```

**No real API keys required.** All external services (YouTube, iTunes, OpenAI, Supabase) are mocked in tests. CI uses stub keys.

**Test layout** mirrors `app/`:

```
tests/
  api/             route handlers, exception handlers, request schemas
  clients/         one test file per external client
  ingestion/       YouTube and App Store fetching
  preprocessing/   URL validation, comment/review cleaning pipeline
  llm/             insight extraction, output schema validation
  jobs/            automated pipeline scripts
  services/        youtube_service, appstore_service, rag_service
  rag/             embed-and-store, retrieve-similar
  config/          prompt template rendering
  conftest.py      shared fixtures
```

**Mocking strategy:** external calls are always mocked. Preprocessing, validation, and schema modules are tested with real data — they're deterministic and have no side effects.

---

## Code Standards

Backend code lives under `app/`. Before opening a PR on backend changes, run `/python-code-review` to check module structure, layer separation, FastAPI endpoint shape, and error handling.

Key rules:
- Services orchestrate pipeline stages — they never call HTTP endpoints or import from `api/`
- Clients wrap exactly one external service — no business logic
- Config values go in `app/config/` — never hardcoded in modules
- Secrets loaded via `keyChecker()` in `app/config/secrets.py` — never read `os.environ` directly
- No `__main__` blocks in services or API modules

Frontend code lives under `frontend/src/`. Run `/frontend-component-standards` before opening a PR on frontend changes.
