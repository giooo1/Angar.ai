# Angar.ai — Phase 2: Requirements Analysis (Partial Completion Report)

**Version:** 1.0
**Status:** Partially complete — sufficient signal to enter Phase 3, with ongoing discovery committed in Phase 6 (beta)
**Author's note:** This document is deliberately honest about the limits of the evidence gathered. Phase 2 was cut short to accelerate technical execution, with the explicit understanding that more customer validation is required during the closed beta.

---

## 1. Phase 2 goal and what was actually done

### Original goal
Validate the product hypothesis through 5 customer interviews, collect 30 labeled invoices for the eval harness, and produce a requirements specification grounded in real customer language.

### What was actually accomplished
- A smaller number of accountant conversations than the original target of 5
- One particularly high-signal unprompted message from a Georgian accountant referencing Oris
- Strong directional signal on product priorities (see section 3)
- Limited collection of labeled invoice samples — to be completed during Phase 5 (Testing)

### What was deferred
- Reaching the full 5-interview target → committed for completion during closed beta (Phase 6, weeks 8–11)
- Building the 30-invoice ground-truth dataset → starts immediately in Phase 3, runs in parallel with build
- Detailed quantitative validation of pricing tiers → reserved for closed beta

### Why we're proceeding to Phase 3 now
The original 5-interview target was a heuristic, not a magic number. The signal received so far is consistent and directionally clear enough to make Phase 3 design decisions. The cost of waiting for 4 more interviews (estimated 2–3 weeks) exceeds the cost of being wrong about the directional signal and pivoting later. The closed beta is the real validation mechanism.

This is an explicit, named tradeoff. It is also a risk — see Risk 2 in the charter.

## 2. Key findings from customer discovery

### Finding 1: RS.ge automation is less important to customers than initially hypothesized
**Strength of evidence:** Directional, not strong

In the conversations conducted, accountants did not describe RS.ge data entry as their primary daily pain. They are familiar with RS.ge, file VAT regularly, and have established habits for it. The friction is real but acceptable.

**Implication for product:** RS.ge automation moves from "core v1 feature" to "verified capability held in reserve." The technical integration is built (see Phase 1 Appendix A) but not exposed in v1 pricing or marketing.

### Finding 2: Oris is where their daily attention lives
**Strength of evidence:** Strong directional signal from one unprompted conversation, consistent with general market knowledge

Oris is the dominant Georgian accounting software. The accountants spoken to use it daily. Data entry into Oris — line by line, by hand, from PDFs — is a clear and frequent pain.

**Implication for product:** Some form of Oris-compatible output (Excel template, CSV, or direct API) will eventually be a feature. Form depends on subsequent customer signal during beta.

### Finding 3: Oris integration is not as easy as it first appeared
**Strength of evidence:** Documented technical investigation

- Oris is on-premises software — each accountant runs their own SQL Server instance, often locally
- The JSON API requires a $2,840 add-on module that most small firms have not purchased
- Excel templates can be modified by users — column names, ordering, custom fields — so a single rigid exporter would fail in practice
- No public test environment exists

**Implication for product:** Oris integration is a non-trivial engineering project that should not be promised in v1. It is buildable as a v1.5 or v2 feature based on what paying customers ask for.

### Finding 4: What customers consistently want is invisible quality
**Strength of evidence:** Directional, but consistent across the interviews conducted

Customer language emphasizes:
- "Smooth as butter" — friction-free user experience
- "Close to 100% accuracy" — extraction trustworthiness above all
- "Easy to use" — minimal cognitive load
- "Priced right" — affordable for individual bookkeepers, scaled for firms

These are non-feature requirements. They translate to *quality bars*, not items on a feature list.

**Implication for product:** The success of v1 will be judged on extraction accuracy and UX polish, not on the count of features. This is reflected in the Phase 1 success metric (95% accuracy bar) and the product principle ("excellent invoice extraction is the product").

## 3. Functional requirements (prioritized by customer signal)

### Tier 1 — Must work perfectly in v1

**FR-1 Extraction quality**
- AI extracts all standard fields from Georgian invoices: vendor/buyer TIN, names, addresses, invoice number, date, currency, line items, VAT amounts, totals
- Field-level accuracy ≥ 95% on the eval set for critical fields (TIN, VAT amount, total amount, date)
- Confidence score per extracted field, exposed to users
- Handles Georgian script (Mkhedruli) at production quality
- Handles multi-currency (GEL, USD, EUR) and reverse VAT (Article 161)

**FR-2 Upload experience**
- Accepts PDF, JPG, PNG, HEIC up to 10MB
- Single and bulk upload (up to 100 files)
- Per-file progress indication
- Extraction completes in under 10 seconds per single-page invoice

**FR-3 Review and edit**
- Side-by-side view: original document next to extracted data
- Click any field to edit
- Save corrections; corrections feed into the prompt improvement loop

**FR-4 Export**
- Universal CSV export with all canonical fields
- JSON export via API for developer customers
- Excel export in a generic, well-documented format

**FR-5 Bilingual UI**
- Full Georgian translation (KA), reviewed by a native speaker
- English translation (EN) as default for international users
- User toggle in settings

