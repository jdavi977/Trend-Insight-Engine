import threading
from datetime import date, datetime, timezone

from openai import OpenAI

from app.config import secrets
from app.config.constants import openai_price
from app.config.secrets import OPENAI_KEY

_MODEL = "gpt-5-mini"
_EMBEDDING_MODEL = "text-embedding-3-small"
_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


# --- daily OpenAI budget accounting (slice 2 §6, issue #59) -----------------
#
# This transport is the single choke point for OpenAI spend: every v2 stage
# routes through `create_chat_completion` (and RAG through `create_embedding`),
# so recording usage×price here makes the daily-budget guard see all spend
# without any call site knowing the budget exists. The running total is a single
# in-process float reset at UTC midnight, seeded at 0 each day (PRD §8 — single
# instance; lost-on-restart resets the window, which is lenient, not unsafe). A
# future multi-instance deploy moves this to a shared store (spec §4, noted).
_spend_lock = threading.Lock()
_spend_usd: float = 0.0
_spend_day: date = datetime.now(timezone.utc).date()


def _roll_day_locked() -> None:
    """Reset the running total when the UTC day has rolled. Caller holds the lock."""
    global _spend_usd, _spend_day
    today = datetime.now(timezone.utc).date()
    if today != _spend_day:
        _spend_day = today
        _spend_usd = 0.0


def _record_usage(model: str, usage) -> None:
    """Add one call's cost (usage tokens × per-model config price) to the total.

    Tolerant of a missing/partial `usage` object — a stage with no usage simply
    contributes nothing rather than crashing the pipeline on accounting.
    """
    if usage is None:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    price = openai_price(model)
    cost = (prompt_tokens / 1000.0) * price["input"] + (
        completion_tokens / 1000.0
    ) * price["output"]
    global _spend_usd
    with _spend_lock:
        _roll_day_locked()
        _spend_usd += cost


def current_spend_usd() -> float:
    """Running OpenAI spend (USD) for the current UTC day."""
    with _spend_lock:
        _roll_day_locked()
        return _spend_usd


def is_budget_exhausted() -> bool:
    """True when today's spend has reached the configured daily ceiling.

    No ceiling configured (``OPENAI_DAILY_BUDGET_USD`` unset) → never exhausted
    (the guard is disabled). Read from the `secrets` module attribute rather than
    a cached import so the ceiling is patchable in tests.
    """
    ceiling = secrets.OPENAI_DAILY_BUDGET_USD
    if ceiling is None:
        return False
    return current_spend_usd() >= ceiling


def reset_spend() -> None:
    """Test seam: zero the running total and re-anchor the UTC day."""
    global _spend_usd, _spend_day
    with _spend_lock:
        _spend_usd = 0.0
        _spend_day = datetime.now(timezone.utc).date()


def create_response(system_prompt: str, user_data: str, assistant_prompt: str) -> str:
    # v1-ONLY helper — hardcodes `_MODEL` and does NOT route through
    # `app.llm.router.resolve()`. Reached only by the legacy youtube/appstore
    # endpoints (via `app.llm.extractInsights.extract_insights`); no v2 path
    # calls it. This is the one documented carve-out from the "no stage
    # hardcodes a model" rule (spec §9 / §11 criterion 5). Decision (issue #54):
    # retire with the rest of v1 in slice 3 rather than route a doomed helper.
    # Do NOT call this from v2 code — v2 uses `create_chat_completion` + resolve().
    client = get_openai_client()
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"\n    Here is the data found {user_data}\n    "},
            {"role": "assistant", "content": assistant_prompt},
        ],
    )
    _record_usage(_MODEL, getattr(response, "usage", None))
    return response.choices[0].message.content


def create_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Generic chat-completion call used by v2 LLM stages.

    Callers obtain `(model, temperature, max_tokens)` from `app.llm.router.resolve(stage)`.
    """
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    _record_usage(model, getattr(response, "usage", None))
    return response.choices[0].message.content


def create_embedding(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(model=_EMBEDDING_MODEL, input=text)
    _record_usage(_EMBEDDING_MODEL, getattr(response, "usage", None))
    return response.data[0].embedding
