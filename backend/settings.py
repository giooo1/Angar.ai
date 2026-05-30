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

    # --- Email: Resend (Phase 4.5 WS4) ---
    resend_api_key: str = Field(default="", description="Resend HTTP API key. Optional in dev.")
    email_from: str = Field(default="Angar.ai <onboarding@resend.dev>")
    frontend_origin: str = Field(default="http://localhost:3000")
    email_verify_token_ttl_hours: int = Field(default=24)
    email_reset_token_ttl_hours: int = Field(default=1)

    # --- Google OAuth sign-in ---
    google_client_id: str = Field(default="", description="Google OAuth 2.0 Web client ID. Empty disables Google sign-in.")
    google_client_secret: str = Field(default="", description="Google OAuth 2.0 client secret.")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/auth/google/callback",
        description="Must exactly match an authorized redirect URI in the Google Cloud console.",
    )

    # --- Stripe (Phase 4.5 WS5) ---
    stripe_secret_key: str = Field(default="", description="sk_test_... / sk_live_... ")
    stripe_webhook_secret: str = Field(default="", description="whsec_... from Stripe CLI or dashboard.")
    stripe_price_id_pro: str = Field(default="", description="Stripe Price ID for the Pro plan.")
    stripe_price_id_business: str = Field(default="", description="Stripe Price ID for the Business plan.")


def get_settings() -> Settings:
    """Return a fresh Settings instance. Called via FastAPI dependency injection."""
    return Settings()


# ---------------------------------------------------------------------------
# Plan → monthly extraction quota (step 6, no Stripe yet)
# ---------------------------------------------------------------------------

PLAN_QUOTAS: dict[str, int] = {
    "free": 50,
    "pro": 100,
    "business": 500,
}

# Display copy for the billing page tiles. Prices come from Stripe at
# checkout — these are advertised numbers only; the source of truth on
# what a customer is charged is whatever the linked Stripe Price says.
PLAN_DISPLAY: dict[str, dict[str, str]] = {
    "free": {"label": "Free", "price": "₾0", "blurb": "Evaluate Angar.ai on real invoices."},
    "pro": {"label": "Pro", "price": "₾49 / month", "blurb": "One-person practice."},
    "business": {"label": "Business", "price": "₾249 / month", "blurb": "Small accounting firm."},
}
