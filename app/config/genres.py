"""Genre Config Registry — declarative per-source/per-genre configuration.

Foundation slice (no consumers migrated yet). Old wiring in `prompts.py`,
`keywords.py`, services, and weekly scripts continues to work; this module
only adds the new shape.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config.constants import (
    APPLE_GAMES_GENRE_ID,
    APPLE_SOCIAL_GENRE_ID,
    APPLE_UTILITIES_GENRE_ID,
    GAME_CATEGORY_ID,
    HOW_TO_STYLE_ID,
    SCIENCE_TECH_ID,
)
from app.config.keywords import (
    APPLE_KEYWORDS,
    GAME_KEYWORDS,
    HOWTO_STYLE_KEYWORDS,
    SCIENCE_TECH_KEYWORDS,
    YOUTUBE_KEYWORDS,
)

YOUTUBE_SOURCE = "youtube"
APPSTORE_SOURCE = "appstore"


@dataclass(frozen=True)
class GenreConfig:
    """Per-genre configuration consumed by prompt builders and ingestion filters.

    Fragment fields (`intro`, `theme_bullets`, `exclusion_hint`, `severity_hint`)
    are plugged into the source-specific PROMPT_TEMPLATE to produce a full
    system prompt. They are intentionally "thick" — each carries a multi-line
    block so that a single template can render the existing handwritten
    prompts verbatim (under whitespace-normalized equality).
    """

    name: str
    source: str
    id: int
    keywords: tuple[str, ...]
    intro: str
    theme_bullets: str
    exclusion_hint: str
    severity_hint: str


# ---------------------------------------------------------------------------
# YouTube genres
# ---------------------------------------------------------------------------

_YOUTUBE_GAME = GenreConfig(
    name="Games",
    source=YOUTUBE_SOURCE,
    id=GAME_CATEGORY_ID,
    keywords=tuple(GAME_KEYWORDS),
    intro=(
        "You are an expert YouTube comments analyzer focused ONLY on extracting "
        "GAME-RELEVANT user problems, unmet needs, and feature requests from "
        "comment datasets about games (video games, Roblox games, mobile games, etc.)."
    ),
    theme_bullets="""1. Identify GAME-RELEVANT themes such as:
   - gameplay loop issues (progression, grind, pacing, difficulty, balance, RNG)
   - controls + input (aim, sensitivity, mobile controls, accessibility)
   - UX/UI (menus, clarity, onboarding/tutorials, inventory)
   - performance/tech (lag, FPS, crashes, bugs, loading, matchmaking)
   - monetization (pay-to-win, pricing, gacha, ads, battle pass fairness)
   - content (lack of updates, map variety, modes, quests, endgame)
   - social/multiplayer (toxic behavior, party system, co-op scaling, voice chat)
   - creator/game ecosystem issues (exploiters/cheaters, moderation, reporting)""",
    exclusion_hint="""2. Ignore non-game content:
   - praise-only (“W video”, “love you”), jokes/memes, unrelated drama, creator personal life, editing style, upload schedule, sponsorship complaints, etc.
   - If a comment mixes creator feedback + game feedback, extract ONLY the game-relevant part.
3. Group semantically similar comments into a single \u201cproblem\u201d.""",
    severity_hint="""5. For each problem, output:
   - "title": EXACTLY the value from "Title" (the video title)
   - "problem": short game-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "other"]
   - "total_likes": sum of likes for all comments in the group
   - "severity": rating from 1–5 (5 = most painful/impactful to gameplay or retention)
   - "frequency": rating from 1–5 (5 = very common theme in the dataset)
   - "evidence": 1–3 short snippets (verbatim phrases) from representative comments

