import threading
from datetime import date, datetime, timezone

from openai import OpenAI

from app.config import secrets
from app.config.constants import openai_price
from app.config.secrets import OPENAI_KEY

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


# --- daily OpenAI budget accounting (slice 2 §6, issue #59) -----------------
#
# This transport is the single choke point for OpenAI spend: every v2 stage
# routes through `create_chat_completion`, so recording usage×price here
# makes the daily-budget guard see all spend
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


def create_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    response_format: dict | None = None,
) -> str:
    """Generic chat-completion call used by v2 LLM stages.

    Callers obtain `(model, temperature, max_tokens)` from `app.llm.router.resolve(stage)`.

    `response_format` is forwarded as-is when given (e.g.
    `{"type": "json_object"}`) — callers that parse the reply as JSON should
    pass it so the model can't wrap the object in a markdown code fence and
    silently break `json.loads`.
    """
    client = get_openai_client()
    kwargs = {} if response_format is None else {"response_format": response_format}
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        **kwargs,
    )
    _record_usage(model, getattr(response, "usage", None))
    return response.choices[0].message.content
