"""Console rendering and JSON persistence for eval runs.

A RunResult is the top-level artifact: it bundles every DocResult from one
harness execution with run-level metadata. We persist RunResult to JSON
(one file per run) and re-load it for --compare-to gating.

The console renderer uses rich for a scannable table; the JSON file is
the durable record that next week's baseline diff reads.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from eval.comparator import DocResult, FieldResult


# ---------------------------------------------------------------------------
# Public shapes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunResult:
    started_at: str                      # ISO 8601 UTC
    completed_at: str
    prompt_version: str
    model: str
    use_cache: bool
    foundation_dir: str
    docs: list[DocResult]
    overall_accuracy: float

    @property
    def total_input_tokens(self) -> int:
        return sum(d.extraction_input_tokens for d in self.docs)

    @property
    def total_cached_input_tokens(self) -> int:
        return sum(d.extraction_cached_input_tokens for d in self.docs)

    @property
    def total_output_tokens(self) -> int:
        return sum(d.extraction_output_tokens for d in self.docs)

    @property
    def parse_failure_count(self) -> int:
        return sum(1 for d in self.docs if d.parse_error is not None)


@dataclass(frozen=True)
class RunComparison:
    baseline_accuracy: float
    current_accuracy: float
    delta: float                         # current - baseline
    newly_failing_fields: list[tuple[str, str]]   # [(doc_name, field_path), ...]
    newly_passing_fields: list[tuple[str, str]]


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_run_result(
    docs: list[DocResult],
    *,
    started_at: datetime,
    completed_at: datetime,
    prompt_version: str,
    model: str,
    use_cache: bool,
    foundation_dir: Path,
) -> RunResult:
    overall = _weighted_overall(docs)
    return RunResult(
        started_at=started_at.astimezone(timezone.utc).isoformat(),
        completed_at=completed_at.astimezone(timezone.utc).isoformat(),
        prompt_version=prompt_version,
        model=model,
        use_cache=use_cache,
        foundation_dir=str(foundation_dir),
        docs=docs,
        overall_accuracy=overall,
    )


def _weighted_overall(docs: list[DocResult]) -> float:
    """Mean of per-doc weighted_accuracy. Each document contributes equally
    so a long waybill with 30 line items doesn't dominate the overall number.
    """
    if not docs:
        return 0.0
    return sum(d.weighted_accuracy for d in docs) / len(docs)


# ---------------------------------------------------------------------------
# Console rendering
# ---------------------------------------------------------------------------

def render_console(
    run: RunResult, console: Console | None = None, top_mismatches: int = 10
) -> None:
    """Pretty-print the run to stdout via rich. Returns nothing."""
    console = console or Console()

    table = Table(title=f"Eval run — {run.model} / prompt {run.prompt_version}")
    table.add_column("Document", style="bold")
    table.add_column("Accuracy", justify="right")
    table.add_column("Strict OK", justify="right")
    table.add_column("Mismatches", justify="right")
    table.add_column("Tokens (in/cache/out)", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Status", justify="center")

    for d in run.docs:
        strict_ok, strict_total = _strict_counts(d.fields)
        mismatches = sum(1 for f in d.fields if not f.correct)
        status = "PASS" if d.parse_error is None and d.weighted_accuracy >= 0.90 else (
            "PARSE-FAIL" if d.parse_error else "FAIL"
        )
        status_style = "green" if status == "PASS" else "red"
        table.add_row(
            d.fixture_name,
            f"{d.weighted_accuracy * 100:.1f}%",
            f"{strict_ok}/{strict_total}",
            str(mismatches),
            f"{d.extraction_input_tokens}/"
            f"{d.extraction_cached_input_tokens}/"
            f"{d.extraction_output_tokens}",
            f"{d.extraction_time_ms}ms",
            f"[{status_style}]{status}[/{status_style}]",
        )

    console.print(table)

    overall_color = (
        "green" if run.overall_accuracy >= 0.95
        else "yellow" if run.overall_accuracy >= 0.85
        else "red"
    )
    summary_lines = [
        f"[{overall_color}]Overall accuracy: {run.overall_accuracy * 100:.2f}%[/]",
        f"Documents: {len(run.docs)} ({run.parse_failure_count} parse failure(s))",
        f"Total tokens — input: {run.total_input_tokens:,}, "
        f"cache reads: {run.total_cached_input_tokens:,}, "
        f"output: {run.total_output_tokens:,}",
    ]
    console.print(Panel("\n".join(summary_lines), title="Summary", expand=False))

    mismatches = _top_mismatches(run.docs, limit=top_mismatches)
    if mismatches:
        mtab = Table(title=f"Top {len(mismatches)} mismatches")
        mtab.add_column("Doc", style="bold")
        mtab.add_column("Field")
        mtab.add_column("Tier")
        mtab.add_column("Expected")
        mtab.add_column("Actual")
        mtab.add_column("Note")
        for doc_name, f in mismatches:
            mtab.add_row(
                doc_name, f.path, f.tier,
                _truncate(repr(f.expected), 40),
                _truncate(repr(f.actual), 40),
                _truncate(f.note or "", 40),
            )
        console.print(mtab)


def _strict_counts(fields: list[FieldResult]) -> tuple[int, int]:
    strict = [f for f in fields if f.tier == "strict"]
    return sum(1 for f in strict if f.correct), len(strict)


def _top_mismatches(
    docs: list[DocResult], limit: int
) -> list[tuple[str, FieldResult]]:
    items: list[tuple[str, FieldResult]] = []
    for d in docs:
        for f in d.fields:
            if not f.correct:
                items.append((d.fixture_name, f))
    # Sort: strict failures first, then by lowest score, then alphabetic
    tier_order = {"strict": 0, "semantic": 1, "free_text": 2}
    items.sort(key=lambda pair: (tier_order[pair[1].tier], pair[1].score, pair[0]))
    return items[:limit]


def _truncate(text: str, width: int) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= width else text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def persist(run: RunResult, runs_dir: Path) -> Path:
    """Write the run as JSON. Returns the resulting file path."""
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = run.started_at.replace(":", "-").replace("+00:00", "Z")
    fname = f"{safe_ts}__{run.prompt_version}__{run.model}.json"
    path = runs_dir / fname
    path.write_text(
        json.dumps(_run_to_dict(run), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def load_run(path: Path) -> RunResult:
    """Load a previously persisted run from JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    docs = [
        DocResult(
            fixture_name=d["fixture_name"],
            fields=[
                FieldResult(
                    path=f["path"],
                    tier=f["tier"],
                    expected=f["expected"],
                    actual=f["actual"],
                    correct=f["correct"],
                    score=f["score"],
                    note=f.get("note"),
                )
                for f in d["fields"]
            ],
            weighted_accuracy=d["weighted_accuracy"],
            parse_error=d.get("parse_error"),
            extraction_input_tokens=d.get("extraction_input_tokens", 0),
            extraction_cached_input_tokens=d.get("extraction_cached_input_tokens", 0),
            extraction_output_tokens=d.get("extraction_output_tokens", 0),
            extraction_time_ms=d.get("extraction_time_ms", 0),
        )
        for d in data["docs"]
    ]
    return RunResult(
        started_at=data["started_at"],
        completed_at=data["completed_at"],
        prompt_version=data["prompt_version"],
        model=data["model"],
        use_cache=data.get("use_cache", True),
        foundation_dir=data.get("foundation_dir", ""),
        docs=docs,
        overall_accuracy=data["overall_accuracy"],
    )


