"""Unit tests for DIP Pydantic models and field normalisation."""

from mcp_server.dip.models import Person


class TestFullName:
    def test_name_parts_joined_in_order(self) -> None:
        p = Person(
            id="1",
            vorname="Ursula",
            namenszusatz="von der",
            nachname="Leyen",
            titel="Dr.  Ursula von der Leyen, Bundesmin., BMVg",
        )
        assert p.full_name == "Ursula von der Leyen"

    def test_titel_not_duplicated(self) -> None:
        p = Person(
            id="1",
            vorname="Friedrich",
            nachname="Merz",
            titel="Friedrich Merz, MdB, CDU/CSU",
        )
        assert p.full_name == "Friedrich Merz"

    def test_falls_back_to_titel_when_no_name_parts(self) -> None:
        p = Person(id="1", titel="Friedrich Merz, MdB, CDU/CSU")
        assert p.full_name == "Friedrich Merz, MdB, CDU/CSU"

    def test_empty_when_nothing_available(self) -> None:
        assert Person(id="1").full_name == ""


class TestFieldNormalisation:
    def test_funktion_as_string_is_wrapped(self) -> None:
        p = Person.model_validate(
            {"id": "1", "funktion": "LMin Soz u. Frauen"}
        )
        assert p.funktion == ["LMin Soz u. Frauen"]

    def test_funktion_as_list_is_kept(self) -> None:
        p = Person.model_validate({"id": "1", "funktion": ["MdB", "Min"]})
        assert p.funktion == ["MdB", "Min"]

    def test_fraktion_as_list_takes_first(self) -> None:
        p = Person.model_validate({"id": "1", "fraktion": ["SPD", "CDU"]})
        assert p.fraktion == "SPD"

    def test_wahlperiode_maps_to_wahlperiode_nummer(self) -> None:
        p = Person.model_validate({"id": "1", "wahlperiode": [19, 20]})
        assert p.wahlperiode_nummer == [19, 20]
