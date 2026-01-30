import json
import time
from schemas.llm_insights import LLMExtraction, ProblemItem
from pathlib import Path

def validateOutput(data):
    data = json.loads(data)

    check = True
    dead_data = []

    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = Path("data") / "invalid_data" / run_id

    try:
        validated = LLMExtraction.model_validate(data)
    except:
        check = False
        print("Please try again")

    if check == True:
        for i in range(len(validated.problems) -1, -1, -1):
            try:
                problem_validation = ProblemItem.model_validate(validated.problems[i])
            except:
                dead_data.append(validated.problems[i])
                validated.problems.pop(i)

    if dead_data:
        run_dir.mkdir(parents=True, exist_ok=False)
        (run_dir / "run.json").write_text(json.dumps(dead_data, indent=2))

    return validated