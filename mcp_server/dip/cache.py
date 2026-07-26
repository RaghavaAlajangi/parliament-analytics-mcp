"""Tiny on-disk TTL cache for DIP API responses.

Parliament data changes slowly, while a distribution query re-paginates
hundreds of records. Caching GET responses keeps repeated queries fast
and keeps request volume against the shared public API key low — which
also avoids triggering the DIP bot-protection layer.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCache:
    """File-per-entry JSON cache keyed by request path and params."""

    def __init__(self, directory: Path, ttl_seconds: float) -> None:
        self._dir = directory
        self._ttl = ttl_seconds
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, path: str, params: dict[str, Any] | None) -> Path:
        key = json.dumps([path, params or {}], sort_keys=True)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return self._dir / f"{digest}.json"

    def get(self, path: str, params: dict[str, Any] | None) -> dict | None:
        """Return the cached response, or None if absent or expired."""
        file = self._path_for(path, params)
        try:
            if time.time() - file.stat().st_mtime > self._ttl:
                return None
            return json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def put(self, path: str, params: dict[str, Any] | None, response: dict) -> None:
        """Store a response; cache failures are logged, never raised."""
        file = self._path_for(path, params)
        try:
            file.write_text(json.dumps(response), encoding="utf-8")
        except OSError:
            logger.warning("Could not write DIP cache entry %s", file)
