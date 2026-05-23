"""Shared pytest fixtures for backend tests.

These fixtures keep every test self-contained: tmp_path-rooted SQLite,
tmp_path-rooted FilesystemStorage, no real Anthropic API calls. Every
test gets a fresh DB and a fresh storage root.

After step 5 (auth), `test_user` + `test_org` fixtures create a fake
authenticated session, and the `client` fixture in test_routes.py
overrides `get_current_user` / `get_current_org` so existing route
tests don't need to call /auth/login.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.auth import hash_password
from backend.db import Base
from backend.models import Organization, OrganizationMember, User
from backend.storage import FilesystemStorage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> FilesystemStorage:
    """A FilesystemStorage rooted under tmp_path/storage."""
    return FilesystemStorage(tmp_path / "storage")


@pytest.fixture
def db_session(tmp_path: Path) -> Iterator[Session]:
    """An isolated SQLite session for one test.

    Uses a per-test SQLite file under tmp_path; tables are created
    fresh, dropped at teardown.
    """
    # Import models so they register on Base.metadata before create_all.
    from backend import models  # noqa: F401

    db_path = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def test_user(db_session: Session) -> User:
    """A persisted User row. Password is `testpass123` (not used in tests directly)."""
    user = User(
        email="tester@example.com",
        password_hash=hash_password("testpass123"),
        full_name="Test Tester",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_org(db_session: Session, test_user: User) -> Organization:
    """A persisted Organization with test_user as the owner."""
    org = Organization(name="Test Org")
    db_session.add(org)
    db_session.flush()
    db_session.add(
        OrganizationMember(organization_id=org.id, user_id=test_user.id, role="owner")
    )
    db_session.commit()
    db_session.refresh(org)
    return org
