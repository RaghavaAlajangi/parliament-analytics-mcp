"""Validated output schemas for each MCP tool."""

from pydantic import BaseModel, Field


class RoleEntry(BaseModel):
    fraktion: str | None = None
    ressort_titel: str | None = None
    wahlperiode_nummer: list[int] = Field(default_factory=list)


class PoliticianResult(BaseModel):
    id: str
    full_name: str
    titel: str | None = None
    funktion: list[str] = Field(default_factory=list)
    fraktion: str | None = None
    wahlperiode: list[int] = Field(default_factory=list)
    roles: list[RoleEntry] = Field(default_factory=list)
    biography_url: str | None = None


class PoliticianListResult(BaseModel):
    query: str
    results: list[PoliticianResult]
    total_found: int


class FraktionShare(BaseModel):
    fraktion: str
    count: int
    percentage: float = Field(ge=0.0, le=100.0)


class FraktionDistribution(BaseModel):
    wahlperiode: int
    total_politicians: int
    shares: list[FraktionShare] = Field(
        description="Sorted descending by count"
    )
    data_quality_notes: list[str] = Field(default_factory=list)


class MemberEntry(BaseModel):
    full_name: str
    fraktion: str | None = None
    wahlperiode: list[int] = Field(default_factory=list)


class MemberListResult(BaseModel):
    wahlperiode: int
    fraktion_filter: str | None = None
    results: list[MemberEntry]
    total_found: int
