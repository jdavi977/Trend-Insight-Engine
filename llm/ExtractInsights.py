from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")

prompt = """
You are an expert Youtube comments analyzer and solutions/problems finder. 
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

client = OpenAI(api_key=OPENAI_KEY)

response = client.responses.create(
    model="gpt-5",
    input="Write a one-sentence bedtime story about a unicorn."
)

print(response.output_text)