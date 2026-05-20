# Angar.ai — Phase 3: Design

**Version:** 1.0
**Status:** Active — entering Phase 4 (Implementation) on completion
**Empirical foundation:** 8-document labeled eval set (~96% real extraction accuracy) + ad-hoc Streamlit testing. Broader stress testing deferred to Phase 5.

---

## 0. Reading guide

This document commits to specific design decisions for v1 of Angar.ai. Each section names what we're building, what we're explicitly not building, and why. Tradeoffs are named in the open.

The decisions assume:
- v1 scope per Charter v1.3 (extraction quality, not RS.ge/Oris automation)
- Next.js frontend, FastAPI backend, Postgres data store
- Solo founder, 12-week build window, ~265 hours total
- ~96% extraction accuracy is sufficient to launch closed beta

If any assumption changes, re-read the affected section before implementing.

---

## 1. System architecture

### 1.1 Two-service architecture, deliberately small

```
┌──────────────────────────────────────────────────────────────┐
│                         Browser                               │
│                                                               │
│                Next.js app (Vercel hosting)                  │
│              ├─ Public marketing pages                       │
│              ├─ Authenticated app pages                      │
│              └─ Auth via NextAuth.js                         │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS, JWT in Authorization header
                           │
┌──────────────────────────▼───────────────────────────────────┐
│                  FastAPI backend (Railway)                   │
│                                                               │
│    ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│    │ Auth        │  │ Extraction   │  │ Billing         │  │
│    │ /api/auth   │  │ /api/extract │  │ /api/billing    │  │
│    └─────────────┘  └──────┬───────┘  └─────────────────┘  │
│                            │                                 │
│                    ┌───────▼────────┐                       │
│                    │ Celery worker  │                       │
│                    │ (extraction    │                       │
│                    │  jobs, async)  │                       │
│                    └───────┬────────┘                       │
└────────────────────────────┼─────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌──────────┐         ┌─────────────┐
   │Postgres │         │   S3-    │         │ Anthropic   │
   │ (data)  │         │compat    │         │ Claude API  │
   │         │         │ storage  │         │ (vision)    │
   └─────────┘         │ (Cloud-  │         └─────────────┘
                       │ flare R2)│
                       └──────────┘
```

### 1.2 What lives where

**Next.js (frontend):**
- All UI: marketing, app, dashboard, settings, billing
- Server-side rendering for marketing pages (SEO)
- Client-side rendering for authenticated app pages
- File upload to backend; never directly to Claude
- NextAuth.js for session management
- API client calls FastAPI backend via fetch with JWT

**FastAPI (backend):**
- All business logic
- Authentication and authorization
- File ingestion: receive PDF/image, persist to object storage, queue extraction job
- Background worker (Celery) handles actual Claude API calls
- Webhooks for Stripe billing events
- Admin endpoints (used by you, not exposed to UI initially)

**Postgres:**
- Users, organizations, sessions
- Documents (metadata, file references)
- Extractions (canonical schema rows, audit trail)
- Billing state (subscriptions, usage counters)
- Eval set and labeled ground truth

**Cloudflare R2 (or S3-compatible):**
- Original uploaded files (PDFs, images)
- Encrypted at rest
- Auto-deleted after 30 days unless user opts in to retain

**Anthropic Claude API:**
- Vision extraction only
- Called from the Celery worker, never from the web request directly
- Sonnet 4.6 by default; Opus 4.7 for fallback on low-confidence retries

### 1.3 What we are deliberately not building in v1

**No microservices.** One FastAPI service, one worker, one database. Splitting into multiple services adds operational complexity that's not worth it before you have 100 customers.

**No GraphQL.** REST endpoints with explicit Pydantic models. GraphQL would be premature for a single client (your own Next.js frontend).

**No Redis for caching, only for Celery broker.** Caching is a problem for when you have measurable load. You don't yet.

**No CDN beyond Vercel's built-in.** No image optimization service. No edge functions. The marketing site is small enough that Vercel's defaults are fine.

