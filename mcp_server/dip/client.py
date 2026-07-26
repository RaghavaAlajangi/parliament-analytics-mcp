"""Async DIP Bundestag API client with pagination and caching."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx

from mcp_server.config import Settings
from mcp_server.dip.cache import ResponseCache
from mcp_server.dip.models import DIPListResponse, Person

logger = logging.getLogger(__name__)

_REDIRECT_CODES = (301, 302, 303, 307, 308)
_PAGE_DELAY = 0.5  # seconds between paginated requests
_MAX_CONCURRENT = 1


class DIPUnavailableError(Exception):
    """DIP is temporarily refusing requests (rate limit or bot protection)."""


class DIPClient:
    """Async client for the DIP Bundestag REST API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.dip_base_url.rstrip("/")
        self._api_key = settings.dip_api_key
        self._max_records = settings.dip_max_records
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
        self._client: httpx.AsyncClient | None = None
        # cumulative HTTP time (excludes cache hits) and inter-page sleep time
        self.api_ms: float = 0.0
        self.delay_ms: float = 0.0
        # whether the most recent _get_cached call was served from cache
        self.last_from_cache: bool = False
        # numFound reported by the API for the most recent get_persons call
        self.last_num_found: int = 0
        self._cache: ResponseCache | None = (
            ResponseCache(Path(settings.dip_cache_dir), settings.dip_cache_ttl)
            if settings.dip_cache_ttl > 0
            else None
        )

    async def __aenter__(self) -> "DIPClient":
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"ApiKey {self._api_key}"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict:
        if self._client is None:
            raise RuntimeError(
                "DIPClient must be used as async context manager"
            )
        url = f"{self._base_url}{path}"

        async with self._semaphore:
            logger.debug("DIP GET %s params=%s", path, params)
            t0 = time.perf_counter()
            response = await self._client.get(url, params=params or {})
            self.api_ms += (time.perf_counter() - t0) * 1000

        if (
            response.status_code == 429
            or response.status_code in _REDIRECT_CODES
        ):
            reason = (
                "rate limited (HTTP 429)"
                if response.status_code == 429
                else f"bot-protection challenge (HTTP {response.status_code})"
            )
            logger.warning("DIP API %s on GET %s", reason, path)
            raise DIPUnavailableError(
                f"DIP API {reason}. Wait a few minutes or verify your API key."
            )

        if not response.is_success:
            logger.error(
                "DIP API error: GET %s -> HTTP %d", path, response.status_code
            )
        response.raise_for_status()
        return response.json()

    async def _get_cached(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict:
        self.last_from_cache = False
        if self._cache is not None:
            cached = self._cache.get(path, params)
            if cached is not None:
                logger.debug("DIP cache hit: GET %s", path)
                self.last_from_cache = True
                return cached
        data = await self._get(path, params)
        if self._cache is not None:
            self._cache.put(path, params, data)
        return data

    @staticmethod
    def _search_candidates(name: str) -> list[str]:
        """Return name variants to try in order.

        The DIP f.person filter expects Lastname Firstname order.
        When a two-token name yields no results we retry with tokens
        swapped so that natural "Firstname Lastname" input also works.
        Single tokens and already-reversed names are returned as-is.
        """
        name = name.strip()
        tokens = name.split()
        if len(tokens) == 2:
            return [name, f"{tokens[1]} {tokens[0]}"]
        return [name]

    async def get_persons(
        self,
        wahlperiode: int | None = None,
        search: str | None = None,
    ) -> AsyncIterator[Person]:
        """Paginate all persons, optionally filtered by wahlperiode or
        search."""
        base_params: dict[str, Any] = {"format": "json"}
        self.last_num_found = 0
        if wahlperiode is not None:
            base_params["f.wahlperiode"] = wahlperiode

        search_terms = self._search_candidates(search) if search else [None]

        for term in search_terms:
            params = dict(base_params)
            if term:
                params["f.person"] = term

            # Peek at the first page to detect zero hits before committing
            first_page = await self._get_cached("/person", params)
            first_resp = DIPListResponse.model_validate(first_page)

            if first_resp.numFound == 0 and len(search_terms) > 1:
                logger.debug(
                    "DIP zero hits for %r, trying reversed form", term
                )
                continue  # try next candidate

            cursor: str | None = None
            total_yielded = 0
            resp = first_resp
            break
        else:
            return  # all candidates returned zero results

        self.last_num_found = first_resp.numFound

        while True:
            if cursor:
                params["cursor"] = cursor
                raw = await self._get_cached("/person", params)
                resp = DIPListResponse.model_validate(raw)
                # DIP signals end-of-list by echoing the request cursor
                # unchanged; yielding such a page would duplicate records
                if resp.cursor == cursor:
                    break

            if not resp.documents:
                break

            for doc in resp.documents:
                try:
                    yield Person.model_validate(doc)
                    total_yielded += 1
                except Exception:
                    logger.warning(
                        "Could not parse person document: %s", doc.get("id")
                    )

            logger.info(
                "DIP pagination: %d/%d records", total_yielded, resp.numFound
            )

            if total_yielded >= self._max_records:
                logger.warning(
                    "DIP max_records cap (%d) reached", self._max_records
                )
                break

            # All reported hits delivered — skip the redundant end-of-list
            # request (only skipped-malformed docs can leave us below it)
            if total_yielded >= resp.numFound:
                break

            cursor = resp.cursor
            if not cursor:
                break
            # Pace consecutive live requests; a cache hit made no request,
            # so no delay is needed before the next page
            if not self.last_from_cache:
                t1 = time.perf_counter()
                await asyncio.sleep(_PAGE_DELAY)
                self.delay_ms += (time.perf_counter() - t1) * 1000

