"""Application configuration loaded from environment variables."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DIP API
    dip_api_key: str
    dip_base_url: str = "https://search.dip.bundestag.de/api/v1"
    dip_page_size: int = 100
    dip_max_concurrent: int = 3

    # LLM
    llm_provider: Literal["groq", "anthropic"] = "groq"
    groq_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    # Routing
    max_router_retries: int = 3

    # Observability
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


def get_settings() -> Settings:
    return Settings()
