"""Per-source extraction — idea-blinded by signature.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §8 (pipeline) + §13 (risk).

One call handles one source (one YouTube video OR one App Store app). Pipeline:

    comments → engagement filter (category-keyed, PRD §7.5)
    → promote to Quote pool with stable quote_ids
    → idea-free LLM prompt via router.resolve('per_source_extract')
    → parse + drop pain items citing IDs not in the pool
    → (PainItem[], Quote[])

The function signature does **not** accept `idea` or `target_gap`. That is the
structural guarantee against confirmation-bias leakage (PRD §7.8 / spec §13):
a future caller cannot leak the idea into per-source prompts because there is
no parameter to leak it through. The orchestrator that calls this function
must not have `idea` in scope at the call site either.

PII redaction is **not** applied here — it lands at persist (spec §8 pipeline
order; tracked separately). Quotes returned by this stage carry raw text in
`text_redacted`; the persist layer will replace that with the redacted form.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path

from pydantic import ValidationError

from app.clients.openai import create_chat_completion
from app.config.constants import engagement_threshold
from app.llm.json_response import strip_code_fence
from app.llm.router import resolve
from app.schemas.runs import PainItem, Quote, SourceMetadata

logger = logging.getLogger(__name__)


class _DefaultSourceTag(logging.Filter):
    """Backstop so records logged without a bound source (module-level
    warnings, etc.) still satisfy the formatter's `%(source_tag)s` field."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "source_tag"):
            record.source_tag = "-"
        return True


# Debug trace for this stage only: mirrors the ad-hoc print()s that used to
# live in extract_per_source, but into a file instead of stdout so a full
# run's output can be inspected after the fact without console truncation.
#
# The orchestrator runs one worker thread per competitor concurrently
# (`asyncio.gather` + `asyncio.to_thread` in run_pipeline_service.py), so
# logging each stage the instant it happens lets other sources' lines land
# mid-block. `_SourceTrace` (below) buffers one source's lines in memory and
# emits them as a single record when the source finishes — one write, so the
# file handler's lock makes it atomic and no other thread can splice into the
# middle of it. Each block also carries a `+N.NNNs` offset per line (elapsed
# since that source started) to make slow stages (ingestion vs. the LLM call)
# visible at a glance.
_DEBUG_LOG_PATH = Path("logs/per_source_extraction_debug.log")
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.FileHandler(_DEBUG_LOG_PATH)
    _file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | source_tag=%(source_tag)s | %(message)s"
        )
    )
    logger.addHandler(_file_handler)
    logger.addFilter(_DefaultSourceTag())
    logger.setLevel(logging.DEBUG)


class _SourceTrace:
    """Buffers one source's debug lines, flushed as a single atomic write.

    Blocks land in the file in whatever order sources *finish* (not the order
    they started), but each block is always contiguous top-to-bottom — no
    grep needed to reassemble one source's story.
    """

    def __init__(self, metadata: SourceMetadata) -> None:
        self._tag = f"{metadata.source}:{metadata.source_id}"
        self._start = time.monotonic()
        self._lines: list[str] = []
        self._level = logging.DEBUG

    def _record(self, level: int, name: str, msg: str, *args: object) -> None:
        text = msg % args if args else msg
        elapsed = time.monotonic() - self._start
        self._lines.append(f"  +{elapsed:7.3f}s {name:<7} {text}")
        self._level = max(self._level, level)

    def debug(self, msg: str, *args: object) -> None:
        self._record(logging.DEBUG, "DEBUG", msg, *args)

    def info(self, msg: str, *args: object) -> None:
        self._record(logging.INFO, "INFO", msg, *args)

    def warning(self, msg: str, *args: object) -> None:
        self._record(logging.WARNING, "WARNING", msg, *args)

    def flush(self) -> None:
        """Emit the buffered block as one record, then reset.

        One `logger.log` call = one `FileHandler.emit` = one lock-protected
        write, which is what keeps the block from being interleaved with a
        concurrently-running source's lines. Emitted at the highest severity
        any line in the block recorded (spec §11 criterion 4: the constructed
        prompt is an INFO-level line, so if a consumer sets this logger to
        INFO — dropping DEBUG noise — the block, and the prompt inside it,
        must still survive rather than being dropped by the DEBUG-only path).
        """
        if not self._lines:
            return
        block = "\n".join(self._lines)
        logger.log(self._level, block, extra={"source_tag": self._tag})
        self._lines.clear()


