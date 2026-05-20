from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/alertix"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/alertix"

    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    cron_token: str = "dev-cron-token-replace-me"

    cors_origins: str = "http://localhost:5173"

    # External APIs
    nasa_firms_map_key: str = ""
    google_flood_hub_key: str = ""
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""

    # R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "alertix"
    r2_public_url: str = ""

    # LLM (Phase 2)
    ollama_url: str = "http://localhost:11434"
    ollama_tunnel_url: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""

    # Email
    resend_api_key: str = ""
    contact_to_email: str = "hello@alertix.ai"

    # Monitoring
    sentry_dsn_backend: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
