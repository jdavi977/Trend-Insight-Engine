# ADR: Test Mock Strategy — Mock External Services, Run Real Internal Logic
Date: 2026-05-01
Status: Draft

Related spec: planning/specs/app-refactor-and-pytest-bootstrap_spec.md (§Mock vs real)

## Context

Currently no tests are done for the app. There are many limitations to having a code base with no tests, especially when making external calls such as YouTube Data API or OpenAI which have costs, rate limits, etc.

## Options Considered

1. **Mock externals, run real internals**
2. **Full-mock unit tests**: mocking everything past the function under test, examples include preprocessing and validators
3. **End-to-end with real APIs**: uses real API calls to test data

## Decision

Chose **Mock externals, run real internals** to minimize costs or quota burns on APIs and focus on where data-shaping internals that can cause failures.

## Tradeoffs Accepted

1. Mock client fixtures must be kept in sync with real API response shapes for accurate mock testing.
2. Tests cross layers and does not specifically point to a single function that caused it
3. Rejecting end-to-end gives up the signal that real third-party APIs still behave as expected

## Consequences

- Closes off: 
    1. Tests that import real APIs.
    2. Over-mocking of `preprocessing/` or schema models 
- Enables:
    1. `clients/` wrapper layer becomes the single mock seam
    2. New contributors can run the tests with no API keys
    3. Able to test `preprocessing/` and validators on every service test for free
