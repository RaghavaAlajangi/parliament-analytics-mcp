"""MCP tool: search plenary session records (Plenarprotokolle)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    PlenarprotokollListResult,
    PlenarprotokollResult,
)

logger = logging.getLogger(__name__)


async def search_plenarprotokolle(
    wahlperiode: int | None = None,
    datum_start: str | None = None,
    datum_end: str | None = None,
    limit: int = 20,
) -> PlenarprotokollListResult:
    """Search plenary session records (Plenarprotokolle) of the Bundestag.

    Use this tool to find records of specific parliamentary sessions,
    e.g. to discover which sessions took place in a date range.

    Args:
        wahlperiode: Wahlperiode number, e.g. 20.
        datum_start: Earliest session date (ISO 8601), e.g. '2023-01-01'.
        datum_end: Latest session date (ISO 8601), e.g. '2023-12-31'.
        limit: Maximum number of results (1–100).

    Returns:
        A list of plenary session records with date and document number.
    """
    settings = get_settings()

    async with DIPClient(settings) as client:
        docs = await client.search_plenarprotokolle(
            wahlperiode=wahlperiode,
            datum_start=datum_start,
            datum_end=datum_end,
            limit=limit,
        )

    results = [
        PlenarprotokollResult(
            id=p.id,
            dokumentnummer=p.dokumentnummer,
            titel=p.titel,
            datum=p.datum,
            wahlperiode=p.wahlperiode,
            herausgeber=p.herausgeber,
            sitzungsbemerkung=p.sitzungsbemerkung,
            vorgangsbezug_anzahl=p.vorgangsbezug_anzahl,
        )
        for p in docs
    ]

    logger.info(
        f"search_plenarprotokolle wp={wahlperiode} start={datum_start} "
        f"end={datum_end} found={len(results)}"
    )

    return PlenarprotokollListResult(
        wahlperiode=wahlperiode,
        datum_start=datum_start,
        datum_end=datum_end,
        results=results,
        total_found=len(results),
    )
