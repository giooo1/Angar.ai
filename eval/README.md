# Angar.ai eval harness

Standalone CLI tool that measures Georgian invoice-extraction accuracy by
running the current prompt against 18 hand-labeled documents and comparing
output to ground truth.

Builds on Phase 3 design doc §5 (`project foundation/angar-ai-phase3-v1.0.md`).
Must pass before any prompt change merges to `main`.

## Setup (one time)

Run from the repo root (where the project's `pyproject.toml` lives):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Set your Anthropic API key (in a `.env` file at the repo root, or as an env var):

```
ANTHROPIC_API_KEY=sk-ant-...
```

Paste your week-1 system prompt into `eval/prompts/v0.md` (replace the
placeholder HTML comment with the prompt body — see the file).

## Run

```powershell
# full run on all 18 docs, Sonnet 4.6 + v0 prompt, prompt caching on
python -m eval.harness

# single document for fast iteration
python -m eval.harness --doc invoice_001

# cheap dev iteration with Haiku
python -m eval.harness --model claude-haiku-4-5-20251001

# regression-gate against a prior baseline run
python -m eval.harness --compare-to eval/runs/<prev>.json --gate 0.02
```

## What it does

For each `(pdf, label.md)` pair in `project foundation/`:
1. Send PDF + system prompt to Claude vision (prompt-cached after doc 1)
2. Parse response → `CanonicalInvoice`
3. Compare field-by-field to the labeled ground truth per Phase 3 §5.2:
   - **Strict** fields (90% weight): TINs, dates, Money amounts, flags
   - **Semantic** fields (60% weight): names, descriptions, addresses
     (exact OR fuzzy with Jaccard ≥ 0.85)
   - **Free-text** fields (30% weight): extraction_notes, vat_treatment_reason
     (topic coverage on key tokens)
4. Print a rich console table + write `eval/runs/<timestamp>__<prompt>__<model>.json`

## Cost

A full Sonnet 4.6 run on 18 docs with caching: roughly **$0.40–$0.60**.
Haiku 4.5: roughly **$0.10**.

## Current baseline

The committed baseline prompt is `eval/prompts/v1.md` (schema-embedded
descendant of the week-1 `v0.md`).

| Metric | Value |
|---|---|
| Run date | 2026-05-21 |
| Model | `claude-sonnet-4-6` |
| Prompt | `v1` |
| Overall accuracy | **87.34%** (mean of per-doc weighted_accuracy across 18 docs) |
| Parse failures | 0 / 18 |
| Total cost (approx) | ~$0.55 |
| Cache hit rate | system prompt cached on docs 2–18 (56,508 cache reads / 56,275 input) |
| Best doc | `invoice_004` at 93.8% |
| Worst doc | `Waybill_List1` at 77.1% |
| Run JSON filename | `2026-05-21T09-01-57.644994+00-00__v1__claude-sonnet-4-6.json` (local under `eval/runs/`) |

To `--compare-to` against this baseline, use the run JSON filename above
on your machine. The baseline file itself is gitignored — runs regenerate
on each invocation.

Top recurring failure patterns on this baseline (for the next prompt
iteration to address):

1. `document_number` whitespace: model returns `'ელ- 0976696987'` with a
   space after the prefix; labels have `'ელ-0976696987'`. Either fix in
   the prompt or relax the comparator's normalization.
2. `vat_treatment_overall` on waybills marked as VAT payers without a
   VAT breakdown column: model returns `'inclusive'`; Phase 3 spec calls
   for the conservative `'unknown'` default.
3. `subtotal_total` and `shipping_cost` left null on free-of-charge
   waybills where labels have explicit zeros (`{"amount": "0",
   "currency": "GEL"}` — per the "preserve explicit zeros" spec rule).
4. `contains_pii_beyond_parties` over-reported (model conservative, label
   reserves it for line-item PII specifically).
5. Product `(ref ...)` fragments split into `sku`/`item_code` on
   DRESSUP-style invoices instead of kept in `description`.

## What this harness does NOT do

- It doesn't touch a database. Results live in `eval/runs/` as JSON files.
- It doesn't run in CI yet (no extraction code in the repo to gate on).
- It doesn't grow the eval set. Add docs by hand-labeling into
  `project foundation/labels/` + dropping the PDF in `project foundation/pdfs/`.
- It doesn't edit the prompt for you — that's the whole point of having
  a measurement layer that surfaces regressions.
