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


def _ensure_engine(settings: Settings | None = None) -> None:
    """Lazy-build the engine + session factory on first use."""
    global _engine, _SessionLocal
    if _engine is not None:
        return
    s = settings or get_settings()

    # SQLite needs the parent directory to exist; create it eagerly.
    if s.database_url.startswith("sqlite:///"):
        db_path = Path(s.database_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    connect_args = {"check_same_thread": False} if s.database_url.startswith("sqlite") else {}
    _engine = create_engine(s.database_url, connect_args=connect_args, future=True)
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

    # Lightweight column adds — create_all never ALTERs existing tables, and
    # there's no migration framework yet. SQLite-safe; remove when Alembic lands.
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


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped session."""
    _ensure_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
