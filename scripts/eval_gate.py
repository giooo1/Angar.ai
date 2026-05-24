#!/usr/bin/env python
"""Pre-commit gate that runs the eval harness when prompt-relevant files change.

Triggered by `.pre-commit-config.yaml`. On every commit:

  1. Inspect `git diff --cached` for staged files.
  2. If any prompt file (`angar_extraction/prompts/*.md`) changed, run the
     harness against THAT prompt version.
  3. Else if the extractor module or the `angar_*` settings lines changed,
     run the harness against the production prompt version (detected from
     `backend.settings.Settings.angar_prompt_version`).
  4. Otherwise, exit 0 immediately — no eval, no spend.

The harness is invoked with `--baseline-threshold 0.9`, so a prompt or
extractor change that drops overall accuracy below 90% aborts the commit.
Explicit override is `git commit --no-verify`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_THRESHOLD = "0.9"

# Paths that, if changed, fire the gate.
PROMPT_PREFIX = "angar_extraction/prompts/"
EXTRACTOR_PATH = "angar_extraction/extractor.py"
SETTINGS_PATH = "backend/settings.py"


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


def main() -> int:
    staged = _staged_files()
    if not staged:
        return 0

    prompt_version = _changed_prompt_version(staged)
    extractor_changed = EXTRACTOR_PATH in staged
    settings_changed = SETTINGS_PATH in staged and _settings_diff_touches_extraction()

    if prompt_version is None and not extractor_changed and not settings_changed:
        # Nothing relevant; skip the eval entirely.
        return 0

    if prompt_version is None:
        prompt_version = _production_prompt_version()

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
    if proc.returncode == 0:
        print("[eval-gate] PASS", file=sys.stderr)
        return 0

    print(
        f"[eval-gate] FAILED (exit {proc.returncode}). Commit aborted.\n"
        f"[eval-gate] To bypass intentionally: git commit --no-verify",
        file=sys.stderr,
    )
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
