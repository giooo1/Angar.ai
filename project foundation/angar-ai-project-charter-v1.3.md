# Angar.ai — Project Charter

**Version:** 1.3
**Last updated:** May 2026
**Status:** Active — entering Phase 3 (Design)

---

## Version history

| Version | Date | Key changes |
|---------|------|-------------|
| 1.0 | Week 1 | Initial charter — RS.ge automation focus |
| 1.1 | Week 1 | RS.ge API verified working; risk #1 downgraded |
| 1.2 | Week 1 | Two-tier auth model discovered; onboarding UX flagged as critical |
| 1.3 | Week 1 | **Product refocused on extraction quality after limited customer signal indicated RS.ge automation is not the primary pain point** |

---

## 1. Problem statement

Georgian accountants and bookkeepers spend hours each week manually transcribing data from supplier invoices — PDFs, scanned images, paper receipts, email attachments — into their accounting software. The dominant accounting software in Georgia is Oris, an on-premises desktop application used by most local firms. Invoices arrive in many formats, often in Georgian script (Mkhedruli), with details that require human judgment to extract correctly: vendor identification, line items, VAT amounts, dates, currencies.

No existing tool extracts this data with both high accuracy and Georgian-language understanding. International tools (Parseur, Rossum, Docparser) don't handle Georgian script reliably and don't know Georgian invoice conventions. Local accounting software requires manual data entry. The result is hundreds of hours of skilled labor per month, across the country, spent on a task that AI can now do well.

## 2. Target user

**Primary:** Georgian accountants and bookkeepers, both in-house and at small accounting firms (2–20 staff), serving SMEs in Tbilisi, Batumi, and Kutaisi. Typically Georgian-speaking, mid-career, deeply familiar with the daily rhythm of invoice processing. Already use Oris.

**Secondary:** International founders running Georgian LLCs who need a bridge between their international accounting workflows (Xero, QuickBooks) and Georgian document conventions.

**Not the target user:** Large enterprises with custom ERPs, micro-businesses below the VAT threshold, individuals filing personal taxes.

## 3. Product principle (the one thing that matters)

> **Excellent invoice extraction is the product. Everything else is downstream.**

If we extract Georgian invoice data with near-perfect accuracy, every downstream use case becomes feasible: CSV export for manual import, Excel templates for Oris, JSON for developers, direct API calls to RS.ge for the customers who want them. If extraction is mediocre, no amount of downstream integration matters.

This principle is the result of early customer signal indicating that:
- Accountants do not prioritize RS.ge automation as much as initially assumed
- Oris is where their daily attention lives, but Oris integration is significantly harder than expected (on-premises software, expensive API module, customizable Excel templates)
- What customers consistently say they want is **invisible quality**: fast, accurate, easy, fairly priced

Acting on this signal: the product focuses on extraction quality first; downstream integrations follow based on what paying customers ask for.

## 4. Success metric (the single number that matters)

By the end of week 12: **10 paying customers contributing at least ₾500 (~$185) in monthly recurring revenue, with extraction accuracy of 95% or higher on a 30-invoice held-out test set.**

Extraction accuracy is the binding constraint, not customer count. A product with 10 customers and 80% accuracy is not viable. A product with 5 customers and 98% accuracy is on the right trajectory.

## 5. Scope boundary

### In scope for v1

- PDF, JPG, PNG, HEIC invoice upload (single and bulk)
- AI-powered extraction of standard Georgian invoice fields:
  - Vendor and buyer TIN, name, address
  - Invoice number, date, currency
  - Line items: description, quantity, unit, unit price, subtotal, VAT, total
  - VAT treatment (standard, zero-rated, exempt, reverse charge)
  - Transport details when present (for waybills)
- Multi-currency support (GEL, USD, EUR)
- Georgian script (Mkhedruli) handling at production-quality accuracy
- Confidence scoring per field
- Side-by-side review UI: original document vs. extracted data, with edit capability
- Universal CSV export
- Bilingual UI (Georgian and English)
- Stripe (USD) and Bank of Georgia or Payme.ge (GEL) billing
- Eval harness with 30+ labeled invoices, run automatically on every prompt change

### Explicitly out of scope for v1, by category

