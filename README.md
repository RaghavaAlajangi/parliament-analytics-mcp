# Parliament Analytics MCP

Analyzes faction (Fraktion) distribution in the German Bundestag using the public
[DIP API](https://dip.bundestag.de/über-dip/hilfe/api). Built on the
[Model Context Protocol](https://modelcontextprotocol.io) with two usage modes:
a deterministic CLI pipeline and an autonomous LLM chat agent.

## Architecture

```
┌─────────────────────────────────┐
│         MCP Server              │
│  get_politician()               │
│  get_fraktion_distribution()    │
│  narrate_distribution()         │
└──────────┬──────────────────────┘
           │
     ┌─────┴──────┐
     ▼            ▼
  CLI (Mode 1)   Chat (Mode 2)
  Deterministic  Autonomous LLM
  pipeline       tool selection
```

**Mode 1 — CLI:** your code routes, calls tools explicitly, LLM only narrates the result.  
**Mode 2 — Chat:** an MCP-compatible LLM picks tools autonomously from your natural language question.

## Setup

**1. Install dependencies**

```bash
pip install -e ".[dev]"
```

**2. Configure environment**

```bash
cp .env.example .env
# Edit .env and fill in your keys:
# - DIP_API_KEY  (.env.example ships the public key, valid until end of
#                 May 2027 — it rotates yearly, see
#                 https://dip.bundestag.de/über-dip/hilfe/api)
# - GROQ_API_KEY (free at https://groq.com/)
```

**3. Run tests**

```bash
pytest tests/ -v
```

## Usage

### Mode 1 — Deterministic CLI

```bash
parliament-cli "Wie ist die Fraktionsverteilung in der 20. Wahlperiode?"
parliament-cli "Wer ist Friedrich Merz?"
```

### Mode 2 — Autonomous MCP Chat

```bash
parliament-chat
# > You: Wie ist die Fraktionsverteilung in der 20. Wahlperiode?
# [calling tool: get_fraktion_distribution({"wahlperiode": 20})]
# > Assistant: Die CDU/CSU ist mit ...
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
| `get_fraktion_distribution` | Calculates % share per Fraktion for a given Wahlperiode |
| `narrate_distribution` | Fetches distribution and produces a natural-language analysis |

## Rate limiting & bot protection

DIP fronts its API with a bot-protection layer (Enodia). Throttled or
suspicious clients receive a `303` redirect to a JavaScript challenge
instead of data — this looks like an invalid API key but is usually
throttling. The client handles this respectfully:

- Retries `429` and challenge redirects with exponential backoff,
  honouring `Retry-After` (`DIP_RETRY_*` settings)
- Optional on-disk response cache (`DIP_CACHE_TTL`) so repeated queries
  don't re-hit the API — parliament data changes slowly
- Configurable pagination delay and concurrency (`DIP_PAGE_DELAY`,
  `DIP_MAX_CONCURRENT`)

The shared public key rotates yearly. If throttling persists, request a
personal 10-year key from parlamentsdokumentation@bundestag.de.

## Project Structure

```
mcp_server/
├── server.py          # MCP server — registers all tools
├── cli.py             # Mode 1: deterministic pipeline
├── chat.py            # Mode 2: autonomous LLM agent
├── config.py          # pydantic-settings config
├── dip/               # DIP API client + Pydantic models
├── aggregation/       # Pure aggregation functions
├── schemas/           # Tool input/output schemas
├── tools/             # MCP tool implementations
└── llm/               # LLM router, narrator, prompts
tests/
├── test_aggregation.py
├── test_schemas.py
├── test_router.py
└── test_dip_client.py
```
