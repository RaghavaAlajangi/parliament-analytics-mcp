"""Validated input schemas for each MCP tool."""

from typing import Literal

from pydantic import BaseModel, Field


class GetPoliticianInput(BaseModel):
    name: str = Field(
        description="Full or partial name, e.g. 'Friedrich Merz'"
    )
    wahlperiode: int | None = Field(
        default=None,
        description="Optional Wahlperiode filter, e.g. 20",
    )


class GetDistributionInput(BaseModel):
    wahlperiode: int = Field(
        description="Wahlperiode number, e.g. 20 for the 20th Bundestag",
        ge=1,
    )


class NarrateInput(BaseModel):
    wahlperiode: int = Field(description="Wahlperiode to narrate results for")
    language: Literal["de", "en"] = Field(
        default="de",
        description="Output language: 'de' for German, 'en' for English",
    )
    style: Literal["concise", "detailed"] = Field(
        default="concise",
        description="Narration style",
    )


class RouterOutput(BaseModel):
    """Structured output from the LLM routing step (Mode 1 only)."""

    tool: Literal[
        "get_politician", "get_fraktion_distribution", "narrate_distribution"
    ]
    arguments: dict
    reasoning: str = Field(
        description="Chain-of-thought kept for auditability"
    )
