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

### People & Factions

| Tool | Description |
|---|---|
| `get_politician` | Look up a politician by name; returns faction and biography data |
| `get_fraktion_distribution` | Calculates % share per Fraktion for a given Wahlperiode |
| `narrate_distribution` | Fetches distribution and produces a natural-language analysis |

### Parliamentary Papers (Drucksachen)

| Tool | Description |
|---|---|
| `search_drucksachen` | Search papers by title, type, originator, or date |
| `get_drucksache` | Fetch full metadata for a single paper by DIP ID |
| `get_drucksache_text` | Fetch the full text content of a paper by DIP ID |

### Legislative Proceedings (Vorgänge)

| Tool | Description |
|---|---|
| `search_vorgaenge` | Search proceedings by title, type, status, subject area, or initiator |
| `get_vorgang` | Fetch full details of a single proceeding by DIP ID |

### Plenary Sessions (Plenarprotokolle)

| Tool | Description |
|---|---|
| `search_plenarprotokolle` | Search session records by Wahlperiode or date range |
| `get_plenarprotokoll` | Fetch full metadata for a single session record by DIP ID |
| `get_plenarprotokoll_text` | Fetch the full transcript of a session by DIP ID |

### Parliamentary Activities (Aktivitäten)

| Tool | Description |
|---|---|
| `search_aktivitaeten` | Search activities (speeches, votes, questions) by person or date |
| `get_aktivitaet` | Fetch full details of a single activity by DIP ID |

The intended call pattern is **search → get-by-ID → get-text** as needed.
Search for discovery; by-ID for complete metadata; text only when document
content must be read or quoted.

## API Design Trade-offs

### Endpoints

The DIP API has six resource types (`person`, `vorgang`, `drucksache`,
`plenarprotokoll`, `aktivitaet`, `vorgangsposition`). Each exposes list/search,
by-ID, and full-text variants. All main resource types are covered here except
`vorgangsposition`, which is a sub-resource of `vorgang` representing individual
procedural steps — not a standalone retrieval target for natural language queries.

### Filter parameters

Each DIP search endpoint accepts 15–25 filter parameters. Only the subset that
maps cleanly to natural language is exposed as tool arguments:

**Included:** `titel`, `drucksachetyp`/`vorgangstyp`, `beratungsstand`,
`wahlperiode`, `urheber`, `initiative`, `sachgebiet`, `f.person`/`f.person_id`,
date ranges.

**Excluded deliberately:**

| Filter | Why excluded |
|---|---|
| `f.gesta` | Internal GESTA reference codes — users won't know these |
| `f.ratsdok`, `f.kom` | EU Council/Commission document numbers — require prior knowledge of specific codes |
| `f.deskriptor` | Controlled vocabulary (ANTHES/PARTHES thesaurus) — LLM cannot reliably generate valid terms |
| `f.dokumentnummer` | Exact document number (e.g. `19/1234`) — if you have it, use the by-ID endpoint instead |
| `f.frage_nummer` | Question list number within a Drucksache — too granular for natural language |
| `f.plenarprotokoll`, `f.drucksache`, `f.vorgang` (as filters) | Cross-reference IDs — require a prior tool call to obtain; not naturally guessable |

**The rule:** if filling a filter requires the user to know an internal
reference code or controlled vocabulary term they couldn't derive from their
question, it does not belong as a tool parameter. Chain search → get-by-ID
instead.

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
