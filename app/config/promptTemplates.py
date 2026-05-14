"""Prompt templates and builders for the Genre Config Registry.

The two PROMPT_TEMPLATE constants encode the shared scaffold (input-shape
description, fixed task steps, output rubric) that is identical across all
genres for a given source.  Genre-specific fragments from GenreConfig are
injected via .format() placeholders:

    {intro}           — "You are …" sentence (YouTube) or full preamble incl.
                        "You will receive …" block (App Store, varies per genre)
    {themes}          — numbered bullet block for the themes step (item 1)
    {exclusion}       — ignore-step block (item 2) plus the "Group semantically
                        similar … into a single 'problem'" line (item 3).  The
                        group line is bundled here because the existing handwritten
                        prompts are inconsistent in their quote character around
                        "problem" — each genre carries the exact wording it needs.
    {severity_anchor} — numbered output-format + Rules block (item 4/5)

youtubePromptOutput and appStorePromptOutput are the output-format reminder
strings preserved verbatim from prompts.py.  Existing consumers keep reading
them from prompts.py until a later migration slice removes that module; they
live here so the new wiring is self-contained.
"""
from __future__ import annotations

from app.config.genres import GenreConfig
from app.schemas.rag import RetrievedInsight


def _prior_insights_block(prior_insights: list[RetrievedInsight]) -> str:
    if not prior_insights:
        return ""
    lines = "\n".join(
        f'- [{i.type}] severity:{i.severity} freq:{i.frequency} — "{i.problem}"'
        for i in prior_insights
    )
    return f"\n\nPreviously observed problems (use as context, do not repeat verbatim):\n{lines}"

# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------

YOUTUBE_PROMPT_TEMPLATE = """
{intro}

You will receive a JSON array of YouTube comments, each with:
- "Title": title of the video
- "Likes": number of likes (string or number)
- "Content": the comment text

Your task:
{themes}
{exclusion}
4. Include problems even if only one comment mentions them (set frequency = 1 in that case).
{severity_anchor}
"""


def build_youtube_prompt(genre: GenreConfig, prior_insights: list[RetrievedInsight] = []) -> str:
    """Render a full YouTube system prompt for *genre*."""
    base = YOUTUBE_PROMPT_TEMPLATE.format(
        intro=genre.intro,
        themes=genre.theme_bullets,
        exclusion=genre.exclusion_hint,
        severity_anchor=genre.severity_hint,
    )
    return base + _prior_insights_block(prior_insights)


youtubePromptOutput = """
- Return ONLY valid JSON in this format:

{
  "source": "youtube",
  "problems": [
    {
      "problem": "string",
      "type": "string",
      "total_likes": 1,
      "severity": 1,
      "frequency": 1
    }
  ]
}

- If no problems exist, make sure to return {"problems": []}
"""

# ---------------------------------------------------------------------------
# App Store
# ---------------------------------------------------------------------------

APPSTORE_PROMPT_TEMPLATE = """
{intro}

You will receive a JSON array of App Store reviews, each with:
- "Title": name of the app
- "rating": star rating (1–5)
- "vote_count": number of helpful votes
- "Content": the review text

Your task:

{themes}

{exclusion}

{severity_anchor}
"""


def build_appstore_prompt(genre: GenreConfig, prior_insights: list[RetrievedInsight] = []) -> str:
    """Render a full App Store system prompt for *genre*."""
    base = APPSTORE_PROMPT_TEMPLATE.format(
        intro=genre.intro,
        themes=genre.theme_bullets,
        exclusion=genre.exclusion_hint,
        severity_anchor=genre.severity_hint,
    )
    return base + _prior_insights_block(prior_insights)


appStorePromptOutput = """
- Return ONLY valid JSON in this format:

{
  "source": "app_store",
  "problems": [
    {
      "problem": "string",
      "type": "feature_request | complaint | usability | performance | pricing | other",
      "average_rating": 0,
      "vote_count": 0,
      "frequency": 1,
      "severity": 1,
      "example_reviews": [
        "string",
        "string"
      ]
    }
  ]
}
"""
