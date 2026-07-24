"""MCP tools: fetch a Plenarprotokoll by ID (metadata or full text)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    PlenarprotokollDetailResult,
    PlenarprotokollTextResult,
)

logger = logging.getLogger(__name__)


async def get_plenarprotokoll(
    protokoll_id: str,
) -> PlenarprotokollDetailResult:
    """Fetch full metadata for a plenary session record by its DIP ID.

    Use this after search_plenarprotokolle to get complete details on a
    specific session.

    Args:
        protokoll_id: The numeric DIP ID of the Plenarprotokoll.

    Returns:
        Full metadata for the plenary session record.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        p = await client.get_plenarprotokoll(protokoll_id)

    logger.info(f"get_plenarprotokoll id={protokoll_id}")
    return PlenarprotokollDetailResult(
        id=p.id,
        dokumentnummer=p.dokumentnummer,
        titel=p.titel,
        datum=p.datum,
        wahlperiode=p.wahlperiode,
        herausgeber=p.herausgeber,
        sitzungsbemerkung=p.sitzungsbemerkung,
        vorgangsbezug_anzahl=p.vorgangsbezug_anzahl,
        pdf_hash=p.pdf_hash,
    )


async def get_plenarprotokoll_text(
    protokoll_id: str,
) -> PlenarprotokollTextResult:
    """Fetch the full transcript text of a plenary session by its DIP ID.

    Use this when you need the actual speech transcript content of a session.
    Full transcripts are very large documents.

    Args:
        protokoll_id: The numeric DIP ID of the Plenarprotokoll.

    Returns:
        Full transcript text plus metadata.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        p = await client.get_plenarprotokoll_text(protokoll_id)

    logger.info(f"get_plenarprotokoll_text id={protokoll_id}")
    return PlenarprotokollTextResult(
        id=p.id,
        dokumentnummer=p.dokumentnummer,
        titel=p.titel,
        datum=p.datum,
        wahlperiode=p.wahlperiode,
        herausgeber=p.herausgeber,
        sitzungsbemerkung=p.sitzungsbemerkung,
        vorgangsbezug_anzahl=p.vorgangsbezug_anzahl,
        pdf_hash=p.pdf_hash,
        text=p.text,
    )
