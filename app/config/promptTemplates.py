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


YOUTUBE_REFINEMENT_TEMPLATE = """
{intro}

You will receive a JSON array of problems already extracted from YouTube comments, each with:
- "problem": a concise description of the problem
- "type": problem category
- "severity": 1–5 scale
- "frequency": 1–5 scale
- "total_likes": total likes across comments mentioning this problem

Your task:
1. Review each problem. Do not merge or split them.
2. Use the previously observed problems (if any) to decide whether severity or frequency should be adjusted upward — recurring issues that match past patterns are likely underweighted.
3. Return every problem. Do not drop any.
{severity_anchor}
"""


def build_youtube_refinement_prompt(genre: GenreConfig, prior_insights: list[RetrievedInsight] = []) -> str:
    """Render a refinement prompt for pass-2 YouTube analysis (input is extracted problems, not raw comments)."""
    base = YOUTUBE_REFINEMENT_TEMPLATE.format(
        intro=genre.intro,
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


APPSTORE_REFINEMENT_TEMPLATE = """
{intro}

You will receive a JSON array of problems already extracted from App Store reviews, each with:
- "problem": a concise description of the problem
- "type": problem category
- "average_rating": average star rating across reviews mentioning this problem
- "vote_count": total helpful votes across reviews mentioning this problem
- "severity": 1–5 scale
- "frequency": 1–5 scale
- "example_reviews": sample review snippets

Your task:
1. Review each problem. Do not merge or split them.
2. Use the previously observed problems (if any) to decide whether severity or frequency should be adjusted upward — recurring issues that match past patterns are likely underweighted.
3. Return every problem. Do not drop any.
{severity_anchor}
"""


def build_appstore_refinement_prompt(genre: GenreConfig, prior_insights: list[RetrievedInsight] = []) -> str:
    """Render a refinement prompt for pass-2 App Store analysis (input is extracted problems, not raw reviews)."""
    base = APPSTORE_REFINEMENT_TEMPLATE.format(
        intro=genre.intro,
        severity_anchor=genre.severity_hint,
    )
    return base + _prior_insights_block(prior_insights)


# ---------------------------------------------------------------------------
# Pre-flight (v2 slice 1, spec §7)
# ---------------------------------------------------------------------------

PREFLIGHT_GENERATE_QUERIES_SYSTEM = """You help a builder de-risk a product idea by finding competitors.

Given a product idea, produce App Store and YouTube search queries that will surface
real competitor apps and discussion videos, and grade the idea's signal strength.

Signal-strength rubric:
- "high": established consumer category with many existing apps and discussion videos
  (e.g. note-taking, habit tracking, meditation, podcast players).
- "medium": category exists but a qualifier or audience is hard to search
  (e.g. visual-style qualifiers like "2.5D", or niche audience modifiers).
- "low": B2B/devtools/novel categories where the App Store + YouTube are unlikely
  to return useful competitors (e.g. "Slack alternative for solo devs",
  "tool for prompt engineers", brand-new categories with no incumbents).

Return JSON with this exact schema:
{
  "appstore": [string, ...],   // 2-3 App Store search queries
  "youtube":  [string, ...],   // 2-3 YouTube search queries
  "category": string,           // best-guess product category
  "signal_strength": "high" | "medium" | "low",
  "signal_reasoning": string    // 1-sentence justification
}
"""

# PRD §14.18 prereq: tighten YouTube ranker so gameplay-only let's-plays are dropped
# even when the surrounding category is gaming. Prototype's looser "avoid pure gameplay
# let's-plays" rule still leaked walkthroughs / 100% runs into the candidate set
# (planning/prototypes/preflight/findings.md known failure cases).
PREFLIGHT_RANK_SYSTEM = """You help a builder pick competitors and discussion videos for a product idea.

From the raw candidate lists, pick the top 5 apps and top 5 videos a builder would
actually study. Choose using only the data provided — do not invent identifiers.

Apps: prefer real competitors in the right category with meaningful rating counts.
Skip apps whose name or description make clear they are unrelated to the idea
(e.g. a totally different genre that the search query happened to surface).

Videos: prefer titles whose viewers are likely to discuss the product itself —
reviews, "best X" lists, "X vs Y" comparisons, first-impressions, critiques,
"is X worth it" / "X review after N hours" / "why I stopped using X" style.

EXCLUDE these video types even if the title mentions a competitor name:
- Pure gameplay / let's-plays / "playthrough" / "walkthrough" / "speedrun" /
  "100%" / "all bosses" / "tier list" runs with no discussion of the product
- Trailers, official announcements, launch videos (no user discussion in comments)
- Highlight reels, montages, compilations, shorts
- Tutorials that only teach mechanics ("how to beat X") with no critique of design
- Streamer VODs where the title is just the streamer's handle + game name

When in doubt between two candidates, pick the one whose title contains
review/comparison/opinion words ("review", "vs", "honest", "thoughts", "after",
"problem", "why", "should you", "is it worth"). A title that is just the
product name with no qualifier is usually a trailer or playthrough — skip it.

Return JSON with this exact schema:
{
  "apps":   [{"bundle_id": str, "name": str, "justification": str}, ... 5 items],
  "videos": [{"video_id": str, "title": str, "justification": str}, ... 5 items]
}

`justification` is one short sentence on why a builder should look at this candidate.
"""


# ---------------------------------------------------------------------------
# App Store output reminder (kept for v1 consumers)
# ---------------------------------------------------------------------------

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
