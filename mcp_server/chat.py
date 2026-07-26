"""Mode — Autonomous MCP Agent.

Connects to the MCP server via stdio or HTTP transport and lets an
MCP-compatible LLM pick tools autonomously.

Usage:
    # Stdio (default) — chat.py spawns the server itself
    parliament-chat

    # HTTP — connect to a running server (e.g. Docker)
    parliament-chat --url http://localhost:8000/mcp
"""

import argparse
import asyncio
import json
import logging
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

from mcp_server.config import Settings, get_settings, load_settings_or_exit

logger = logging.getLogger(__name__)


async def chat_loop(server_url: str | None = None) -> None:
    """Run an interactive chat loop backed by the MCP server.

    Parameters
    ----------
    server_url : str | None
        HTTP URL of a running server (e.g. http://localhost:8000/mcp). When
        None, spawns the server locally via stdio.
    """
    settings = get_settings()

    if server_url:
        transport_ctx = streamable_http_client(server_url)
    else:
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
        )
        transport_ctx = stdio_client(server_params)

    async with transport_ctx as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover available tools from the MCP server
            tools_response = await session.list_tools()
            mcp_tools = tools_response.tools
            tool_names = [t.name for t in mcp_tools]
            logger.info("Connected to MCP server, tools: %s", tool_names)

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

            system_prompt = (
                "You are a German parliamentary data assistant. "
                "You have access to tools that fetch live data from the "
                "Bundestag DIP API. "
                "When a tool returns results, present the actual data "
                "from the tool response — names, Fraktion, percentages, "
                "IDs — exactly as returned. "
                "Never say you cannot retrieve information if a tool was "
                "called successfully. Never invent or summarise vaguely "
                "when concrete data is available."
            )

            messages: list[dict] = [
                {"role": "system", "content": system_prompt}
            ]

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

                # Agentic loop: LLM may call tools multiple times before
                # answering
                while True:
                    if settings.llm_provider == "groq":
                        response_text, tool_calls = await _groq_chat(
                            messages, tool_schemas, settings
                        )
                    elif settings.llm_provider == "openai":
                        response_text, tool_calls = await _openai_chat(
                            messages, tool_schemas, settings
                        )
                    else:
                        raise ValueError(
                            f"Unknown LLM provider: {settings.llm_provider}"
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

                        print("-" * 50)
                        print(f"  [tool call: {tool_name}({tool_args})]")

                        t0 = time.perf_counter()
                        try:
                            result = await asyncio.wait_for(
                                session.call_tool(tool_name, tool_args),
                                timeout=settings.tool_timeout,
                            )
                        except TimeoutError:
                            total_ms = (time.perf_counter() - t0) * 1000
                            print(f"  [timeout after {total_ms:.0f}ms]")
                            print("  ------------------------------------")
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": (
                                        f"Tool '{tool_name}' timed out after "
                                        f"{settings.tool_timeout:.0f}s. "
                                        "The data source may be slow or "
                                        "rate-limiting. Please try again."
                                    ),
                                }
                            )
                            continue
                        total_ms = (time.perf_counter() - t0) * 1000
                        result_text = (
                            result.content[0].text if result.content else "{}"
                        )
                        if result.isError:
                            print(f"  [error: {result_text}]")
                        else:
                            print(
                                "  [tool status: ok,"
                                f" latency={total_ms:.0f}ms]"
                            )
                        print("-" * 50)

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
    settings: Settings,
) -> tuple[str, list[dict]]:
    from groq import AsyncGroq  # type: ignore[import-untyped]

    client = AsyncGroq(api_key=settings.groq_api_key)
    t0 = time.perf_counter()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    llm_ms = (time.perf_counter() - t0) * 1000
    u = response.usage
    print(
        f"  [llm groq/{settings.llm_model} "
        f"tokens={u.total_tokens} "
        f"latency={llm_ms:.0f}ms]"
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


async def _openai_chat(
    messages: list[dict],
    tools: list[dict],
    settings: Settings,
) -> tuple[str, list[dict]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    t0 = time.perf_counter()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
    llm_ms = (time.perf_counter() - t0) * 1000
    u = response.usage
    print(
        f"  [llm openai/{settings.llm_model} "
        f"tokens={u.total_tokens} "
        f"latency={llm_ms:.0f}ms]"
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Parliament Analytics chat")
    parser.add_argument(
        "--url",
        metavar="URL",
        default=None,
        help=(
            "HTTP URL of a running MCP server "
            "(e.g. http://localhost:8000/mcp). "
            "Omit to spawn the server locally via stdio."
        ),
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    load_settings_or_exit()
    try:
        asyncio.run(chat_loop(server_url=args.url))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
