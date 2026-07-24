"""MCP tool: look up a politician by name."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    PoliticianListResult,
    PoliticianResult,
)

logger = logging.getLogger(__name__)


async def get_politician(
    name: str, wahlperiode: int | None = None
) -> PoliticianListResult:
    """Look up biographical and faction data for a named politician.

    Parameters
    ----------
    name : str
        Full or partial name, e.g. 'Friedrich Merz'.
    wahlperiode : int or None, optional
        Optional Wahlperiode filter, e.g. 20.

    Returns
    -------
    PoliticianListResult
        A list of matching politicians with their Fraktion and metadata.
    """
    settings = get_settings()
    results: list[PoliticianResult] = []

    async with DIPClient(settings) as client:
        async for person in client.get_persons(
            wahlperiode=wahlperiode, search=name
        ):
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
        f"get_politician query={name} wahlperiode={wahlperiode} "
        f"found={len(results)}"
    )

    return PoliticianListResult(
        query=name,
        results=results,
        total_found=len(results),
    )
