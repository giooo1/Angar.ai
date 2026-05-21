"""Load and version-tag system prompts for the extraction agent.

Prompts live as plain text in `eval/prompts/<version>.md`. The harness reads
the file verbatim and passes it as Claude's system prompt. Versioning
happens by filename — never edit a committed prompt; copy to a new file.

A sentinel check refuses to load v0.md (the placeholder created during
scaffolding) until Giorgi pastes his week-1 prompt over the HTML comment.
"""

from __future__ import annotations

import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# If the prompt file's text-content (stripped of HTML comments and whitespace)
# is empty, the file is still a placeholder and the harness must refuse to run.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


class PromptError(Exception):
    """A prompt version could not be loaded or is still the placeholder."""


def load_prompt(version: str) -> str:
    """Read `eval/prompts/<version>.md` and return its verbatim content.

    Raises PromptError if the file is missing or is still the v0 placeholder.
    Note: the returned string includes the original file content as-is, not
    the placeholder-stripped version. The stripping is only for the
    is-this-empty? check.
    """
    path = PROMPTS_DIR / f"{version}.md"
    if not path.is_file():
        available = list_versions()
        raise PromptError(
            f"Prompt version '{version}' not found at {path}. "
            f"Available versions: {available or '(none)'}"
        )

    content = path.read_text(encoding="utf-8")
    if _is_placeholder(content):
        raise PromptError(
            f"Prompt file {path} is still the placeholder. "
            f"Paste your real system prompt into this file (replace the "
            f"HTML comment block) before running the harness."
        )
    return content


def list_versions() -> list[str]:
    """All prompt versions present in eval/prompts/, sorted, no extension."""
    if not PROMPTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.md") if p.stem != "README")


def _is_placeholder(content: str) -> bool:
    """A prompt file is a placeholder if it has no meaningful text content.

    Strips HTML comments (the scaffolding placeholder is wrapped in <!-- ... -->)
    and whitespace. If nothing remains, the file is still a placeholder.
    """
    stripped = _HTML_COMMENT_RE.sub("", content).strip()
    return stripped == ""
