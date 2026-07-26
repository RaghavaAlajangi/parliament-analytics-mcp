"""Pydantic models for DIP Bundestag API responses."""

from pydantic import BaseModel, Field, model_validator


class PersonRole(BaseModel):
    """A single role entry for a person (e.g. Fraktion membership)."""

    fraktion: str | None = None
    wahlperiode_nummer: list[int] = Field(default_factory=list)
    ressort_titel: str | None = None


class Person(BaseModel):
    """A politician as returned by GET /person list endpoint."""

    id: str
    vorname: str | None = None
    nachname: str | None = None
    titel: str | None = None          # full display title from API
    namenszusatz: str | None = None
    funktion: list[str] = Field(default_factory=list)  # e.g. ["MdB", "Bundespräs."]
    # API returns fraktion as list[str]; we store the first entry
    fraktion: str | None = None
    # API returns wahlperiode as list[int]
    wahlperiode_nummer: list[int] = Field(default_factory=list)
    person_roles: list[PersonRole] = Field(default_factory=list)
    basisdaten_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalise_api_fields(cls, data: dict) -> dict:
        # fraktion comes as a list from the search endpoint
        fraktion = data.get("fraktion")
        if isinstance(fraktion, list):
            data["fraktion"] = fraktion[0] if fraktion else None

        # funktion is a plain string per the API spec, but the search
        # endpoint may return it multi-valued; accept both — a validation
        # failure here would silently drop the whole person record
        funktion = data.get("funktion")
        if isinstance(funktion, str):
            data["funktion"] = [funktion]

        # wahlperiode (list endpoint) → wahlperiode_nummer
        if "wahlperiode_nummer" not in data and "wahlperiode" in data:
            data["wahlperiode_nummer"] = data["wahlperiode"]

        return data

    def fraktion_for(self, wahlperiode: int) -> str | None:
        """Return the Fraktion active in the given Wahlperiode."""
        for role in self.person_roles:
            if wahlperiode in role.wahlperiode_nummer and role.fraktion:
                return role.fraktion
        # Fall back to the top-level fraktion field
        return self.fraktion

    @property
    def full_name(self) -> str:
        """Plain name, e.g. 'Ursula von der Leyen'.

        `titel` is NOT included: the API returns it as the full display
        string ('Dr. Ursula von der Leyen, Bundesmin., ...'), which would
        duplicate the name. It is used only as a fallback when the name
        parts are missing.
        """
        parts = [self.vorname, self.namenszusatz, self.nachname]
        name = " ".join(p for p in parts if p)
        return name or (self.titel or "")


class PersonDetail(Person):
    """Extended politician model from GET /person/{id}."""


class DIPListResponse(BaseModel):
    """Generic paginated list response wrapper from the DIP API."""

    cursor: str | None = None
    numFound: int = 0
    documents: list[dict] = Field(default_factory=list)
