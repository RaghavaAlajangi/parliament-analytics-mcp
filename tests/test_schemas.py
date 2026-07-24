"""Unit tests for Pydantic tool input/output schemas."""

import pytest
from pydantic import ValidationError

from mcp_server.schemas.tool_inputs import RouterOutput
from mcp_server.schemas.tool_outputs import (
    FraktionShare,
    NarrationResult,
)


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
