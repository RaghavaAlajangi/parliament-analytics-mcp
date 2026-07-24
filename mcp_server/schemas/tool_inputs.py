"""Input schemas for LLM-driven routing.

Tool input validation itself lives on the tool signatures
(Annotated[..., Field(...)]) — FastMCP builds and enforces the JSON
schema from there, so no separate input models are needed.
"""

from typing import Literal

from pydantic import BaseModel, Field


class RouterOutput(BaseModel):
    """Structured output from the LLM routing step (Mode 1 only)."""

    tool: Literal[
        "get_politician", "get_fraktion_distribution", "narrate_distribution"
    ]
    arguments: dict
    reasoning: str = Field(
        description="Chain-of-thought kept for auditability"
    )
