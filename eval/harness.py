"""Eval harness CLI entry point.

Usage:
    python -m eval.harness                         # full run, defaults
    python -m eval.harness --doc invoice_001       # one doc by basename
    python -m eval.harness --model claude-haiku-4-5-20251001
    python -m eval.harness --prompt-version v0
    python -m eval.harness --compare-to <prev>.json --gate 0.02
    python -m eval.harness --no-cache              # disable prompt caching

Exits:
    0  — run finished; if a gate was set, accuracy held within the threshold
    1  — runtime failure (missing API key, missing prompt, etc.)
    2  — regression gate exceeded (accuracy dropped more than --gate)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console

from eval.comparator import compare
from eval.extractor import Extractor
from eval.fixtures import Fixture, FixtureError, load_fixtures, load_single
from eval.prompt import PromptError
from eval.report import (
    build_run_result,
    compare_runs,
    load_run,
    persist,
    render_comparison,
    render_console,
)

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_PROMPT_VERSION = "v0"


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    console = Console()
    load_dotenv()  # picks up ANTHROPIC_API_KEY from repo-root .env

    repo_root = Path(__file__).resolve().parents[1]
    foundation_dir = Path(args.foundation) if args.foundation else repo_root / "project foundation"
    runs_dir = Path(args.runs_dir) if args.runs_dir else repo_root / "eval" / "runs"

    # Pre-flight: fail fast on the obvious misconfigurations.
    if not _check_api_key(console):
        return 1

    try:
        fixtures = _select_fixtures(foundation_dir, args.doc)
    except FixtureError as exc:
        console.print(f"[red]Fixture error:[/red] {exc}")
        return 1

    if not fixtures:
        console.print("[yellow]No fixtures matched the selection — nothing to run.[/yellow]")
        return 1

    try:
        extractor = Extractor(
            model=args.model,
            prompt_version=args.prompt_version,
            use_cache=not args.no_cache,
        )
    except PromptError as exc:
        console.print(f"[red]Prompt error:[/red] {exc}")
        return 1

    console.print(
        f"Running [bold]{len(fixtures)}[/bold] fixture(s) on "
        f"[cyan]{args.model}[/cyan] with prompt [cyan]{args.prompt_version}[/cyan], "
        f"cache={'on' if not args.no_cache else 'off'}"
    )

    started = datetime.now(tz=timezone.utc)
    docs = []
    for i, fx in enumerate(fixtures, start=1):
        console.print(f"  [{i}/{len(fixtures)}] {fx.name} ...", end="")
        result = extractor.extract(fx.pdf_path)
        doc_result = compare(
            expected=fx.ground_truth,
            actual=result.canonical,
            fixture_name=fx.name,
            parse_error=result.parse_error,
            extraction_input_tokens=result.input_tokens,
            extraction_cached_input_tokens=result.cached_input_tokens,
            extraction_output_tokens=result.output_tokens,
            extraction_time_ms=result.processing_time_ms,
        )
        docs.append(doc_result)
        marker = "[red] FAIL[/red]" if doc_result.parse_error else f" {doc_result.weighted_accuracy * 100:.1f}%"
        console.print(marker)

    completed = datetime.now(tz=timezone.utc)

    run = build_run_result(
        docs,
        started_at=started,
        completed_at=completed,
        prompt_version=args.prompt_version,
        model=args.model,
        use_cache=not args.no_cache,
        foundation_dir=foundation_dir,
    )

    output_path = persist(run, runs_dir)
    console.print(f"\nResults persisted to [cyan]{output_path}[/cyan]\n")

    render_console(run, console=console, top_mismatches=args.top_mismatches)

    if args.compare_to:
        try:
            baseline = load_run(Path(args.compare_to))
        except (OSError, KeyError, ValueError) as exc:
            console.print(f"[red]Could not load baseline {args.compare_to}:[/red] {exc}")
            return 1
        cmp_ = compare_runs(baseline, run)
        console.print()
        passed = render_comparison(cmp_, gate=args.gate, console=console)
        return 0 if passed else 2

    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m eval.harness",
        description="Run the Angar.ai extraction eval harness.",
    )
    parser.add_argument(
        "--doc",
        help="Run a single document by basename (e.g. 'invoice_001'). "
             "Default: run all 18 documents.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Anthropic model identifier (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--prompt-version",
        default=DEFAULT_PROMPT_VERSION,
        help=f"Prompt file under eval/prompts/ (default: {DEFAULT_PROMPT_VERSION}).",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable prompt-cache control. Useful for cost-comparison runs.",
    )
    parser.add_argument(
        "--compare-to",
        help="Path to a previous run JSON. Computes accuracy delta and "
             "exits non-zero if regression exceeds --gate.",
    )
    parser.add_argument(
        "--gate",
        type=float,
        default=0.02,
        help="Maximum tolerated accuracy drop vs --compare-to baseline. "
             "Default: 0.02 (2%%) per Phase 3 design doc section 5.3.",
    )
    parser.add_argument(
        "--top-mismatches",
        type=int,
        default=10,
        help="Number of top failing fields to show in the console summary (default: 10).",
    )
    parser.add_argument(
        "--foundation",
        help="Override the foundation directory (default: ./project foundation). "
             "For testing only.",
    )
    parser.add_argument(
        "--runs-dir",
        help="Override the runs output directory (default: ./eval/runs). "
             "For testing only.",
    )
    return parser


def _select_fixtures(foundation_dir: Path, name: str | None) -> list[Fixture]:
    if name:
        return [load_single(foundation_dir, name)]
    return load_fixtures(foundation_dir)


def _check_api_key(console: Console) -> bool:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return True
    console.print(
        "[red]Missing ANTHROPIC_API_KEY.[/red] Put it in a .env file at the repo "
        "root or export it in your shell. See eval/README.md."
    )
    return False


if __name__ == "__main__":
    sys.exit(main())
