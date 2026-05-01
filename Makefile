.PHONY: test

PYTEST ?= venv/bin/pytest

test:
	$(PYTEST)
