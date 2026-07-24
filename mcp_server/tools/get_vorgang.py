"""MCP tool: fetch a Vorgang (legislative proceeding) by ID."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import VorgangDetailResult

logger = logging.getLogger(__name__)


async def get_vorgang(vorgang_id: str) -> VorgangDetailResult:
    """Fetch full details of a legislative proceeding by its DIP ID.

    Use this after search_vorgaenge to get the complete record of a
    proceeding, including its subject descriptors, consent requirements,
    and GESTA reference number.

    Args:
        vorgang_id: The numeric DIP ID of the Vorgang.

    Returns:
        Full metadata for the Vorgang.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        v = await client.get_vorgang(vorgang_id)

    logger.info(f"get_vorgang id={vorgang_id}")
    return VorgangDetailResult(
        id=v.id,
        titel=v.titel,
        vorgangstyp=v.vorgangstyp,
        beratungsstand=v.beratungsstand,
        wahlperiode=v.wahlperiode,
        datum=v.datum,
        initiative=v.initiative,
        abstract=v.abstract,
        sachgebiet=v.sachgebiet,
        deskriptoren=[d.name for d in v.deskriptor if d.name],
        zustimmungsbeduerftigkeit=v.zustimmungsbeduerftigkeit,
        mitteilung=v.mitteilung,
        gesta=v.gesta,
    )