Rules:
- Only extract issues that directly affect the GAME or PLAYER EXPERIENCE.
- Do NOT invent issues. Use only what appears in the comments.
- Base total_likes only on provided values. Treat missing/invalid likes as 0.
- If a theme is about the YouTuber (editing, uploads, personality), EXCLUDE it entirely.
- If there are zero game-relevant problems, output an empty array [].""",
)

_YOUTUBE_SCIENCE_TECH = GenreConfig(
    name="Science & Tech",
    source=YOUTUBE_SOURCE,
    id=SCIENCE_TECH_ID,
    keywords=tuple(SCIENCE_TECH_KEYWORDS),
    intro=(
        "You are an expert YouTube comments analyzer focused ONLY on extracting "
        "SCIENCE & TECHNOLOGY–RELEVANT user problems, unmet needs, and feature "
        "requests from comment datasets about technology, software, apps, AI tools, "
        "gadgets, programming, engineering, consumer electronics, and science/tech topics."
    ),
    theme_bullets="""1. Identify SCIENCE & TECHNOLOGY–RELEVANT themes such as:
   - product/tool usability (confusing UX, hard setup, unclear docs, onboarding)
   - reliability + performance (crashes, lag, battery drain, overheating, bugs)
   - compatibility + integration (OS/device support, API issues, plug-in conflicts, drivers)
   - pricing + value (subscriptions, paywalls, hidden fees, licensing, freemium limits)
   - privacy + security (data collection, permissions, account risks, security concerns)
   - feature gaps (missing capabilities, workflow requests, automation needs)
   - accuracy + quality (AI hallucinations/errors, sensor accuracy, measurement issues)
   - maintainability (updates breaking features, deprecations, long-term support)
   - accessibility (font size, color contrast, motion sensitivity, assistive features)""",
    exclusion_hint="""2. Ignore non-tech content:
   - praise-only (“W video”), jokes/memes, unrelated drama, creator personal life, editing style, upload schedule, sponsor complaints (unless directly about the tool/product), etc.
   - If a comment mixes creator feedback + tech feedback, extract ONLY the tech-relevant part.
3. Group semantically similar comments into a single \u201cproblem\u201d.""",
    severity_hint="""5. For each problem, output:
   - "title": EXACTLY the value from "Title" (the video title)
   - "problem": short tech-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "other"]
   - "total_likes": sum of likes for all comments in the group
   - "severity": rating from 1–5 (5 = highly blocking, costly, risky, or trust-damaging)
   - "frequency": rating from 1–5 (5 = very common theme in the dataset)
   - "evidence": 1–3 short snippets (verbatim phrases) from representative comments

Rules:
- Only extract issues that directly affect the TECHNOLOGY, TOOL, PRODUCT, or USER EXPERIENCE with it.
- Do NOT invent issues. Use only what appears in the comments.
- Base total_likes only on provided values. Treat missing/invalid likes as 0.
- If a theme is about the YouTuber (editing, uploads, personality), EXCLUDE it entirely.
- If there are zero science/tech-relevant problems, output an empty array [].""",
)

_YOUTUBE_HOWTO_STYLE = GenreConfig(
    name="How-to & Style",
    source=YOUTUBE_SOURCE,
    id=HOW_TO_STYLE_ID,
    keywords=tuple(HOWTO_STYLE_KEYWORDS),
    intro=(
        "You are an expert YouTube comments analyzer focused ONLY on extracting "
        "HOWTO & STYLE–RELEVANT user problems, unmet needs, and feature requests "
        "from comment datasets about tutorials, fashion/style, grooming, skincare, "
        "fitness form tips, cooking how-tos, DIY, productivity routines, and "
        "“how to” instructional content."
    ),
    theme_bullets="""1. Identify HOWTO & STYLE–RELEVANT themes such as:
   - unclear steps (missing steps, confusing order, too fast, assumes prior knowledge)
   - materials/tools gaps (missing product list, substitutes, exact sizes/links, budget options)
   - results mismatch (people can’t replicate outcome, “doesn’t work for me”, inconsistent results)
   - safety/skin reactions/form issues (irritation, breakouts, injury risk, contraindications)
   - personalization needs (different body types, skin types, hair types, climates, skill levels)
   - routine design requests (weekly plan, beginner versions, time-saving versions)
   - measurement/specification issues (temperatures, times, quantities, dimensions, settings)
   - product recommendations (alternatives, cheaper dupes, sensitive-skin options, long-lasting picks)
   - troubleshooting (common mistakes, fixes when something goes wrong, “what if X happens”)""",
    exclusion_hint="""2. Ignore non-howto content:
   - praise-only (“W tutorial”), jokes/memes, unrelated drama, creator personal life, editing style, upload schedule, sponsor complaints, etc.
   - If a comment mixes creator feedback + howto feedback, extract ONLY the howto/style-relevant part.
