from openai import OpenAI
from app.config.prompts import youtubeSystemPrompt, youtubePromptOutput, appStoreSystemPrompt, appStorePromptOutput
from app.config.config import OPENAI_KEY

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