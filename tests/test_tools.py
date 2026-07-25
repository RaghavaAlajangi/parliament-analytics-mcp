"""Unit tests for MCP tools with a mocked DIP client."""

from unittest.mock import patch

import pytest

from mcp_server.config import Settings
from mcp_server.dip.models import Person
from mcp_server.tools.get_distribution import get_fraktion_distribution


def _mock_settings() -> Settings:
    return Settings(dip_api_key="BTK2024", groq_api_key="test")


class _FakeDIPClient:
    """Stands in for DIPClient; yields a canned list of persons."""

    def __init__(self, persons: list[Person]) -> None:
        self._persons = persons
        self.api_ms: float = 0.0
        self.delay_ms: float = 0.0

    async def __aenter__(self) -> "_FakeDIPClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get_persons(self, wahlperiode=None, search=None):
        for person in self._persons:
            yield person


def _person(pid: str, fraktion: str | None, wahlperioden: list[int]) -> Person:
    return Person(
        id=pid,
        vorname="Test",
        nachname=f"Person{pid}",
        fraktion=fraktion,
        wahlperiode_nummer=wahlperioden,
    )


class TestGetFraktionDistribution:
    @pytest.mark.asyncio
    async def test_other_wahlperioden_filtered_client_side(self) -> None:
        persons = [
            _person("1", "SPD", [20]),
            _person("2", "CDU/CSU", [20]),
            _person("3", "FDP", [19]),  # not in WP 20 — must be excluded
            _person("4", "SPD", []),  # no WP data — must be excluded
        ]
        with (
            patch(
                "mcp_server.tools.get_distribution.DIPClient",
                return_value=_FakeDIPClient(persons),
            ),
            patch(
                "mcp_server.tools.get_distribution.get_settings",
                return_value=_mock_settings(),
            ),
        ):
            result = await get_fraktion_distribution(wahlperiode=20)

        assert result.total_politicians == 2
        assert {s.fraktion for s in result.shares} == {"SPD", "CDU/CSU"}
        assert any("excluded" in n for n in result.data_quality_notes)

    @pytest.mark.asyncio
    async def test_no_exclusion_note_when_all_match(self) -> None:
        persons = [_person("1", "SPD", [20]), _person("2", "CDU/CSU", [20])]
        with (
            patch(
                "mcp_server.tools.get_distribution.DIPClient",
                return_value=_FakeDIPClient(persons),
            ),
            patch(
                "mcp_server.tools.get_distribution.get_settings",
                return_value=_mock_settings(),
            ),
        ):
            result = await get_fraktion_distribution(wahlperiode=20)

        assert result.total_politicians == 2
        assert result.data_quality_notes == []
