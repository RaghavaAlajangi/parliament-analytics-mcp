# Parliament Analytics MCP

Analyzes faction (Fraktion) distribution in the German Bundestag using the public
[DIP API](https://dip.bundestag.de/ueber-dip/hilfe/api). Built on the
[Model Context Protocol](https://modelcontextprotocol.io) — an LLM picks tools
autonomously from your natural language question.

## Setup

**1. Create and activate a virtual environment**

Using `venv`:
```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

Or using `uv` (faster):
```bash
uv venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

**2. Install dependencies**

```bash
# pip
pip install -e ".[dev]"
# uv
uv pip install -e ".[dev]"
```

**3. Configure environment**

```bash
cp .env.example .env
# Fill in:
# - DIP_API_KEY  (.env.example ships the public key, valid until May 2027)
# - GROQ_API_KEY (free at https://groq.com/) or OPENAI_API_KEY
```

**4. Run tests**

```bash
pytest tests/ -v
```

## Usage

### Autonomous MCP Chat

```bash
parliament-chat
# You: Wie ist die Fraktionsverteilung in der 21. Wahlperiode?
#  [llm openai/gpt-4.1-mini tokens=441 latency=1762ms]
# --------------------------------------------------
#  [tool call: get_fraktion_distribution({'wahlperiode': 21})]
#  [tool status: ok, latency=4830ms]
# --------------------------------------------------
#  [llm openai/gpt-4.1-mini tokens=766 latency=2216ms]

# Assistant: Die CDU/CSU ist mit ...
```

### MCP Server (for Claude Desktop or other MCP clients)

```bash
parliament-mcp
```

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "parliament-analytics": {
      "command": "parliament-mcp",
      "env": {
        "DIP_API_KEY": "see .env.example for the current public key",
        "GROQ_API_KEY": "your_key"
      }
    }
  }
}
```

## Tools

| Tool | Description |
|---|---|
| `get_politician` | Look up a politician by name; returns faction and biography data |
| `get_members` | List politicians in a Wahlperiode, optionally filtered by Fraktion |
| `get_fraktion_distribution` | Calculates % share per Fraktion for a given Wahlperiode |

## Deliverables

- **3 MCP tools** exposed via a `fastmcp` server:
  - `get_politician` — look up a politician by name, returns Fraktion and biography data
  - `get_members` — browse members of a Wahlperiode, optionally filtered by Fraktion
  - `get_fraktion_distribution` — compute percentage share per Fraktion for a given Wahlperiode
- **Autonomous chat agent** (`parliament-chat`) — an LLM connects to the MCP server, picks tools from natural language input, and synthesises the answer
- **Installable package** with a `parliament-chat` entry point; no manual server wiring needed
- **Inline observability** — every tool call logs LLM token usage, latency, and DIP API/delay timing to the console (production systems would route this to Langfuse or OpenTelemetry)
- **On-disk response cache** — avoids re-hitting the DIP API for repeated queries within a 24 h window

## Design Decisions & Assumptions

**Autonomous tool calling over deterministic routing.** The original intent was a deterministic pipeline where the LLM only extracts parameters and routing happens in code. MCP's design delegates tool selection entirely to the LLM, so the implemented architecture is fully autonomous — the LLM decides which tool to call and when. This is a conscious trade-off: simpler code, but tool choice is non-deterministic.

**Intentional simplicity.** Complex retry logic (exponential back-off, circuit breakers), distributed tracing, and multi-agent coordination were scoped out. The DIP API is a single external dependency; a simple cache and a clear error on throttling is sufficient for this challenge.

**LLM providers.** Both OpenAI and Groq are supported as drop-in alternatives via `LLM_PROVIDER` in `.env`. Groq is the default (free tier, fast inference). Switch to OpenAI by setting `LLM_PROVIDER=openai`.

**DIP API assumptions.** The `f.person` filter expects `Lastname Firstname` order; the client tries both orderings automatically. The `f.wahlperiode` filter is applied server-side but not guaranteed to be exhaustive, so results are also filtered client-side. The shared public API key is valid until May 2027.

## Rate limiting

DIP fronts its API with bot-protection (Enodia). Throttled clients receive a
`303` redirect instead of data. If this happens, wait a few minutes before retrying.
Optional on-disk response cache (`DIP_CACHE_TTL`) avoids re-hitting the API for
repeated queries — parliament data changes slowly.

The shared public key rotates yearly. If throttling persists, request a personal
10-year key from parlamentsdokumentation@bundestag.de.

## Project Structure

```
mcp_server/
├── server.py          # MCP server — registers all tools
├── chat.py            # Autonomous LLM chat agent
├── config.py          # pydantic-settings config
├── dip/               # DIP API client + Pydantic models
├── aggregation/       # Pure aggregation functions
├── schemas/           # Tool output schemas
└── tools/             # MCP tool implementations
tests/
├── test_aggregation.py
├── test_config.py
├── test_dip_client.py
├── test_models.py
├── test_server.py
└── test_tools.py
```
