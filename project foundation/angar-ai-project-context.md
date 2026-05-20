# Angar.ai — Project Context

**Purpose of this document:** Load a new chat session (or future-you after a break) into the Angar.ai project in 5 minutes. Paste this at the start of any new conversation about the project before asking for help.

**Last updated:** End of week 1 (May 2026)
**Current phase:** Phase 3 (Design) — entered with closed-beta validation pending in Phase 6

---

## The project in three sentences

I'm building **Angar.ai**, an AI-powered tool that extracts data from Georgian invoices, waybills, and tax documents with near-perfect accuracy. The target customer is Georgian accountants and bookkeepers who currently retype invoice data into Oris (the dominant local accounting software) and RS.ge (the Revenue Service tax portal). My single guiding principle is *"excellent invoice extraction is the product — everything else is downstream."*

## Who I am, what stage I'm at

- Solo founder, working on this project ~22 hours/week over 12 weeks
- Based in Georgia, Georgian-speaking
- Building in public for accountability
- Currently end of week 1; success metric is 10 paying customers + 95% extraction accuracy by week 12
- Budget: ~$250 total to launch (Anthropic API ~$80/month, hosting $10/month, domain, etc.)

---

## What's verified and working

These are facts, not assumptions. Treat as ground truth.

### Technical foundation
- **RS.ge SOAP API integration is verified working end-to-end.** 56 operations discovered, write capability confirmed via real `save_waybill` call on test environment. Five undocumented validation quirks documented (driver TIN required, plate format AANNNAA, CHEK_DRIVER_TIN semantics, UN_ID resolution, service-user-vs-account-user auth model).
- **Test credentials in use:** service user `giooo114:206322102` (note: `<user>:<TIN>` format is required, not just `<user>`)
- **Test entity TIN:** 206322102 → UN_ID 731937
- **Oris has two integration paths:** REST/JSON API (requires $2,840 paid module per customer) and Excel template import (universal but customer-customizable). API doc has 357 pages; Excel template has 18 columns. Neither integration is built yet.
- **Claude vision extraction is working at ~96% real accuracy** on 8 hand-labeled Georgian documents (90.65% on strict scoring; ~96% after correcting for label-style disagreements that don't reflect extraction failures).

### Real extraction failures still to fix
Only three genuine extraction bugs remain on the eval set:
1. Latin-transliterated Georgian gets silently converted to Mkhedruli (loses source fidelity)
2. Georgian IBANs occasionally miss a character (should be 22 chars exact)
3. `references_other_document` field gets populated from non-invoice references (e.g., order codes)

Fix: three targeted prompt rules. Not yet applied.

---

## What I've decided, and why

These are commitments. Don't relitigate without strong reason.

### Product scope (v1)
- **In:** PDF/JPG/PNG/HEIC upload, AI extraction of standard Georgian invoice fields, side-by-side review UI, CSV/JSON export, bilingual KA+EN UI, Stripe (USD) + manual GEL bank transfer billing
- **Out:** Direct RS.ge automation (capability ready but held back from v1 pricing), Oris API integration, Oris Excel template flexibility, mobile app, languages beyond GE/EN, other countries
- **Built but not exposed:** RS.ge integration with five quirks handled — activate as "Pro tier" when first customer requests

### Pricing direction (not committed)
Three tiers seem likely based on Oris API access reality:
- Tier 1 (~60% of market): Solo accountants with no Oris API → ₾49/month, RS.ge + CSV/Excel export
- Tier 2 (~30% of market): Mid-size firms with Oris API module → ₾199-299/month, full automation
- Tier 3 (~10% of market): Large firms/agencies → ₾499+/month or annual

### Schema model
Single canonical Pydantic schema (`canonical.py` v0.2), separate adapters per downstream system. Seller/buyer field names kept (per Option 1 decision) — stays close to RS.ge/Oris conventions, relies on null for documents that don't fit. Adapters drop fields, never add.

### Customer discovery status
**Honest state:** fewer than 5 interviews completed. Acting on directional signal:
- RS.ge automation is *not* the top customer priority (less than initially hypothesized)
- Oris integration is what customers want, but they can't articulate the form
- What they consistently say: "smooth as butter," "close to 100% accuracy," "easy to use," "priced right"
- Full 5 interviews deferred to Phase 6 closed beta

### Tech stack
- **Backend:** Python, FastAPI, Pydantic, Postgres
- **Frontend:** Next.js (TBD; possibly Streamlit for early demos)
- **AI:** Claude vision via Anthropic API (default Sonnet 4.6 for cost; Opus 4.7 only if accuracy plateaus)
- **Hosting:** Railway (backend + Postgres) + Vercel (frontend) or similar
- **Auth:** Email + password; org-level multi-user
- **Payments:** Stripe (international USD); manual bank transfer for early Georgian customers; BOG Pay added later

---

## What's still genuinely uncertain

Don't treat these as decided. They need real customer signal to resolve.

- Will accountants actually use this daily, or abandon it after a week?
- Is ₾49/month the right entry price? Too low devalues; too high blocks adoption
- Which downstream export do real customers want first: CSV, Oris Excel, Oris API, or RS.ge automation?
- Is 95% accuracy genuinely "good enough" in real customer hands, or does that bar need to be higher?
- Does the bilingual UI work for both audiences, or do Georgian and English customers want fundamentally different products?
- What's the actual retention curve at the ₾49 vs ₾299 price points?

---

## How I work, and how I want help

### My working style
- I hold signals rather than acting immediately on every new piece of information
- I prefer disciplined critique over enthusiastic agreement
- I want honest pushback when I'm wrong, including on emotional/avoidance topics
- I avoid scope creep; new discoveries go to a backlog, not into the current sprint
- I value finishing what's in front of me over starting new things

### What I want from an AI assistant
- Be specific and concrete. Vague advice wastes time.
- Push back when I'm chasing the wrong thing, including when "the wrong thing" is comfortable
- Don't overload me with options when a recommendation would be more useful
- Distinguish "I know this" from "I'm assuming this"
- When I say "you decide," gently insist that I decide — the project is mine
- Use Georgian (Mkhedruli) when writing customer-facing copy; otherwise English is fine
- Long, structured documents are welcome; bullet-point spam is not

### What I want you to *not* do
- Don't write code that calls real APIs without flagging cost
- Don't add features to v1 scope without explicit ask
- Don't suggest pivots without naming the tradeoff explicitly
- Don't tell me to "talk to customers more" if I've already said I will — just help me do it
- Don't congratulate me before delivering useful work

---

## Key documents in the project

If I'm referencing one of these and you haven't seen it, ask:

| Document | What it contains | Status |
|---|---|---|
| `angar-ai-project-charter-v1.3.md` | Problem, target user, scope, risks, success metric | Current |
| `angar-ai-phase2-v1.0.md` | Requirements from customer discovery — honest about partial completion | Current |
| `angar-ai-extraction-agent-spec.md` | What the AI does, accuracy targets, Georgian rules, anti-goals | v1.0 |
| `canonical.py` | Pydantic schema for extracted data | v0.2 (after 8-doc labeling) |
| `adapters.py` | Sketch of RS.ge XML, RS.ge invoice, Oris JSON, Oris Excel adapters | v0.1 (not yet updated for canonical v0.2) |
| `test_rsge_api.py` | RS.ge API smoke test (read operations) | Working |
| `test_save_waybill.py` | RS.ge write test (creates real waybill) | Working |
| `labeling/label_*.md` | 8 hand-labeled Georgian documents = eval ground truth | Complete |
| `outputs/*.json` | First extraction run results — 90.65% strict / ~96% real accuracy | Current |
| `weak_docs_error_analysis.md` | Diagnosis of remaining errors by bucket | Current |

---

## Current state and next milestone

**Where I am:** End of week 1. Charter v1.3 committed. Schema v0.2 working. RS.ge integration verified. First eval run complete with ~96% real accuracy. Streamlit demo working on my machine. Have not yet shown anything to a real customer.

**Next milestone:** Show the demo to one real Georgian accountant, watch them use it on their own invoices, and update the charter to v1.4 based on what I learn. This is more important than further prompt tuning, schema refinement, or any other engineering work.

**Active risks I'm watching:**
1. **Burnout:** 7 days of intense work, sustainable pace requires discipline now
2. **Customer-discovery procrastination:** Building is comfortable; talking to customers is not
3. **Prompt over-engineering:** Adding rules for hypothetical documents instead of waiting for real failures
4. **Scope creep from new discoveries:** Oris API, Excel template flexibility, Latin transliteration — all real but none in v1

---

## How to use this document

When starting a new chat session about Angar.ai:

1. Paste this document at the top
2. State what's changed since this document was last updated
3. State your specific question or what you want help with
4. Reference specific files by name when discussing them

When *I* haven't updated this document in over a week, it's stale. Ask me to update it before doing significant work, because outdated context produces wrong advice.

---

## A reflection that should outlive any individual session

The Angar.ai project's biggest asset is not the code or the schema or the API access. It's **the discipline of holding signals without immediately acting on them.** Every time a new discovery has appeared (Facebook message, Oris API doc, Oris Excel template flexibility, real labeled documents, ~96% accuracy), the right response has been to note it and continue the current sprint — not to pivot.

That discipline is what makes a solo 12-week project finishable. Lose it, and the project becomes a notebook of half-built ideas instead of a shipped product.

When in doubt, ask: **"does this directly advance extraction quality, customer acquisition, or paid retention?"** If not, defer.
