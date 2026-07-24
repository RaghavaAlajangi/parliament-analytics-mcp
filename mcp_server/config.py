"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DIP API
    dip_api_key: str
    dip_base_url: str = "https://search.dip.bundestag.de/api/v1"
    dip_page_size: int = 100
    dip_max_concurrent: int = 3
    dip_page_delay: float = 0.0  # seconds between paginated requests
    dip_max_records: int = 300  # hard cap across all pages
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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


def get_settings() -> Settings:
    return Settings()