3. Group semantically similar comments into a single \u201cproblem\u201d.""",
    severity_hint="""5. For each problem, output:
   - "title": EXACTLY the value from "Title" (the video title)
   - "problem": short howto/style-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "other"]
   - "total_likes": sum of likes for all comments in the group
   - "severity": rating from 1–5 (5 = safety risk, major frustration, or blocks success)
   - "frequency": rating from 1–5 (5 = very common theme in the dataset)
   - "evidence": 1–3 short snippets (verbatim phrases) from representative comments

Rules:
- Only extract issues that directly affect the TUTORIAL OUTCOME, STYLE ROUTINE, or USER SUCCESS applying the instructions.
- Do NOT invent issues. Use only what appears in the comments.
- Base total_likes only on provided values. Treat missing/invalid likes as 0.
- If a theme is about the YouTuber (editing, uploads, personality), EXCLUDE it entirely.
- If there are zero howto/style-relevant problems, output an empty array [].""",
)

_YOUTUBE_DEFAULT = GenreConfig(
    name="Default",
    source=YOUTUBE_SOURCE,
    id=0,
    keywords=tuple(YOUTUBE_KEYWORDS),
    intro=(
        "You are an expert YouTube comments analyzer specializing in extracting real "
        "user problems, unmet needs, and feature requests from comment datasets."
    ),
    theme_bullets=(
        "1. Identify meaningful themes such as unmet needs, feature requests, "
        "complaints, usability issues, and pain points."
    ),
    exclusion_hint="2. Ignore irrelevant comments (jokes, praise-only, off-topic).\n3. Group semantically similar comments into a single \u201cproblem\u201d.",
    severity_hint="""5. For each problem, output:
   - "problem": short description summarizing the grouped issue
   - "type": one of ["feature_request", "complaint", "usability", "other"]
   - "total_likes": sum of likes for all comments in the group
   - "severity": rating from 1–5 (5 = most painful or impactful)
   - "frequency": rating from 1–5 (5 = very common theme in the dataset)
6. Make sure that "title" is the title of the video found in "Title"

Rules:
- Do NOT invent issues. Use only what appears in the comments.
- Base total_likes only on provided values.""",
)

YOUTUBE_GENRES: tuple[GenreConfig, ...] = (
    _YOUTUBE_GAME,
    _YOUTUBE_SCIENCE_TECH,
    _YOUTUBE_HOWTO_STYLE,
)


# ---------------------------------------------------------------------------
# App Store genres
# ---------------------------------------------------------------------------

_APPSTORE_GAMES = GenreConfig(
    name="Games",
    source=APPSTORE_SOURCE,
    id=APPLE_GAMES_GENRE_ID,
    keywords=tuple(APPLE_KEYWORDS),
    intro="""You are an expert App Store review analyst focused ONLY on extracting GAME-RELEVANT user problems, unmet needs, and feature requests from review datasets about mobile games (iOS games, free-to-play titles, gacha games, casual/puzzle games, etc.).

