import json
from llm_insights import LLMExtraction

raw = """
{
    "source": "youtubea",
    "title": null,
    "problems": [
        {
            "problem": "App is not suitable for experienced users or those aiming to build large/bulky muscles (limited advanced/strength-building programs).",
            "type": "feature_request",
            "total_likes": 487,
            "severity": 3,
            "frequency": 6
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
            "frequency": 1
        }
    ]
}
"""

data = json.loads(raw)

try:
    validated = LLMExtraction.model_validate(data)
    print(validated)
except:
    print("Please try again")
# print(validated.problems[0].severity)

# Plans: make a BaseModel for each validated.problems to validate each problem. think of what to do
# for data that fails the validation