**No multi-region deployment.** Single region (Europe — Railway's EU region) is correct for a Georgian-first product. Latency to Tbilisi is fine.

**No Kubernetes.** Railway's managed deployment is sufficient. K8s is a step you take when you outgrow Railway, not before.

### 1.4 Tradeoff: synchronous vs asynchronous extraction

The biggest architectural choice: should the user wait for extraction, or fire-and-forget?

**Decision: asynchronous.** Upload returns immediately with a `document_id`. Extraction runs in the background. The frontend polls (or websocket subscribes) for status.

**Why:** Real-world extraction takes 5-15 seconds with Claude vision. Synchronous HTTP requests timing out at 30 seconds is a real concern, especially for bulk uploads. Async also lets us batch multiple documents efficiently and recover gracefully from Claude API failures.

**Tradeoff accepted:** More complexity in the frontend (polling/websocket logic), more state to manage. We're paying this complexity cost in exchange for resilience and bulk-upload capability.

---

## 2. Database schema

### 2.1 Core tables

```sql
-- Users and orgs (multi-tenant from day one)
users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,  -- argon2
    full_name TEXT,
    locale TEXT NOT NULL DEFAULT 'en',  -- 'en' or 'ka'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
)

organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    tin TEXT,  -- Georgian TIN if applicable
    plan TEXT NOT NULL DEFAULT 'free',  -- 'free' | 'pro' | 'business'
    monthly_extraction_quota INT NOT NULL DEFAULT 10,
    monthly_extractions_used INT NOT NULL DEFAULT 0,
    quota_reset_at TIMESTAMPTZ NOT NULL,
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

organization_members (
    organization_id UUID REFERENCES organizations(id),
    user_id UUID REFERENCES users(id),
    role TEXT NOT NULL,  -- 'owner' | 'admin' | 'member'
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (organization_id, user_id)
)
```

### 2.2 Documents and extractions

```sql
-- One row per uploaded file
documents (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    uploaded_by_user_id UUID REFERENCES users(id),
    original_filename TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,  -- dedup key
    file_size_bytes BIGINT NOT NULL,
    file_mime_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,  -- R2 object key
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delete_at TIMESTAMPTZ NOT NULL,  -- default 30 days from upload
    deleted_at TIMESTAMPTZ,
    UNIQUE (organization_id, file_sha256)  -- dedup within org
)

CREATE INDEX idx_documents_org_uploaded ON documents(organization_id, uploaded_at DESC);
CREATE INDEX idx_documents_delete_at ON documents(delete_at) WHERE deleted_at IS NULL;

-- One row per extraction attempt (a document may have multiple extractions over time)
extractions (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    status TEXT NOT NULL,  -- 'pending' | 'running' | 'completed' | 'failed'
    prompt_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    canonical_data JSONB,  -- the CanonicalInvoice as JSON
    field_confidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings TEXT[] NOT NULL DEFAULT '{}',
    error_message TEXT,
    processing_time_ms INT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

CREATE INDEX idx_extractions_doc ON extractions(document_id, created_at DESC);
CREATE INDEX idx_extractions_status ON extractions(status) WHERE status IN ('pending', 'running');

-- User corrections (feed back into eval set)
extraction_corrections (
    id UUID PRIMARY KEY,
    extraction_id UUID REFERENCES extractions(id),
    corrected_by_user_id UUID REFERENCES users(id),
    field_path TEXT NOT NULL,  -- e.g. 'seller.tin' or 'items[2].quantity'
    original_value JSONB,
    corrected_value JSONB,
    corrected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

CREATE INDEX idx_corrections_extraction ON extraction_corrections(extraction_id);
```

### 2.3 Eval set (operational, not customer-facing)

```sql
-- Hand-labeled ground truth for ongoing accuracy measurement
eval_documents (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    file_sha256 TEXT NOT NULL UNIQUE,
    storage_path TEXT NOT NULL,
    canonical_truth JSONB NOT NULL,  -- the hand-labeled CanonicalInvoice
    notes TEXT,  -- "phone-number-as-TIN trap" etc.
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

-- One row per eval run (run after every prompt change)
eval_runs (
    id UUID PRIMARY KEY,
    prompt_version TEXT NOT NULL,
    model_version TEXT NOT NULL,
    total_fields INT NOT NULL,
    correct_fields INT NOT NULL,
    accuracy NUMERIC(5,4) NOT NULL,  -- e.g. 0.9637
    per_document_results JSONB NOT NULL,  -- {doc_id: {fields, correct, mismatches}}
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    notes TEXT
)
```

### 2.4 Billing

```sql
subscriptions (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) UNIQUE,
    stripe_subscription_id TEXT UNIQUE,
    plan TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'active' | 'past_due' | 'canceled'
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)

-- Audit log for billing events (Stripe webhooks)
billing_events (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id),
    stripe_event_id TEXT UNIQUE,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### 2.5 Design decisions worth flagging

**One canonical schema lives in two places.** The Pydantic models in `canonical.py` are the source of truth in the application. The Postgres `extractions.canonical_data` column is a JSONB copy. When you change `canonical.py`, write a migration that handles existing JSONB rows.

**Soft delete for documents, hard delete for files.** The `documents` row persists with `deleted_at` set, but the R2 file is hard-deleted at the `delete_at` timestamp. This gives you audit trails without storing customer files indefinitely.

**Dedup at the org level, not globally.** Two different organizations can both have a file with the same hash. Within one org, re-uploading the same file returns the existing document and its existing extraction.

**No tenant isolation beyond `organization_id` filtering.** Row-level security in Postgres is overkill at this stage. Every query filters by `organization_id` at the application layer. Discipline + tests, not infrastructure.

---

## 3. API contract

### 3.1 General principles

- **REST + JSON.** Versioned at `/api/v1/...`
- **JWT in `Authorization: Bearer <token>` header.** Refresh tokens via NextAuth.
- **Pydantic models for all request/response bodies.** Auto-generated OpenAPI docs at `/docs` (admin-only in production).
- **Consistent error format:**
  ```json
  {"error": {"code": "INVALID_FILE_TYPE", "message_en": "...", "message_ka": "..."}}
  ```
- **No batching endpoints in v1.** Multiple documents = multiple uploads. Keep it simple.

### 3.2 Endpoints

```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh

GET    /api/v1/me                       -> current user + org info
PATCH  /api/v1/me                       -> update locale, name, etc.

POST   /api/v1/documents                 -> upload (multipart)
GET    /api/v1/documents                 -> list (paginated)
GET    /api/v1/documents/{id}            -> single doc + latest extraction
DELETE /api/v1/documents/{id}            -> soft delete

POST   /api/v1/documents/{id}/extract    -> trigger re-extraction
GET    /api/v1/extractions/{id}          -> extraction status + data
PATCH  /api/v1/extractions/{id}/fields   -> submit corrections

GET    /api/v1/extractions/{id}/export   -> ?format=csv|json|xlsx

POST   /api/v1/billing/checkout-session  -> Stripe checkout
POST   /api/v1/billing/portal-session    -> Stripe customer portal
POST   /api/v1/billing/webhook           -> Stripe webhook (HMAC-verified)
```

### 3.3 Upload flow in detail

```
1. POST /api/v1/documents (multipart/form-data, file + optional name)
   Response: 202 Accepted
   Body: { document_id, extraction_id, status: "pending" }

2. Backend persists file to R2, creates documents row, queues Celery job

3. Frontend polls GET /api/v1/extractions/{extraction_id}
   - status: "pending"  | "running" | "completed" | "failed"
   - When status = "completed", body includes canonical_data

4. (Alternative: subscribe to /ws/extractions/{extraction_id} for push)
```

**Polling cadence:** 2-second intervals for first 30 seconds, then 5-second intervals. Stop polling after 2 minutes with a "still working, check back" message.

**Websocket optional for v1.** Polling is simpler. Switch to websockets if you find users staring at loading states.

### 3.4 Rate limits

- **Uploads:** 100 per minute per org (matches the bulk-upload UX cap)
- **Auth:** 10 login attempts per email per hour
- **API in general:** 1000 requests per minute per user

Implemented with a Redis-backed rate limiter. Returns 429 with retry-after header.

---

## 4. Critical user flows

Five screens. These are wireframes-in-prose, not pixel mockups. Wireframes get refined in Phase 4 when you're actually building. The point here is to commit to *what each screen does*, not what it looks like.

### 4.1 Upload screen (the most-used screen in the product)

**Purpose:** Get a file from the user to extraction with minimum friction.

**Elements (top to bottom):**
- Large drag-and-drop zone covering the upper half of the page
- "Or click to browse" text inside the drop zone
- Below the drop zone: a counter showing this month's usage (e.g., "47 of 200 extractions used this month")
- Recent uploads list (last 10) with their extraction status indicators
- Each recent item is clickable, taking you to its review page

**Behavior:**
- Multiple files dropped at once = multiple parallel uploads, each with its own progress indicator
- File too large or wrong type = inline error, no toast
- Successful upload = jump straight to the review screen with a loading state
- If user navigates away during extraction, the document still completes in the background

**Explicitly not in v1:**
- Camera capture from desktop (defer to mobile-first v2)
- Email-in-an-attachment (high-value but defer)
- Folder watch / auto-import (v2 enterprise)

### 4.2 Review screen (the screen that determines product quality perception)

**Purpose:** Show the customer what was extracted, let them verify and correct, get them to "save" or "export."

**Layout:** Two-pane, side-by-side.

**Left pane:** The original document rendered (PDF page, image), zoomable, with pan controls. Mobile-tablet falls back to a tabbed view (Document / Data).

**Right pane:** Extracted data, in this order:
1. Document type badge + acceptance status (red banner if rejected: "This document appears to be a bank payment order, not an invoice")
2. Document number, date, currency (three small fields)
3. Seller block: name, TIN, party type, address, script badge if non-Mkhedruli
4. Buyer block: same shape
5. Line items table
6. Totals (subtotal, VAT, shipping, discount, grand total)
7. Special flags ("Free of charge waybill", "Reverse VAT", "Contains PII")
8. Extraction notes (collapsible)
9. Confidence indicator at the top right of the right pane (single overall %)

**Field-level interaction:**
- Every field is click-to-edit
- Fields with confidence < 0.8 are highlighted yellow
- Fields with confidence < 0.6 are highlighted red and a tooltip suggests review
- When user edits a field, the new value is saved to `extraction_corrections` immediately
- A small "✓ Verified" badge appears next to each field the user has explicitly confirmed (one click)

**Bottom of right pane:**
- Big "Save" button (saves verification state, doesn't change data)
- "Export" dropdown (CSV, JSON, XLSX)
- "Re-extract" link (low-emphasis, for when the user genuinely thinks the AI got it wrong)

### 4.3 Documents list / dashboard

**Purpose:** Find a past document quickly.

**Elements:**
- Search box (searches across document_number, seller name, buyer name)
- Filter chips: Date range, Document type, Acceptance status, Has corrections
- Table: thumbnail, filename, document number, date, seller, grand total, status, uploaded date
- Pagination at 50 per page
- Bulk actions: Export selected as CSV, Delete selected

**Sort:** Newest first by default.

**Why this matters:** Accountants reference past invoices constantly. A slow or hard-to-search dashboard kills the product's daily usability.

### 4.4 Settings

**Purpose:** Account, organization, language, billing.

**Sections:**
- Profile (name, email, password, language toggle KA/EN)
- Organization (name, TIN, members list with invite)
- Billing (current plan, usage, upgrade button → Stripe portal)
- Data & privacy (delete account, export all data, retention period)
- API access (v2, hide for v1)

Boring screen. Build last, don't overthink.

### 4.5 Marketing landing page

**Purpose:** Convert a Georgian accountant who clicks the link to a signup.

**Sections (top to bottom):**
1. Headline in Georgian: clear value statement (e.g., *"ფაქტურების ავტომატური მკითხველი ქართველი ბუღალტრებისთვის"*)
2. Subheadline in English for international visitors
3. 30-second demo video or animated GIF showing upload → extracted data
4. Three benefits with icons (accuracy, speed, time saved)
5. Pricing table (3 tiers from charter)
6. Trusted-by / testimonials (empty for closed beta; fill from beta customers)
7. FAQ (5-7 questions; in both languages)
8. CTA to sign up

**Language default:** Georgian. English toggle in nav bar.

---

## 5. Eval harness design

This is the engineering process for keeping extraction accuracy from regressing as you change the prompt. Without it, you'll silently break the product.

### 5.1 What the eval harness does

For each `eval_documents` row:
1. Run the current extraction prompt against the file
2. Compare the AI's output to the `canonical_truth`
3. Score field-by-field (not just overall)
4. Surface mismatches in a readable diff
5. Save the result as an `eval_runs` row

### 5.2 Scoring rules (improved from your week 1 harness)

The week 1 harness was too strict. v1 scoring uses three tiers per field:

**Strict-match fields** (90% weight):
- `accepted`, `document_type`, `is_vat_invoice`, `is_free_of_charge`, `is_reverse_vat`
- `document_number` (after normalizing # prefix and whitespace)
- `document_date`, `document_currency`
- `seller.tin`, `buyer.tin` (must match exactly after whitespace strip)
- `seller.tin_label_present`, `buyer.tin_label_present`
- All `Money` amounts (compared as Decimal with full precision)
- `items[*].quantity`, `items[*].unit_price.amount`, `items[*].total.amount`

**Semantic-match fields** (medium weight):
- `seller.name`, `buyer.name` — exact match OR known-equivalent (transliteration-aware)
- `items[*].description` — exact OR fuzzy match (Jaccard > 0.85 on token set)
- `seller.address`, `buyer.address` — fuzzy match

**Free-text fields** (low weight, topic-coverage scoring):
- `extraction_notes` — score by topic coverage, not exact match
- `vat_treatment_reason` — same
- `rejection_reason` — must capture the same core reason but wording flexible

**Overall accuracy** = weighted average across all field types. Display both per-field and overall numbers.

### 5.3 When the eval runs

- **On every prompt change** (manual or CI trigger)
- **Daily** on the latest production prompt (catches model drift)
- **On every PR** that touches the extraction code
- **Threshold gate:** if accuracy drops more than 2% vs the last green run, the PR is blocked

### 5.4 Eval set growth strategy

Start with the 8 documents. Grow to 30 by end of Phase 5. Grow continuously after launch by:

- Adding every customer-corrected extraction (after re-labeling)
- Adding every new document type that fails
- Adding hard cases proactively when noticed (low-quality scans, edge currencies, mixed scripts)

**Goal:** 100 labeled documents by week 12. Diverse, real, representative.

---

## 6. Security and privacy

Brief but committed. Tax data is sensitive; PII is sensitive; this section can't be hand-waved.

### 6.1 Credential storage

- **User passwords:** argon2id with sensible parameters; never stored plaintext, never logged
- **JWTs:** signed with rotating keys; 1-hour access tokens, 30-day refresh tokens
- **Stripe customer IDs:** stored in DB; secret keys in Railway environment, never in repo
- **Anthropic API key:** Railway environment only; backend service only; never exposed to frontend

### 6.2 Data handling

- **Uploaded files:** encrypted at rest in R2 (R2's default)
- **PII fields:** when `contains_pii_beyond_parties = true`, line item descriptions are masked in logs (regex-replace patient-name-like strings)
- **Logs:** structured JSON; never include full canonical_data, never include file contents; field corrections logged with `field_path` only, not values
- **File retention:** 30 days default; user can opt-out (delete on extraction completion) or extend (paid tier)
- **Right to delete:** account deletion hard-deletes all rows and R2 files within 7 days

### 6.3 Transport security

- HTTPS only; HSTS enforced
- Backend `/docs` endpoint protected behind admin auth
- CORS allows only the Next.js frontend's domain in production

### 6.4 Audit logging

- Every extraction logged with: doc_id, user_id, org_id, prompt_version, model_version, success/fail, duration
- Every authentication event logged: login, logout, password change, plan change
- Every billing event logged from Stripe webhooks
- 1-year retention on audit logs

### 6.5 What we are deliberately not building in v1

**No SOC 2 prep.** Premature for closed beta. Plan for it before enterprise tier.

**No customer-managed encryption keys.** Standard R2 encryption is fine.

**No two-factor authentication.** Add after first paying customer asks. Email + strong password is acceptable for closed beta.

**No GDPR Data Processing Agreement template.** Plain privacy policy is sufficient until you have an EU customer who specifically asks.

---

## 7. What's intentionally underspecified

Three things this document doesn't decide, on purpose:

**The Postgres connection pool size, Celery worker count, etc.** These are operational tuning concerns, set per-environment in Phase 4. Defaults from FastAPI / Celery docs are fine for closed beta load.

**Exact wireframe pixel layouts.** Real frontend work in Phase 4 will iterate. The prose in section 4 commits to *what each screen does*, not how it looks.

**Detailed error code taxonomy.** Specific error codes get defined as Phase 4 implementation surfaces real failure modes. Section 3.1 commits to the *shape* of errors; specific codes are emergent.

---

## 8. Definition of done — Phase 3

Phase 3 is complete when:

- [x] System architecture committed (section 1)
- [x] Database schema written (section 2)
- [x] API endpoints enumerated (section 3)
- [x] Five critical screens described (section 4)
- [x] Eval harness scoring rules committed (section 5)
- [x] Security and privacy posture committed (section 6)
- [x] Tradeoffs named openly (every section)
- [x] Empirical foundation acknowledged (8 labels + ad-hoc Streamlit)

**Phase 3: COMPLETE. Entering Phase 4 (Implementation).**

---

## 9. What changes in Phase 4

Phase 4 is implementation. The disciplines that matter most:

1. **Build the eval harness first**, before any user-facing code. Without it, accuracy regresses invisibly.
2. **Build the upload + review flow second.** That's the demo path; that's what gets shown to customers.
3. **Build auth + billing third.** Necessary for paying customers but not for closed beta.
4. **Build dashboard + settings last.** Boring but necessary.

This order means at week 6 you have a usable closed beta even if you've slipped on the polish.

---

## Appendix — Stack summary in one screen

| Layer | Technology | Hosted on |
|---|---|---|
| Frontend | Next.js 15+, TypeScript, Tailwind CSS, shadcn/ui | Vercel |
| Auth | NextAuth.js (email + password initially) | Vercel |
| Backend | FastAPI, Python 3.12, Pydantic v2 | Railway |
| Background jobs | Celery + Redis | Railway |
| Database | Postgres 16 | Railway |
| File storage | Cloudflare R2 (S3-compatible) | Cloudflare |
| AI extraction | Claude Sonnet 4.6 (vision) | Anthropic API |
| Billing | Stripe (USD) + manual bank transfer (GEL) | Stripe |
| Email | Resend (transactional) | Resend |
| Monitoring | Sentry (errors), Plausible (analytics) | Sentry, self-host |
| CI/CD | GitHub Actions | GitHub |

**Total monthly cost at zero customers:** ~$15
**Total monthly cost at 10 paying customers:** ~$50
**Total monthly cost at 100 paying customers:** ~$300 (mostly Claude API)

This stack is deliberately boring. None of it is going to surprise you in week 8.
