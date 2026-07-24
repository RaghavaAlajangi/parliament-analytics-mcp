"""Thin LLM client wrapper supporting Groq and OpenAI providers."""

import logging

from mcp_server.config import Settings

logger = logging.getLogger(__name__)


async def complete(
    prompt: str, system: str, settings: Settings
) -> tuple[str, str]:
    """Call the configured LLM provider and return (response_text, model_used).

    Parameters
    ----------
    prompt : str
        User message content.
    system : str
        System prompt content.
    settings : Settings
        Application settings (provider, model, keys).

    Returns
    -------
    tuple[str, str]
        Tuple of (response text, model identifier used).
    """
    if settings.llm_provider == "groq":
        return await _complete_groq(prompt, system, settings)
    if settings.llm_provider == "openai":
        return await _complete_openai(prompt, system, settings)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


async def _complete_groq(
    prompt: str, system: str, settings: Settings
) -> tuple[str, str]:
    from groq import AsyncGroq  # type: ignore[import-untyped]

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

    client = AsyncGroq(api_key=settings.groq_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    text = response.choices[0].message.content or ""
    logger.info(
        f"LLM call provider=groq model={settings.llm_model} "
        f"prompt_tokens={response.usage.prompt_tokens} "
        f"completion_tokens={response.usage.completion_tokens}"
    )
    return text, settings.llm_model


async def _complete_openai(
    prompt: str, system: str, settings: Settings
) -> tuple[str, str]:
    from openai import AsyncOpenAI

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    text = response.choices[0].message.content or ""
    logger.info(
        f"LLM call provider=openai model={settings.llm_model} "
        f"prompt_tokens={response.usage.prompt_tokens} "
        f"completion_tokens={response.usage.completion_tokens}"
    )
    return text, settings.llm_model
