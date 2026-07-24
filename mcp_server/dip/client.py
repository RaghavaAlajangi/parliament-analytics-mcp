"""Async DIP Bundestag API client with pagination, retries, and rate limiting."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mcp_server.config import Settings
from mcp_server.dip.models import (
    DIPListResponse,
    Person,
    PersonDetail,
)

logger = logging.getLogger(__name__)


class DIPClient:
    """Async client for the DIP Bundestag REST API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.dip_base_url.rstrip("/")
        self._api_key = settings.dip_api_key
        self._page_size = settings.dip_page_size
        self._semaphore = asyncio.Semaphore(settings.dip_max_concurrent)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DIPClient":
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
    )
    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict:
        assert self._client is not None, (
            "DIPClient must be used as async context manager"
        )
        all_params = {"apikey": self._api_key, **(params or {})}
        url = f"{self._base_url}{path}"

        async with self._semaphore:
            logger.debug(
                "DIP GET %s params=%s",
                path,
                {k: v for k, v in all_params.items() if k != "apikey"},
            )
            response = await self._client.get(url, params=all_params)

        response.raise_for_status()
        return response.json()

    async def get_persons(
        self,
        wahlperiode: int | None = None,
        search: str | None = None,
    ) -> AsyncIterator[Person]:
        """Paginate all persons, optionally filtered by wahlperiode or search
        term."""
        params: dict[str, Any] = {"format": "json", "rows": self._page_size}
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if search:
            params["q"] = search

        cursor: str | None = None

        while True:
            if cursor:
                params["cursor"] = cursor

            raw = await self._get("/person", params)
            resp = DIPListResponse.model_validate(raw)

            for doc in resp.documents:
                try:
                    yield Person.model_validate(doc)
                except Exception:
                    logger.warning(
                        f"Could not parse person document: {doc.get('id')}"
                    )

            cursor = resp.cursor
            if not cursor:
                break

    async def get_person(self, person_id: str) -> PersonDetail:
        """Fetch a single politician by ID."""
        raw = await self._get(f"/person/{person_id}", {"format": "json"})
        return PersonDetail.model_validate(raw)

