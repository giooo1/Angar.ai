"""SQLAlchemy 2.x engine + session factory + Base.

Uses SQLite for local-dev (per the step-2 plan). When the Postgres swap
lands later, only the connection string in settings changes; the ORM
models, sessions, and dependencies stay the same.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.settings import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all backend ORM models."""


_engine = None
_SessionLocal = None


def _normalize_db_url(url: str) -> str:
    """Make a hosted Postgres URL SQLAlchemy-ready with the psycopg v3 driver.

    Railway/Heroku-style URLs come as `postgres://` or bare `postgresql://`;
    both default SQLAlchemy to psycopg2. We ship psycopg v3, so rewrite the
    scheme to `postgresql+psycopg://`. SQLite and already-qualified URLs pass
    through untouched.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _ensure_engine(settings: Settings | None = None) -> None:
    """Lazy-build the engine + session factory on first use."""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    s = settings or get_settings()
    url = _normalize_db_url(s.database_url)

    # SQLite needs the parent directory to exist; create it eagerly.
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args, future=True)
    _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False, future=True)


def get_engine():
    _ensure_engine()
    return _engine


def init_db() -> None:
    """Create all tables that don't already exist. Called from main.py on startup.

    Sufficient until step 5 (auth) introduces Alembic migrations.
    """
    _ensure_engine()
    # Import models so they register on Base.metadata before create_all.
    from backend import models  # noqa: F401
    Base.metadata.create_all(bind=_engine)

    # Lightweight column adds for EXISTING dev SQLite DBs that predate these
    # columns — create_all never ALTERs existing tables, and there's no
    # migration framework yet. SQLite-only: on a fresh Postgres, create_all
    # already builds these columns (and the SQLite type names here aren't all
    # valid PG types). Remove when Alembic lands.
    if _engine.dialect.name == "sqlite":
        from sqlalchemy import inspect, text
        cols = {c["name"] for c in inspect(_engine).get_columns("extractions")}
        _added = [
            ("approved_at", "DATETIME"),
            ("corrected_data", "JSON"),
        ]
        with _engine.begin() as conn:
            for name, sqltype in _added:
                if name not in cols:
                    conn.execute(text(f"ALTER TABLE extractions ADD COLUMN {name} {sqltype}"))

    # One-time quota normalization: the Free plan dropped from 50 → 25. Bring
    # legacy Free orgs (still carrying the old default) in line. Idempotent —
    # after the first run no Free org has 50, and paid orgs are untouched.
    from sqlalchemy import text as _text
    with _engine.begin() as conn:
        conn.execute(
            _text(
                "UPDATE organizations SET monthly_extraction_quota = 25 "
                "WHERE plan = 'free' AND monthly_extraction_quota = 50"
            )
        )


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    _ensure_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