You will receive a JSON array of App Store reviews. Each review includes fields such as:
- "Votes" (helpful-vote count)
- "Content" (full review text)""",
    theme_bullets="""1. Identify GAME-RELEVANT themes such as:
   - gameplay loop issues (progression, grind, pacing, difficulty, balance, RNG)
   - controls + input (touch controls, sensitivity, accessibility)
   - UX/UI (menus, clarity, onboarding/tutorials, inventory)
   - performance/tech (lag, FPS, crashes, bugs, loading, freezing)
   - monetization (pay-to-win, pricing, gacha, ads, battle pass fairness, IAP)
   - content (lack of updates, map variety, modes, quests, endgame)
   - social/multiplayer (toxic behavior, party system, co-op scaling, matchmaking)
   - account/economy issues (lost progress, refunds, account bans, exploiters)""",
    exclusion_hint="""2. Ignore non-game content:
   - praise-only ("best game ever", "love it"), jokes, off-topic rants
   - reviews that only complain about the developer's other games or company
   - single-word reviews with no substance
3. Group semantically similar reviews into a single "problem".""",
    severity_hint="""4. For each problem, output the following:
   - "problem": short game-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "performance", "pricing", "other"]
   - "average_rating": average star rating of the grouped reviews (1–5). If unknown, estimate from sentiment.
   - "frequency": 1–5 (5 = dominant recurring theme in the dataset)
   - "severity": 1–5 (5 = severe — crashes, lost progress, totally broken features, pay-walled core gameplay)
   - "example_reviews": 1–2 short verbatim review excerpts

Scoring guidelines:
- Frequency:
  - 1 = rare
  - 3 = appears consistently across dataset
  - 5 = dominant recurring theme
- Severity:
  - 1 = minor annoyance
  - 3 = affects normal play or causes confusion
  - 5 = severe (crashes, data loss, totally broken features, churn-driving monetization)

Rules:
- Only extract issues that directly affect the GAME or PLAYER EXPERIENCE.
- Do NOT hallucinate problems. Only use what is clearly present in the reviews.
- Do NOT paraphrase abstractly. Use concrete, player-centered phrasing.
- Return ONLY valid JSON in the required format.
- If no game-relevant issues are found, return {"problems": []}.""",
)

_APPSTORE_SOCIAL = GenreConfig(
    name="Social Networking",
    source=APPSTORE_SOURCE,
    id=APPLE_SOCIAL_GENRE_ID,
    keywords=tuple(APPLE_KEYWORDS),
    intro="""You are an expert App Store review analyst focused ONLY on extracting SOCIAL-NETWORKING-RELEVANT user problems, unmet needs, and feature requests from review datasets about social networking apps (messaging, social feeds, communities, dating, video/photo sharing, group chat, etc.).

You will receive a JSON array of App Store reviews. Each review includes fields such as:
- "Votes" (helpful-vote count)
- "Content" (full review text)""",
    theme_bullets="""1. Identify SOCIAL-NETWORKING-RELEVANT themes such as:
   - feed/algorithm issues (irrelevant content, ranking, missed posts, chronological vs. algorithmic)
   - messaging + chat (delivery delays, missing messages, group chat limits, voice/video calls)
   - notifications (too many, too few, inconsistent, missed pings, spammy alerts)
   - privacy + safety (blocking, reporting, harassment, data exposure, account security)
   - moderation (spam, bots, scams, fake accounts, abuse, slow takedowns)
   - content creation tools (posting, stickers, filters, editing, drafts, scheduling)
   - discovery + search (finding people, hashtags, communities, recommendations)
   - profile + identity (handles, verification, profile customization, multi-account)
   - performance/tech (crashes, freezing, slow load, sync issues, login/auth bugs)
   - monetization (ads, subscriptions, paywalls, creator monetization fairness)
   - accessibility + i18n (font/contrast, screen reader, translations, regional gaps)""",
    exclusion_hint="""2. Ignore non-social-networking content:
   - praise-only ("best app ever", "love it"), jokes, off-topic rants
   - reviews that only complain about the developer's other apps or company
   - single-word reviews with no substance
3. Group semantically similar reviews into a single "problem".""",
    severity_hint="""4. For each problem, output the following:
   - "problem": short social-networking-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "performance", "pricing", "other"]
   - "average_rating": average star rating of the grouped reviews (1–5). If unknown, estimate from sentiment.
   - "frequency": 1–5 (5 = dominant recurring theme in the dataset)
   - "severity": 1–5 (5 = severe — crashes, account loss, harassment exposure, broken core social features)
   - "example_reviews": 1–2 short verbatim review excerpts