**Downstream integrations** — defer until paying customers request specific ones:
- Direct RS.ge `save_waybill` automation (verified working as a capability — held in reserve)
- Direct RS.ge `save_invoice` automation
- Direct Oris API integration (`AcceptOperation`)
- Direct Xero or QuickBooks posting

**Why deferred:** Customer signal so far does not support these as launch features. They are buildable on top of the canonical extraction layer when needed, but each carries onboarding friction (credentials, permissions, customer-side setup) and pricing complexity. Better to launch on extraction quality and add integrations as upsells.

**Oris-specific Excel templates** — defer until at least 3 paying customers ask:
- User-uploaded template column mapping
- Saved template profiles per customer
- Excel generation matching customer's specific Oris format

**Out of scope entirely for v1:**
- Mobile app (responsive web is enough)
- Bank reconciliation, payments processing
- Other document types: contracts, payroll, customs declarations
- Languages other than Georgian and English
- Other countries (Armenia, Azerbaijan are explicitly v2)
- White-label / agency multi-tenancy

Scope creep is the single biggest risk to a solo 12-week project. Anything outside the in-scope list above is deferred regardless of customer interest.

## 6. Top 5 risks and mitigations

### Risk 1 — Extraction accuracy is the entire product, and it must be near-perfect
**Likelihood:** Medium · **Impact:** Critical

With the product refocused on extraction quality, anything below 95% accuracy on critical fields (vendor TIN, total amount, VAT amount, date) means customers will not trust the tool. Below 90% means they will not adopt it at all.

*Mitigation:*
- Build the eval harness in week 1 of implementation, before any UI work
- Label 30+ real invoices manually to create ground truth
- Run accuracy benchmarks weekly; track per-field accuracy over time
- Iterate the system prompt with explicit Georgian-specific rules (e.g., "TIN is 9 or 11 digits, VAT rate is always 18% in Georgia, dates use DD.MM.YYYY")
- Use Claude vision for Georgian script (best available for non-Latin scripts)
- If accuracy plateaus below 95% on critical fields, do not launch — pivot to invoice types where accuracy is already high

### Risk 2 — Customer signal is still thin
**Likelihood:** High · **Impact:** High

The product refocus to extraction-first is based on a small number of customer conversations. The plural of anecdote is not data. The risk is that the next 5 accountant interviews reveal a different priority (e.g., that RS.ge automation actually matters a lot to a different customer segment).

*Mitigation:*
- Continue customer interviews in parallel with build work — minimum 1 per week
- Build the closed beta with at least 5 accountants before public launch
- Treat the first 10 paying customers as ongoing research participants — interview each one monthly
- Be willing to pivot the product within v1 scope if Phase 6 beta reveals a different primary need

### Risk 3 — Solo founder burnout before week 12
**Likelihood:** High · **Impact:** Critical

The biggest single risk to any solo project. Twelve weeks of consistent work while balancing other commitments is hard. Each "wow, let's pivot" moment from new information (Oris API doc, Oris Excel templates, customer messages) burns energy that should go to execution.

*Mitigation:*
- Two-hour daily minimum, six days a week. One rest day, non-negotiable.
- Public weekly progress posts for accountability.
- A standing rule: new discoveries go into a backlog file, not into the current week's plan.
- If a week passes without a measurable deliverable, stop and re-plan instead of pushing through.

### Risk 4 — Local payment integration is harder than expected
**Likelihood:** Medium · **Impact:** Medium

Stripe alone will lose 30–50% of Georgian customers who only have local debit cards. BOG Pay and Payme.ge integrations are poorly documented and require business registration in Georgia.

*Mitigation:*
- For the closed beta, accept manual bank transfer in GEL — no payment integration needed.
- Build Stripe first for international users and the first paying customers.
- Add BOG Pay only after first 5 paying Georgian customers prove the demand.

### Risk 5 — Georgian-language UI mistakes embarrass the brand
**Likelihood:** Medium · **Impact:** Medium

Machine-translated Georgian reads as foreign. Native speakers will instantly recognize bad translations and assume the entire product is unreliable.

*Mitigation:*
- All Georgian UI copy reviewed by a native speaker before launch.
- Maintain `i18n/ka.json` separately from English for easy review.
- Default the marketing site to English with a Georgian toggle until copy is professionally vetted.

