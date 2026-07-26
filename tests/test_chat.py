"""Unit tests for the autonomous agent loop in chat.py."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server.chat import chat_loop


def _mock_settings(**overrides):
    from mcp_server.config import Settings

    defaults = {
        "dip_api_key": "BTK2024",
        "groq_api_key": "test-groq-key",
        "llm_provider": "groq",
        "llm_model": "llama3-8b-8192",
        "tool_timeout": 30.0,
    }
    return Settings(**{**defaults, **overrides})


def _make_mcp_tool(name: str) -> MagicMock:
    tool = MagicMock()
    tool.name = name
    tool.description = f"Tool {name}"
    tool.inputSchema = {"type": "object", "properties": {}}
    return tool


def _make_tool_call(tc_id: str, name: str, args: str = "{}") -> dict:
    return {
        "id": tc_id,
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


class TestAgentLoop:
    @pytest.mark.asyncio
    async def test_final_answer_no_tool_calls(self, capsys) -> None:
        """LLM returns a direct answer with no tool calls — loop exits after
        one LLM call."""
        settings = _mock_settings()

        fake_tool_result = MagicMock()
        fake_tool_result.content = [MagicMock(text='{"ok": true}')]
        fake_tool_result.isError = False

        with (
            patch("mcp_server.chat.get_settings", return_value=settings),
            patch("mcp_server.chat.load_settings_or_exit"),
            patch("mcp_server.chat.stdio_client") as mock_stdio,
            patch(
                "mcp_server.chat._groq_chat",
                new=AsyncMock(return_value=("Hello!", [])),
            ),
            patch("builtins.input", side_effect=["What is 2+2?", EOFError]),
        ):
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(
                tools=[_make_mcp_tool("get_politician")]
            )
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            from mcp.client.session import ClientSession

            with (
                patch.object(
                    ClientSession,
                    "__aenter__",
                    AsyncMock(return_value=mock_session),
                ),
                patch.object(
                    ClientSession, "__aexit__", AsyncMock(return_value=None)
                ),
            ):
                await chat_loop()

        out = capsys.readouterr().out
        assert "Hello!" in out

    @pytest.mark.asyncio
    async def test_tool_call_result_fed_back_to_llm(self, capsys) -> None:
        """LLM calls a tool, result is injected into messages, LLM then
        produces final answer."""
        settings = _mock_settings()

        tool_call = _make_tool_call(
            "tc1", "get_politician", '{"name": "Merz"}'
        )

        # First LLM call returns a tool call; second returns the final answer
        groq_side_effects = [
            (None, [tool_call]),
            ("Friedrich Merz is in CDU/CSU.", []),
        ]

        fake_tool_result = MagicMock()
        fake_tool_result.content = [
            MagicMock(text='{"name": "Friedrich Merz"}')
        ]
        fake_tool_result.isError = False

        with (
            patch("mcp_server.chat.get_settings", return_value=settings),
            patch("mcp_server.chat.load_settings_or_exit"),
            patch("mcp_server.chat.stdio_client") as mock_stdio,
            patch(
                "mcp_server.chat._groq_chat",
                new=AsyncMock(side_effect=groq_side_effects),
            ),
            patch("builtins.input", side_effect=["Who is Merz?", EOFError]),
        ):
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(
                tools=[_make_mcp_tool("get_politician")]
            )
            mock_session.call_tool = AsyncMock(return_value=fake_tool_result)
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            from mcp.client.session import ClientSession

            with (
                patch.object(
                    ClientSession,
                    "__aenter__",
                    AsyncMock(return_value=mock_session),
                ),
                patch.object(
                    ClientSession, "__aexit__", AsyncMock(return_value=None)
                ),
            ):
                await chat_loop()

        out = capsys.readouterr().out
        assert "Friedrich Merz is in CDU/CSU." in out
        # Tool call must have been executed
        mock_session.call_tool.assert_awaited_once_with(
            "get_politician", {"name": "Merz"}
        )

    @pytest.mark.asyncio
    async def test_tool_timeout_injects_error_message(self, capsys) -> None:
        """A timed-out tool call injects an error tool message and the loop
        continues."""
        settings = _mock_settings(tool_timeout=0.001)

        tool_call = _make_tool_call(
            "tc2", "get_politician", '{"name": "Scholz"}'
        )

        groq_side_effects = [
            (None, [tool_call]),
            ("Sorry, the tool timed out.", []),
        ]

        async def _slow_tool(*_args):
            await asyncio.sleep(10)  # will be cancelled by wait_for

        with (
            patch("mcp_server.chat.get_settings", return_value=settings),
            patch("mcp_server.chat.load_settings_or_exit"),
            patch("mcp_server.chat.stdio_client") as mock_stdio,
            patch(
                "mcp_server.chat._groq_chat",
                new=AsyncMock(side_effect=groq_side_effects),
            ),
            patch("builtins.input", side_effect=["Who is Scholz?", EOFError]),
        ):
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()
            mock_session.list_tools.return_value = MagicMock(
                tools=[_make_mcp_tool("get_politician")]
            )
            mock_session.call_tool = _slow_tool
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            from mcp.client.session import ClientSession

            with (
                patch.object(
                    ClientSession,
                    "__aenter__",
                    AsyncMock(return_value=mock_session),
                ),
                patch.object(
                    ClientSession, "__aexit__", AsyncMock(return_value=None)
                ),
            ):
                await chat_loop()

        out = capsys.readouterr().out
        # Timeout banner must be shown
        assert "timeout" in out.lower()
        # Loop must still reach a final answer
        assert "Sorry, the tool timed out." in out

    def test_unknown_provider_rejected_by_settings(self) -> None:
        """Settings rejects an unknown llm_provider at construction time.

        The Literal constraint on Settings.llm_provider means an invalid value
        can never reach the agent loop — it's caught before the server starts.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="llm_provider"):
            _mock_settings(llm_provider="unknown_llm")


