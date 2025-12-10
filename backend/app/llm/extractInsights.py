import os
from openai import OpenAI
from dotenv import load_dotenv
from config.prompts import youtubeSystemPrompt, youtubePromptOutput, appStoreSystemPrompt, appStorePromptOutput

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_KEY")

def extractInsights(data, systemPrompt, promptOutput):
    client = OpenAI(api_key=OPENAI_KEY)

    userDataPrompt = f"""
    Here is the data found {data}
    """
    
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "developer", "content": systemPrompt},
            {"role": "user", "content": userDataPrompt},
            {"role": "assistant", "content": promptOutput}
        ]
    )

    return response.output_text