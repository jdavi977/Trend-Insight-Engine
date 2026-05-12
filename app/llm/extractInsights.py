import json
import time
from pathlib import Path

from pydantic import ValidationError

from app.clients.openai import create_response
from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem


def extract_insights(
    data: list,
    system_prompt: str,
    output_prompt: str,
    source: str = "youtube",
) -> LLMExtraction | None:
    """
    Returns a validated LLMExtraction, or None if the model returned
    no usable problems. Caller handles None as 'skip this item'.
    Per-problem validation drops malformed entries and quarantines them.
    """
    raw = create_response(system_prompt=system_prompt, user_data=data, assistant_prompt=output_prompt)

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(parsed, list):
        if not parsed:
            return None
        parsed = parsed[0]

    if not parsed.get("problems"):
        return None

    detected_source = parsed.get("source", source)
    item_type = YoutubeProblemItem if detected_source == "youtube" else AppStoreProblemItem

    run_id = time.strftime("%Y%m%d_%H%M%S")
    base_dir = Path("data") / "invalid_data" / run_id

    dead_items = []
    valid_problems = []
    for item in parsed["problems"]:
        try:
            valid_problems.append(item_type.model_validate(item).model_dump())
        except ValidationError:
            dead_items.append(item)

    if dead_items:
        run_dir = base_dir
        counter = 1
        while (run_dir / "run.json").exists():
            run_dir = base_dir.parent / f"{base_dir.name}_{counter}"
            counter += 1
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run.json").write_text(json.dumps(dead_items, indent=2))

    if not valid_problems:
        return None

    parsed["problems"] = valid_problems

    try:
        return LLMExtraction.model_validate(parsed)
    except ValidationError:
        return None
