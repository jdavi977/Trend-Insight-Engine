"""Public keyword-list exports used by preprocessing configs.

Keyword lists live in ``app/config/genres.py`` as the single source of truth.
This module re-exports the ones needed by the preprocessing layer so that
``app/config/preprocessing.py`` has a stable, public import target.
"""
from __future__ import annotations

from app.config.genres import _APPLE_KEYWORDS as APPLE_KEYWORDS

__all__ = ["APPLE_KEYWORDS"]
