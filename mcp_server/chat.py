"""Mode 2 — Autonomous MCP Agent.

Connects to the MCP server via stdio transport and lets an MCP-compatible
LLM pick tools autonomously. The LLM reads tool descriptions, selects
the right tool, and formulates the answer — no routing code needed here.

Usage:
    # Terminal 1: start the MCP server
    python -m mcp_server.server

    # Terminal 2: start the chat client
    python -m mcp_server.chat

The chat client uses the Groq (or Anthropic) API with native tool-calling,
passing the MCP server's tool schemas directly to the LLM.
"""

import asyncio
import json
import logging
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcp_server.config import get_settings

logger = logging.getLogger(__name__)


async def chat_loop() -> None:
    """Run an interactive chat loop backed by the MCP server."""
    settings = get_settings()

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover available tools from the MCP server
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools
            logger.info(
                "Connected to MCP server, tools: %s",
                [t.name for t in mcp_tools],
            )

            # Convert MCP tool schemas to the format the LLM provider expects
            tool_schemas = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
                for t in mcp_tools
            ]

            print("Parliament Analytics — autonomous chat mode")
            print("Type your question, or 'quit' to exit.\n")

            messages: list[dict] = []

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                if user_input.lower() in {"quit", "exit", "q"}:
                    break
                if not user_input:
                    continue

                messages.append({"role": "user", "content": user_input})

                # Agentic loop: LLM may call tools multiple times before answering
                while True:
                    if settings.llm_provider == "groq":
                        response_text, tool_calls = await _groq_chat(
                            messages, tool_schemas, settings
                        )
                    else:
                        response_text, tool_calls = await _anthropic_chat(
                            messages, tool_schemas, settings
                        )

                    if not tool_calls:
                        # LLM produced a final answer
                        print(f"\nAssistant: {response_text}\n")
                        messages.append(
                            {"role": "assistant", "content": response_text}
                        )
                        break

                    # Execute each tool call via MCP and feed results back
                    messages.append(
                        {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": tool_calls,
                        }
                    )

                    for tc in tool_calls:
                        tool_name = tc["function"]["name"]
                        tool_args = json.loads(tc["function"]["arguments"])

                        print(f"  [calling tool: {tool_name}({tool_args})]")

                        result = await session.call_tool(tool_name, tool_args)
                        result_text = (
                            result.content[0].text if result.content else "{}"
                        )

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": result_text,
                            }
                        )


async def _groq_chat(
    messages: list[dict],
    tools: list[dict],
    settings,
) -> tuple[str, list[dict]]:
    from groq import AsyncGroq  # type: ignore[import-untyped]

    client = AsyncGroq(api_key=settings.groq_api_key)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    msg = response.choices[0].message
    tool_calls = [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }
        for tc in (msg.tool_calls or [])
    ]
    return msg.content or "", tool_calls


async def _anthropic_chat(
    messages: list[dict],
    tools: list[dict],
    settings,
) -> tuple[str, list[dict]]:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    anthropic_tools = [
        {
            "name": t["function"]["name"],
            "description": t["function"]["description"],
            "input_schema": t["function"]["parameters"],
        }
        for t in tools
    ]
    # Filter out tool-result messages for the system/user/assistant turns Anthropic expects
    anthropic_messages = [m for m in messages if m.get("role") != "tool"]

    response = await client.messages.create(
        model=settings.llm_model,
        messages=anthropic_messages,
        tools=anthropic_tools,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    text = next((b.text for b in response.content if hasattr(b, "text")), "")
    tool_calls = [
        {
            "id": b.id,
            "type": "function",
            "function": {"name": b.name, "arguments": json.dumps(b.input)},
        }
        for b in response.content
        if b.type == "tool_use"
    ]
    return text, tool_calls


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
