"""Async DIP Bundestag API client with pagination, retries, and rate
limiting."""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from mcp_server.config import Settings
from mcp_server.dip.models import (
    Aktivitaet,
    DIPListResponse,
    Drucksache,
    DrucksacheDetail,
    DrucksacheText,
    Person,
    PersonDetail,
    Plenarprotokoll,
    PlenarprotokollText,
    Vorgang,
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

    # --- Person ---

    async def get_persons(
        self,
        wahlperiode: int | None = None,
        search: str | None = None,
    ) -> AsyncIterator[Person]:
        """Paginate all persons, optionally filtered by wahlperiode or
        search."""
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
                        "Could not parse person document: %s", doc.get("id")
                    )

            cursor = resp.cursor
            if not cursor:
                break

    async def get_person(self, person_id: str) -> PersonDetail:
        """Fetch a single politician by ID."""
        raw = await self._get(f"/person/{person_id}", {"format": "json"})
        return PersonDetail.model_validate(raw)

    # --- Drucksache ---

    async def search_drucksachen(
        self,
        titel: str | None = None,
        drucksachetyp: str | None = None,
        wahlperiode: int | None = None,
        urheber: str | None = None,
        datum_start: str | None = None,
        datum_end: str | None = None,
        limit: int = 20,
    ) -> list[Drucksache]:
        """Search parliamentary papers (Drucksachen).

        Filters:
            titel: keyword in the document title
            drucksachetyp: e.g. 'Antrag', 'Gesetzentwurf', 'Kleine Anfrage'
            wahlperiode: legislative period number
            urheber: originating party or body, e.g. 'Bundesregierung'
            datum_start / datum_end: document date range (ISO 8601)
        """
        params: dict[str, Any] = {"format": "json", "rows": min(limit, 100)}
        if titel:
            params["f.titel"] = titel
        if drucksachetyp:
            params["f.drucksachetyp"] = drucksachetyp
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if urheber:
            params["f.urheber"] = urheber
        if datum_start:
            params["f.datum.start"] = datum_start
        if datum_end:
            params["f.datum.end"] = datum_end

        raw = await self._get("/drucksache", params)
        resp = DIPListResponse.model_validate(raw)
        results = []
        for doc in resp.documents:
            try:
                results.append(Drucksache.model_validate(doc))
            except Exception:
                logger.warning("Could not parse drucksache: %s", doc.get("id"))
        return results

    async def get_drucksache(self, drucksache_id: str) -> DrucksacheDetail:
        """Fetch full metadata for a single Drucksache by ID."""
        raw = await self._get(
            f"/drucksache/{drucksache_id}", {"format": "json"}
        )
        return DrucksacheDetail.model_validate(raw)

    async def get_drucksache_text(self, drucksache_id: str) -> DrucksacheText:
        """Fetch full text + metadata for a single Drucksache by ID."""
        raw = await self._get(
            f"/drucksache-text/{drucksache_id}", {"format": "json"}
        )
        return DrucksacheText.model_validate(raw)

    # --- Vorgang ---

    async def search_vorgaenge(
        self,
        titel: str | None = None,
        vorgangstyp: str | None = None,
        wahlperiode: int | None = None,
        beratungsstand: str | None = None,
        sachgebiet: str | None = None,
        initiative: str | None = None,
        datum_start: str | None = None,
        datum_end: str | None = None,
        limit: int = 20,
    ) -> list[Vorgang]:
        """Search legislative proceedings (Vorgänge).

        Filters:
            titel: keyword in the proceeding title
            vorgangstyp: e.g. 'Gesetzgebung', 'Antrag', 'Anfrage'
            wahlperiode: legislative period number
            beratungsstand: current status, e.g. 'Verkündet', 'Abgeschlossen'
            sachgebiet: subject area, e.g. 'Innere Sicherheit'
            initiative: initiating party, e.g. 'Bundesregierung'
            datum_start / datum_end: document date range (ISO 8601)
        """
        params: dict[str, Any] = {"format": "json", "rows": min(limit, 100)}
        if titel:
            params["f.titel"] = titel
        if vorgangstyp:
            params["f.vorgangstyp"] = vorgangstyp
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if beratungsstand:
            params["f.beratungsstand"] = beratungsstand
        if sachgebiet:
            params["f.sachgebiet"] = sachgebiet
        if initiative:
            params["f.initiative"] = initiative
        if datum_start:
            params["f.datum.start"] = datum_start
        if datum_end:
            params["f.datum.end"] = datum_end

        raw = await self._get("/vorgang", params)
        resp = DIPListResponse.model_validate(raw)
        results = []
        for doc in resp.documents:
            try:
                results.append(Vorgang.model_validate(doc))
            except Exception:
                logger.warning("Could not parse vorgang: %s", doc.get("id"))
        return results

    async def get_vorgang(self, vorgang_id: str) -> Vorgang:
        """Fetch full metadata for a single Vorgang by ID."""
        raw = await self._get(f"/vorgang/{vorgang_id}", {"format": "json"})
        return Vorgang.model_validate(raw)

    # --- Plenarprotokoll ---

    async def search_plenarprotokolle(
        self,
        wahlperiode: int | None = None,
        datum_start: str | None = None,
        datum_end: str | None = None,
        limit: int = 20,
    ) -> list[Plenarprotokoll]:
        """Search plenary session records (Plenarprotokolle).

        Filters:
            wahlperiode: legislative period number
            datum_start / datum_end: session date range (ISO 8601)
        """
        params: dict[str, Any] = {"format": "json", "rows": min(limit, 100)}
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if datum_start:
            params["f.datum.start"] = datum_start
        if datum_end:
            params["f.datum.end"] = datum_end

        raw = await self._get("/plenarprotokoll", params)
        resp = DIPListResponse.model_validate(raw)
        results = []
        for doc in resp.documents:
            try:
                results.append(Plenarprotokoll.model_validate(doc))
            except Exception:
                logger.warning(
                    "Could not parse plenarprotokoll: %s", doc.get("id")
                )
        return results

    async def get_plenarprotokoll(
        self, protokoll_id: str
    ) -> Plenarprotokoll:
        """Fetch full metadata for a single Plenarprotokoll by ID."""
        raw = await self._get(
            f"/plenarprotokoll/{protokoll_id}", {"format": "json"}
        )
        return Plenarprotokoll.model_validate(raw)

    async def get_plenarprotokoll_text(
        self, protokoll_id: str
    ) -> PlenarprotokollText:
        """Fetch full text + metadata for a single Plenarprotokoll by ID."""
        raw = await self._get(
            f"/plenarprotokoll-text/{protokoll_id}", {"format": "json"}
        )
        return PlenarprotokollText.model_validate(raw)

    # --- Aktivitaet ---

    async def search_aktivitaeten(
        self,
        person: str | None = None,
        person_id: str | None = None,
        wahlperiode: int | None = None,
        datum_start: str | None = None,
        datum_end: str | None = None,
        sachgebiet: str | None = None,
        limit: int = 20,
    ) -> list[Aktivitaet]:
        """Search parliamentary activities (speeches, votes, questions).

        Filters:
            person: politician name, e.g. 'Scholz' (partial match)
            person_id: exact person ID (more precise than name)
            wahlperiode: legislative period number
            datum_start / datum_end: activity date range (ISO 8601)
            sachgebiet: subject area filter, e.g. 'Umwelt'
        """
        params: dict[str, Any] = {"format": "json", "rows": min(limit, 100)}
        if person:
            params["f.person"] = person
        if person_id:
            params["f.person_id"] = person_id
        if wahlperiode is not None:
            params["f.wahlperiode"] = wahlperiode
        if datum_start:
            params["f.datum.start"] = datum_start
        if datum_end:
            params["f.datum.end"] = datum_end
        if sachgebiet:
            params["f.sachgebiet"] = sachgebiet

        raw = await self._get("/aktivitaet", params)
        resp = DIPListResponse.model_validate(raw)
        results = []
        for doc in resp.documents:
            try:
                results.append(Aktivitaet.model_validate(doc))
            except Exception:
                logger.warning(
                    "Could not parse aktivitaet: %s", doc.get("id")
                )
        return results

    async def get_aktivitaet(self, aktivitaet_id: str) -> Aktivitaet:
        """Fetch full metadata for a single Aktivität by ID."""
        raw = await self._get(
            f"/aktivitaet/{aktivitaet_id}", {"format": "json"}
        )
        return Aktivitaet.model_validate(raw)
