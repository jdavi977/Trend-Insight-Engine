"""Standalone end-to-end pre-flight smoke run (issue #45 acceptance criterion 5).

Runs the productionised pre-flight pipeline against one idea using real APIs
(OpenAI + iTunes Search + YouTube Data v3) and prints the structured result.

Usage:
    python -m app.jobs.preflight_smoke "note-taking app with better offline sync"
    python -m app.jobs.preflight_smoke    # uses a default consumer idea
"""
from __future__ import annotations

import json
import sys
import time

from app.services.preflight_service import run as run_preflight

_DEFAULT_IDEA = "note-taking app with better offline sync"

# Pre-flight runs synchronously inside POST /runs and must stay ≤10s (PRD §8).
# This is the measurement gate for slice 3 §7.3: only parallelize the source
# fan-out if a real run breaches this budget — otherwise it stays sequential.
_PREFLIGHT_BUDGET_SECONDS = 10.0


def main(argv: list[str]) -> int:
    idea = " ".join(argv[1:]).strip() or _DEFAULT_IDEA
    print(f"Pre-flight idea: {idea!r}\n")

    started = time.perf_counter()
    result = run_preflight(idea)
    elapsed = time.perf_counter() - started

    print(json.dumps(result.model_dump(), indent=2))
    print(
        f"\nSummary: signal={result.signal_strength} "
        f"category={result.category!r} "
        f"candidates={len(result.candidates)}"
    )
    budget = "OK" if elapsed <= _PREFLIGHT_BUDGET_SECONDS else "OVER BUDGET"
    print(f"Latency: {elapsed:.2f}s / {_PREFLIGHT_BUDGET_SECONDS:.0f}s budget [{budget}]")
    if elapsed > _PREFLIGHT_BUDGET_SECONDS:
        print(
            "  Budget breached — consider the §7.3 fan-out parallelization "
            "(asyncio.gather over the independent search I/O)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
