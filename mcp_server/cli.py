"""Mode 1 — Deterministic CLI.

Your code explicitly routes, calls tools, and narrates.
LLM is used only for intent extraction and final narration.

Usage:
    python -m mcp_server.cli "Wie ist die Fraktionsverteilung in der 20. Wahlperiode?"
    python -m mcp_server.cli "Wer ist Friedrich Merz?"
"""

import asyncio
import logging
import sys

from mcp_server.llm.router import RoutingError, route
from mcp_server.tools.get_distribution import get_fraktion_distribution
from mcp_server.tools.get_politician import get_politician
from mcp_server.tools.narrate import narrate_distribution

logger = logging.getLogger(__name__)


async def run(query: str) -> None:
    routing = await route(query)
    logger.info("Routed to tool=%s args=%s", routing.tool, routing.arguments)

    if routing.tool == "get_politician":
        result = await get_politician(**routing.arguments)
        print(result.model_dump_json(indent=2))

    elif routing.tool == "get_fraktion_distribution":
        result = await get_fraktion_distribution(**routing.arguments)
        print(result.model_dump_json(indent=2))

    elif routing.tool == "narrate_distribution":
        result = await narrate_distribution(**routing.arguments)
        print(result.text)
        if not result.validation_passed:
            print(
                "\n[Warning: narration validation did not pass]",
                file=sys.stderr,
            )

    else:
        print(f"Unknown tool: {routing.tool}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if len(sys.argv) < 2:
        print('Usage: parliament-cli "<your question>"', file=sys.stderr)
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    try:
        asyncio.run(run(query))
    except RoutingError as exc:
        print(f"Could not understand query: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error")
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
