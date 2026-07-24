"""Validated input schemas for each MCP tool."""

from typing import Literal

from pydantic import BaseModel, Field


class GetPoliticianInput(BaseModel):
    name: str = Field(
        description="Full or partial name, e.g. 'Friedrich Merz'"
    )
    wahlperiode: int | None = Field(
        default=None,
        description="Optional Wahlperiode filter, e.g. 20",
    )


class GetDistributionInput(BaseModel):
    wahlperiode: int = Field(
        description="Wahlperiode number, e.g. 20 for the 20th Bundestag",
        ge=1,
    )


class NarrateInput(BaseModel):
    wahlperiode: int = Field(description="Wahlperiode to narrate results for")
    language: Literal["de", "en"] = Field(
        default="de",
        description="Output language: 'de' for German, 'en' for English",
    )
    style: Literal["concise", "detailed"] = Field(
        default="concise",
        description="Narration style",
    )


class SearchDrucksachenInput(BaseModel):
    titel: str | None = Field(
        default=None,
        description="Title keyword to search for, e.g. 'Klimaschutz'",
    )
    drucksachetyp: str | None = Field(
        default=None,
        description="Type filter, e.g. 'Antrag', 'Gesetzentwurf', 'Anfrage'",
    )
    wahlperiode: int | None = Field(
        default=None,
        description="Wahlperiode number, e.g. 20",
    )
    datum_start: str | None = Field(
        default=None,
        description="Earliest date filter (ISO 8601), e.g. '2021-01-01'",
    )
    datum_end: str | None = Field(
        default=None,
        description="Latest date filter (ISO 8601), e.g. '2023-12-31'",
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )


class SearchVorgaengeInput(BaseModel):
    titel: str | None = Field(
        default=None,
        description="Title keyword, e.g. 'Bundeshaushalt'",
    )
    vorgangstyp: str | None = Field(
        default=None,
        description="Type of proceeding, e.g. 'Gesetzgebung', 'Antrag'",
    )
    wahlperiode: int | None = Field(
        default=None,
        description="Wahlperiode number, e.g. 20",
    )
    beratungsstand: str | None = Field(
        default=None,
        description="Current status, e.g. 'Verkündet', 'Abgeschlossen'",
    )
    limit: int = Field(default=20, ge=1, le=100)


class SearchPlenarprotokolleInput(BaseModel):
    wahlperiode: int | None = Field(
        default=None,
        description="Wahlperiode number, e.g. 20",
    )
    datum_start: str | None = Field(
        default=None,
        description="Earliest session date (ISO 8601), e.g. '2023-01-01'",
    )
    datum_end: str | None = Field(
        default=None,
        description="Latest session date (ISO 8601), e.g. '2023-12-31'",
    )
    limit: int = Field(default=20, ge=1, le=100)


class SearchAktivitaetenInput(BaseModel):
    person: str | None = Field(
        default=None,
        description="Politician name to filter by, e.g. 'Scholz'",
    )
    person_id: str | None = Field(
        default=None,
        description="Exact person ID from Personenstammdaten",
    )
    wahlperiode: int | None = Field(
        default=None,
        description="Wahlperiode number, e.g. 20",
    )
    datum_start: str | None = Field(
        default=None,
        description="Earliest date (ISO 8601)",
    )
    datum_end: str | None = Field(
        default=None,
        description="Latest date (ISO 8601)",
    )
    limit: int = Field(default=20, ge=1, le=100)


class RouterOutput(BaseModel):
    """Structured output from the LLM routing step (Mode 1 only)."""

    tool: Literal[
        "get_politician",
        "get_fraktion_distribution",
        "narrate_distribution",
        "search_drucksachen",
        "get_drucksache",
        "get_drucksache_text",
        "search_vorgaenge",
        "get_vorgang",
        "search_plenarprotokolle",
        "get_plenarprotokoll",
        "get_plenarprotokoll_text",
        "search_aktivitaeten",
        "get_aktivitaet",
    ]
    arguments: dict
    reasoning: str = Field(
        description="Chain-of-thought kept for auditability"
    )
