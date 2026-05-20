# Angar.ai eval harness

Standalone CLI tool that measures Georgian invoice-extraction accuracy by
running the current prompt against 18 hand-labeled documents and comparing
output to ground truth.

Builds on Phase 3 design doc §5 (`project foundation/angar-ai-phase3-v1.0.md`).
Must pass before any prompt change merges to `main`.

## Setup (one time)

```powershell
cd eval
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

## What this harness does NOT do

- It doesn't touch a database. Results live in `eval/runs/` as JSON files.
- It doesn't run in CI yet (no extraction code in the repo to gate on).
- It doesn't grow the eval set. Add docs by hand-labeling into
  `project foundation/labels/` + dropping the PDF in `project foundation/pdfs/`.
- It doesn't edit the prompt for you — that's the whole point of having
  a measurement layer that surfaces regressions.
