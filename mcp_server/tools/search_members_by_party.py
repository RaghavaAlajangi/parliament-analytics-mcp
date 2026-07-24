"""MCP tool: list all members of a Fraktion, optionally filtered by Bundesland."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    PoliticianListResult,
    PoliticianResult,
)

logger = logging.getLogger(__name__)

# Canonical Fraktion name fragments for fuzzy matching
_FRAKTION_ALIASES: dict[str, str] = {
    "grüne": "Bündnis 90/Die Grünen",
    "gruene": "Bündnis 90/Die Grünen",
    "b90": "Bündnis 90/Die Grünen",
    "spd": "SPD",
    "cdu": "CDU/CSU",
    "csu": "CDU/CSU",
    "cdu/csu": "CDU/CSU",
    "fdp": "FDP",
    "afd": "AfD",
    "linke": "DIE LINKE",
    "die linke": "DIE LINKE",
    "bsw": "BSW",
    "fraktionslos": "Fraktionslos",
}


def _normalize_fraktion(raw: str) -> str:
    """Map a user-supplied party name to the canonical DIP Fraktion string."""
    return _FRAKTION_ALIASES.get(raw.lower().strip(), raw)


async def search_members_by_party(
    fraktion: str,
    wahlperiode: int,
    bundesland: str | None = None,
) -> PoliticianListResult:
    """List all members (MdB) of a parliamentary party group (Fraktion).

    Use this tool when the user asks who belongs to a specific party, e.g.
    'Who are the Green members from Bavaria?' or 'List all SPD MPs in the 20th
    Bundestag'. This is NOT a name search — use get_politician for that.

    The tool paginates all persons for the given Wahlperiode and filters
    client-side by Fraktion and optionally by Bundesland.

    Args:
        fraktion: Party name, e.g. 'Grüne', 'SPD', 'CDU/CSU', 'AfD', 'FDP'.
                  Common abbreviations and German variants are accepted.
        wahlperiode: Wahlperiode number, e.g. 20 for the current Bundestag.
        bundesland: Optional German state filter, e.g. 'Bayern', 'NRW',
                    'Nordrhein-Westfalen'. Partial match (case-insensitive).

    Returns:
        A list of matching politicians with their Fraktion and metadata.
    """
    settings = get_settings()
    canonical = _normalize_fraktion(fraktion)
    results: list[PoliticianResult] = []

    async with DIPClient(settings) as client:
        async for person in client.get_persons(wahlperiode=wahlperiode):
            person_fraktion = person.fraktion or ""
            if canonical.lower() not in person_fraktion.lower():
                continue
            if bundesland and not _bundesland_matches(
                person.bundesland, bundesland
            ):
                continue
            results.append(
                PoliticianResult(
                    id=person.id,
                    full_name=person.full_name,
                    fraktion=person.fraktion,
                    wahlperiode=person.wahlperiode_nummer,
                    biography_url=person.basisdaten_url,
                )
            )

    logger.info(
        "search_members_by_party fraktion=%s bundesland=%s wp=%d found=%d",
        canonical,
        bundesland,
        wahlperiode,
        len(results),
    )

    return PoliticianListResult(
        query=f"{fraktion}" + (f" ({bundesland})" if bundesland else ""),
        results=results,
        total_found=len(results),
    )


def _bundesland_matches(person_bl: str | None, query: str) -> bool:
    if not person_bl:
        return False
    return query.lower() in person_bl.lower()
