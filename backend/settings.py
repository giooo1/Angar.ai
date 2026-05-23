"""Backend settings, read from env / .env at the repo root.

ANTHROPIC_API_KEY is the only secret the backend depends on; it MUST be
set for the server to do useful work. All other settings have local-dev
defaults that put state under backend/.local/ (gitignored).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Secrets ---
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude vision.")

    # --- Storage and persistence ---
    database_url: str = Field(
        default=f"sqlite:///{_REPO_ROOT / 'backend' / '.local' / 'angar.db'}"
    )
    storage_dir: Path = Field(default=_REPO_ROOT / "backend" / ".local" / "files")

    # --- Extraction config ---
    angar_model: str = Field(default="claude-sonnet-4-6")
    angar_prompt_version: str = Field(default="v3")
    angar_use_cache: bool = Field(default=True)

    # --- Upload limits ---
    max_upload_bytes: int = Field(default=10 * 1024 * 1024)
    allowed_mime_types: tuple[str, ...] = (
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/heic",
    )

    # --- Multi-tenancy stubs (used only in tests now; production paths require a real user) ---
    default_org_id: str = Field(default="demo-org")
    default_user_id: str = Field(default="demo-user")

    # --- File retention ---
    retention_days: int = Field(default=30)

    # --- Auth: JWT + session cookie (Phase 4 step 5) ---
    jwt_secret: str = Field(default="", description="HS256 signing key. REQUIRED at runtime.")
    jwt_algorithm: str = Field(default="HS256")
    session_cookie_name: str = Field(default="angar_session")
    session_max_age_seconds: int = Field(default=7 * 24 * 3600)
    cookie_secure: bool = Field(default=False)  # set true in production over HTTPS
    cookie_samesite: str = Field(default="lax")  # "lax" | "strict" | "none"


def get_settings() -> Settings:
    """Return a fresh Settings instance. Called via FastAPI dependency injection."""
    return Settings()


# ---------------------------------------------------------------------------
# Plan → monthly extraction quota (step 6, no Stripe yet)
# ---------------------------------------------------------------------------

PLAN_QUOTAS: dict[str, int] = {
    "free": 50,
}