## 7. Resource budget

| Category | Cost | Notes |
|---|---|---|
| Claude API | ~$80/month | Higher than initial estimate due to vision usage |
| Hosting (Railway) | $10/month | Backend + Postgres + Redis |
| Hosting (Vercel) | $0 | Free tier sufficient for v1 |
| Domain (angar.ai) | $80/year | .ai pricing |
| Sentry (errors) | $0 | Free tier |
| Stripe fees | 2.9% + $0.30 per transaction | |
| **Total to launch** | **~$250** | First 12 weeks |

Time: ~265 hours over 12 weeks (22 hours/week average).

## 8. What's verified vs. what's assumed

This section exists because being honest about uncertainty saves weeks later.

### Verified (have evidence)
- ✅ RS.ge SOAP API is reachable and functional (56 operations, write capability confirmed)
- ✅ Two-tier RS.ge authentication model (account creds vs. service user creds)
- ✅ End-to-end `save_waybill` works against the test environment
- ✅ Five RS.ge-specific validation quirks documented in `docs/rsge_quirks.md`
- ✅ Oris has both a JSON API (paid) and an Excel template import (free)
- ✅ Claude vision handles Georgian script with acceptable quality (qualitative impression — needs formal eval)

### Assumed (limited evidence)
- ⚠️ RS.ge automation is not customers' top priority — based on a small number of interviews
- ⚠️ Oris integration is what customers want, but they can't articulate what form it should take
- ⚠️ Extraction quality is the dominant feature in customer minds
- ⚠️ ₾49 / ₾99 / ₾299 pricing tiers will convert — not tested with real customers yet
- ⚠️ Bookkeepers are the right primary customer (vs. individual SME owners)

### Not yet known
- ❓ How many real customers will pay for extraction alone, without immediate Oris/RS.ge automation
- ❓ Whether closed-beta accountants will actually use the product daily or abandon it
- ❓ Whether Oris Excel template flexibility is a must-have or nice-to-have
- ❓ What the actual retention curve looks like at the ₾49 vs ₾299 price points

The "Assumed" and "Not yet known" sections should shrink every week as more evidence comes in. Update this section as part of the weekly review.

## 9. Definition of done — Phase 1

Phase 1 is complete when:
- [x] Project charter written and reviewed
- [x] All five risks have a named mitigation
- [x] The success metric is visible and committed to
- [x] Calendar blocks for the next 4 weeks are protected
- [x] The product principle can be stated in one sentence to anyone

**Phase 1: COMPLETE. Ready to enter Phase 3 (Design) with parallel ongoing customer discovery.**

## 10. One-sentence product description

**For accountants:** "Angar.ai extracts data from your Georgian invoices with near-perfect accuracy, so you stop retyping every receipt."

**For founders:** "Angar.ai turns Georgian invoices into clean structured data your accountant can use anywhere."

**For investors / GITA:** "AI-powered Georgian-language document extraction infrastructure, focused first on the 80,000 VAT-registered businesses in Georgia, with a clear expansion path to the South Caucasus."

---

## Appendix A — Verified RS.ge integration capabilities

The RS.ge integration is built and verified but held back from v1 launch scope (see section 5). Capabilities ready to be activated when paying customers request:

- Read waybills via `get_waybills_v1` (last 3 days max)
- Create waybills via `save_waybill`
- Read/edit/delete waybills via standard CRUD operations
- Read invoice reference data (units, types, error codes)
- 56 total API operations available

This is a real asset, not a wasted week of work. When a customer says "can you push directly to RS.ge?" the answer is "yes, we have the integration ready — that's our Pro tier." Holding capability in reserve is fine; building it on day one and not depending on it for launch is fine.

## Appendix B — Verified Oris integration paths

Documented but not yet tested:

- Oris JSON API (`AcceptOperation`, `SupplyOperation`, `TransactionSetVAT`) — requires customer to have purchased the $2,840 API module
- Oris Excel template import — universally available, but templates are customer-customizable, requiring a column-mapping UI

Both are buildable. Neither is in v1 scope. The decision on which to prioritize will come from paying customers.
