import json
import time
from pathlib import Path
from pydantic import ValidationError
from app.schemas.llm import LLMExtraction, YoutubeProblemItem, AppStoreProblemItem


def validateOutput(data):
    data = json.loads(data)

    if not data.get("problems"):
        return data

    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path("data") / "invalid_data" / run_id

    source = data.get("source", "youtube")
    item_type = YoutubeProblemItem if source == "youtube" else AppStoreProblemItem

    dead_data = []
    valid_problems = []
    for item in data["problems"]:
        try:
            valid_problems.append(item_type.model_validate(item).model_dump())
        except ValidationError:
            dead_data.append(item)

    if dead_data:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run.json").write_text(json.dumps(dead_data, indent=2))

    if not valid_problems:
        return data

    data["problems"] = valid_problems
    try:
        return LLMExtraction.model_validate(data)
    except ValidationError:
        print("Please try again")
        return data