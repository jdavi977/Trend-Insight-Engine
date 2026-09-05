from openai import OpenAI

from app.config.secrets import OPENAI_KEY

_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_KEY)
    return _client


def create_chat_completion(
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    response_format: dict | None = None,
) -> str:
    """Generic chat-completion call used by v2 LLM stages.

    Callers obtain `(model, temperature, max_tokens)` from `app.llm.router.resolve(stage)`.

    `response_format` is forwarded as-is when given (e.g.
    `{"type": "json_object"}`) — callers that parse the reply as JSON should
    pass it so the model can't wrap the object in a markdown code fence and
    silently break `json.loads`.
    """
    client = get_openai_client()
    kwargs = {} if response_format is None else {"response_format": response_format}
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
        **kwargs,
    )
    return response.choices[0].message.content
