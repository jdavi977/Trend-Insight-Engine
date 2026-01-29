import json
from schemas.llm_insights import LLMExtraction, ProblemItem

def validateOutput(data):
    data = json.loads(data)

    check = True
    dead_data = []

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
    return validated