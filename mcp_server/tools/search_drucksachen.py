"""MCP tool: search parliamentary papers (Drucksachen)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    DrucksacheListResult,
    DrucksacheResult,
)

logger = logging.getLogger(__name__)


async def search_drucksachen(
    titel: str | None = None,
    drucksachetyp: str | None = None,
    wahlperiode: int | None = None,
    datum_start: str | None = None,
    datum_end: str | None = None,
    limit: int = 20,
) -> DrucksacheListResult:
    """Search parliamentary papers (Drucksachen) in the Bundestag.

    Args:
        titel: Title keyword to search for, e.g. 'Klimaschutz'.
        drucksachetyp: Document type filter, e.g. 'Antrag', 'Gesetzentwurf'.
        wahlperiode: Wahlperiode number, e.g. 20.
        datum_start: Earliest date (ISO 8601), e.g. '2021-01-01'.
        datum_end: Latest date (ISO 8601), e.g. '2023-12-31'.
        limit: Maximum number of results (1–100).

    Returns:
        A list of matching Drucksachen with metadata.
    """
    settings = get_settings()

    async with DIPClient(settings) as client:
        docs = await client.search_drucksachen(
            titel=titel,
            drucksachetyp=drucksachetyp,
            wahlperiode=wahlperiode,
            datum_start=datum_start,
            datum_end=datum_end,
            limit=limit,
        )

    results = [
        DrucksacheResult(
            id=d.id,
            dokumentnummer=d.dokumentnummer,
            drucksachetyp=d.drucksachetyp,
            titel=d.titel,
            datum=d.datum,
            wahlperiode=d.wahlperiode,
            herausgeber=d.herausgeber,
            autoren_anzahl=d.autoren_anzahl,
        )
        for d in docs
    ]

    logger.info(
        f"search_drucksachen titel={titel} typ={drucksachetyp} "
        f"wp={wahlperiode} found={len(results)}"
    )

    return DrucksacheListResult(
        query_titel=titel,
        wahlperiode=wahlperiode,
        results=results,
        total_found=len(results),
    )
