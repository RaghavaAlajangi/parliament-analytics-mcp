"""MCP server entrypoint — registers all tools and starts the server."""

import logging

from fastmcp import FastMCP

from mcp_server.tools.get_distribution import get_fraktion_distribution
from mcp_server.tools.get_politician import get_politician
from mcp_server.tools.narrate import narrate_distribution
from mcp_server.tools.get_aktivitaet import get_aktivitaet
from mcp_server.tools.get_drucksache import get_drucksache, get_drucksache_text
from mcp_server.tools.get_plenarprotokoll import (
    get_plenarprotokoll,
    get_plenarprotokoll_text,
)
from mcp_server.tools.get_vorgang import get_vorgang
from mcp_server.tools.search_aktivitaeten import search_aktivitaeten
from mcp_server.tools.search_members_by_party import search_members_by_party
from mcp_server.tools.search_drucksachen import search_drucksachen
from mcp_server.tools.search_plenarprotokolle import search_plenarprotokolle
from mcp_server.tools.search_vorgaenge import search_vorgaenge

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="parliament-analytics",
    instructions=(
        "You are a German parliamentary data assistant. "
        "Use the available tools to look up politicians and calculate "
        "faction (Fraktion) distributions in the Bundestag. "
        "Always use tool results directly — never invent statistics."
    ),
)

mcp.tool()(get_politician)
mcp.tool()(get_fraktion_distribution)
mcp.tool()(narrate_distribution)
mcp.tool()(search_drucksachen)
mcp.tool()(get_drucksache)
mcp.tool()(get_drucksache_text)
mcp.tool()(search_vorgaenge)
mcp.tool()(get_vorgang)
mcp.tool()(search_plenarprotokolle)
mcp.tool()(get_plenarprotokoll)
mcp.tool()(get_plenarprotokoll_text)
mcp.tool()(search_aktivitaeten)
mcp.tool()(search_members_by_party)
mcp.tool()(get_aktivitaet)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Parliament Analytics MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