_SYSTEM_PROMPT = """You analyse a batch of verbatim user feedback about ONE product (a YouTube video discussion or an App Store app) and extract concrete PAIN ITEMS — recurring complaints, frustrations, or unmet needs.

You will receive a numbered pool of quotes, each tagged with a stable quote_id. Each pain item you emit must cite at least one quote_id drawn verbatim from the pool.

RULES (non-negotiable; violations will be discarded by a downstream validator):
1. Every pain item MUST cite at least one quote_id drawn verbatim from the pool. Do NOT invent quote_ids.
2. One pain item per distinct theme. Merge near-duplicates; do not split one complaint across multiple items.
3. Pain item `text` is a one-sentence neutral description of the complaint — do not editorialise, do not infer features the quotes do not mention.
4. Skip praise, off-topic chatter, and spam. If the pool contains no pain, return {"pain_items": []}.

Return ONLY valid JSON in this shape:
{
  "pain_items": [
    {"text": "<one-sentence neutral description>", "quote_ids": ["<id>", "<id>", ...]}
  ]
}
"""


def _engagement_value(row: dict, source: str) -> int:
    """Extract the engagement score from a source-native row.

    YouTube rows carry `Likes` (int). App Store rows from the iTunes RSS feed
    carry `vote_count` (string). Bad / missing values coerce to 0.
    """
    field = "Likes" if source == "youtube" else "vote_count"
    try:
        return int(row.get(field, 0) or 0)
    except (ValueError, TypeError):
        return 0


def _comment_text(row: dict) -> str:
    """Pull the comment body from either source's row shape.

    Cleaned rows expose `Content`; raw YouTube rows from `list_comment_threads`
    expose `Text`; raw App Store rows expose `content`. Accept any of them so
    this stage doesn't need to know which upstream stage produced the row.
    """
    text = row.get("Content") or row.get("Text") or row.get("content") or ""
    return text.strip()


def _quote_id(source_id: str, text: str) -> str:
    """Stable, content-addressed quote_id.

    Identical (source_id, text) pairs always hash to the same id, so test
    fixtures are referentially transparent and identical comments seen across
    re-runs land on the same id. Eight hex chars is ~4.3B possibilities —
    collisions across a single video's ≤200 comments are astronomically rare.
    """
    digest = hashlib.sha1(f"{source_id}|{text}".encode("utf-8")).hexdigest()[:8]
    return f"q_{digest}"


def _filter_by_engagement(
    comments: list[dict], source: str, category: str
) -> list[dict]:
    threshold = engagement_threshold(source, category)
    return [row for row in comments if _engagement_value(row, source) >= threshold]


def _build_quote_pool(
    comments: list[dict], metadata: SourceMetadata
) -> list[Quote]:
    """Promote engagement-passing comments to Quotes with stable ids.

    Drops rows with empty text. Dedupes by quote_id (identical text from the
    same source collapses to one Quote — the synthesis pool sees each unique
    voice once).
    """
    seen: dict[str, Quote] = OrderedDict()
    for row in comments:
        text = _comment_text(row)
        if not text:
            continue
        qid = _quote_id(metadata.source_id, text)
        if qid in seen:
            continue
        like_count = max(_engagement_value(row, metadata.source), 0)
        seen[qid] = Quote(
            quote_id=qid,
            source=metadata.source,
            source_id=metadata.source_id,
            text_redacted=text,
            like_count=like_count,
        )
    return list(seen.values())


