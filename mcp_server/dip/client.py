"""Async DIP Bundestag API client with pagination, retries, and caching."""

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from mcp_server.config import Settings
from mcp_server.dip.cache import ResponseCache
from mcp_server.dip.models import DIPListResponse, Person, PersonDetail

logger = logging.getLogger(__name__)

_REDIRECT_CODES = (301, 302, 303, 307, 308)
_RETRY_ATTEMPTS = 4
_RETRY_MIN_WAIT = 1.0  # seconds
_RETRY_MAX_WAIT = 30.0  # seconds
_PAGE_DELAY = 0.5  # seconds between paginated requests
_MAX_CONCURRENT = 1


class DIPUnavailableError(Exception):
    """DIP is temporarily refusing requests (rate limit or bot protection).

    The DIP API sits behind Enodia bot-protection that answers throttled
    clients with a redirect instead of a 429. Both are transient and retryable.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (DIPUnavailableError, httpx.TransportError)):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code >= 500
    )


def _make_wait():
    exponential = wait_exponential(
        multiplier=1, min=_RETRY_MIN_WAIT, max=_RETRY_MAX_WAIT
    )

    def _wait(retry_state) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if (
            isinstance(exc, DIPUnavailableError)
            and exc.retry_after is not None
        ):
            return min(exc.retry_after, _RETRY_MAX_WAIT)
        return exponential(retry_state)

    return _wait


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
        self._cache: ResponseCache | None = (
            ResponseCache(Path(settings.dip_cache_dir), settings.dip_cache_ttl)
            if settings.dip_cache_ttl > 0
            else None
        )
        # Wire retry at instance level so tests can patch self._get directly
        self._get = retry(
            stop=stop_after_attempt(_RETRY_ATTEMPTS),
            wait=_make_wait(),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )(self._request)

    async def __aenter__(self) -> "DIPClient":
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"ApiKey {self._api_key}"},
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _request(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict:
        assert self._client is not None, (
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
            try:
                retry_after = float(response.headers.get("retry-after"))
            except (TypeError, ValueError):
                retry_after = None
            reason = (
                "rate limited (HTTP 429)"
                if response.status_code == 429
                else f"redirected to bot-protection challenge "
                f"(HTTP {response.status_code})"
            )
            logger.warning("DIP API %s on GET %s, backing off", reason, path)
            raise DIPUnavailableError(
                f"DIP API {reason}. Wait a few minutes/verify your API key.",
                retry_after=retry_after,
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
        if self._cache is not None:
            cached = self._cache.get(path, params)
            if cached is not None:
                logger.debug("DIP cache hit: GET %s", path)
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
        """Paginate all persons, optionally filtered by wahlperiode or search."""
        base_params: dict[str, Any] = {"format": "json"}
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

            # Yield from the first (already-fetched) page, then paginate
            cursor: str | None = None
            total_yielded = 0
            resp = first_resp
            raw = first_page
            break
        else:
            # All candidates returned zero results
            return

        while True:
            if cursor:
                params["cursor"] = cursor
                raw = await self._get_cached("/person", params)
                resp = DIPListResponse.model_validate(raw)

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

            cursor = resp.cursor
            if not cursor or total_yielded >= resp.numFound:
                break
            t1 = time.perf_counter()
            await asyncio.sleep(_PAGE_DELAY)
            self.delay_ms += (time.perf_counter() - t1) * 1000

    async def get_person(self, person_id: str) -> PersonDetail:
        """Fetch a single politician by ID."""
        raw = await self._get_cached(
            f"/person/{person_id}", {"format": "json"}
        )
        return PersonDetail.model_validate(raw)
