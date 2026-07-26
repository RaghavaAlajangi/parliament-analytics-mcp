# Parliament Analytics MCP

Analyzes faction (Fraktion) distribution in the German Bundestag using the public
[DIP API](https://dip.bundestag.de/ueber-dip/hilfe/api). Built on the
[Model Context Protocol](https://modelcontextprotocol.io) — an LLM picks tools
autonomously from your natural language question.

## Setup

**1. Install dependencies**

```bash
pip install -e ".[dev]"
```

**2. Configure environment**

```bash
cp .env.example .env
# Fill in:
# - DIP_API_KEY  (.env.example ships the public key, valid until May 2027)
# - GROQ_API_KEY (free at https://groq.com/) or OPENAI_API_KEY
```

**3. Run tests**

```bash
pytest tests/ -v
```

## Usage

### Autonomous MCP Chat

```bash
parliament-chat
# You: Wie ist die Fraktionsverteilung in der 21. Wahlperiode?
# [calling tool: get_fraktion_distribution({"wahlperiode": 21})]
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
