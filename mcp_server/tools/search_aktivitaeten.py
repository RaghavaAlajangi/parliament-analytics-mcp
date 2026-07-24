"""MCP tool: search parliamentary activities (speeches, votes, etc.)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    AktivitaetListResult,
    AktivitaetResult,
)

logger = logging.getLogger(__name__)


async def search_aktivitaeten(
    person: str | None = None,
    person_id: str | None = None,
    wahlperiode: int | None = None,
    datum_start: str | None = None,
    datum_end: str | None = None,
    limit: int = 20,
) -> AktivitaetListResult:
    """Search parliamentary activities (speeches, questions, votes) in the
    Bundestag.

    Use this tool to find what a specific politician did — e.g. speeches
    given, written questions submitted, or votes cast.

    Args:
        person: Politician name to filter by, e.g. 'Scholz' or 'Olaf Scholz'.
        person_id: Exact person ID from Personenstammdaten (more precise than
        name).
        wahlperiode: Wahlperiode number, e.g. 20.
        datum_start: Earliest date (ISO 8601), e.g. '2023-01-01'.
        datum_end: Latest date (ISO 8601), e.g. '2023-12-31'.
        limit: Maximum number of results (1–100).

    Returns:
        A list of parliamentary activities with type, date, and context.
    """
    settings = get_settings()

    async with DIPClient(settings) as client:
        docs = await client.search_aktivitaeten(
            person=person,
            person_id=person_id,
            wahlperiode=wahlperiode,
            datum_start=datum_start,
            datum_end=datum_end,
            limit=limit,
        )

    results = [
        AktivitaetResult(
            id=a.id,
            aktivitaetsart=a.aktivitaetsart,
            titel=a.titel,
            datum=a.datum,
            wahlperiode=a.wahlperiode,
            dokumentart=a.dokumentart,
            person_id=a.person_id,
            abstract=a.abstract,
            vorgangsbezug_anzahl=a.vorgangsbezug_anzahl,
        )
        for a in docs
    ]

    logger.info(
        f"search_aktivitaeten person={person or person_id} wp={wahlperiode} "
        f"found={len(results)}"
    )

    return AktivitaetListResult(
        query_person=person or person_id,
        wahlperiode=wahlperiode,
        results=results,
        total_found=len(results),
    )
