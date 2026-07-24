"""MCP tool: look up a politician by name."""

import logging
from typing import Annotated

from pydantic import Field

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import (
    PoliticianListResult,
    PoliticianResult,
    RoleEntry,
)

logger = logging.getLogger(__name__)


MAX_POLITICIAN_RESULTS = 5


async def get_politician(
    name: Annotated[
        str,
        Field(
            min_length=2,
            description="Full or partial name, e.g. 'Friedrich Merz'",
        ),
    ],
    wahlperiode: Annotated[
        int | None,
        Field(ge=1, description="Optional Wahlperiode filter, e.g. 20"),
    ] = None,
) -> PoliticianListResult:
    """Look up biographical and faction data for a named politician.

    Uses the DIP f.person filter which matches both first and last name,
    supporting both hyphenated and space-separated forms.

    Parameters
    ----------
    name : str
        Full or partial name, e.g. 'Friedrich Merz' or
        'Steinmeier Frank-Walter'.
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
                    titel=person.titel,
                    funktion=person.funktion,
                    fraktion=person.fraktion,
                    wahlperiode=person.wahlperiode_nummer,
                    roles=[
                        RoleEntry(
                            fraktion=r.fraktion,
                            ressort_titel=r.ressort_titel,
                            wahlperiode_nummer=r.wahlperiode_nummer,
                        )
                        for r in person.person_roles
                    ],
                    biography_url=person.basisdaten_url,
                )
            )
            if len(results) >= MAX_POLITICIAN_RESULTS:
                break

    logger.info(
        f"get_politician query={name!r} wahlperiode={wahlperiode} "
        f"found={len(results)}"
    )

    return PoliticianListResult(
        query=name,
        results=results,
        total_found=len(results),
    )
