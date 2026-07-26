"""Unit tests for Fraktion distribution aggregation logic."""

from mcp_server.aggregation.fraktion import FRAKTIONSLOS, compute_distribution
from mcp_server.dip.models import Person


def _person(fraktion: str | None, wahlperiode: int = 20) -> Person:
    return Person(
        id="x",
        vorname="Test",
        nachname="Person",
        fraktion=fraktion,
        wahlperiode_nummer=[wahlperiode],
    )


class TestComputeDistribution:
    def test_empty_input_returns_zero_total(self) -> None:
        result = compute_distribution([], wahlperiode=20)
        assert result.total_politicians == 0
        assert result.shares == []
        assert any(
            "No politician records found" in n for n in result.data_quality_notes
        )

    def test_single_fraktion(self) -> None:
        persons = [_person("SPD")] * 3
        result = compute_distribution(persons, wahlperiode=20)
        assert result.total_politicians == 3
        assert len(result.shares) == 1
        assert result.shares[0].fraktion == "SPD"
        assert result.shares[0].percentage == 100.0

    def test_multiple_fraktionen_sorted_descending(self) -> None:
        persons = [_person("CDU")] * 4 + [_person("SPD")] * 2 + [_person("Grüne")] * 1
        result = compute_distribution(persons, wahlperiode=20)
        assert result.shares[0].fraktion == "CDU"
        assert result.shares[0].count == 4
        assert result.shares[-1].count == 1

    def test_percentages_sum_to_100(self) -> None:
        persons = [_person("CDU")] * 3 + [_person("SPD")] * 1
        result = compute_distribution(persons, wahlperiode=20)
        total_pct = sum(s.percentage for s in result.shares)
        assert abs(total_pct - 100.0) < 0.01

    def test_missing_fraktion_counted_as_fraktionslos(self) -> None:
        persons = [_person("CDU"), _person(None), _person(None)]
        result = compute_distribution(persons, wahlperiode=20)
        fraktionslos = next(
            (s for s in result.shares if s.fraktion == FRAKTIONSLOS), None
        )
        assert fraktionslos is not None
        assert fraktionslos.count == 2

    def test_data_quality_note_when_missing(self) -> None:
        persons = [_person("CDU"), _person(None)]
        result = compute_distribution(persons, wahlperiode=20)
        assert any(FRAKTIONSLOS in n for n in result.data_quality_notes)

    def test_no_quality_note_when_all_assigned(self) -> None:
        persons = [_person("CDU"), _person("SPD")]
        result = compute_distribution(persons, wahlperiode=20)
        assert result.data_quality_notes == []

    def test_wahlperiode_preserved(self) -> None:
        result = compute_distribution([_person("CDU")], wahlperiode=19)
        assert result.wahlperiode == 19
