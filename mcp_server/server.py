"""MCP server entrypoint — registers all tools and starts the server."""

import logging

from fastmcp import FastMCP

from mcp_server.tools.get_distribution import get_fraktion_distribution
from mcp_server.tools.get_politician import get_politician
from mcp_server.tools.narrate import narrate_distribution

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


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Parliament Analytics MCP server")
    mcp.run()


if __name__ == "__main__":
    main()
