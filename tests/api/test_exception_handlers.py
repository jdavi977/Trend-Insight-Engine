"""Regression tests for the exception handlers wired into the FastAPI app.

`main.py` declares two handlers whose first parameter is annotated as `Request`,
but the symbol was never imported. Under PEP 649 lazy evaluation the bug
hides until something resolves the annotations — which is exactly what
`typing.get_type_hints` and many tooling/IDE paths do.
"""
from __future__ import annotations

import typing

from app.api import errors


def test_validation_exception_handler_annotations_resolve():
    typing.get_type_hints(errors.validation_exception_handler)


def test_general_http_exception_handler_annotations_resolve():
    typing.get_type_hints(errors.general_http_exception_handler)