**FR-6 Account and billing**
- Email + password auth
- Organizations with multiple users
- Per-month extraction limits enforced
- Stripe (USD) for international payment
- Manual bank transfer (GEL) accepted in early stage; BOG Pay added when justified

### Tier 2 — Built but held in reserve

**FR-7 RS.ge automation (capability ready, not in v1 pricing)**
- Full `save_waybill` integration via SOAP API
- Triggered only for customers on a Pro+ tier when activated
- Onboarding flow for service user credentials (deferred to when activated)

### Tier 3 — Backlog (build when paying customers request)

**FR-8 Direct Oris Excel template export**
- Customer uploads their own Oris template once
- UI for column mapping (their column → canonical field)
- Saved profile per customer; future extractions auto-fill their template

**FR-9 Direct Oris JSON API integration**
- For customers with the Oris API module purchased
- One-click push from extraction result to Oris `AcceptOperation`

**FR-10 Direct RS.ge invoice (save_invoice)**
- For customers who want VAT invoice automation, not just waybills
- Includes the full invoice lifecycle: create, send, confirm, link to declaration

## 4. Non-functional requirements

| Category | Requirement | Notes |
|---|---|---|
| Performance | Single invoice extraction < 10s; bulk of 100 < 5 minutes | Critical for "smooth as butter" perception |
| Availability | 99% uptime measured monthly | Acceptable for a small early-stage tool |
| Accuracy | ≥ 95% on critical fields, ≥ 90% on all fields | The single most important non-feature requirement |
| Security | TLS in transit; encrypted-at-rest in Postgres; credentials never logged | Prerequisite for handling tax data |
| Privacy | Original files deleted within 24h of extraction unless user opts in | GDPR consideration |
| Localization | Native-reviewed Georgian + English UI | Affects all customer-facing surfaces |
| Browser support | Latest 2 versions of Chrome, Firefox, Safari, Edge | |

## 5. Three user stories that drive v1

### US-1 — The accountant who needs to trust the data
**As a** Georgian accountant managing multiple SME clients,
**I want to** upload a stack of invoices and see extracted data so accurate I rarely need to correct it,
**so that** I can use this tool daily without losing trust in it after the first wrong number.

**Acceptance criteria:**
- Can upload 50+ invoices in one session
- Accuracy on critical fields is high enough that I correct fewer than 1 in 20 extractions
- When I do correct something, the correction is saved and visible
- The interface doesn't get in my way

### US-2 — The bookkeeper who wants their time back
**As a** bookkeeper who currently spends 4 hours a week retyping invoice data,
**I want to** drop in a PDF and download a clean CSV in seconds,
**so that** I can spend that time on higher-value work or simply on more clients.

**Acceptance criteria:**
- The drag-and-drop interface is obvious; no training needed
- Extraction completes within the time it takes to make tea
- CSV opens cleanly in Excel with no character encoding issues
- Georgian text appears correctly in all fields

### US-3 — The international founder
**As a** foreign founder with a Georgian LLC,
**I want to** extract Georgian-invoice data into a format my international accountant can read,
**so that** I'm not the bottleneck between Georgian paperwork and global accounting software.

**Acceptance criteria:**
- Sign up and pay in USD via Stripe
- UI defaults to English
- Export produces clean CSV/JSON; currency conversion shown but not silently applied
- Georgian text appears as Georgian (no transliteration)

## 6. What we still need to learn

This section is the honest companion to Phase 1's "Assumed" and "Not yet known" sections. The closed beta in Phase 6 must answer:

1. **Will accountants actually use this daily, or abandon it after a week?** The strongest validation is retention, not initial enthusiasm.

2. **Is ₾49/month the right entry price?** Too low and people don't value it. Too high and price becomes the objection. Test by varying.

3. **Which downstream export does the first paying customer actually need?** Universal CSV, Oris-shaped Excel, Oris API, or RS.ge automation. The answer will determine v1.5 priorities.

4. **Is accuracy good enough?** The 95% target is the bar. Whether real customers experience it as "good enough" is a separate empirical question.

5. **Does the bilingual UI work for both audiences?** Native Georgian speakers and English-speaking expats have different aesthetic expectations.

6. **What's the actual churn rate?** Until at least 10 paying customers have stayed (or churned) over 30+ days, every prediction about retention is a guess.

## 7. Definition of done — Phase 2

Phase 2 has a hybrid completion model:

- [x] Sufficient directional signal to make Phase 3 design decisions
- [x] Product principle defined and committed to
- [x] Functional and non-functional requirements written
- [x] Three primary user stories drafted
- [x] Risks documented and acknowledged
- [ ] Five completed accountant interviews — **deferred to Phase 6 closed beta**
- [ ] Thirty labeled invoice samples — **deferred to Phase 3/5 (built in parallel with eval harness)**

**Phase 2: Partially complete. Sufficient to enter Phase 3.**
**Remaining items move to Phase 5–6 as named follow-ups, not as silent gaps.**

---

## Appendix — Customer language captured

Direct quotes (paraphrased; preserve exact wording when available):

- "It would be interesting if Oris received this kind of information automatically"
- "Smooth as butter"
- "Close to 100% accuracy"
- "Easy to use"
- "Priced right"

These phrases — particularly "smooth as butter" and "close to 100% accuracy" — should be considered when writing landing page copy in Phase 6.
