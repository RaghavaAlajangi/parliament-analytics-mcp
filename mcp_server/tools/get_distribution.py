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

    Parameters
    ----------
    wahlperiode : int
        Wahlperiode number, e.g. 20 for the 20th Bundestag.

    Returns
    -------
    FraktionDistribution
        Sorted distribution with percentage shares per Fraktion.
    """
    settings = get_settings()
    persons = []

    async with DIPClient(settings) as client:
        async for person in client.get_persons(wahlperiode=wahlperiode):
            persons.append(person)

    # The f.wahlperiode filter is sent to the API, but its effect on the
    # /person list is not guaranteed — filter client-side as well so the
    # distribution never counts records from other legislative periods.
    in_period = [
        p for p in persons if wahlperiode in p.wahlperiode_nummer
    ]
    excluded = len(persons) - len(in_period)

    logger.info(
        f"get_fraktion_distribution wahlperiode={wahlperiode} "
        f"fetched={len(persons)} in_period={len(in_period)}"
    )

    result = compute_distribution(in_period, wahlperiode)

    if excluded:
        result.data_quality_notes.append(
            f"{excluded} fetched records were not associated with "
            f"Wahlperiode {wahlperiode} and were excluded."
        )
    if len(persons) >= settings.dip_max_records:
        result.data_quality_notes.append(
            f"Result is based on a sample of {len(persons)} records "
            f"(capped at dip_max_records={settings.dip_max_records}). "
            "Percentages are approximate."
        )

    return result
