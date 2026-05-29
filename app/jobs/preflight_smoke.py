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

from app.services.preflight_service import run as run_preflight

_DEFAULT_IDEA = "note-taking app with better offline sync"


def main(argv: list[str]) -> int:
    idea = " ".join(argv[1:]).strip() or _DEFAULT_IDEA
    print(f"Pre-flight idea: {idea!r}\n")

    result = run_preflight(idea)

    print(json.dumps(result.model_dump(), indent=2))
    print(
        f"\nSummary: signal={result.signal_strength} "
        f"category={result.category!r} "
        f"candidates={len(result.candidates)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
