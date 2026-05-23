import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_JWT_SECRET = "local-dev-secret-change-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    # Database settings
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/alertix"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/alertix"
    db_max_connections: int = 20
    db_pool_min_size: int = 1
    db_read_replica_url: Optional[str] = None

    # Model & ML settings
    model_weights_dir: str = "./models"
    require_model_weights: bool = False

    # AI guardrails and behavior
    enable_ai_guardrails: bool = True
    ai_summary_max_tokens: int = 1024

    # Redis / ingestion resilience
    redis_retry_attempts: int = 5
    redis_retry_backoff_ms: int = 200

    redis_url: str = "redis://localhost:6379/0"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    cron_token: str = "dev-cron-token-replace-me"

    cors_origins: str = "http://localhost:5173"

    # External APIs
    nasa_firms_map_key: str = ""
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""
    cwc_flood_dashboard_url: str = "https://cwc.gov.in/ffm_dashboard"
    cwc_daily_report_url: str = "https://cwc.gov.in/fmo/dfsra"
    state_flood_bulletin_urls: str = ""
    weather_ingest_points: str = ""

    # R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "alertix"
    r2_public_url: str = ""
    storage_backend: str = "local"
    local_upload_dir: str = "uploads"
    damage_model_checkpoint: str = ""
    flood_lstm_checkpoint: str = ""
    flood_unet_checkpoint: str = ""

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
    def state_flood_bulletin_url_list(self) -> list[str]:
        return [url.strip() for url in self.state_flood_bulletin_urls.split(",") if url.strip()]

    @property
    def weather_ingest_point_list(self) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for raw_point in self.weather_ingest_points.split(";"):
            if not raw_point.strip():
                continue
            try:
                lat, lon = [float(part.strip()) for part in raw_point.split(",", maxsplit=1)]
            except ValueError:
                continue
            points.append((lat, lon))
        return points

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate_jwt_secret(self) -> None:
        """Raise RuntimeError if JWT secret is unsafe in non-development environments."""
        secret = self.supabase_jwt_secret
        is_dev = self.app_env == "development" or os.getenv("ENVIRONMENT", "").lower() == "development"
        if not is_dev:
            if not secret or secret == _DEV_JWT_SECRET:
                raise RuntimeError(
                    "SUPABASE_JWT_SECRET must be set to a secure random string in "
                    f"non-development environments (app_env={self.app_env!r}). "
                    "Set ENVIRONMENT=development to bypass this check only in local dev."
                )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def get_jwt_secret() -> str:
    """Return the JWT secret, falling back to dev default only in development mode."""
    settings = get_settings()
    if settings.supabase_jwt_secret:
        return settings.supabase_jwt_secret
    is_dev = (
        settings.app_env == "development"
        or os.getenv("ENVIRONMENT", "").lower() == "development"
    )
    if not is_dev:
        raise RuntimeError(
            "SUPABASE_JWT_SECRET is not set. Cannot issue or verify JWTs in production."
        )
    return _DEV_JWT_SECRET
