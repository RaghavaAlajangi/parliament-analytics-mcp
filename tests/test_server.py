"""Integration tests for the MCP server tool registration and input
validation."""

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcp_server.server import mcp


class TestMCPServer:
    @pytest.mark.asyncio
    async def test_all_tools_registered(self) -> None:
        async with Client(mcp) as client:
            tools = await client.list_tools()
        assert {t.name for t in tools} == {
            "get_politician",
            "get_members",
            "get_fraktion_distribution",
        }

    @pytest.mark.asyncio
    async def test_invalid_wahlperiode_rejected_before_execution(
        self,
    ) -> None:
        async with Client(mcp) as client:
            with pytest.raises(ToolError):
                await client.call_tool(
                    "get_fraktion_distribution", {"wahlperiode": 0}
                )

    @pytest.mark.asyncio
    async def test_empty_name_rejected(self) -> None:
        async with Client(mcp) as client:
            with pytest.raises(ToolError):
                await client.call_tool("get_politician", {"name": ""})
