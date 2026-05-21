"""FastAPI app entry point.

Run with: python -m uvicorn backend.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import init_db


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Angar.ai backend",
    description="Georgian-invoice extraction API. See Phase 3 design doc.",
    version="0.1.0",
    lifespan=_lifespan,
)

# CORS for local Next.js dev (step 3 will run on :3000). Production CORS
# narrowing is a step 5 concern.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Trivial liveness probe."""
    return {"status": "ok"}


# Routes are registered as they land. Step 2 adds the extraction router.
from backend.routes.extraction import router as extraction_router  # noqa: E402

app.include_router(extraction_router, prefix="/api/v1", tags=["extraction"])
