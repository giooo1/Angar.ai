# Angar.ai backend

Phase 4 step 2: the FastAPI service that takes a customer's uploaded
PDF and returns a `CanonicalInvoice`. Local-only for now; Railway +
Postgres + Cloudflare R2 + Celery deployment lands in later steps.

## Setup (one time)

From the repo root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Set `ANTHROPIC_API_KEY` in `.env` at the repo root (already set if you
ran the eval harness).

## Run

```powershell
python -m uvicorn backend.main:app --reload
```

Server listens on `http://localhost:8000`. OpenAPI docs at
`http://localhost:8000/docs`.

## API surface (Phase 3 §3.3)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/healthz` | Liveness probe; returns `{"status": "ok"}` |
| `POST` | `/api/v1/documents` | Upload a PDF/JPG/PNG/HEIC, runs extraction sync, returns 202 with `{document_id, extraction_id, status}` |
| `GET` | `/api/v1/extractions/{id}` | Poll an extraction; returns `status`, `prompt_version`, `model_version`, `canonical_data`, `warnings`, `error_message`, `processing_time_ms` |
| `POST` | `/api/v1/documents/{id}/extract` | Re-extract an existing document; creates a new Extraction row |

Example:

```powershell
curl -F "file=@project foundation\pdfs\invoice_001.pdf" http://localhost:8000/api/v1/documents
```

## What's intentionally NOT here (yet)

- **Auth.** Every row uses the stubbed `demo-org` / `demo-user` IDs. Real
  NextAuth integration lands in Phase 4 step 5.
- **Celery / Redis async workers.** Extraction runs synchronously inside
  the request handler. The response shape (`status` field, separate
  `extraction_id`) is async-correct so swapping to Celery later won't
  break the frontend's polling code.
- **Postgres.** SQLite at `backend/.local/angar.db` for local dev. The
  ORM models are SQLAlchemy so the swap is a connection-string change
  plus the `JSON` → `JSONB` column-type change.
- **Cloudflare R2.** Local filesystem at `backend/.local/files/`,
  abstracted behind a `Storage` ABC.
- **Corrections / export / documents-list endpoints.** Step 4 work.
- **Billing, quotas, webhooks.** Step 6 work.
- **Deletion / retention scheduler.** Rows have `delete_at` populated
  but no background job sweeps them yet.

## Local state

Everything mutable lives under `backend/.local/` (gitignored):

```
backend/.local/
├── angar.db                                   # SQLite DB
└── files/
    └── demo-org/<sha256>.pdf                  # Uploaded files
```

Reset state by deleting the directory:

```powershell
Remove-Item -Recurse -Force backend\.local
```

The next request will recreate everything.

## Tests

```powershell
pytest backend/tests/ -v
```

34 tests, no real Anthropic calls (every Extractor is a MagicMock). The
full eval+backend suite is 150 tests.

## Architecture

```
HTTP request
   │
   ▼
backend/routes/extraction.py   ← FastAPI handlers (UploadFile, Path)
   │     (Depends: get_db, get_storage, get_extractor_dep, get_settings_dep)
   ▼
backend/extraction_service.py  ← store_uploaded_file / run_extraction / create_reextract
   │
   ├─→ backend/storage.py            ← FilesystemStorage (→ R2Storage later)
   ├─→ backend/models.py             ← Document, Extraction (SQLAlchemy)
   └─→ angar_extraction.Extractor    ← Anthropic SDK + v3 prompt + cache
              │
              └─→ angar_schema.CanonicalInvoice
```

## Verified end-to-end

A real `invoice_001.pdf` flowing through the full stack produces:

- `document_number: "IN234454"`
- `seller.name: "DRESSUP.GE"`
- `buyer.name: "Giorgi Gakharia"`
- `grand_total: {"amount": "722.75", "currency": "GEL"}`
- 4 line items
- `prompt_version: "v3"`, `model_version: "claude-sonnet-4-6"`
- `processing_time_ms: ~27000` (within the 5–30s expected range)

Dedup verified: re-uploading the same PDF returns the same
`document_id` and `extraction_id`.
