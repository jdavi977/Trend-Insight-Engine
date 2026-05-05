# ADR: Test Mock Strategy — Mock External Services, Run Real Internal Logic
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Mock vs real)

## Context
> _What situation forced this decision? Describe the state of the codebase, the pain point, or the trigger in your own words. 1–2 sentences. Avoid solution language here — only the problem._

Hints to draw from:
- The pytest bootstrap spec is introducing a `/tests/` tree mirroring `app/` and needs a default rule for what gets mocked vs run for real.
- Tests in this codebase will cross multiple layers (preprocessing → validators → services → clients → external APIs) — without a rule, every test author re-decides where to cut.
- External calls in scope: YouTube Data API v3, iTunes RSS, OpenAI (gpt-4o), Supabase. Each has cost, rate limits, network flakiness, or non-determinism.
- Internal logic in scope: `preprocessing/`, `validateUrl.py`, `validateOutput.py`, Pydantic schema models — pure, deterministic, fast.

## Options Considered
> _List the real alternatives you weighed. Minimum 2. For each, write one line describing what that path would actually look like in this codebase. If you can only think of one option, the decision is not yet ripe — go think harder before filling this in._

1. **Mock externals, run real internals** — _your one-line description_
2. **Full-mock unit tests** — _your one-line description (mock everything past the function under test, including preprocessing and validators)_
3. **End-to-end with real APIs** — _your one-line description (hit YouTube, iTunes, OpenAI, Supabase live in CI)_

## Decision
> _Which option did you choose, and what is the single primary reason? One sentence. If you need a paragraph to justify it, the reason probably isn't the real reason — keep digging._

Chose **[Option ?]** because …

Hints to draw from when picking the "single primary reason":
- Determinism / CI reliability: which option will or won't flake on a Tuesday morning.
- Cost: OpenAI and YouTube quota burn per CI run vs zero.
- Confidence in real bugs: which option would actually have caught the kind of regression you fear most (URL parsing, schema drift, prompt-output shape).
- Speed of the feedback loop while refactoring.
- Where the real risk lives in this codebase — at the network boundary, or in the data-shaping internals.

## Tradeoffs Accepted
> _Every choice gives something up. What did you lose by not picking the other options? What new complexity, discipline, or future cost did you take on? Be specific — "some overhead" is not a tradeoff, "one extra file per endpoint flow" is._

Hints — concrete costs of the chosen option:
- Need a `conftest.py` with mock client fixtures for YouTube/iTunes/OpenAI/Supabase, and `tests/fixtures/` JSON to feed them — fixtures must be kept in sync with real API response shapes.
- Mocks can drift from reality: a YouTube response shape change won't be caught until prod. No CI signal for live API breakage.
- Tests cross layers (preprocessing + validators + service together), so a failure points to "somewhere in this slice" rather than a single function — slightly noisier localization than pure unit tests.
- By rejecting full-mock: gives up the tightest possible per-function isolation; refactors inside `preprocessing/` will ripple into service tests.
- By rejecting end-to-end: gives up the only signal that real third-party APIs still behave as expected; that signal has to come from somewhere else (manual smoke, scheduled job, monitoring).

-
-

## Consequences
> _Two halves: what does this **close off** (things the codebase will no longer do, patterns that are now disallowed) and what does this **enable** (things that get easier, seams that now exist). Write at least one of each._

Hints to draw from:
- Closes off: tests that import the real `openai`, `googleapiclient`, `requests` (for iTunes), or `supabase` SDKs at call time; tests that need network or secrets to run; over-mocking of `preprocessing/` or schema models inside service tests.
- Enables: a `clients/` wrapper layer becomes the single mock seam — services can be tested with a one-line fixture swap; `preprocessing/` and validators get exercised on every service test for free; CI stays offline, free, and deterministic; new contributors can run the full suite with no API keys.

- Closes off:
- Enables:
