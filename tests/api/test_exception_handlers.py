"""Regression tests for the exception handlers wired into the FastAPI app.

`main.py` declares two handlers whose first parameter is annotated as `Request`,
but the symbol was never imported. Under PEP 649 lazy evaluation the bug
hides until something resolves the annotations — which is exactly what
`typing.get_type_hints` and many tooling/IDE paths do.
"""
from __future__ import annotations

import typing

from app import main


def test_validation_exception_handler_annotations_resolve():
    typing.get_type_hints(main.validation_exception_handler)


def test_general_http_exception_handler_annotations_resolve():
    typing.get_type_hints(main.general_http_exception_handler)
