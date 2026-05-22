# Angar.ai frontend

Phase 4 step 3: the customer-facing Next.js app. Currently covers the
upload flow + app shell; review/dashboard/settings are placeholders.

## Stack

- Next.js 16.2.6 (App Router) + React 19 + TypeScript
- Tailwind v4 (CSS-first `@theme` tokens in `globals.css`)
- `next/font/google` for Inter, Fraunces, Noto Sans + Serif Georgian, JetBrains Mono
- Native `fetch` + `FormData` — no Axios, no state library, no form library

## Setup (one time)

From this folder:

```powershell
npm install
cp .env.example .env.local
# .env.local already points NEXT_PUBLIC_API_URL at http://localhost:8000
```

## Run

Frontend (this folder):

```powershell
npm run dev
```

Backend (separate terminal, from the repo root):

```powershell
python -m uvicorn backend.main:app --reload
```

Open [http://localhost:3000](http://localhost:3000) — `/` redirects to `/upload`.

## Routes

| Path | Purpose | Status |
|---|---|---|
| `/` | redirect to `/upload` | live |
| `/upload` | drag-drop PDF, runs real extraction against the backend | live |
| `/dashboard` | document library | placeholder (step 7) |
| `/review` | side-by-side review of one extraction | placeholder (step 4) |
| `/settings` | profile, org, billing, data | placeholder (step 5) |

## Architecture

```
app/(app)/                  ← route group: shares the sidebar + topbar shell
  layout.tsx                ← Sidebar + Topbar wrapping every app screen
  upload/page.tsx           ← composes the Upload components below

components/
  shell/{sidebar,topbar,nav-item,usage-card}.tsx
  upload/{upload-zone,upload-queue,recent-uploads,usage-panel,tips-panel}.tsx
  ui/{button,chip,icons}.tsx

lib/
  api.ts          ← uploadDocument / getExtraction / pollExtraction / reextract
  api-types.ts    ← TS shadow of backend/api_schemas.py
  utils.ts        ← cn() class-name joiner

hooks/
  use-upload.ts   ← per-file state machine: queued → uploading → extracting → completed/failed
```

The `useUpload()` hook is the single source of truth for the upload
queue + recent-uploads list. It calls `uploadDocument()` then
`pollExtraction()` (Phase 3 §3.3 cadence: 2s for the first 30s, then 5s,
abort after 2 minutes). The backend is currently synchronous so the
first poll already returns `completed`, but the code is shaped for
Celery-async later.

## What's intentionally not here

- **No auth.** The app shell renders for any visitor; backend stubs `demo-org` / `demo-user`. NextAuth comes in step 5.
- **No persistence across reloads.** The Recent Uploads list is in-memory only — reload clears it. SQLite is the source of truth; step 7 (Dashboard) loads history.
- **No marketing landing.** Hero v2.html design is for a future effort.
- **No mobile / responsive polish.** Desktop-first per the design.
- **No bulk upload, no email-attachment intake.** Buttons exist but are disabled.
- **No tests.** Manual smoke only at this stage. Playwright e2e arrives with CI in a later step.

## Manual smoke test

With both servers running:

1. Open [http://localhost:3000/upload](http://localhost:3000/upload)
2. Drag `project foundation/pdfs/invoice_001.pdf` onto the drop zone
3. Watch the file appear in the Processing strip as "extracting"
4. ~25 seconds later it moves to Recent Uploads with status "done" and sub-line `DRESSUP.GE · IN234454 · 2025-05-19`
5. Drag the same PDF again — dedup kicks in, the existing entry is reused (backend returns the same document_id / extraction_id)
6. Drop a `.txt` file — UI shows a "failed" chip with the backend's bilingual `INVALID_FILE_TYPE` message
