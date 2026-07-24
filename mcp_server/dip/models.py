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
    fraktion: str | None = None
    bundesland: str | None = None
    wahlperiode_nummer: list[int] = Field(default_factory=list)
    basisdaten_url: str | None = None

    @property
    def full_name(self) -> str:
        parts = [self.titel, self.vorname, self.namenszusatz, self.nachname]
        return " ".join(p for p in parts if p)


class PersonDetail(Person):
    """Extended politician model from GET /person/{id}."""

    roles: list[PersonRole] = Field(default_factory=list)


# --- Drucksache ---

class Urheber(BaseModel):
    titel: str | None = None
    rolle: str | None = None


class Drucksache(BaseModel):
    """A parliamentary paper from GET /drucksache list."""

    id: str
    typ: str | None = None
    dokumentart: str | None = None
    drucksachetyp: str | None = None
    dokumentnummer: str | None = None
    wahlperiode: int | None = None
    herausgeber: str | None = None
    datum: str | None = None
    titel: str | None = None
    autoren_anzahl: int = 0
    vorgangsbezug_anzahl: int = 0
    urheber: list[Urheber] = Field(default_factory=list)


class DrucksacheDetail(Drucksache):
    """Full detail from GET /drucksache/{id}."""

    anlagen: str | None = None
    pdf_hash: str | None = None


class DrucksacheText(DrucksacheDetail):
    """Full text + metadata from GET /drucksache-text/{id}."""

    text: str | None = None


# --- Vorgang ---

class VorgangDeskriptor(BaseModel):
    name: str | None = None
    typ: str | None = None


class Vorgang(BaseModel):
    """A legislative proceeding from GET /vorgang list."""

    id: str
    typ: str | None = None
    beratungsstand: str | None = None
    vorgangstyp: str | None = None
    wahlperiode: int | None = None
    initiative: list[str] = Field(default_factory=list)
    datum: str | None = None
    titel: str
    abstract: str | None = None
    sachgebiet: list[str] = Field(default_factory=list)
    deskriptor: list[VorgangDeskriptor] = Field(default_factory=list)
    gesta: str | None = None
    zustimmungsbeduerftigkeit: list[str] = Field(default_factory=list)
    mitteilung: str | None = None


# --- Plenarprotokoll ---

class Plenarprotokoll(BaseModel):
    """A plenary session record from GET /plenarprotokoll list."""

    id: str
    typ: str | None = None
    dokumentart: str | None = None
    dokumentnummer: str | None = None
    wahlperiode: int | None = None
    herausgeber: str | None = None
    datum: str | None = None
    titel: str | None = None
    vorgangsbezug_anzahl: int = 0
    sitzungsbemerkung: str | None = None
    pdf_hash: str | None = None


class PlenarprotokollText(Plenarprotokoll):
    """Full text + metadata from GET /plenarprotokoll-text/{id}."""

    text: str | None = None


# --- Aktivitaet ---

class Aktivitaet(BaseModel):
    """A parliamentary activity (speech, vote, etc.) from GET /aktivitaet."""

    id: str
    aktivitaetsart: str | None = None
    typ: str | None = None
    dokumentart: str | None = None
    wahlperiode: int | None = None
    datum: str | None = None
    titel: str | None = None
    person_id: str | None = None
    vorgangsbezug_anzahl: int = 0
    abstract: str | None = None


# --- Generic list wrapper ---

class DIPListResponse(BaseModel):
    """Generic paginated list response wrapper from the DIP API."""

    cursor: str | None = None
    numFound: int = 0
    documents: list[dict] = Field(default_factory=list)
