import json
from llm_insights import LLMExtraction, ProblemItem

raw = """
{
    "source": "youtube",
    "title": null,
    "problems": [
        {
            "problem": "App is not suitable for experienced users or those aiming to build large/bulky muscles (limited advanced/strength-building programs).",
            "type": "feature_request",
            "total_likes": 487,
            "severity": 3,
            "frequency": 3
        },
        {
            "problem": "Users lack affordable access to gyms and equipment and therefore need effective no-equipment/home workout solutions.",
            "type": "other",
            "total_likes": 1407,
            "severity": 4,
            "frequency": 7
        },
        {
            "problem": "No clear progression pathway or guidance for when to 'upgrade' from the app to more advanced/gym routines.",
            "type": "usability",
            "total_likes": 436,
            "severity": 2,
            "frequency": 8
        }
    ]
}
"""

data = json.loads(raw)

check = True

dead_data = []

try:
    validated = LLMExtraction.model_validate(data)
    print(validated)
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
print("--")
print(validated)
print("--")
print(dead_data)

# print(validated.problems[0].severity)
# Plans: make a BaseModel for each validated.problems to validate each problem. think of what to do
# for data that fails the validation