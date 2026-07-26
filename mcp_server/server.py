"""MCP server entrypoint — registers all tools and starts the server."""

import logging

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_server.config import load_settings_or_exit
from mcp_server.tools.get_distribution import get_fraktion_distribution
from mcp_server.tools.get_members import get_members
from mcp_server.tools.get_politician import get_politician

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
mcp.tool()(get_members)
mcp.tool()(get_fraktion_distribution)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse(
        {"status": "ok", "service": "parliament-analytics-mcp"}
    )


def main() -> None:
    """Start the MCP server using stdio transport (for local/Claude Desktop
    use)."""
    logging.basicConfig(level=logging.INFO)
    load_settings_or_exit()
    logger.info("Starting Parliament Analytics MCP server (stdio)")
    mcp.run()


def main_http() -> None:
    """Start the MCP server over HTTP (for Docker / remote deployments)."""
    import os

    logging.basicConfig(level=logging.INFO)
    load_settings_or_exit()
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    logger.info(
        "Starting Parliament Analytics MCP server (http %s:%s)", host, port
    )
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
