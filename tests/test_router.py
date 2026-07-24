"""Unit tests for the LLM router (Mode 1) with mocked LLM responses."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.llm.router import RoutingError, route


def _mock_settings():
    from mcp_server.config import Settings

    return Settings(
        dip_api_key="test", groq_api_key="test", max_router_retries=3
    )


def _valid_response(tool: str, arguments: dict) -> str:
    return json.dumps(
        {"tool": tool, "arguments": arguments, "reasoning": "test"}
    )


class TestRoute:
    @pytest.mark.asyncio
    async def test_successful_routing_get_politician(self) -> None:
        raw = _valid_response("get_politician", {"name": "Friedrich Merz"})
        with patch(
            "mcp_server.llm.router.complete",
            new=AsyncMock(return_value=(raw, "llama3")),
        ):
            result = await route(
                "Wer ist Friedrich Merz?", settings=_mock_settings()
            )
        assert result.tool == "get_politician"
        assert result.arguments["name"] == "Friedrich Merz"

    @pytest.mark.asyncio
    async def test_successful_routing_get_distribution(self) -> None:
        raw = _valid_response("get_fraktion_distribution", {"wahlperiode": 20})
        with patch(
            "mcp_server.llm.router.complete",
            new=AsyncMock(return_value=(raw, "llama3")),
        ):
            result = await route(
                "Fraktionsverteilung 20. Wahlperiode",
                settings=_mock_settings(),
            )
        assert result.tool == "get_fraktion_distribution"

    @pytest.mark.asyncio
    async def test_retry_on_invalid_json(self) -> None:
        valid = _valid_response("get_politician", {"name": "Merz"})
        side_effects = [("not json", "llama3"), (valid, "llama3")]
        with patch(
            "mcp_server.llm.router.complete",
            new=AsyncMock(side_effect=side_effects),
        ):
            result = await route("Wer ist Merz?", settings=_mock_settings())
        assert result.tool == "get_politician"

    @pytest.mark.asyncio
    async def test_retry_prompt_includes_previous_error(self) -> None:
        valid = _valid_response("get_politician", {"name": "Merz"})
        mock = AsyncMock(
            side_effect=[("not json", "llama3"), (valid, "llama3")]
        )
        with patch("mcp_server.llm.router.complete", new=mock):
            await route("Wer ist Merz?", settings=_mock_settings())
        retry_prompt = mock.call_args_list[1].kwargs["prompt"]
        assert "Previous attempt failed with:" in retry_prompt
        assert retry_prompt.rstrip().endswith("Please correct and try again.")

    @pytest.mark.asyncio
    async def test_raises_routing_error_after_all_retries(self) -> None:
        with patch(
            "mcp_server.llm.router.complete",
            new=AsyncMock(return_value=("bad json", "llama3")),
        ):
            with pytest.raises(RoutingError):
                await route("some query", settings=_mock_settings())

    @pytest.mark.asyncio
    async def test_strips_markdown_code_fences(self) -> None:
        raw = f"```json\n{_valid_response('get_politician', {'name': 'Merz'})}\n```"
        with patch(
            "mcp_server.llm.router.complete",
            new=AsyncMock(return_value=(raw, "llama3")),
        ):
            result = await route("Wer ist Merz?", settings=_mock_settings())
        assert result.tool == "get_politician"
