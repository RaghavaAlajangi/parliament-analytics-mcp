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
