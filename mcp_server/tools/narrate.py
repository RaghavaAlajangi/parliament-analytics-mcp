"""MCP tool: narrate a Fraktion distribution in natural language."""

import logging
from typing import Annotated, Literal

from pydantic import Field

from mcp_server.llm.narrator import narrate
from mcp_server.schemas.tool_outputs import (
    FraktionDistribution,
    NarrationResult,
)
from mcp_server.tools.get_distribution import get_fraktion_distribution

logger = logging.getLogger(__name__)


async def narrate_distribution(
    wahlperiode: Annotated[
        int,
        Field(ge=1, description="Wahlperiode number, e.g. 20"),
    ],
    language: Literal["de", "en"] = "de",
    style: Literal["concise", "detailed"] = "concise",
) -> NarrationResult:
    """Fetch Fraktion distribution and produce a readable natural-language
    analysis.

    First calls get_fraktion_distribution internally, then passes the
    structured result to an LLM for narration. The LLM only sees pre-computed
    numbers — it cannot hallucinate statistics.

    Parameters
    ----------
    wahlperiode : int
        Wahlperiode number, e.g. 20.
    language : {'de', 'en'}, optional
        Output language — 'de' for German, 'en' for English.
    style : {'concise', 'detailed'}, optional
        'concise' for a short summary, 'detailed' for full analysis.

    Returns
    -------
    NarrationResult
        Generated text with validation status.
    """
    distribution: FraktionDistribution = await get_fraktion_distribution(
        wahlperiode
    )
    return await narrate(distribution, language=language, style=style)
