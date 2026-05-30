# Deploying Angar.ai

Backend → **Railway** (Docker). Frontend → **Vercel** (Next.js). They run on
separate hosts, so the session-cookie note below matters.

---

## Backend (Railway)

The repo root has a `Dockerfile` that installs the project (`backend` +
`angar_schema` + `angar_extraction`) and runs uvicorn on `$PORT`.

1. **New Railway project → Deploy from repo.** Railway detects the `Dockerfile`
   and builds it. (Build context is the repo root; `.dockerignore` excludes the
   frontend, local state, and secrets.)
2. **Add Postgres** (Railway → New → Database → PostgreSQL). It exposes
   `DATABASE_URL`; reference it on the backend service. The app rewrites the
   scheme to the psycopg v3 driver automatically (`backend/db.py`).
3. **Add a Volume** to the backend service (e.g. mount path `/data`) so uploaded
   PDFs survive redeploys, and set `STORAGE_DIR=/data/files`. Without this,
   uploads are lost on every deploy (container filesystem is ephemeral).
4. **Set environment variables** (Service → Variables):

   | Variable | Value / notes |
   |---|---|
   | `ANTHROPIC_API_KEY` | your Anthropic key (required) |
   | `JWT_SECRET` | a long random string (required — auth breaks if empty) |
   | `DATABASE_URL` | reference Railway Postgres (`${{Postgres.DATABASE_URL}}`) |
   | `STORAGE_DIR` | `/data/files` (your volume mount) |
   | `CORS_ORIGINS` | your frontend origin, e.g. `https://app.angar.ai` (comma-separated for multiple) |
   | `FRONTEND_ORIGIN` | same frontend origin (used for OAuth + redirects) |
   | `COOKIE_SECURE` | `true` (HTTPS in prod) |
   | `COOKIE_SAMESITE` | `lax` with custom subdomains, or `none` for raw platform domains (see below) |
   | `COOKIE_DOMAIN` | e.g. `.angar.ai` for subdomain sharing; leave unset for host-only |
   | `RESEND_API_KEY` | optional (email verification / reset) |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | optional (Google sign-in, currently hidden in the UI) |

5. Health check: `GET /healthz` → `{"status":"ok"}`.

---

## Frontend (Vercel)

No code changes or special files needed.

1. **Import the repo → set Root Directory = `frontend`.** Next.js is
   auto-detected (build `next build`).
2. **Environment variable:** `NEXT_PUBLIC_API_URL` = the backend's public URL
   (e.g. `https://api.angar.ai`). This is what the browser calls.
3. Deploy. The self-hosted PDF assets in `frontend/public/` (worker, cmaps,
   fonts) ship as static files.

---

## ⚠️ The session cookie across two hosts (read this)

Auth uses an HttpOnly `angar_session` cookie set by the backend. In dev it works
because both servers are on `localhost`. In production the browser must accept a
cookie from the backend while you're on the frontend — that's only reliable if
they share a registrable domain.

**Recommended — custom subdomains of one domain:**
- Frontend `https://app.angar.ai` (Vercel custom domain)
- Backend `https://api.angar.ai` (Railway custom domain)
- Set `COOKIE_DOMAIN=.angar.ai`, `COOKIE_SAMESITE=lax`, `COOKIE_SECURE=true`,
  `CORS_ORIGINS=https://app.angar.ai`, `FRONTEND_ORIGIN=https://app.angar.ai`,
  and `NEXT_PUBLIC_API_URL=https://api.angar.ai` on the frontend.
- The cookie is then first-party to both → works in every browser.

**Quick but fragile — raw platform domains** (`*.vercel.app` + `*.up.railway.app`):
- These are different sites, so the cookie is third-party. Set
  `COOKIE_SAMESITE=none` + `COOKIE_SECURE=true`. It may work in Chrome today but
  is blocked by Safari (ITP) and is on borrowed time as browsers sunset
  third-party cookies. Use a custom domain before inviting real users.

---

## Notes
- The DB has no migration framework yet (`create_all` + a SQLite-only column
  shim). A fresh Postgres builds the current schema correctly; schema changes
  after launch will need Alembic.
- `git`-tracked secrets: none. `.env` is gitignored and excluded from the image.
