"""Pydantic models for DIP Bundestag API responses."""

from pydantic import BaseModel, Field


class PersonRole(BaseModel):
    """A single role entry for a person (e.g. Fraktion membership)."""

    id: str
    person_id: str = Field(alias="person")
    fraktion: str | None = None
    wahlperiode_nummer: list[int] = Field(default_factory=list)
    ressort_titel: str | None = None

    model_config = {"populate_by_name": True}


class Person(BaseModel):
    """A politician as returned by GET /person list endpoint."""

    id: str
    vorname: str | None = None
    nachname: str | None = None
    titel: str | None = None
    namenszusatz: str | None = None
    geburtsdatum: str | None = None
    geburtsort: str | None = None
    geschlecht: str | None = None
    # Fraktion may be embedded directly in list response
    fraktion: str | None = None
    wahlperiode_nummer: list[int] = Field(default_factory=list)
    basisdaten_url: str | None = None

    @property
    def full_name(self) -> str:
        parts = [self.titel, self.vorname, self.namenszusatz, self.nachname]
        return " ".join(p for p in parts if p)


class PersonDetail(Person):
    """Extended politician model from GET /person/{id}."""

    roles: list[PersonRole] = Field(default_factory=list)


class DIPListResponse(BaseModel):
    """Generic paginated list response wrapper from the DIP API."""

    cursor: str | None = None
    numFound: int = 0
    documents: list[dict] = Field(default_factory=list)
