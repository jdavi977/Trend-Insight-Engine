"""Snapshot tests: build_*_prompt(genre) output matches the existing
handwritten system prompts in app/config/prompts.py.

Both sides are whitespace-normalised (runs of whitespace → single space,
leading/trailing stripped) before comparison so that template line-break
differences don't matter.  On failure the assertion message shows both sides
in full so drift is easy to debug.
"""
from __future__ import annotations

import re

import pytest

from app.config.genres import (
    APPSTORE_GENRES,
    APPSTORE_SOURCE,
    YOUTUBE_GENRES,
    YOUTUBE_SOURCE,
    get_default_genre,
)
from app.config.promptTemplates import build_appstore_prompt, build_youtube_prompt
from app.config.prompts import (
    appStoreGamesSystemPrompt,
    appStoreSocialSystemPrompt,
    appStoreSystemPrompt,
    appStoreUtilitiesSystemPrompt,
    youtubeGameSystemPrompt,
    youtubeHowtoStyleSystemPrompt,
    youtubeScienceTechSystemPrompt,
    youtubeSystemPrompt,
)


def _norm(text: str) -> str:
    """Collapse all whitespace runs to a single space and strip edges."""
    return re.sub(r"\s+", " ", text).strip()


def _genre(registry: tuple, name: str):
    return next(g for g in registry if g.name == name)


# ---------------------------------------------------------------------------
# YouTube genre prompts (3 named genres)
# ---------------------------------------------------------------------------


class TestYoutubeGenrePrompts:
    def test_games_matches_handwritten(self):
        genre = _genre(YOUTUBE_GENRES, "Games")
        actual = _norm(build_youtube_prompt(genre))
        expected = _norm(youtubeGameSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_science_tech_matches_handwritten(self):
        genre = _genre(YOUTUBE_GENRES, "Science & Tech")
        actual = _norm(build_youtube_prompt(genre))
        expected = _norm(youtubeScienceTechSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_howto_style_matches_handwritten(self):
        genre = _genre(YOUTUBE_GENRES, "How-to & Style")
        actual = _norm(build_youtube_prompt(genre))
        expected = _norm(youtubeHowtoStyleSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_default_matches_handwritten(self):
        default = get_default_genre(YOUTUBE_SOURCE)
        actual = _norm(build_youtube_prompt(default))
        expected = _norm(youtubeSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )


# ---------------------------------------------------------------------------
# App Store genre prompts (3 named genres)
# ---------------------------------------------------------------------------


class TestAppStoreGenrePrompts:
    def test_games_matches_handwritten(self):
        genre = _genre(APPSTORE_GENRES, "Games")
        actual = _norm(build_appstore_prompt(genre))
        expected = _norm(appStoreGamesSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_social_matches_handwritten(self):
        genre = _genre(APPSTORE_GENRES, "Social Networking")
        actual = _norm(build_appstore_prompt(genre))
        expected = _norm(appStoreSocialSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_utilities_matches_handwritten(self):
        genre = _genre(APPSTORE_GENRES, "Utilities")
        actual = _norm(build_appstore_prompt(genre))
        expected = _norm(appStoreUtilitiesSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )

    def test_default_matches_handwritten(self):
        default = get_default_genre(APPSTORE_SOURCE)
        actual = _norm(build_appstore_prompt(default))
        expected = _norm(appStoreSystemPrompt)
        assert actual == expected, (
            f"\n\nACTUAL (normalised):\n{actual}"
            f"\n\nEXPECTED (normalised):\n{expected}"
        )
