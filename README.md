# Angar.ai

**Georgian invoice & document extraction.** Upload a PDF (invoice, waybill, receipt,
contract…), and Claude's vision model extracts it into a structured, schema-validated
JSON canonical. Review and correct the result side-by-side with the source document,
then export to CSV / XLSX.

> Built for Georgian-language source documents — the canonical schema and the review UI
> preserve the original script (Mkhedruli) end to end.

---

## What it does

```
Upload PDF ──▶ Extract (Claude vision) ──▶ Schema-validate ──▶ Review & correct ──▶ Export (CSV / XLSX)
```

- **Extraction** — header fields + line items into a typed `CanonicalInvoice`, with
  per-field confidence and typed error codes for failures.
- **Review** — a two-axis field-state model that separates "empty / not on the document"
  from "low confidence," so corrections focus on what actually needs a human.
- **Library** — a paginated, searchable archive of every extraction per organization.
- **Accounts & billing** — email/password auth (argon2id + JWT), per-org monthly quotas,
  and tiered plans.

## Repository layout

| Path | What it is |
|------|------------|
| [`angar_schema/`](angar_schema/) | Shared canonical schema (Pydantic) — the source of truth for extracted data |
| [`angar_extraction/`](angar_extraction/) | Extraction prompt + Claude vision adapter |
| [`backend/`](backend/) | FastAPI service — auth, upload, extraction, review, export, billing |
| [`frontend/`](frontend/) | Next.js 16 (App Router) + React 19 customer app |
| [`eval/`](eval/) | Extraction eval harness + labeled ground-truth set (quality gate) |
| [`Dockerfile`](Dockerfile), [`DEPLOY.md`](DEPLOY.md) | Production build + deployment runbook |

## Tech stack

- **Backend** — Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2. SQLite in dev,
  Postgres in production. Auth via argon2id + HS256 JWT in an HttpOnly cookie; rate
  limiting via slowapi.
- **Frontend** — Next.js 16.2.6 (App Router, server components), React 19, Tailwind v4
  (CSS-first `@theme` tokens), self-hosted PDF rendering (pdfjs).
- **Model** — Anthropic Claude (vision) via the `anthropic` SDK.
- **Quality** — an eval harness (`python -m eval.harness`) gates changes to the
  extraction prompt against a labeled set, run automatically via a pre-commit hook.

## Local development

Requires Python 3.11+ and Node 20+.

**Backend**
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell  (use `source .venv/bin/activate` on macOS/Linux)
pip install -e ".[dev]"
python -m uvicorn backend.main:app --reload   # http://localhost:8000  (docs at /docs)
```

**Frontend**
```bash
cd frontend
npm install
cp .env.example .env.local           # points NEXT_PUBLIC_API_URL at http://localhost:8000
npm run dev                          # http://localhost:3000
```

**Tests**
```bash
pytest -m "not e2e"                  # fast suite; the e2e marker makes a real (paid) model call
```

## Configuration

All secrets are supplied via environment variables — **never committed**. `.env` files are
gitignored; only `frontend/.env.example` (a non-secret template) is tracked.

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | ✅ | Claude vision — the only secret the extractor needs |
| `JWT_SECRET` | ✅ (prod) | HS256 session-cookie signing key |
| `DATABASE_URL` | prod | Postgres connection string (SQLite used if unset) |
| `STORAGE_DIR` | prod | Filesystem path for stored uploads |
| `CORS_ORIGINS` | prod | Comma-separated allowed origins |
| `COOKIE_DOMAIN` | prod | Session-cookie domain |
| `RESEND_API_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `GOOGLE_CLIENT_ID/SECRET` | optional | Email, billing, and OAuth integrations |

## Deployment

Frontend on Vercel, backend on Railway (Docker), Postgres on Neon. The frontend proxies
`/api/*` to the backend so the session cookie stays first-party. See [`DEPLOY.md`](DEPLOY.md)
for the full runbook and gotchas.

## License

Proprietary — © Giorgi Gakharia. All rights reserved. This source is published for
visibility; it is not licensed for reuse, redistribution, or derivative works.
