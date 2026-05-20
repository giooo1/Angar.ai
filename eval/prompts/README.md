# Prompt versions

Each file in this folder is one version of the Angar.ai extraction system
prompt. The eval harness loads the version specified by
`--prompt-version <name>` (default: `v0`).

## Adding a new version

1. Copy the current best version: `cp v0.md v1.md`
2. Edit `v1.md` with your changes.
3. Run the harness against the new version:
   ```
   python -m eval.harness --prompt-version v1 --compare-to eval/runs/<previous-baseline>.json --gate 0.02
   ```
4. If accuracy holds (or improves), `v1.md` becomes the new baseline. The
   `--gate 0.02` flag (per Phase 3 §5.3) blocks the change if accuracy
   regresses more than 2% vs the named baseline.

## Conventions

- File names: lowercase, no dots, e.g. `v0.md`, `v1.md`, `v1.1.md`,
  `v2-experimental.md`.
- File contents: just the prompt body. No frontmatter, no metadata, no
  surrounding code fences. The harness reads the file verbatim.
- Treat older prompt files as immutable — they're the artifact behind a
  recorded eval run. If you must edit history, also edit the eval run JSON
  that references that version.

## What goes in a prompt vs. what goes in code

The prompt is *the instructions Claude follows during vision extraction*.
The Pydantic schema in `project foundation/canonical.py` is the *contract*
for the JSON Claude returns. The prompt should reference the schema by
field name and explain Georgian-specific rules (see
`angar-ai-extraction-agent-spec.md` §"Georgian-specific extraction rules").
Schema changes are NOT prompt changes — they're a separate, more invasive
kind of change that requires updating labels + comparator together.
