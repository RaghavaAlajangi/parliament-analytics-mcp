"""MCP tool: calculate Fraktion distribution for a Wahlperiode."""

import logging

from mcp_server.aggregation.fraktion import compute_distribution
from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import FraktionDistribution

logger = logging.getLogger(__name__)


async def get_fraktion_distribution(wahlperiode: int) -> FraktionDistribution:
    """Calculate the percentage share of each Fraktion in a given Wahlperiode.

    Paginates all politicians from the DIP API, resolves their Fraktion,
    and returns a sorted distribution with data quality notes.

    Args:
        wahlperiode: Wahlperiode number, e.g. 20 for the 20th Bundestag.

    Returns:
        FraktionDistribution with percentage shares per Fraktion.
    """
    settings = get_settings()
    persons = []

    async with DIPClient(settings) as client:
        async for person in client.get_persons(wahlperiode=wahlperiode):
            persons.append(person)

    logger.info(
        f"get_fraktion_distribution wahlperiode={wahlperiode} "
        f"total_persons={len(persons)}"
    )

    return compute_distribution(persons, wahlperiode)
