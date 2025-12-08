import os
from openai import OpenAI
from dotenv import load_dotenv
from config.prompts import youtubeSystemPrompt, youtubePromptOutput

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")

def extractInsights(data):
    client = OpenAI(api_key=OPENAI_KEY)

    userDataPrompt = f"""
    Here is the data found {data}
    """

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "developer", "content": youtubeSystemPrompt},
            {"role": "user", "content": userDataPrompt},
            {"role": "assistant", "content": youtubePromptOutput}
        ]
    )

    return response.output_text