class TestProviderHelpers:
    """Thin unit tests for the Groq and OpenAI chat helper functions."""

    @pytest.mark.asyncio
    async def test_groq_chat_returns_text_and_empty_tool_calls(self) -> None:
        settings = _mock_settings()
        messages = [{"role": "user", "content": "hello"}]
        tools: list[dict] = []

        fake_choice = MagicMock()
        fake_choice.message.content = "Hi there!"
        fake_choice.message.tool_calls = []

        fake_usage = MagicMock()
        fake_usage.total_tokens = 10

        fake_response = MagicMock()
        fake_response.choices = [fake_choice]
        fake_response.usage = fake_usage

        with patch("groq.AsyncGroq") as MockGroq:
            mock_client = AsyncMock()
            MockGroq.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                return_value=fake_response
            )

            from mcp_server import chat as chat_mod

            text, tool_calls = await chat_mod._groq_chat(
                messages, tools, settings
            )

        assert text == "Hi there!"
        assert tool_calls == []

    @pytest.mark.asyncio
    async def test_groq_chat_returns_tool_calls(self) -> None:
        settings = _mock_settings()
        messages = [{"role": "user", "content": "look up Merz"}]
        tools: list[dict] = []

        fake_tc = MagicMock()
        fake_tc.id = "tc99"
        fake_tc.function.name = "get_politician"
        fake_tc.function.arguments = '{"name": "Merz"}'

        fake_choice = MagicMock()
        fake_choice.message.content = None
        fake_choice.message.tool_calls = [fake_tc]

        fake_usage = MagicMock()
        fake_usage.total_tokens = 20

        fake_response = MagicMock()
        fake_response.choices = [fake_choice]
        fake_response.usage = fake_usage

        with patch("groq.AsyncGroq") as MockGroq:
            mock_client = AsyncMock()
            MockGroq.return_value = mock_client
            mock_client.chat.completions.create = AsyncMock(
                return_value=fake_response
            )

            from mcp_server import chat as chat_mod

            text, tool_calls = await chat_mod._groq_chat(
                messages, tools, settings
            )

        assert text == ""
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "tc99"
        assert tool_calls[0]["function"]["name"] == "get_politician"
