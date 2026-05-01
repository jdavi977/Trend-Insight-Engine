from openai import OpenAI

from app.config.secrets import OPENAI_KEY

_MODEL = "gpt-5-mini"
_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


def create_response(system_prompt: str, user_data: str, assistant_prompt: str) -> str:
    client = get_openai_client()
    response = client.responses.create(
        model=_MODEL,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": f"\n    Here is the data found {user_data}\n    "},
            {"role": "assistant", "content": assistant_prompt},
        ],
    )
    return response.output_text
