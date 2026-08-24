"""Model-routing resolver.

Spec: planning/specs/v2-slice-1-end-to-end_spec.md §9 / PRD §10.1.

Every v2 LLM call site obtains its `(model, temperature, max_tokens)` config
through `resolve(stage)`. Stage-to-model mapping lives in
`app.config.constants.MODEL_ROUTING` — swap models per stage without touching
call sites (architecture-as-config, PRD §14.21).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config.constants import MODEL_ROUTING

Stage = Literal[
    "preflight_classify",
    "preflight_rank",
    "per_source_extract",
    "synthesis",
]


@dataclass(frozen=True)
class ModelConfig:
    model: str
    temperature: float
    max_tokens: int


def resolve(stage: str) -> ModelConfig:
    try:
        cfg = MODEL_ROUTING[stage]
    except KeyError as exc:
        raise ValueError(
            f"Unknown LLM stage {stage!r}. "
            f"Known stages: {sorted(MODEL_ROUTING)}"
        ) from exc
    return ModelConfig(
        model=cfg["model"],
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
    )
