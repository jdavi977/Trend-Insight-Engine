from openai import OpenAI

from app.config.secrets import OPENAI_KEY

_MODEL = "gpt-5-mini"
_EMBEDDING_MODEL = "text-embedding-3-small"
_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


def create_response(system_prompt: str, user_data: str, assistant_prompt: str) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"\n    Here is the data found {user_data}\n    "},
            {"role": "assistant", "content": assistant_prompt},
        ],
    )
    return response.choices[0].message.content


def create_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Generic chat-completion call used by v2 LLM stages.

    Callers obtain `(model, temperature, max_tokens)` from `app.llm.router.resolve(stage)`.
    """
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content


def create_embedding(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(model=_EMBEDDING_MODEL, input=text)
    return response.data[0].embedding
