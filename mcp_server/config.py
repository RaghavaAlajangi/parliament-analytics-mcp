"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DIP API
    dip_api_key: str
    dip_base_url: str = "https://search.dip.bundestag.de/api/v1"
    dip_max_concurrent: int = 3
    dip_page_delay: float = 0.0  # seconds between paginated requests
    # Runaway guard only — must exceed the size of one Wahlperiode
    # (~1000-2000 person records) or distributions are computed on a
    # biased sample
    dip_max_records: int = 5000
    dip_retry_attempts: int = 4
    dip_retry_min_wait: float = 1.0  # seconds, exponential backoff floor
    dip_retry_max_wait: float = 30.0  # seconds, backoff/Retry-After ceiling
    dip_cache_ttl: float = 0.0  # seconds; 0 disables response caching
    dip_cache_dir: str = ".dip_cache"
    tool_timeout: float = 60.0  # seconds before a tool call is aborted

    # LLM
    llm_provider: Literal["groq", "openai"] = "groq"
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048

    # Routing
    max_router_retries: int = 3

    # Observability
    log_level: str = "INFO"

    # extra="ignore": unknown keys in .env (e.g. left over from older
    # versions) must never crash startup
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


def get_settings() -> Settings:
    return Settings()


def load_settings_or_exit() -> Settings:
    """Load settings at process startup with a readable failure mode.

    A missing or incomplete .env produces a clear one-line error instead
    of a raw validation traceback on the first tool call.
    """
    try:
        return Settings()
    except ValidationError as exc:
        missing = ", ".join(
            ".".join(str(part) for part in err["loc"]).upper()
            for err in exc.errors()
        )
        raise SystemExit(
            f"Configuration error ({missing}): copy .env.example to .env "
            "and fill in the required values."
        ) from exc
