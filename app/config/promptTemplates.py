"""Prompt templates for the v2 pre-flight stage (PRD §7.3, spec §7).

The v1 genre-templated extraction prompts (build_youtube_prompt,
build_appstore_prompt, refinement builders, *PromptOutput strings) were
removed with the v1 surface in slice 3 (issue #72). The v2 per-source
extraction and synthesis prompts live with their stages
(app/services/per_source_extraction_service.py, app/llm/synthesis.py).
"""
from __future__ import annotations

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
