"""Synthesis stage — pooled quotes + pain items → grounded, ranked GapItems.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §8 (pipeline), §5 (grounding
contract). The synthesis call is the highest-risk LLM step in slice 1: it sees
the full pooled quote set across all sources and must produce gaps that cite
real quote IDs (≥2 each). The post-processing validator enforces the grounding
contract — rejected gaps are dropped, never auto-repaired.

The prompt lives here (not promptTemplates.py) because it is long, stage-
specific, and tightly coupled to the JSON schema this module parses back. See
issue #49 open-question resolution.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from typing import Iterable

from pydantic import ValidationError

from app.clients.openai import create_chat_completion
from app.llm.router import resolve
from app.schemas.runs import Coverage, GapItem, PainItem, Quote

_SYSTEM_PROMPT = """You are a product-research synthesizer. You receive a pool of verbatim user quotes harvested from competing products (each quote has a stable quote_id), plus per-source pain items already extracted from those quotes. Optionally you also receive an idea the researcher is exploring, and a target_gap they want validated.

Your task: produce a ranked list of distinct product GAPS — concrete unmet needs, recurring complaints, or feature requests — grounded in the quote pool.

RULES (non-negotiable; violations will be discarded by a downstream validator):
1. Every gap MUST cite at least 2 quote_ids drawn verbatim from the pool. Do NOT invent quote_ids.
2. Prefer gaps that span multiple competitors over single-competitor gripes.
3. severity is 1–5 (1 = mild nit, 3 = meaningful friction, 5 = dealbreaker / data loss).
4. Rank gaps by importance (highest first). Aim for 3–7 gaps; fewer well-grounded gaps beats many weakly-grounded ones.
5. Do NOT echo the idea or target_gap text back as a gap. Gaps must be derived from the quotes.

Return ONLY valid JSON in this shape:
{
  "gaps": [
    {"gap": "<one-sentence description>", "severity": 1-5, "evidence_quote_ids": ["<id>", "<id>", ...]}
  ]
}
"""


def _build_user_message(
    idea: str,
    target_gap: str | None,
    quotes: list[Quote],
    pain_items: list[PainItem],
) -> str:
    quote_lines = [
        f'  {q.quote_id} [{q.source}/{q.source_id}, likes={q.like_count}]: "{q.text_redacted}"'
        for q in quotes
    ]
    pain_lines = [
        f"  - [{p.source}/{p.source_id}] {p.text} (cites: {', '.join(p.quote_ids)})"
        for p in pain_items
    ]
    target_block = f"target_gap: {target_gap}\n" if target_gap else ""
    return (
        f"idea: {idea}\n"
        f"{target_block}"
        f"\nQuote pool ({len(quotes)} quotes):\n"
        + "\n".join(quote_lines)
        + f"\n\nPer-source pain items ({len(pain_items)}):\n"
        + ("\n".join(pain_lines) if pain_lines else "  (none)")
    )


def _call_llm(user_message: str) -> str:
    cfg = resolve("synthesis")
    return create_chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
    )


def _parse_candidates(raw: str) -> list[dict]:
    """Tolerate a couple of common LLM JSON shapes; return [] on anything else."""
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []
    if isinstance(parsed, list):
        parsed = {"gaps": parsed}
    if not isinstance(parsed, dict):
        return []
    gaps = parsed.get("gaps")
    return gaps if isinstance(gaps, list) else []


def _competitor_key(quote: Quote) -> str:
    """Slice 1: a competitor is identified by (source, source_id).

    The per-source extractor fans out one batch per competitor — its source_id is
    that competitor's identifier (video_id / app bundle). Synthesis just trusts
    that mapping rather than threading the competitor list through.
    """
    return f"{quote.source}:{quote.source_id}"


def _build_gap(
    candidate: dict,
    ordinal: int,
    pool_index: dict[str, Quote],
) -> GapItem | None:
    """Apply the grounding contract; return None if the candidate must be dropped."""
    quote_ids = candidate.get("evidence_quote_ids") or []
    if not isinstance(quote_ids, list):
        return None
    deduped: list[str] = list(OrderedDict.fromkeys(quote_ids))
    if len(deduped) < 2:
        return None
    if any(qid not in pool_index for qid in deduped):
        return None

    cited = [pool_index[qid] for qid in deduped]
    competitors = list(OrderedDict.fromkeys(_competitor_key(q) for q in cited))

    try:
        return GapItem(
            gap_id=f"gap_{ordinal:03d}",
            gap=candidate.get("gap", ""),
            severity=candidate.get("severity", 0),
            frequency=len(deduped),
            spread=len(competitors),
            competitors_present=competitors,
            evidence_quote_ids=deduped,
        )
    except ValidationError:
        return None


def _coverage(quotes: list[Quote], gaps: Iterable[GapItem]) -> Coverage:
    retrieved = len(quotes)
    cited_ids: set[str] = set()
    for gap in gaps:
        cited_ids.update(gap.evidence_quote_ids)
    cited = len(cited_ids)
    ratio = (cited / retrieved) if retrieved else 0.0
    return Coverage(quotes_retrieved=retrieved, quotes_cited=cited, citation_ratio=ratio)


def synthesize(
    idea: str,
    target_gap: str | None,
    quotes: list[Quote],
    pain_items: list[PainItem],
) -> tuple[list[GapItem], Coverage]:
    """Run the synthesis LLM call and validate against the grounding contract.

    Any candidate gap with fewer than 2 citations, or citing a quote_id not in
    the pool, is silently rejected (spec §5 — not auto-repaired).
    """
    pool_index = {q.quote_id: q for q in quotes}
    raw = _call_llm(_build_user_message(idea, target_gap, quotes, pain_items))
    candidates = _parse_candidates(raw)

    gaps: list[GapItem] = []
    for candidate in candidates:
        gap = _build_gap(candidate, ordinal=len(gaps) + 1, pool_index=pool_index)
        if gap is not None:
            gaps.append(gap)

    return gaps, _coverage(quotes, gaps)
