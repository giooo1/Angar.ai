"""End-to-end smoke against a real Anthropic API call.

Opt-in via the `e2e` marker — `pytest -q` skips it by default
(see pyproject.toml's `-m 'not e2e'`). Run explicitly with:

    pytest -m e2e

The pre-commit eval gate (scripts/eval_gate.py) also triggers this
smoke when the wiring files change (extraction_service.py, main.py,
settings.py). The reasoning is that today's "missing ANTHROPIC_API_KEY"
bug shipped because my smoke used fake bytes that always failed at
extraction time, masking auth/config errors. This test uses a real
Georgian invoice PDF and asserts the full pipeline reaches `completed`.

Cost: one Sonnet call per run (~$0.02–0.05). Set ANTHROPIC_API_KEY in
.env or skip via --no-verify when committing.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db import Base, get_db
from backend.main import app
from backend.models import Organization, OrganizationMember, User
from backend.rate_limit import limiter
from backend.routes.extraction import get_settings_dep, get_storage
from backend.settings import Settings
from backend.storage import FilesystemStorage

pytestmark = pytest.mark.e2e

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "e2e" / "smoke.pdf"


@pytest.fixture(scope="module")
def e2e_settings(tmp_path_factory) -> Settings:
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set; cannot run real e2e smoke")
    base = tmp_path_factory.mktemp("e2e")
    return Settings(
        database_url=f"sqlite:///{base / 'e2e.db'}",
        storage_dir=base / "files",
        anthropic_api_key=api_key,
        jwt_secret="e2e-jwt-secret",
        resend_api_key="",  # no email needed
    )


@pytest.fixture(scope="module")
def e2e_engine(e2e_settings):
    engine = create_engine(
        e2e_settings.database_url,
        connect_args={"check_same_thread": False},
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(e2e_engine) -> Iterator[Session]:
    SessionLocal = sessionmaker(bind=e2e_engine, autocommit=False, autoflush=False, future=True)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def real_org_and_user(db_session):
    from backend.auth import hash_password

    user = User(
        email="e2e@example.com",
        password_hash=hash_password("e2e-password-1"),
        full_name="E2E User",
    )
    org = Organization(
        name="E2E Org",
        monthly_extraction_quota=50,
        monthly_extractions_used=0,
        quota_reset_at=datetime.now(tz=timezone.utc) + timedelta(days=30),
    )
    db_session.add(user)
    db_session.add(org)
    db_session.flush()
    db_session.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="owner"))
    db_session.commit()
    db_session.refresh(user)
    db_session.refresh(org)
    return user, org


@pytest.fixture
def client(db_session, e2e_settings, real_org_and_user) -> Iterator[TestClient]:
    from backend.auth import get_current_org, get_current_user

    user, org = real_org_and_user
    storage = FilesystemStorage(e2e_settings.storage_dir)

    def _db_override():
        yield db_session

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_settings_dep] = lambda: e2e_settings
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org] = lambda: org

    # Conftest's autouse fixture disabled the limiter — re-confirm.
    limiter.enabled = False

    yield TestClient(app)
    app.dependency_overrides.clear()


def test_upload_real_georgian_invoice_yields_canonical_data(client: TestClient) -> None:
    """The bug from today (missing ANTHROPIC_API_KEY → TypeError) would
    fail this test with `error_code='ANTHROPIC_AUTH'` instead of reaching
    `status='completed'`.
    """
    assert FIXTURE_PDF.exists(), f"missing test fixture: {FIXTURE_PDF}"
    pdf_bytes = FIXTURE_PDF.read_bytes()

    upload = client.post(
        "/api/v1/documents",
        files={"file": ("smoke.pdf", pdf_bytes, "application/pdf")},
    )
    assert upload.status_code == 202, upload.text
    body = upload.json()
    extraction_id = body["extraction_id"]

    # Backend extraction is synchronous in this codepath; status should
    # already be terminal, but poll anyway in case that changes.
    deadline = time.time() + 90
    final_status = None
    final_body: dict = {}
    while time.time() < deadline:
        r = client.get(f"/api/v1/extractions/{extraction_id}")
        assert r.status_code == 200
        final_body = r.json()
        final_status = final_body["status"]
        if final_status in ("completed", "failed"):
            break
        time.sleep(1)

    assert final_status == "completed", (
        f"e2e extraction did not complete: status={final_status} "
        f"error_code={final_body.get('error_code')} "
        f"error_message={final_body.get('error_message')}"
    )
    canonical = final_body["canonical_data"]
    assert canonical is not None
    # Document number is typically present on a Georgian waybill.
    # If our smoke fixture happens to be one without a number we still
    # require *some* canonical data — i.e. extraction parsed the response.
    assert isinstance(canonical, dict)
    assert len(canonical) > 0
