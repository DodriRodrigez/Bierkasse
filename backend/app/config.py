"""Application configuration (pydantic-settings).

Values can be overridden via environment variables or a local `.env` file.
Only development defaults are provided; production MUST set SECRET_KEY.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="BIERKASSE7_", extra="ignore")

    app_name: str = "Bierkasse7"
    debug: bool = True

    # SQLite for development; set to a postgresql:// URL for production.
    database_url: str = "sqlite:///./bierkasse7.db"

    # JWT
    secret_key: str = "dev-only-insecure-secret-change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS (Vite dev server)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Bootstrap accounts (created by the seed scripts). Override in `.env`;
    # the defaults are placeholders and MUST NOT be used in production.
    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "change-me"
    bootstrap_member_password: str = "change-me"

    # Verrechnungs-E-Mail (Ausstandsbenachrichtigungen)
    # Ohne smtp_host wird keine echte Mail versendet, sondern in outbox_dir abgelegt.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    mail_from: str = "verrechnung@example.com"
    mail_from_name: str = "Bierkasse7 Verrechnung"
    outbox_dir: str = "outbox"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