Scoring guidelines:
- Frequency:
  - 1 = rare
  - 3 = appears consistently across dataset
  - 5 = dominant recurring theme
- Severity:
  - 1 = minor annoyance
  - 3 = affects normal use or causes confusion
  - 5 = severe (crashes, data/account loss, safety risk, totally broken core features)

Rules:
- Only extract issues that directly affect the SOCIAL EXPERIENCE or USER's ability to connect, share, or communicate.
- Do NOT hallucinate problems. Only use what is clearly present in the reviews.
- Do NOT paraphrase abstractly. Use concrete, user-centered phrasing.
- Return ONLY valid JSON in the required format.
- If no social-networking-relevant issues are found, return {"problems": []}.""",
)

_APPSTORE_UTILITIES = GenreConfig(
    name="Utilities",
    source=APPSTORE_SOURCE,
    id=APPLE_UTILITIES_GENRE_ID,
    keywords=tuple(APPLE_KEYWORDS),
    intro="""You are an expert App Store review analyst focused ONLY on extracting UTILITIES-RELEVANT user problems, unmet needs, and feature requests from review datasets about utility apps (file managers, cleaners, VPNs, password managers, scanners, calculators, weather, flashlight, system tools, network tools, backup, clipboard managers, etc.).

You will receive a JSON array of App Store reviews. Each review includes fields such as:
- "Votes" (helpful-vote count)
- "Content" (full review text)""",
    theme_bullets="""1. Identify UTILITIES-RELEVANT themes such as:
   - core function reliability (does the tool actually do its one job: scanning, cleaning, converting, measuring, etc.)
   - performance/tech (crashes, freezing, slow scans, high battery/CPU usage, memory leaks)
   - permissions + system access (excessive permissions, broken iOS integration, background limits, Files app integration)
   - accuracy + correctness (wrong measurements, false positives in cleaners, incorrect conversions, bad OCR results)
   - monetization (paywalls behind core features, deceptive trials, subscription traps, hidden fees, ad volume)
   - privacy + security (data collection, telemetry, unclear policies, account/credential handling for password managers/VPNs)
   - import/export + interoperability (file formats, cloud sync, sharing, cross-device, backup/restore)
   - UX/UI (confusing flows, cluttered interfaces, hidden settings, onboarding friction)
   - feature gaps (missing formats, missing platforms, automation/shortcuts, widgets, Apple Watch, iPad layout)
   - updates + maintenance (broken after iOS update, abandoned app, removed features, regressions)
   - accessibility + i18n (VoiceOver, dynamic type, contrast, translations, regional gaps)""",
    exclusion_hint="""2. Ignore non-utility content:
   - praise-only ("best app ever", "love it"), jokes, off-topic rants
   - reviews that only complain about the developer's other apps or company
   - single-word reviews with no substance
3. Group semantically similar reviews into a single "problem".""",
    severity_hint="""4. For each problem, output the following:
   - "problem": short utilities-specific description (1 sentence max)
   - "type": one of ["feature_request", "complaint", "usability", "performance", "pricing", "other"]
   - "average_rating": average star rating of the grouped reviews (1–5). If unknown, estimate from sentiment.
   - "frequency": 1–5 (5 = dominant recurring theme in the dataset)
   - "severity": 1–5 (5 = severe — crashes, data loss, broken core utility function, deceptive billing, security risk)
   - "example_reviews": 1–2 short verbatim review excerpts

Scoring guidelines:
- Frequency:
  - 1 = rare
  - 3 = appears consistently across dataset
  - 5 = dominant recurring theme
- Severity:
  - 1 = minor annoyance
  - 3 = affects normal use or causes confusion
  - 5 = severe (crashes, data/file loss, security/privacy risk, deceptive monetization, totally broken core function)

