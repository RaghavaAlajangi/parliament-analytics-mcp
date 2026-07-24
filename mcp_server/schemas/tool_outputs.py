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


class DrucksacheResult(BaseModel):
    id: str
    dokumentnummer: str | None
    drucksachetyp: str | None
    titel: str | None
    datum: str | None
    wahlperiode: int | None
    herausgeber: str | None
    autoren_anzahl: int


class DrucksacheListResult(BaseModel):
    query_titel: str | None
    wahlperiode: int | None
    results: list[DrucksacheResult]
    total_found: int


class VorgangResult(BaseModel):
    id: str
    titel: str
    vorgangstyp: str | None
    beratungsstand: str | None
    wahlperiode: int | None
    datum: str | None
    initiative: list[str]
    abstract: str | None
    sachgebiet: list[str]


class VorgangListResult(BaseModel):
    query_titel: str | None
    wahlperiode: int | None
    results: list[VorgangResult]
    total_found: int


class PlenarprotokollResult(BaseModel):
    id: str
    dokumentnummer: str | None
    titel: str | None
    datum: str | None
    wahlperiode: int | None
    herausgeber: str | None
    sitzungsbemerkung: str | None
    vorgangsbezug_anzahl: int


class PlenarprotokollListResult(BaseModel):
    wahlperiode: int | None
    datum_start: str | None
    datum_end: str | None
    results: list[PlenarprotokollResult]
    total_found: int


class AktivitaetResult(BaseModel):
    id: str
    aktivitaetsart: str | None
    titel: str | None
    datum: str | None
    wahlperiode: int | None
    dokumentart: str | None
    person_id: str | None
    abstract: str | None
    vorgangsbezug_anzahl: int


class AktivitaetListResult(BaseModel):
    query_person: str | None
    wahlperiode: int | None
    results: list[AktivitaetResult]
    total_found: int


# --- Detail / full-text results ---


class DrucksacheDetailResult(DrucksacheResult):
    anlagen: str | None = None
    pdf_hash: str | None = None
    urheber: list[str] = []


class DrucksacheTextResult(DrucksacheDetailResult):
    text: str | None = None


class VorgangDetailResult(VorgangResult):
    deskriptoren: list[str] = []
    zustimmungsbeduerftigkeit: list[str] = []
    mitteilung: str | None = None
    gesta: str | None = None


class PlenarprotokollDetailResult(PlenarprotokollResult):
    pdf_hash: str | None = None


class PlenarprotokollTextResult(PlenarprotokollDetailResult):
    text: str | None = None


class AktivitaetDetailResult(AktivitaetResult):
    pass
