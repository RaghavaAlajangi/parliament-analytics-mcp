"""Unit tests for the DIP API client with mocked HTTP responses."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.config import Settings
from mcp_server.dip.client import DIPClient, DIPUnavailableError


def _mock_settings() -> Settings:
    return Settings(dip_api_key="BTK2024", groq_api_key="test")


def _person_doc(person_id: str, fraktion: str | None = "CDU") -> dict:
    return {
        "id": person_id,
        "vorname": "Max",
        "nachname": "Mustermann",
        "fraktion": fraktion,
        "wahlperiode_nummer": [20],
    }


class TestDIPClientPagination:
    @pytest.mark.asyncio
    async def test_single_page_no_cursor(self) -> None:
        response = {
            "cursor": None,
            "numFound": 1,
            "documents": [_person_doc("p1")],
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client, "_get", new=AsyncMock(return_value=response)
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 1
        assert persons[0].id == "p1"

    @pytest.mark.asyncio
    async def test_multiple_pages_follow_cursor(self) -> None:
        page1 = {
            "cursor": "next_cursor",
            "numFound": 2,
            "documents": [_person_doc("p1")],
        }
        page2 = {
            "cursor": None,
            "numFound": 2,
            "documents": [_person_doc("p2")],
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client, "_get", new=AsyncMock(side_effect=[page1, page2])
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 2
        assert {p.id for p in persons} == {"p1", "p2"}

    @pytest.mark.asyncio
    async def test_malformed_document_is_skipped(self) -> None:
        response = {
            "cursor": None,
            "numFound": 2,
            "documents": [
                _person_doc("p1"),
                {"id": None, "INVALID_FIELD": True},  # malformed
            ],
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client, "_get", new=AsyncMock(return_value=response)
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        # Only the valid document is yielded; malformed one is skipped with a warning
        assert len(persons) == 1


class TestDIPClientResilience:
    @pytest.mark.asyncio
    async def test_api_key_sent_as_authorization_header(
        self, httpx_mock
    ) -> None:
        httpx_mock.add_response(
            json={"cursor": None, "numFound": 0, "documents": []}
        )
        async with DIPClient(_mock_settings()) as client:
            [p async for p in client.get_persons(wahlperiode=20)]

        request = httpx_mock.get_request()
        assert request.headers["Authorization"] == "ApiKey BTK2024"
        assert "apikey" not in str(request.url)

    @pytest.mark.asyncio
    async def test_429_is_retried_until_success(self, httpx_mock) -> None:
        httpx_mock.add_response(
            status_code=429, headers={"Retry-After": "0"}
        )
        httpx_mock.add_response(
            json={
                "cursor": None,
                "numFound": 1,
                "documents": [_person_doc("p1")],
            }
        )

        async with DIPClient(_mock_settings()) as client:
            persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 1

    @pytest.mark.asyncio
    async def test_bot_challenge_redirect_raises_after_retries(
        self, httpx_mock
    ) -> None:
        settings = Settings(
            dip_api_key="BTK2024",
            groq_api_key="test",
            dip_retry_attempts=2,
            dip_retry_min_wait=0.01,
            dip_retry_max_wait=0.02,
        )
        for _ in range(2):
            httpx_mock.add_response(
                status_code=303,
                headers={"location": "/.enodia/challenge"},
            )

        with pytest.raises(DIPUnavailableError):
            async with DIPClient(settings) as client:
                [p async for p in client.get_persons(wahlperiode=20)]
