"""MCP tool: list politicians in a Wahlperiode, optionally by Fraktion."""

import logging
from typing import Annotated

from pydantic import Field

from mcp_server.config import get_settings
from mcp_server.dip.client import DIPClient
from mcp_server.schemas.tool_outputs import MemberEntry, MemberListResult

logger = logging.getLogger(__name__)

MAX_MEMBERS = 20


async def get_members(
    wahlperiode: Annotated[
        int,
        Field(ge=1, description="Wahlperiode number, e.g. 21"),
    ],
    fraktion: Annotated[
        str | None,
        Field(description="Optional Fraktion filter, e.g. 'SPD' or 'CDU/CSU'"),
    ] = None,
    limit: Annotated[
        int,
        Field(
            ge=1,
            le=MAX_MEMBERS,
            description="How many names to return (max 20)",
        ),
    ] = 5,
) -> MemberListResult:
    """List politicians who were members of the Bundestag in a given
    Wahlperiode.

    Optionally filter by Fraktion. Returns up to `limit` names (default 5).

    Parameters
    ----------
    wahlperiode : int
        Wahlperiode number, e.g. 21 for the current (21st) Bundestag.
    fraktion : str or None, optional
        Fraktion name to filter by, e.g. 'SPD', 'CDU/CSU', 'AfD'.
    limit : int, optional
        Number of results to return (1–20, default 5).
    """
    settings = get_settings()
    results: list[MemberEntry] = []

    fraktion_lower = fraktion.lower() if fraktion else None

    async with DIPClient(settings) as client:
        async for person in client.get_persons(wahlperiode=wahlperiode):
            # Resolve the Fraktion the person belonged to in THIS
            # Wahlperiode (same rule as get_fraktion_distribution) —
            # the top-level field only reflects the current Fraktion
            person_fraktion = person.fraktion_for(wahlperiode)
            if fraktion_lower and (
                person_fraktion is None
                or fraktion_lower not in person_fraktion.lower()
            ):
                continue
            results.append(
                MemberEntry(
                    full_name=person.full_name,
                    fraktion=person_fraktion,
                    wahlperiode=person.wahlperiode_nummer,
                )
            )
            if len(results) >= limit:
                break

    logger.info(
        "get_members wahlperiode=%d fraktion=%r"
        " found=%d api=%.0fms delay=%.0fms",
        wahlperiode,
        fraktion,
        len(results),
        client.api_ms,
        client.delay_ms,
    )

    return MemberListResult(
        wahlperiode=wahlperiode,
        fraktion_filter=fraktion,
        results=results,
        total_found=len(results),
    )