def _run_to_dict(run: RunResult) -> dict:
    return {
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "use_cache": run.use_cache,
        "foundation_dir": run.foundation_dir,
        "overall_accuracy": run.overall_accuracy,
        "total_input_tokens": run.total_input_tokens,
        "total_cached_input_tokens": run.total_cached_input_tokens,
        "total_output_tokens": run.total_output_tokens,
        "parse_failure_count": run.parse_failure_count,
        "docs": [_doc_to_dict(d) for d in run.docs],
    }


def _doc_to_dict(d: DocResult) -> dict:
    return {
        "fixture_name": d.fixture_name,
        "weighted_accuracy": d.weighted_accuracy,
        "parse_error": d.parse_error,
        "extraction_input_tokens": d.extraction_input_tokens,
        "extraction_cached_input_tokens": d.extraction_cached_input_tokens,
        "extraction_output_tokens": d.extraction_output_tokens,
        "extraction_time_ms": d.extraction_time_ms,
        "fields": [asdict(f) for f in d.fields],
    }


# ---------------------------------------------------------------------------
# Run-to-run comparison (the regression gate)
# ---------------------------------------------------------------------------

def compare_runs(baseline: RunResult, current: RunResult) -> RunComparison:
    """Compute overall accuracy delta + symmetric per-field diff.

    A field is 'newly failing' if it was correct in baseline and not in
    current — that's the regression signal you actually care about. The
    reverse (newly passing) is informational.
    """
    base_field_status = _field_status_index(baseline)
    curr_field_status = _field_status_index(current)

    newly_failing: list[tuple[str, str]] = []
    newly_passing: list[tuple[str, str]] = []
    for key, was_correct in base_field_status.items():
        now_correct = curr_field_status.get(key)
        if now_correct is None:
            continue
        if was_correct and not now_correct:
            newly_failing.append(key)
        elif not was_correct and now_correct:
            newly_passing.append(key)

    return RunComparison(
        baseline_accuracy=baseline.overall_accuracy,
        current_accuracy=current.overall_accuracy,
        delta=current.overall_accuracy - baseline.overall_accuracy,
        newly_failing_fields=sorted(newly_failing),
        newly_passing_fields=sorted(newly_passing),
    )


def _field_status_index(run: RunResult) -> dict[tuple[str, str], bool]:
    out: dict[tuple[str, str], bool] = {}
    for d in run.docs:
        for f in d.fields:
            out[(d.fixture_name, f.path)] = f.correct
    return out


def render_comparison(
    cmp_: RunComparison, gate: float, console: Console | None = None
) -> bool:
    """Print the regression-gate verdict. Returns True if pass, False if regressed."""
    console = console or Console()
    drop = -cmp_.delta if cmp_.delta < 0 else 0.0
    regressed = drop > gate

    color = "red" if regressed else "green"
    verdict = "REGRESSION" if regressed else ("OK" if cmp_.delta >= 0 else "TOLERATED")
    lines = [
        f"Baseline accuracy: {cmp_.baseline_accuracy * 100:.2f}%",
        f"Current accuracy:  {cmp_.current_accuracy * 100:.2f}%",
        f"Delta:             {cmp_.delta * 100:+.2f}%",
        f"Gate threshold:    {gate * 100:.2f}% maximum drop",
        f"Newly failing:     {len(cmp_.newly_failing_fields)} field(s)",
        f"Newly passing:     {len(cmp_.newly_passing_fields)} field(s)",
    ]
    console.print(Panel(
        "\n".join(lines),
        title=f"[{color}]{verdict}[/{color}]",
        expand=False,
    ))

    if regressed and cmp_.newly_failing_fields:
        rt = Table(title="Newly failing fields")
        rt.add_column("Document")
        rt.add_column("Field")
        for doc_name, path in cmp_.newly_failing_fields[:25]:
            rt.add_row(doc_name, path)
        console.print(rt)

    return not regressed
