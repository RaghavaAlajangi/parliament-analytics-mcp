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
# - DIP_API_KEY  (use BTK2024 for the free demo key)
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
        "DIP_API_KEY": "BTK2024",
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
