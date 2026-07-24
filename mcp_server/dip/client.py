"""Async DIP Bundestag API client with pagination, retries, and rate
limiting."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from mcp_server.config import Settings
from mcp_server.dip.models import (
    DIPListResponse,
    Person,
    PersonDetail,
)

logger = logging.getLogger(__name__)

_REDIRECT_CODES = (301, 302, 303, 307, 308)


class DIPUnavailableError(Exception):
    """DIP is temporarily refusing requests (rate limit or bot protection).

    The DIP API sits behind a bot-protection layer (Enodia) that answers
    throttled or suspicious clients with a redirect to a JavaScript
    challenge instead of a 429. Both cases are transient and retryable.
    """

    def __init__(
        self, message: str, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


def _is_retryable(exc: BaseException) -> bool:
    """Retry on throttling, transient network errors, and 5xx responses."""
    if isinstance(exc, (DIPUnavailableError, httpx.TransportError)):
        return True
    return (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code >= 500
    )


def _make_wait(settings: Settings):
    """Wait strategy: honour Retry-After when sent, else back off
    exponentially."""
    exponential = wait_exponential(
        multiplier=1,
        min=settings.dip_retry_min_wait,
        max=settings.dip_retry_max_wait,
    )

    def _wait(retry_state) -> float:
        exc = retry_state.outcome.exception() if retry_state.outcome else None
        if (
            isinstance(exc, DIPUnavailableError)
            and exc.retry_after is not None
        ):
            return min(exc.retry_after, settings.dip_retry_max_wait)
        return exponential(retry_state)

    return _wait


class DIPClient:
    """Async client for the DIP Bundestag REST API."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.dip_base_url.rstrip("/")
        self._api_key = settings.dip_api_key
        self._page_size = settings.dip_page_size
        self._page_delay = settings.dip_page_delay
        self._max_records = settings.dip_max_records
        self._semaphore = asyncio.Semaphore(settings.dip_max_concurrent)
        self._client: httpx.AsyncClient | None = None
        # Retry settings come from config, so tests and deployments can
        # tune backoff without touching code
        self._get = retry(
            stop=stop_after_attempt(settings.dip_retry_attempts),
            wait=_make_wait(settings),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )(self._request)

    async def __aenter__(self) -> "DIPClient":
        # API key travels in the Authorization header, never in the URL,
        # so it cannot leak into server logs or proxies
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
            response = await self._client.get(url, params=params or {})

        if (
            response.status_code == 429
            or response.status_code in _REDIRECT_CODES
        ):
            retry_after_header = response.headers.get("retry-after")
            try:
                retry_after = float(retry_after_header)
            except (TypeError, ValueError):
                retry_after = None
            reason = (
                "rate limited (HTTP 429)"
                if response.status_code == 429
                else "redirected to the bot-protection challenge "
                f"(HTTP {response.status_code})"
            )
            logger.warning("DIP API %s on GET %s, backing off", reason, path)
            raise DIPUnavailableError(
                f"DIP API {reason}. The service throttles automated "
                "clients. If this persists: wait a few minutes, verify "
                "the API key is current (the public key rotates yearly), "
                "or request a personal key from "
                "parlamentsdokumentation@bundestag.de.",
                retry_after=retry_after,
            )
        if not response.is_success:
            logger.error(
                "DIP API error: GET %s -> HTTP %d: %s",
                path,
                response.status_code,
                response.text[:200],
            )
        response.raise_for_status()
        return response.json()

    async def get_persons(
        self,
        wahlperiode: int | None = None,
        search: str | None = None,
    ) -> AsyncIterator[Person]:
        """Paginate all persons, optionally filtered by wahlperiode or search.

        Parameters
        ----------
        wahlperiode : int or None, optional
            Filter results to this Wahlperiode number.
        search : str or None, optional
            Free-text search term matched against person names.

        Yields
        ------
        Person
            Validated Person records from the DIP API.
        """
        params: dict[str, Any] = {"format": "json", "rows": self._page_size}
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if search:
            params["f.person"] = search

        cursor: str | None = None
        total_yielded = 0

        while True:
            if cursor:
                params["cursor"] = cursor

            raw = await self._get("/person", params)
            resp = DIPListResponse.model_validate(raw)

            for doc in resp.documents:
                try:
                    yield Person.model_validate(doc)
                    total_yielded += 1
                except Exception:
                    logger.warning(
                        f"Could not parse person document: {doc.get('id')}"
                    )

            logger.info(
                "DIP pagination progress: %d/%d records",
                total_yielded,
                resp.numFound,
            )

            if total_yielded >= self._max_records:
                logger.warning(
                    "DIP max_records cap (%d) reached, stopping pagination",
                    self._max_records,
                )
                break

            cursor = resp.cursor
            if cursor and self._page_delay > 0:
                await asyncio.sleep(self._page_delay)
            if not cursor:
                break

    async def get_person(self, person_id: str) -> PersonDetail:
        """Fetch a single politician by ID.

        Parameters
        ----------
        person_id : str
            DIP person identifier.

        Returns
        -------
        PersonDetail
            Full politician record including roles.
        """
        raw = await self._get(f"/person/{person_id}", {"format": "json"})
        return PersonDetail.model_validate(raw)
