"""Unit tests for Pydantic tool input/output schemas."""

import pytest
from pydantic import ValidationError

from mcp_server.schemas.tool_inputs import (
    GetDistributionInput,
    GetPoliticianInput,
    RouterOutput,
)
from mcp_server.schemas.tool_outputs import (
    FraktionShare,
    NarrationResult,
)


class TestGetPoliticianInput:
    def test_valid_name_only(self) -> None:
        m = GetPoliticianInput(name="Friedrich Merz")
        assert m.name == "Friedrich Merz"
        assert m.wahlperiode is None

    def test_valid_with_wahlperiode(self) -> None:
        m = GetPoliticianInput(name="Angela Merkel", wahlperiode=19)
        assert m.wahlperiode == 19

    def test_empty_name_allowed(self) -> None:
        # Empty string is technically valid — the DIP API handles empty search
        m = GetPoliticianInput(name="")
        assert m.name == ""


class TestGetDistributionInput:
    def test_valid(self) -> None:
        m = GetDistributionInput(wahlperiode=20)
        assert m.wahlperiode == 20

    def test_zero_wahlperiode_invalid(self) -> None:
        with pytest.raises(ValidationError):
            GetDistributionInput(wahlperiode=0)

    def test_missing_wahlperiode_invalid(self) -> None:
        with pytest.raises(ValidationError):
            GetDistributionInput()  # type: ignore[call-arg]


class TestRouterOutput:
    def test_valid(self) -> None:
        m = RouterOutput(
            tool="get_politician",
            arguments={"name": "Merz"},
            reasoning="User asked for a person lookup.",
        )
        assert m.tool == "get_politician"

    def test_invalid_tool_name(self) -> None:
        with pytest.raises(ValidationError):
            RouterOutput(tool="unknown_tool", arguments={}, reasoning="")  # type: ignore[arg-type]


class TestFraktionShare:
    def test_percentage_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            FraktionShare(fraktion="SPD", count=10, percentage=110.0)

    def test_valid(self) -> None:
        s = FraktionShare(fraktion="SPD", count=10, percentage=50.0)
        assert s.fraktion == "SPD"


class TestNarrationResult:
    def test_valid(self) -> None:
        r = NarrationResult(
            text="Die CDU...",
            model_used="llama3",
            validation_passed=True,
            wahlperiode=20,
        )
        assert r.validation_passed is True