def _build_user_message(
    quotes: list[Quote], metadata: SourceMetadata
) -> str:
    title_block = f"title: {metadata.title}\n" if metadata.title else ""
    quote_lines = "\n".join(
        f'  {q.quote_id} (likes={q.like_count}): "{q.text_redacted}"' for q in quotes
    )
    return (
        f"source: {metadata.source}\n"
        f"source_id: {metadata.source_id}\n"
        f"{title_block}"
        f"\nQuote pool ({len(quotes)} quotes):\n{quote_lines}"
    )


def _call_llm(user_message: str, log: "_SourceTrace") -> str:
    cfg = resolve("per_source_extract")
    # Spec §11 criterion 4 + §13: log the constructed prompt so the no-idea
    # property is grep-verifiable from logs. The function signature already
    # guarantees absence; the log lets a reviewer confirm post-hoc.
    log.info(
        "per_source_extract prompt | system=%r | user=%r",
        _SYSTEM_PROMPT, user_message,
    )
    return create_chat_completion(
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        model=cfg.model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        response_format={"type": "json_object"},
    )


def _parse_pain_items(raw: str, log: "_SourceTrace") -> list[dict]:
    """Tolerate the same JSON shapes the synthesis parser handles."""
    try:
        parsed = json.loads(strip_code_fence(raw))
    except (json.JSONDecodeError, ValueError):
        log.warning("per_source_extract: failed to parse LLM JSON: %r", raw)
        return []
    if isinstance(parsed, list):
        parsed = {"pain_items": parsed}
    if not isinstance(parsed, dict):
        return []
    items = parsed.get("pain_items")
    return items if isinstance(items, list) else []


def _validate_pain_items(
    candidates: list[dict],
    pool: list[Quote],
    metadata: SourceMetadata,
) -> list[PainItem]:
    """Apply the grounding contract: every cited quote_id must be in the pool."""
    pool_ids = {q.quote_id for q in pool}
    out: list[PainItem] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        cited_raw = candidate.get("quote_ids") or []
        if not isinstance(cited_raw, list):
            continue
        cited = list(OrderedDict.fromkeys(
            qid for qid in cited_raw if isinstance(qid, str) and qid in pool_ids
        ))
        if not cited:
            continue
        try:
            out.append(PainItem(
                source=metadata.source,
                source_id=metadata.source_id,
                text=candidate.get("text", ""),
                quote_ids=cited,
            ))
        except ValidationError:
            continue
    return out


def extract_per_source(
    comments: list[dict],
    source_metadata: SourceMetadata,
) -> tuple[list[PainItem], list[Quote]]:
    """Run idea-blinded per-source extraction for one source.

    Args:
        comments: Source-native rows (YouTube `{Likes, Text|Content, ...}` or
            App Store `{vote_count, content|Content, ...}`). The function does
            not assume any upstream cleaning beyond what the ingestion clients
            produce.
        source_metadata: Identifies the source for grounding + selects the
            engagement threshold via PRD §7.5 category.

    Returns:
        ``(pain_items, quotes)`` where every `PainItem.quote_ids[i]` is a
        member of `{q.quote_id for q in quotes}`. Returns `([], [])` when no
        comment clears the engagement threshold.
    """
    log = _SourceTrace(source_metadata)
    try:
        log.debug("source: %s", source_metadata.source)
        log.debug("comments: %r", comments)
        filtered = _filter_by_engagement(
            comments, source_metadata.source, source_metadata.category
        )
        log.debug("filtered: %r", filtered)
        quote_pool = _build_quote_pool(filtered, source_metadata)
        if not quote_pool:
            return ([], [])

        log.debug("quote_pool: %r", quote_pool)
        raw = _call_llm(_build_user_message(quote_pool, source_metadata), log)

        log.debug("raw: %r", raw)

        pain_items = _validate_pain_items(
            _parse_pain_items(raw, log), quote_pool, source_metadata
        )
        log.debug("pain_items: %r", pain_items)

        return (pain_items, quote_pool)
    finally:
        log.flush()
