"""Model-routing resolver tests (spec §9)."""
from __future__ import annotations

import pytest

from app.config.constants import MODEL_ROUTING
from app.llm.router import ModelConfig, resolve


REQUIRED_STAGES = (
    "preflight_classify",
    "preflight_rank",
    "per_source_extract",
    "synthesis",
    "idea_match",
)


@pytest.mark.parametrize("stage", REQUIRED_STAGES)
def test_resolves_each_required_stage(stage):
    cfg = resolve(stage)
    assert isinstance(cfg, ModelConfig)
    assert cfg.model
    assert 0.0 <= cfg.temperature <= 2.0
    assert cfg.max_tokens > 0


def test_v1_routes_every_stage_to_gpt_4o():
    """Spec §9: v1 ships gpt-4o for every stage."""
    for stage in REQUIRED_STAGES:
        assert resolve(stage).model == "gpt-4o"


def test_unknown_stage_raises_value_error():
    with pytest.raises(ValueError, match="Unknown LLM stage"):
        resolve("not_a_stage")


def test_routing_table_covers_all_required_stages():
    assert set(MODEL_ROUTING) >= set(REQUIRED_STAGES)
