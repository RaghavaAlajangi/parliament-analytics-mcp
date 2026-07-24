"""MCP tool: fetch a parliamentary activity by ID."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import AktivitaetDetailResult

logger = logging.getLogger(__name__)


async def get_aktivitaet(aktivitaet_id: str) -> AktivitaetDetailResult:
    """Fetch full details of a parliamentary activity by its DIP ID.

    Use this after search_aktivitaeten to get the complete record of a
    specific activity (speech, vote, written question, etc.).

    Args:
        aktivitaet_id: The numeric DIP ID of the Aktivität.

    Returns:
        Full metadata for the parliamentary activity.
    """
    settings = get_settings()
    async with DIPClient(settings) as client:
        a = await client.get_aktivitaet(aktivitaet_id)

    logger.info(f"get_aktivitaet id={aktivitaet_id}")
    return AktivitaetDetailResult(
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
