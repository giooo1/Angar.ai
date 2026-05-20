"""Unit tests for eval.report.

Round-trip persistence (persist/load) and compare_runs logic — the
regression gate's correctness depends on both. Console rendering is
not asserted byte-for-byte (rich output formatting changes between
versions); we just verify it doesn't crash.
"""

from __future__ import annotations

from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from eval.comparator import DocResult, FieldResult
from eval.report import (
    RunComparison,
    RunResult,
    build_run_result,
    compare_runs,
    load_run,
    persist,
    render_comparison,
    render_console,
)


def _field(path: str, correct: bool, tier: str = "strict", score: float | None = None) -> FieldResult:
    return FieldResult(
        path=path,
        tier=tier,  # type: ignore[arg-type]
        expected="x",
        actual="x" if correct else "y",
        correct=correct,
        score=score if score is not None else (1.0 if correct else 0.0),
        note=None,
    )


def _doc(name: str, accuracy: float, fields: list[FieldResult] | None = None) -> DocResult:
    return DocResult(
        fixture_name=name,
        fields=fields or [_field("a", True), _field("b", True)],
        weighted_accuracy=accuracy,
        parse_error=None,
    )


def _build(
    docs: list[DocResult],
    *,
    prompt_version: str = "v0",
    model: str = "claude-sonnet-4-6",
) -> RunResult:
    return build_run_result(
        docs,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc),
        prompt_version=prompt_version,
        model=model,
        use_cache=True,
        foundation_dir=Path("project foundation"),
    )


# ---------------------------------------------------------------------------
# build_run_result
# ---------------------------------------------------------------------------

class TestBuildRunResult:
    def test_overall_is_mean_of_per_doc_accuracy(self) -> None:
        run = _build([_doc("a", 1.0), _doc("b", 0.5), _doc("c", 0.0)])
        assert run.overall_accuracy == pytest.approx(0.5)

    def test_empty_docs_returns_zero_accuracy(self) -> None:
        assert _build([]).overall_accuracy == 0.0

    def test_iso_timestamps_in_utc(self) -> None:
        run = _build([_doc("a", 1.0)])
        assert run.started_at.endswith("+00:00") or run.started_at.endswith("Z")
        assert run.completed_at.endswith("+00:00") or run.completed_at.endswith("Z")


# ---------------------------------------------------------------------------
# persist / load round-trip
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_round_trip_preserves_run(self, tmp_path: Path) -> None:
        original = _build([
            _doc("invoice_001", 0.96, [
                _field("seller.tin", True),
                _field("buyer.name", False, tier="semantic", score=0.4),
            ]),
            _doc("invoice_002", 0.85, [_field("grand_total", False)]),
        ])
        path = persist(original, tmp_path)
        loaded = load_run(path)
        assert loaded.overall_accuracy == original.overall_accuracy
        assert len(loaded.docs) == 2
        assert loaded.docs[0].fixture_name == "invoice_001"
        # Field reconstruction preserves correct/score/tier
        f = loaded.docs[0].fields[1]
        assert f.path == "buyer.name"
        assert f.tier == "semantic"
        assert f.score == 0.4
        assert not f.correct

    def test_persist_filename_includes_version_and_model(self, tmp_path: Path) -> None:
        run = _build([_doc("a", 1.0)], prompt_version="v3", model="claude-haiku-4-5")
        path = persist(run, tmp_path)
        assert "v3" in path.name
        assert "claude-haiku-4-5" in path.name
        assert path.suffix == ".json"

    def test_persist_creates_dir(self, tmp_path: Path) -> None:
        nested = tmp_path / "deeply" / "nested" / "runs"
        run = _build([_doc("a", 1.0)])
        path = persist(run, nested)
        assert path.exists()


# ---------------------------------------------------------------------------
# compare_runs
# ---------------------------------------------------------------------------

class TestCompareRuns:
    def test_no_change(self) -> None:
        run = _build([_doc("a", 1.0, [_field("x", True)])])
        cmp_ = compare_runs(run, run)
        assert cmp_.delta == 0.0
        assert cmp_.newly_failing_fields == []
        assert cmp_.newly_passing_fields == []

    def test_detects_newly_failing_field(self) -> None:
        baseline = _build([_doc("a", 1.0, [_field("x", True), _field("y", True)])])
        current = _build([_doc("a", 0.5, [_field("x", True), _field("y", False)])])
        cmp_ = compare_runs(baseline, current)
        assert cmp_.delta == pytest.approx(-0.5)
        assert cmp_.newly_failing_fields == [("a", "y")]

    def test_detects_newly_passing_field(self) -> None:
        baseline = _build([_doc("a", 0.5, [_field("x", True), _field("y", False)])])
        current = _build([_doc("a", 1.0, [_field("x", True), _field("y", True)])])
        cmp_ = compare_runs(baseline, current)
        assert cmp_.delta == pytest.approx(0.5)
        assert cmp_.newly_passing_fields == [("a", "y")]

    def test_field_only_in_baseline_is_ignored(self) -> None:
        """If a field disappears (schema change), don't count it as either direction."""
        baseline = _build([_doc("a", 1.0, [_field("x", True), _field("dropped", True)])])
        current = _build([_doc("a", 1.0, [_field("x", True)])])
        cmp_ = compare_runs(baseline, current)
        assert cmp_.newly_failing_fields == []
        assert cmp_.newly_passing_fields == []


# ---------------------------------------------------------------------------
# render_comparison: gate logic
# ---------------------------------------------------------------------------

class TestRegressionGate:
    def _silent_console(self) -> Console:
        return Console(file=StringIO(), force_terminal=False)

    def test_improvement_passes_gate(self) -> None:
        cmp_ = RunComparison(0.90, 0.95, 0.05, [], [("a", "x")])
        assert render_comparison(cmp_, gate=0.02, console=self._silent_console()) is True

    def test_drop_within_gate_passes(self) -> None:
        cmp_ = RunComparison(0.96, 0.945, -0.015, [], [])
        # Drop of 0.015 < gate 0.02 → tolerated
        assert render_comparison(cmp_, gate=0.02, console=self._silent_console()) is True

    def test_drop_exceeds_gate_fails(self) -> None:
        cmp_ = RunComparison(0.96, 0.90, -0.06, [("a", "x")], [])
        assert render_comparison(cmp_, gate=0.02, console=self._silent_console()) is False

    def test_drop_exactly_at_gate_passes(self) -> None:
        cmp_ = RunComparison(0.96, 0.94, -0.02, [], [])
        # Drop equals gate → still tolerated (strict >, not >=)
        assert render_comparison(cmp_, gate=0.02, console=self._silent_console()) is True


# ---------------------------------------------------------------------------
# render_console: smoke test (doesn't crash)
# ---------------------------------------------------------------------------

class TestRenderConsole:
    def test_does_not_crash_on_empty_run(self) -> None:
        run = _build([])
        render_console(run, console=Console(file=StringIO(), force_terminal=False))

    def test_does_not_crash_with_mismatches(self) -> None:
        run = _build([_doc("a", 0.5, [_field("x", False)])])
        render_console(run, console=Console(file=StringIO(), force_terminal=False))

    def test_does_not_crash_with_parse_failure(self) -> None:
        d = DocResult(
            fixture_name="bad",
            fields=[_field("x", False)],
            weighted_accuracy=0.0,
            parse_error="json decode failed",
        )
        render_console(_build([d]), console=Console(file=StringIO(), force_terminal=False))
