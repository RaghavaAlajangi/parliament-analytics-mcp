"""LLM narration: convert structured FraktionDistribution into readable
prose."""

import logging
from pathlib import Path
from typing import Literal

from mcp_server.config import get_settings
from mcp_server.llm.client import complete
from mcp_server.schemas.tool_outputs import (
    FraktionDistribution,
    NarrationResult,
)

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).parent / "prompts" / "narrator.txt"


async def narrate(
    distribution: FraktionDistribution,
    language: Literal["de", "en"] = "de",
    style: Literal["concise", "detailed"] = "concise",
) -> NarrationResult:
    """Narrate a FraktionDistribution as natural language prose.

    The LLM receives only pre-computed, validated numbers — it cannot
    hallucinate statistics. Output is post-validated before returning.

    Parameters
    ----------
    distribution : FraktionDistribution
        Pre-computed distribution data to narrate.
    language : {'de', 'en'}, optional
        Output language; 'de' for German, 'en' for English.
    style : {'concise', 'detailed'}, optional
        Narration style.

    Returns
    -------
    NarrationResult
        Generated text together with model identifier and validation status.
    """
    settings = get_settings()
    distribution_json = distribution.model_dump_json(indent=2)

    system_template = _PROMPT_PATH.read_text(encoding="utf-8")
    system = system_template.format(
        style=style,
        language="German" if language == "de" else "English",
        distribution_json=distribution_json,
    )

    text, model_used = await complete(
        prompt="Please write the analysis now.",
        system=system,
        settings=settings,
    )

    # Post-validate: response must reference at least one known Fraktion name
    known_fraktionen = {s.fraktion for s in distribution.shares}
    validation_passed = any(f in text for f in known_fraktionen)

    if not validation_passed:
        logger.warning(
            "Narration validation failed — no Fraktion names found in output. "
            f"model={model_used} wahlperiode={distribution.wahlperiode}"
        )

    return NarrationResult(
        text=text,
        model_used=model_used,
        validation_passed=validation_passed,
        wahlperiode=distribution.wahlperiode,
    )
