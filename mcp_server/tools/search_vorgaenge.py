"""MCP tool: search legislative proceedings (Vorgänge)."""

import logging

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import VorgangListResult, VorgangResult

logger = logging.getLogger(__name__)


async def search_vorgaenge(
    titel: str | None = None,
    vorgangstyp: str | None = None,
    wahlperiode: int | None = None,
    beratungsstand: str | None = None,
    limit: int = 20,
) -> VorgangListResult:
    """Search legislative proceedings (Vorgänge) in the Bundestag.

    Args:
        titel: Title keyword, e.g. 'Bundeshaushalt'.
        vorgangstyp: Type of proceeding, e.g. 'Gesetzgebung', 'Antrag'.
        wahlperiode: Wahlperiode number, e.g. 20.
        beratungsstand: Current status, e.g. 'Verkündet', 'Abgeschlossen'.
        limit: Maximum number of results (1–100).

    Returns:
        A list of matching Vorgänge with metadata and status.
    """
    settings = get_settings()

    async with DIPClient(settings) as client:
        docs = await client.search_vorgaenge(
            titel=titel,
            vorgangstyp=vorgangstyp,
            wahlperiode=wahlperiode,
            beratungsstand=beratungsstand,
            limit=limit,
        )

    results = [
        VorgangResult(
            id=v.id,
            titel=v.titel,
            vorgangstyp=v.vorgangstyp,
            beratungsstand=v.beratungsstand,
            wahlperiode=v.wahlperiode,
            datum=v.datum,
            initiative=v.initiative,
            abstract=v.abstract,
            sachgebiet=v.sachgebiet,
        )
        for v in docs
    ]

    logger.info(
        f"search_vorgaenge titel={titel} typ={vorgangstyp} wp={wahlperiode} "
        f"found={len(results)}"
    )

    return VorgangListResult(
        query_titel=titel,
        wahlperiode=wahlperiode,
        results=results,
        total_found=len(results),
    )
