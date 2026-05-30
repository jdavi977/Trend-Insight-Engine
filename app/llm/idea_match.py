"""Idea-match stage — does the researcher's target_gap show up in the gaps?

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §8 (pipeline) + §5 (IdeaMatch).

Only runs when the run carries a `target_gap`. The model is shown the discovered
gaps (already grounded + ranked by synthesis) and the quote pool, and judges
whether any single gap corresponds to the researcher's hypothesis. The verdict is
one of ``matches`` / ``partial`` / ``no_match``.

Like the other v2 LLM stages, the call routes through
`app.llm.router.resolve('idea_match')`, and the post-processing step never trusts
the model blindly: a returned `gap_id` that isn't among the discovered gaps, or
evidence quote_ids outside the pool, are repaired/dropped before building the
`IdeaMatch` (spec §5 grounding discipline).
"""
from __future__ import annotations

import json
import logging
from collections import OrderedDict

from app.clients.openai import create_chat_completion
from app.llm.router import resolve
from app.schemas.runs import GapItem, IdeaMatch, Quote

logger = logging.getLogger(__name__)

_VALID_VERDICTS = ("matches", "partial", "no_match")

_SYSTEM_PROMPT = """You judge whether a researcher's hypothesised TARGET GAP is borne out by the gaps already discovered in competing products.

You receive: the researcher's idea, their target_gap hypothesis, the ranked list of discovered gaps (each with a gap_id and the evidence quote_ids that ground it), and the verbatim quote pool.

Pick the SINGLE discovered gap that best corresponds to the target_gap and assign a verdict:
- "matches": a discovered gap clearly is the target_gap.
- "partial": a discovered gap overlaps the target_gap but is broader, narrower, or only adjacent.
- "no_match": no discovered gap corresponds to the target_gap.

RULES:
1. Choose gap_id only from the discovered gaps you were given. Do NOT invent one.
2. evidence_quote_ids must be drawn from the chosen gap's own evidence. Do NOT invent quote_ids.
3. For "no_match", set gap_id to the closest gap anyway (or the top gap) and leave evidence_quote_ids empty.

Return ONLY valid JSON in this shape:
{"gap_id": "<id>", "verdict": "matches" | "partial" | "no_match", "evidence_quote_ids": ["<id>", ...]}
"""


def _build_user_message(
    idea: str,
    target_gap: str,
    gaps: list[GapItem],
    quotes: list[Quote],
) -> str:
    gap_lines = [
        f"  {g.gap_id} (severity={g.severity}): {g.gap} "
        f"[evidence: {', '.join(g.evidence_quote_ids)}]"
        for g in gaps
    ]
    quote_lines = [
        f'  {q.quote_id} [{q.source}/{q.source_id}]: "{q.text_redacted}"'
        for q in quotes
    ]
    return (
        f"idea: {idea}\n"
        f"target_gap: {target_gap}\n"
        f"\nDiscovered gaps ({len(gaps)}):\n"
        + "\n".join(gap_lines)
        + f"\n\nQuote pool ({len(quotes)} quotes):\n"
        + "\n".join(quote_lines)
    )


def _call_llm(user_message: str) -> str:
    cfg = resolve("idea_match")
    return create_chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )


def _parse(raw: str, gaps: list[GapItem]) -> IdeaMatch:
    """Coerce the model's JSON into a grounded `IdeaMatch`.

    `gaps` is non-empty (the caller guards). An unknown / missing gap_id falls
    back to the top-ranked gap so the result is always schema-valid; evidence is
    filtered to the chosen gap's own citations (system-prompt rule #2), not the
    whole pool. Defaults to `no_match` on any parse trouble.
    """
    gaps_by_id = {g.gap_id: g for g in gaps}

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}

    gap_id = parsed.get("gap_id")
    if gap_id not in gaps_by_id:
        gap_id = gaps[0].gap_id

    verdict = parsed.get("verdict")
    if verdict not in _VALID_VERDICTS:
        verdict = "no_match"

    # Evidence must ground the CHOSEN gap, so filter to that gap's own citations
    # rather than the full quote pool — otherwise quotes belonging to a different
    # gap would pass validation and falsely "support" the match.
    chosen_evidence = set(gaps_by_id[gap_id].evidence_quote_ids)
    raw_evidence = parsed.get("evidence_quote_ids") or []
    if not isinstance(raw_evidence, list):
        raw_evidence = []
    evidence = list(OrderedDict.fromkeys(
        qid for qid in raw_evidence if isinstance(qid, str) and qid in chosen_evidence
    ))

    return IdeaMatch(gap_id=gap_id, verdict=verdict, evidence_quote_ids=evidence)


def match_idea(
    idea: str,
    target_gap: str,
    gaps: list[GapItem],
    quotes: list[Quote],
) -> IdeaMatch | None:
    """Return an `IdeaMatch` for `target_gap`, or None when there's nothing to match.

    Returns None when no gaps survived synthesis — there is no candidate to judge
    against, so the run simply carries no idea_match.
    """
    if not gaps:
        return None
    raw = _call_llm(_build_user_message(idea, target_gap, gaps, quotes))
    result = _parse(raw, gaps)
    logger.info("idea_match gap_id=%s verdict=%s", result.gap_id, result.verdict)
    return result
