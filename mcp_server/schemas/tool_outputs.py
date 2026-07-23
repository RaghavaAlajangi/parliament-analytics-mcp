"""Validated output schemas for each MCP tool."""

from pydantic import BaseModel, Field


class PoliticianResult(BaseModel):
    id: str
    full_name: str
    fraktion: str | None
    wahlperiode: list[int]
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


class NarrationResult(BaseModel):
    text: str
    model_used: str
    validation_passed: bool
    wahlperiode: int
