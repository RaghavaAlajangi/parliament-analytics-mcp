"""Unit tests for the DIP API client with mocked HTTP responses."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.config import Settings
from mcp_server.dip.client import DIPClient, DIPUnavailableError


def _mock_settings(**overrides) -> Settings:
    defaults = {
        "dip_api_key": "BTK2024",
        "groq_api_key": "test",
        "dip_cache_ttl": 0,
    }
    return Settings(**{**defaults, **overrides})


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
                client, "_get_cached", new=AsyncMock(return_value=response)
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
                client,
                "_get_cached",
                new=AsyncMock(side_effect=[page1, page2]),
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 2
        assert {p.id for p in persons} == {"p1", "p2"}

    @pytest.mark.asyncio
    async def test_empty_page_stops_pagination(self) -> None:
        """An empty documents list must terminate pagination.

        Without the early-break guard, skipped malformed docs cause
        total_yielded to drift below numFound, and the loop would fetch
        an empty next page forever (or until the cursor is exhausted).
        """
        page1 = {
            "cursor": "c2",
            "numFound": 2,
            "documents": [_person_doc("p1")],
        }
        page2 = {
            "cursor": "c3",
            "numFound": 2,
            "documents": [],  # server returned an empty page — must stop here
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client,
                "_get_cached",
                new=AsyncMock(side_effect=[page1, page2]),
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 1
        assert persons[0].id == "p1"

    @pytest.mark.asyncio
    async def test_repeated_cursor_terminates_without_duplicates(
        self,
    ) -> None:
        """DIP signals end-of-list by echoing the request cursor unchanged.

        Even if that final page still carries documents, they must not be
        yielded a second time — and the loop must terminate.
        """
        # numFound overstates the parseable docs, so the yield count alone
        # can never terminate the loop; only the cursor echo can.
        page = {
            "cursor": "LAST",
            "numFound": 3,
            "documents": [_person_doc("p1"), _person_doc("p2")],
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client, "_get_cached", new=AsyncMock(return_value=page)
            ) as mock_get:
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert [p.id for p in persons] == ["p1", "p2"]  # no duplicates
        assert mock_get.await_count == 2  # first page + echoed-cursor page

    @pytest.mark.asyncio
    async def test_no_extra_request_when_all_hits_delivered(self) -> None:
        """When numFound is reached, the redundant end-of-list request
        (and its politeness delay) must be skipped."""
        page = {
            "cursor": "LAST",
            "numFound": 1,
            "documents": [_person_doc("p1")],
        }

        async with DIPClient(_mock_settings()) as client:
            with patch.object(
                client, "_get_cached", new=AsyncMock(return_value=page)
            ) as mock_get:
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        assert len(persons) == 1
        assert mock_get.await_count == 1
        assert client.delay_ms == 0

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
                client, "_get_cached", new=AsyncMock(return_value=response)
            ):
                persons = [p async for p in client.get_persons(wahlperiode=20)]

        # Only the valid document is yielded; malformed one is skipped with a
        # warning
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
    async def test_rate_limit_raises(self, httpx_mock) -> None:
        httpx_mock.add_response(status_code=429)

        with pytest.raises(DIPUnavailableError):
            async with DIPClient(_mock_settings()) as client:
                [p async for p in client.get_persons(wahlperiode=20)]

    @pytest.mark.asyncio
    async def test_bot_challenge_redirect_raises(self, httpx_mock) -> None:
        httpx_mock.add_response(
            status_code=303,
            headers={"location": "/.enodia/challenge"},
        )

        with pytest.raises(DIPUnavailableError):
            async with DIPClient(_mock_settings()) as client:
                [p async for p in client.get_persons(wahlperiode=20)]


class TestDIPClientCache:
    @pytest.mark.asyncio
    async def test_second_call_served_from_cache(
        self, httpx_mock, tmp_path
    ) -> None:
        settings = _mock_settings(
            dip_cache_ttl=60.0, dip_cache_dir=str(tmp_path)
        )
        # Only ONE HTTP response is queued; the second identical query
        # must be answered from the cache or the mock would fail.
        httpx_mock.add_response(
            json={
                "cursor": None,
                "numFound": 1,
                "documents": [_person_doc("p1")],
            }
        )

        async with DIPClient(settings) as client:
            first = [p async for p in client.get_persons(wahlperiode=20)]
        async with DIPClient(settings) as client:
            second = [p async for p in client.get_persons(wahlperiode=20)]

        assert [p.id for p in first] == [p.id for p in second] == ["p1"]

    @pytest.mark.asyncio
    async def test_expired_entry_refetches(self, httpx_mock, tmp_path) -> None:
        settings = _mock_settings(
            dip_cache_ttl=0.000001, dip_cache_dir=str(tmp_path)
        )
        for _ in range(2):
            httpx_mock.add_response(
                json={
                    "cursor": None,
                    "numFound": 1,
                    "documents": [_person_doc("p1")],
                }
            )

        async with DIPClient(settings) as client:
            [p async for p in client.get_persons(wahlperiode=20)]
        async with DIPClient(settings) as client:
            [p async for p in client.get_persons(wahlperiode=20)]

        # both queued responses were consumed — no stale cache reuse
        assert len(httpx_mock.get_requests()) == 2

    @pytest.mark.asyncio
    async def test_cached_pages_skip_page_delay(
        self, httpx_mock, tmp_path
    ) -> None:
        """The inter-page politeness delay paces live requests only;
        a fully cached pagination must not sleep at all."""
        settings = _mock_settings(
            dip_cache_ttl=60.0, dip_cache_dir=str(tmp_path)
        )
        httpx_mock.add_response(
            json={
                "cursor": "c2",
                "numFound": 2,
                "documents": [_person_doc("p1")],
            }
        )
        httpx_mock.add_response(
            json={
                "cursor": "c3",
                "numFound": 2,
                "documents": [_person_doc("p2")],
            }
        )

        async with DIPClient(settings) as live_client:
            first = [p async for p in live_client.get_persons(wahlperiode=20)]
        async with DIPClient(settings) as cached_client:
            second = [
                p async for p in cached_client.get_persons(wahlperiode=20)
            ]

        assert [p.id for p in first] == [p.id for p in second] == ["p1", "p2"]
        assert len(httpx_mock.get_requests()) == 2  # second run fully cached
        assert live_client.delay_ms > 0  # live pages are paced
        assert cached_client.delay_ms == 0  # cache hits skip the delay
