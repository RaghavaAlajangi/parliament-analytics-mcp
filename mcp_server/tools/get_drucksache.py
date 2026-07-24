"""MCP tools: fetch a Drucksache by ID (metadata or full text)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    DrucksacheDetailResult,
    DrucksacheTextResult,
)

logger = logging.getLogger(__name__)


async def get_drucksache(drucksache_id: str) -> DrucksacheDetailResult:
    """Fetch full metadata for a single parliamentary paper by its DIP ID.

    Use this after search_drucksachen to get complete details on a specific
    paper, including its authors, originating body, and attachments.

    Args:
        drucksache_id: The numeric DIP ID of the Drucksache.

    Returns:
        Full metadata for the Drucksache.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        d = await client.get_drucksache(drucksache_id)

    logger.info(f"get_drucksache id={drucksache_id}")
    return DrucksacheDetailResult(
        id=d.id,
        dokumentnummer=d.dokumentnummer,
        drucksachetyp=d.drucksachetyp,
        titel=d.titel,
        datum=d.datum,
        wahlperiode=d.wahlperiode,
        herausgeber=d.herausgeber,
        autoren_anzahl=d.autoren_anzahl,
        anlagen=d.anlagen,
        pdf_hash=d.pdf_hash,
        urheber=[u.titel for u in d.urheber if u.titel],
    )


async def get_drucksache_text(drucksache_id: str) -> DrucksacheTextResult:
    """Fetch the full text content of a parliamentary paper by its DIP ID.

    Use this when you need to read the actual content of a Drucksache,
    not just its metadata. Full text can be large.

    Args:
        drucksache_id: The numeric DIP ID of the Drucksache.

    Returns:
        Full text plus metadata for the Drucksache.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        d = await client.get_drucksache_text(drucksache_id)

    logger.info(f"get_drucksache_text id={drucksache_id}")
    return DrucksacheTextResult(
        id=d.id,
        dokumentnummer=d.dokumentnummer,
        drucksachetyp=d.drucksachetyp,
        titel=d.titel,
        datum=d.datum,
        wahlperiode=d.wahlperiode,
        herausgeber=d.herausgeber,
        autoren_anzahl=d.autoren_anzahl,
        anlagen=d.anlagen,
        pdf_hash=d.pdf_hash,
        urheber=[u.titel for u in d.urheber if u.titel],
        text=d.text,
    )
