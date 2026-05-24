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

# absolute floor — exits 3 if overall accuracy drops below the threshold
python -m eval.harness --baseline-threshold 0.9
```

## Pre-commit gate

A pre-commit hook (`scripts/eval_gate.py`, configured in
`.pre-commit-config.yaml`) runs the harness automatically when files
that affect extraction accuracy change:

- any `angar_extraction/prompts/v*.md`
- `angar_extraction/extractor.py`
- the `angar_*` lines in `backend/settings.py`

It runs with `--baseline-threshold 0.9` and aborts the commit if the
18-doc baseline drops below 90%. To bypass intentionally (e.g. you're
mid-iteration and the next commit will fix it):

```bash
git commit --no-verify -m "..."
```

Install the hook once after cloning:

```bash
pip install -e ".[dev]"
pre-commit install
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

The committed baseline prompt is `eval/prompts/v3.md` (document-type-scoped
descendant of v2; itself a schema-embedded descendant of the week-1 `v0.md`).

| Metric | Value |
|---|---|
| Run date | 2026-05-21 |
| Model | `claude-sonnet-4-6` |
| Prompt | `v3` |
| Overall accuracy | **91.98%** (mean of per-doc weighted_accuracy across 18 docs) |
| Parse failures | 0 / 18 |
| Total cost (approx) | ~$0.55 per full run |
| Cache hit rate | 119,187 cache reads vs 56,275 input — full reuse on docs 2–18 |
| Docs ≥ 90% | 14 / 18 |
| Docs ≥ 95% | 9 / 18 |
| Best doc | `invoice_001` at 98.5% |
| Worst doc | `invoice_003` (payment-order rejection) at 78.8% |
| Run JSON filename | `2026-05-21T09-...__v3__claude-sonnet-4-6.json` (local under `eval/runs/`) |

### Iteration history

| Prompt | Date | Overall | Parse fails | What changed |
|---|---|---|---|---|
| `v0` | 2026-05-21 | 0.0% | 18/18 | Week-1 prompt; no schema description → model invented its own |
| `v1` | 2026-05-21 | 87.34% | 0/18 | Added explicit schema reference (field names, Money shape, enum values) |
| `v2` | 2026-05-21 | 88.43% | 1/18 | Added waybill VAT-default, explicit-zero, two-code-column rules. Waybills 11/11 ≥93.9% but invoices regressed (waybill rules leaked) |
| `v3` | 2026-05-21 | **91.98%** | 0/18 | Scoped rules by document type; tightened honest-nulls; JSON-escaped ASCII `"` inside Mkhedruli company names |

### Remaining failure patterns (for v4 if pursued)

1. `party_type` over-conservative on waybills: model says `"unknown"` when
   the document does show a 9-digit labeled TIN that should give
   `"legal_entity"`. v3 was tuned to fix v2's over-eagerness; the dial
   needs to swing back slightly.
2. `script = "mixed"` over-applied: model marks a party as mixed when
   a single non-Mkhedruli char appears that the label tolerates as pure
   Mkhedruli. The "any one Latin character" rule may be too strict.
3. `transport.has_trailer = False` vs `None` and similar transport-block
   presence calls on free-of-charge waybills: model populates when label
   leaves null.
4. `vehicle_plate` minor errors (`'AA310'` vs `'AA310X'`) — model
   over-reading the trailer-plate column.
5. `invoice_003` (Terabank payment order) sits at 78.8% — the rejection
   path matches but `references_other_document` and free-text fields
   wobble. Limited upside without per-doc-family canonical phrasing.

To `--compare-to` against this baseline, use the v3 run JSON filename
above on your machine. The baseline file itself is gitignored — runs
regenerate on each invocation.

## What this harness does NOT do

- It doesn't touch a database. Results live in `eval/runs/` as JSON files.
- It doesn't run in CI yet (no extraction code in the repo to gate on).
- It doesn't grow the eval set. Add docs by hand-labeling into
  `project foundation/labels/` + dropping the PDF in `project foundation/pdfs/`.
- It doesn't edit the prompt for you — that's the whole point of having
  a measurement layer that surfaces regressions.
