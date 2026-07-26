# Parliament Analytics MCP

[![CI](https://github.com/RaghavaAlajangi/parliament-analytics-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RaghavaAlajangi/parliament-analytics-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/RaghavaAlajangi/parliament-analytics-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/RaghavaAlajangi/parliament-analytics-mcp)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP-blueviolet?logo=anthropic&logoColor=white)](https://github.com/jlowin/fastmcp)

Analyzes faction (Fraktion) distribution in the German Bundestag using the public
[DIP API](https://dip.bundestag.de/ueber-dip/hilfe/api). Built on the
[Model Context Protocol](https://modelcontextprotocol.io) — an LLM picks tools
autonomously from your natural language question.

## Table of Contents

1. [Deliverables](#deliverables)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
   - [Option A — Docker (client delivery)](#option-a--docker-client-delivery)
   - [Option B — Local CLI](#option-b--local-cli)
   - [Option C — Claude Desktop](#option-c--claude-desktop)
6. [Tools Reference](#tools-reference)
7. [Design Decisions & Trade-offs](#design-decisions--trade-offs)
8. [Known Limitations](#known-limitations)
9. [Rate Limiting](#rate-limiting)
10. [Project Structure](#project-structure)

## Deliverables

| # | Deliverable | Details |
|---|---|---|
| 1 | **MCP server** | `FastMCP` server exposing 3 tools over stdio or HTTP |
| 2 | **3 MCP tools** | `get_politician`, `get_members`, `get_fraktion_distribution` |
| 3 | **Autonomous chat agent** | `parliament-chat` CLI — LLM picks tools from natural language |
| 4 | **Docker delivery** | Multi-stage `Dockerfile` + `docker-compose.yml` |
| 5 | **Installable Python package** | `parliament-chat` and `parliament-mcp` CLI entry points |
| 6 | **Pydantic v2 schemas** | All tool inputs and outputs are strictly typed |
| 7 | **On-disk API cache** | Avoids re-fetching DIP data within a configurable TTL |
| 8 | **Inline observability** | LLM token counts and per-tool latency printed to console |
| 9 | **Test suite** | `pytest` coverage across tools, models, aggregation, and config |
| 10 | **`/health` endpoint** | Returns `200 OK` in HTTP mode for load balancer / health checks |

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Docker + Docker Compose | any recent | Only for Option A |
| DIP API key | — | Public key ships in `.env.example`, valid until May 2027 |
| Groq API key | — | Free at [groq.com](https://groq.com/) — or provide `OPENAI_API_KEY` instead |

## Installation

Clone the repo and install the package into a virtual environment.

**Using `uv` (recommended):**
```bash
git clone https://github.com/RaghavaAlajangi/parliament-analytics-mcp.git
cd parliament-analytics-mcp
uv venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

**Using `pip`:**
```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

After installation, three CLI commands are available in your shell:

| Command | Purpose |
|---|---|
| `parliament-mcp` | Start the MCP server (stdio transport — for Claude Desktop and local use) |
| `parliament-mcp-http` | Start the MCP server (HTTP transport — for Docker and remote use) |
| `parliament-chat` | Interactive LLM chat agent that connects to the MCP server |

**Verify the installation by running the test suite:**
```bash
pytest tests/ -v
```

## Configuration

All configuration is done via environment variables. Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

The only values you **must** change are the API keys. Everything else has a sensible default:

| Variable | Default | Required | Description |
|---|---|---|---|
| `DIP_API_KEY` | — | **Yes** | Bundestag DIP API key. The public key ships in `.env.example` (valid until May 2027). |
| `GROQ_API_KEY` | — | If `LLM_PROVIDER=groq` | Free key at [groq.com](https://groq.com/). |
| `OPENAI_API_KEY` | — | If `LLM_PROVIDER=openai` | OpenAI API key. |
| `LLM_PROVIDER` | `groq` | No | `groq` or `openai`. |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | No | Model name for the chosen provider. |
| `LLM_TEMPERATURE` | `0.2` | No | Sampling temperature. |
| `LLM_MAX_TOKENS` | `2048` | No | Max tokens per LLM response. |
| `DIP_BASE_URL` | `https://search.dip.bundestag.de/api/v1` | No | DIP API base URL. |
| `DIP_MAX_RECORDS` | `5000` | No | Max records fetched per tool call. |
| `DIP_CACHE_TTL` | `86400` | No | DIP response cache TTL in seconds (`0` = disabled). |
| `DIP_CACHE_DIR` | `.dip_cache` | No | Directory for on-disk response cache. |
| `TOOL_TIMEOUT` | `60.0` | No | Per-tool call timeout in seconds. |
| `MCP_HOST` | `0.0.0.0` | No | Bind host for HTTP transport (Docker mode). |
| `MCP_PORT` | `8000` | No | Port for HTTP transport (Docker mode). |
| `LOG_LEVEL` | `INFO` | No | Python logging level. |

## Running the Application

### Option A — Docker (client delivery)

This is the recommended approach for handing the application to a client.
The client only needs Docker installed and a `.env` file with their API keys.

**Step 1 — Configure environment:**
```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY (DIP_API_KEY is already filled in)
```

**Step 2 — Build and start:**
```bash
docker compose up --build -d
```

**Step 3 — Verify the server is healthy:**
```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "parliament-analytics-mcp"}
```

**Step 4 — Connect the chat client:**
```bash
parliament-chat --url http://localhost:8000/mcp
```

**Stop the service:**
```bash
docker compose down
```

> **Note:** DIP API responses are persisted in a named Docker volume (`dip-cache`) so data
> survives container restarts. To clear it: `docker volume rm parliament-analytics-mcp_dip-cache`.

### Option B — Local CLI

For development or running without Docker.

**Quick start — single terminal:**

`parliament-chat` spawns the MCP server as a subprocess automatically — no separate terminal needed:
```bash
parliament-chat
```

**Two-terminal mode:**

Terminal 1 — start the MCP server:
```bash
parliament-mcp
```

Terminal 2 — connect the chat client to the running server:
```bash
parliament-chat --url http://localhost:8000/mcp
```

**Example session:**
```
You: Wie ist die Fraktionsverteilung in der 21. Wahlperiode?
  [tool call: get_fraktion_distribution(wahlperiode=21)]
  [tool status: ok, latency=4830ms]

Assistant: Die CDU/CSU fuehrt mit 28.4%, gefolgt von der SPD mit 20.1% ...

You: Wer ist Friedrich Merz?
  [tool call: get_politician(name=Friedrich Merz)]
  [tool status: ok, latency=1230ms]

Assistant: Friedrich Merz ist Mitglied der CDU/CSU-Fraktion ...
```

### Option C — Claude Desktop

To use the MCP tools directly inside Claude Desktop, add the server to your config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "parliament-analytics": {
      "command": "parliament-mcp",
      "env": {
        "DIP_API_KEY": "see .env.example for the current public key",
        "GROQ_API_KEY": "your_groq_api_key"
      }
    }
  }
}
```

Claude Desktop starts the MCP server automatically on launch.

## Tools Reference

All three tools are exposed via the MCP server. The LLM selects the appropriate
tool based on your question — you never call them directly.

### `get_politician`

Look up a single politician by name.

| Parameter | Type | Description |
|---|---|---|
| `name` | `str` | Full name in any order (e.g. `Friedrich Merz` or `Merz Friedrich`) |

Returns: Fraktion, Wahlperioden, biography excerpt, DIP person ID.

### `get_members`

List all members of a given Wahlperiode, optionally filtered by Fraktion.

| Parameter | Type | Description |
|---|---|---|
| `wahlperiode` | `int` | Wahlperiode number (e.g. `20`, `21`) |
| `fraktion` | `str` (optional) | Filter by Fraktion (e.g. `CDU/CSU`, `SPD`) |

Returns: list of members with name, Fraktion, and DIP ID.

### `get_fraktion_distribution`

Calculate the percentage share of each Fraktion in a given Wahlperiode.

| Parameter | Type | Description |
|---|---|---|
| `wahlperiode` | `int` | Wahlperiode number (e.g. `20`, `21`) |

Returns: Fraktion → percentage mapping, total member count, and `data_quality_notes`.

## Design Decisions & Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| **MCP over a custom REST API** | The challenge requires MCP. It also means any MCP-capable LLM can use the tools without custom integration code. | Adds the MCP protocol as a dependency; heavier than a plain HTTP API for simple use cases. |
| **Autonomous LLM tool selection** | The LLM reads tool descriptions and picks the right one from natural language — no routing logic to maintain. | Non-deterministic; the LLM may pick the wrong tool on ambiguous queries. |
| **Dual transport (stdio + HTTP)** | stdio works for Claude Desktop and local dev; HTTP is required for Docker. A `--url` flag switches between them at runtime with no server-code changes. | Two entry points (`parliament-mcp` and `parliament-mcp-http`) to maintain. |
| **Groq as default LLM** | Free tier, fast inference, native tool-calling support. | Stricter rate limits than OpenAI; model availability may change. |
| **On-disk response cache** | Parliament data changes slowly; caching avoids repeated DIP API hits and Enodia throttling. | Can serve stale data after a parliamentary reshuffle. Set `DIP_CACHE_TTL=0` to disable. |
| **Client-side Wahlperiode filtering** | The DIP `f.wahlperiode` filter is not guaranteed exhaustive. In-process filtering ensures correctness. | Fetches more records than strictly needed, increasing first-request latency on a cold cache. |
| **Pydantic v2 for all schemas** | Strict typing on all inputs and outputs catches bad LLM-generated arguments before they reach the API. | Schema mismatches surface as validation errors the LLM must retry. |

## Known Limitations

- **"Fraktionslos" count is inflated** — the DIP `/person` endpoint returns every person documented
  in parliamentary materials for a Wahlperiode, including government members, Bundesrat participants,
  and other non-MdB records. These appear without a Fraktion and are counted as `Fraktionslos`.
  Every distribution result includes a `data_quality_notes` field that flags this explicitly.

- **No persistent conversation memory** — each `parliament-chat` session starts fresh. The message
  history exists only in-process and is lost when the session exits.

- **No authentication on the HTTP server** — the Docker service is designed for private/internal use.
  Do not expose port 8000 to the public internet without adding a reverse proxy with authentication.

- **Cold-cache latency** — fetching all members of a Wahlperiode can take 5–30 seconds on the first
  request, depending on network conditions and DIP API throttling.

- **Factual accuracy is not guaranteed** — the challenge spec explicitly notes that data discrepancies
  are possible. The focus is technical correctness, not parliamentary accuracy.

## Rate Limiting

DIP fronts its API with bot-protection middleware (Enodia). Throttled requests receive a `303`
redirect instead of data. If you hit this:

1. Wait a few minutes before retrying.
2. Enable the on-disk cache (`DIP_CACHE_TTL=3600` or higher) to reduce repeated API hits.
3. If throttling persists, request a personal 10-year key from `parlamentsdokumentation@bundestag.de`.

The public key in `.env.example` rotates yearly (current key valid until May 2027).

## Project Structure

```
parliament-analytics-mcp/
├── Dockerfile                  # Multi-stage build for the MCP HTTP server
├── docker-compose.yml          # Single-service compose with dip-cache volume
├── .env.example                # All required variables with safe defaults
├── pyproject.toml              # Package metadata, CLI entry points, dev deps
├── mcp_server/
│   ├── server.py               # FastMCP server — tool registration + /health route
│   ├── chat.py                 # LLM chat agent (stdio auto-spawn or --url HTTP)
│   ├── config.py               # pydantic-settings — all config in one place
│   ├── dip/
│   │   ├── client.py           # Async DIP API client with pagination and cache
│   │   ├── models.py           # Pydantic models for DIP API responses
│   │   └── cache.py            # TTL-aware disk cache for DIP responses
│   ├── aggregation/
│   │   └── fraktion.py         # Pure function: compute Fraktion % distribution
│   ├── schemas/
│   │   └── tool_outputs.py     # Pydantic output schemas for all three tools
│   └── tools/
│       ├── get_distribution.py # Tool: Fraktion % distribution
│       ├── get_members.py      # Tool: list members of a Wahlperiode
│       └── get_politician.py   # Tool: single politician lookup
└── tests/
    ├── test_aggregation.py
    ├── test_config.py
    ├── test_dip_client.py
    ├── test_models.py
    ├── test_server.py
    └── test_tools.py
```
