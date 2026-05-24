#!/usr/bin/env python
"""Pre-commit gate: eval harness + real-PDF e2e smoke, file-pattern triggered.

Configured by `.pre-commit-config.yaml`. On every commit:

  1. If any prompt file (`angar_extraction/prompts/*.md`) changed, run
     the eval harness against THAT prompt version.
  2. Else if `angar_extraction/extractor.py` or the `angar_*` settings
     lines in `backend/settings.py` changed, run the eval against the
     production prompt version.
  3. If any pipeline-wiring file changed
     (`backend/extraction_service.py`, `backend/main.py`, the rest of
     `backend/settings.py`), additionally run the real-PDF e2e smoke
     (`pytest -m e2e`). This is the layer that catches the
     missing-env-var / SDK-wiring class of bugs a pure prompt eval can't
     see.
  4. Otherwise exit 0 immediately — no eval, no spend.

Explicit override: `git commit --no-verify`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_THRESHOLD = "0.9"

# Paths that, if changed, fire the eval gate.
PROMPT_PREFIX = "angar_extraction/prompts/"
EXTRACTOR_PATH = "angar_extraction/extractor.py"
SETTINGS_PATH = "backend/settings.py"

# Paths that, if changed, fire the e2e smoke. Extractor changes already
# fire the eval gate above, which is the right tool for that file.
WIRING_PATHS = (
    "backend/extraction_service.py",
    "backend/main.py",
)


def _staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in out.stdout.splitlines() if line]


def _settings_diff_touches_extraction() -> bool:
    """True iff the staged diff of backend/settings.py touches an `angar_` line."""
    out = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--", SETTINGS_PATH],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in out.stdout.splitlines():
        if line.startswith(("+++", "---")):
            continue
        if line.startswith(("+", "-")) and "angar_" in line:
            return True
    return False


def _changed_prompt_version(staged: list[str]) -> str | None:
    """If a single prompt file changed, return its version slug (e.g. 'v3').
    If multiple prompt files changed, return the highest-versioned one
    (typically the one the user is iterating on)."""
    versions: list[str] = []
    for path in staged:
        if not path.startswith(PROMPT_PREFIX):
            continue
        name = Path(path).stem  # 'v3' from 'v3.md'
        if re.fullmatch(r"v\d+", name):
            versions.append(name)
    if not versions:
        return None
    versions.sort(key=lambda s: int(s[1:]))
    return versions[-1]


def _production_prompt_version() -> str:
    """Best-effort read of the production prompt version from backend settings.
    Falls back to 'v3' if Settings can't be loaded (e.g. broken .env)."""
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from backend.settings import Settings  # noqa: E402

        return Settings().angar_prompt_version
    except Exception:  # noqa: BLE001
        return "v3"


def _run_eval(prompt_version: str) -> int:
    print(
        f"[eval-gate] running harness against prompt={prompt_version} "
        f"with --baseline-threshold {BASELINE_THRESHOLD}",
        file=sys.stderr,
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.harness",
            "--prompt-version",
            prompt_version,
            "--baseline-threshold",
            BASELINE_THRESHOLD,
        ],
        cwd=str(REPO_ROOT),
    )
    return proc.returncode


def _run_e2e_smoke() -> int:
    print(
        "[eval-gate] running real-PDF e2e smoke (pytest -m e2e)",
        file=sys.stderr,
    )
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "e2e", "-q"],
        cwd=str(REPO_ROOT),
    )
    return proc.returncode


def main() -> int:
    staged = _staged_files()
    if not staged:
        return 0

    prompt_version = _changed_prompt_version(staged)
    extractor_changed = EXTRACTOR_PATH in staged
    settings_touches_extraction = (
        SETTINGS_PATH in staged and _settings_diff_touches_extraction()
    )
    wiring_changed = any(p in staged for p in WIRING_PATHS) or SETTINGS_PATH in staged

    needs_eval = prompt_version is not None or extractor_changed or settings_touches_extraction
    needs_e2e = wiring_changed

    if not needs_eval and not needs_e2e:
        return 0

    if needs_eval:
        if prompt_version is None:
            prompt_version = _production_prompt_version()
        rc = _run_eval(prompt_version)
        if rc != 0:
            print(
                f"[eval-gate] EVAL FAILED (exit {rc}). Commit aborted.\n"
                f"[eval-gate] To bypass intentionally: git commit --no-verify",
                file=sys.stderr,
            )
            return rc

    if needs_e2e:
        rc = _run_e2e_smoke()
        if rc != 0:
            print(
                f"[eval-gate] E2E SMOKE FAILED (exit {rc}). Commit aborted.\n"
                f"[eval-gate] To bypass intentionally: git commit --no-verify",
                file=sys.stderr,
            )
            return rc

    print("[eval-gate] PASS", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
