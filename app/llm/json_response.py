"""Shared parsing helper for LLM call sites that expect a JSON object back.

Call sites pass `response_format={"type": "json_object"}` to
`create_chat_completion`, which stops the model from wrapping its reply in a
markdown code fence. `strip_code_fence` is a defense-in-depth fallback for
models/edge cases that still emit a fenced ```json ... ``` block despite that
setting — without it, `json.loads` raises and the reply is silently dropped.
"""
from __future__ import annotations

import re

_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL)


def strip_code_fence(raw: str) -> str:
    """Strip a surrounding ```json ... ``` (or bare ```) fence, if present."""
    match = _FENCE_RE.match(raw.strip())
    return match.group(1) if match else raw
