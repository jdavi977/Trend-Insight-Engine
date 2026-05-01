from app.clients.openai import create_response


def extractInsights(data, systemPrompt, promptOutput):
    return create_response(
        system_prompt=systemPrompt,
        user_data=data,
        assistant_prompt=promptOutput,
    )