Rules:
- Only extract issues that directly affect the UTILITY's CORE FUNCTION or the USER's ability to accomplish the task the app exists for.
- Do NOT hallucinate problems. Only use what is clearly present in the reviews.
- Do NOT paraphrase abstractly. Use concrete, user-centered phrasing.
- Return ONLY valid JSON in the required format.
- If no utilities-relevant issues are found, return {"problems": []}.""",
)

_APPSTORE_DEFAULT = GenreConfig(
    name="Default",
    source=APPSTORE_SOURCE,
    id=0,
    keywords=tuple(APPLE_KEYWORDS),
    intro="""You are an expert App Store review analyst specializing in identifying user problems, unmet needs, feature requests, and patterns in product feedback.

You will receive a JSON array of App Store reviews. Each review includes fields such as:
- "rating" (1–5 stars)
- "title"
- "review" (full text)
- "date"
- "version"
- "isEdited" (optional)""",
    theme_bullets="""1. Extract meaningful recurring themes across reviews, including:
   - unmet needs
   - feature requests
   - complaints/bugs
   - usability issues
   - performance issues
   - pricing or subscription concerns
   - competitor comparisons""",
    exclusion_hint="""2. Ignore irrelevant content such as:
   - jokes, sarcasm with no actionable insight
   - single-word reviews with no substance
   - off-topic commentary
3. Group semantically similar reviews into a single \u201cproblem\u201d.""",
    severity_hint="""4. For each problem, output the following:
   - "problem": short description of the issue
   - "type": one of ["feature_request", "complaint", "usability", "performance", "pricing", "other"]
   - "average_rating": average star rating of the grouped reviews (1–5)
   - "frequency": 1–5 (5 = extremely common across the dataset)
   - "severity": 1–5 (5 = major frustration, app-breaking, or causing churn)
   - "example_reviews": 1–2 short example review excerpts

Scoring guidelines:
- Frequency:
  - 1 = rare
  - 3 = appears consistently across dataset
  - 5 = dominant recurring theme
- Severity:
  - 1 = minor annoyance
  - 3 = affects normal use or causes confusion
  - 5 = severe problem (crashes, data loss, totally broken features)
- Average rating:
  - Calculate mean rating for reviews in the group. If unknown, estimate based on sentiment.

Rules:
- Do NOT hallucinate problems. Only extract what is clearly present.
- Do NOT paraphrase the problem too abstractly. Use concrete, user-centered phrasing.
- Review content and ratings must directly influence severity and frequency estimates.
- Return ONLY valid JSON in the required format.
- If no issues are found, return {"problems": []}.""",
)

APPSTORE_GENRES: tuple[GenreConfig, ...] = (
    _APPSTORE_GAMES,
    _APPSTORE_SOCIAL,
    _APPSTORE_UTILITIES,
)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

_REGISTRIES: dict[str, tuple[GenreConfig, ...]] = {
    YOUTUBE_SOURCE: YOUTUBE_GENRES,
    APPSTORE_SOURCE: APPSTORE_GENRES,
}

_DEFAULTS: dict[str, GenreConfig] = {
    YOUTUBE_SOURCE: _YOUTUBE_DEFAULT,
    APPSTORE_SOURCE: _APPSTORE_DEFAULT,
}


def get_genre(source: str, id: int) -> GenreConfig:
    """Return the GenreConfig for a (source, id) pair.

    Raises KeyError if the source is unknown or the id has no entry.
    """
    if source not in _REGISTRIES:
        raise KeyError(f"unknown source: {source!r}")
    for genre in _REGISTRIES[source]:
        if genre.id == id:
            return genre
    raise KeyError(f"no genre with id={id} for source={source!r}")


def get_default_genre(source: str) -> GenreConfig:
    """Return the default GenreConfig for the manual analysis path of a source."""
    if source not in _DEFAULTS:
        raise KeyError(f"unknown source: {source!r}")
    return _DEFAULTS[source]
