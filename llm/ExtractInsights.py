import os
from openai import OpenAI
from dotenv import load_dotenv
from preprocessing.CommentClean import loadAndClean

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")

systemPrompt = """
You are an expert Youtube comments analyzer and solutions/prosblems finder. 
You will receive a JSON of youtube comments which include: Likes and Text. 
This is your task. 
1. Find recurring unmet needs/wants/solutions/complaints.
2. Group similar problems into a single 'problem'.
3. For each problem, output:
problem: "short description of the problem"
type: "feature request" | "complaint" | "usability" | "other"
total_likes: the total amount of likes summed up from each problem that is grouped
severity: 1-5 (5 being very painful)
frequency: 1-5 (5 being very common)
"""

systemPromptOutput = """
Here is the example JSON array of comments I want you to return:

{
    "Problems:": [
        {
            "problem": "string",
            "type": "string",
            "total_likes": 1,
            "severity": 1,
            "frequency": 1,
        },
    ]
}
"""
def extractInsights(data):
    client = OpenAI(api_key=OPENAI_KEY)

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": systemPrompt},
            {"role": "user", "content": [{
                "type": "input_text", "input_text": data}]},
            {"role": "system", "content": systemPromptOutput}
        ]
    )

    print(response.output_text)

extractInsights(loadAndClean())