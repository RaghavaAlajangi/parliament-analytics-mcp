"""LLM router: extract tool intent and arguments from natural language
(Mode 1)."""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from mcp_server.config import Settings, get_settings
from mcp_server.llm.client import complete
from mcp_server.schemas.tool_inputs import RouterOutput

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "router.txt"


class RoutingError(Exception):
    """Raised when the LLM fails to produce a valid tool call after retries."""


async def route(
    user_query: str, settings: Settings | None = None
) -> RouterOutput:
    """Parse a natural language query into a structured tool call.

    Retries up to settings.max_router_retries times on Pydantic validation
    failure, appending the error to the prompt so the LLM can self-correct.

    Parameters
    ----------
    user_query : str
        Free-form user question.
    settings : Settings or None, optional
        Settings override; uses get_settings() if None.

    Returns
    -------
    RouterOutput
        RouterOutput with tool name, arguments, and reasoning.

    Raises
    ------
    RoutingError
        If all retry attempts fail.
    """
    if settings is None:
        settings = get_settings()

    system = _PROMPT_PATH.read_text(encoding="utf-8")
    prompt = user_query
    last_error: str = ""

    for attempt in range(1, settings.max_router_retries + 1):
        if last_error:
            prompt = f"{user_query}\n\nPrevious attempt failed with: "
            f"{last_error}\nPlease correct and try again."

        raw, _ = await complete(
            prompt=prompt, system=system, settings=settings
        )

        try:
            # Strip markdown code fences if the model wraps output
            cleaned = (
                raw.strip()
                .removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
            parsed = RouterOutput.model_validate(json.loads(cleaned))
            logger.info(
                f"Router success attempt={attempt} tool={parsed.tool} "
                f"reasoning={parsed.reasoning}"
            )
            return parsed
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            logger.warning(f"Router attempt {attempt} failed: {last_error}")

    raise RoutingError(
        f"Could not extract tool call after {settings.max_router_retries}"
        f"attempts. Last error: {last_error}"
    )
