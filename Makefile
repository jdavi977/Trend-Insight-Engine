.PHONY: test check-refs

PYTEST ?= venv/bin/pytest
PYTHON ?= venv/bin/python

test:
	$(PYTEST)

# Every path, skill, and document referenced by CLAUDE.md and the four domain
# CONTEXT.md files must resolve on disk (engineering-standards-alignment A2).
check-refs:
	$(PYTHON) scripts/check_context_refs.py
