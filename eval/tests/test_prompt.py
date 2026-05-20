"""Unit tests for eval.prompt.

No filesystem dependencies beyond pytest's tmp_path. Tests stub out
PROMPTS_DIR via monkeypatching so they don't depend on what's in the
real eval/prompts/ folder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from eval import prompt as prompt_module
from eval.prompt import PromptError, _is_placeholder, list_versions, load_prompt


@pytest.fixture
def stub_prompts_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect prompt.PROMPTS_DIR at a tmp_path scratch dir for the test."""
    monkeypatch.setattr(prompt_module, "PROMPTS_DIR", tmp_path)
    return tmp_path


class TestIsPlaceholder:
    def test_empty_string_is_placeholder(self) -> None:
        assert _is_placeholder("")

    def test_whitespace_only_is_placeholder(self) -> None:
        assert _is_placeholder("   \n\t  \n")

    def test_html_comment_only_is_placeholder(self) -> None:
        assert _is_placeholder("<!-- paste your prompt here -->")

    def test_html_comment_with_whitespace_is_placeholder(self) -> None:
        assert _is_placeholder("  \n<!-- comment -->\n  ")

    def test_real_content_is_not_placeholder(self) -> None:
        assert not _is_placeholder("You are an invoice extraction assistant.")

    def test_content_after_comment_is_not_placeholder(self) -> None:
        body = "<!-- instructions -->\nYou are an invoice extraction assistant."
        assert not _is_placeholder(body)


class TestLoadPrompt:
    def test_loads_real_content(self, stub_prompts_dir: Path) -> None:
        (stub_prompts_dir / "v0.md").write_text(
            "You are an invoice extraction assistant.", encoding="utf-8"
        )
        assert load_prompt("v0") == "You are an invoice extraction assistant."

    def test_returns_verbatim_including_comments(self, stub_prompts_dir: Path) -> None:
        """Comments only matter for the placeholder check; the loaded content is verbatim."""
        body = "<!-- ignore me -->\nReal prompt body here."
        (stub_prompts_dir / "v1.md").write_text(body, encoding="utf-8")
        assert load_prompt("v1") == body

    def test_raises_on_missing_version(self, stub_prompts_dir: Path) -> None:
        with pytest.raises(PromptError, match="not found"):
            load_prompt("does_not_exist")

    def test_raises_on_placeholder(self, stub_prompts_dir: Path) -> None:
        placeholder_body = "<!-- paste your prompt here -->\n"
        (stub_prompts_dir / "v0.md").write_text(placeholder_body, encoding="utf-8")
        with pytest.raises(PromptError, match="still the placeholder"):
            load_prompt("v0")

    def test_raises_on_empty_file(self, stub_prompts_dir: Path) -> None:
        (stub_prompts_dir / "v0.md").write_text("", encoding="utf-8")
        with pytest.raises(PromptError, match="still the placeholder"):
            load_prompt("v0")

    def test_missing_version_message_lists_available(self, stub_prompts_dir: Path) -> None:
        (stub_prompts_dir / "v0.md").write_text("real content", encoding="utf-8")
        (stub_prompts_dir / "v1.md").write_text("more content", encoding="utf-8")
        with pytest.raises(PromptError, match="\\['v0', 'v1'\\]"):
            load_prompt("v99")


class TestListVersions:
    def test_lists_md_files_sorted_excluding_readme(self, stub_prompts_dir: Path) -> None:
        for name in ("v0.md", "v2.md", "v1.md", "README.md"):
            (stub_prompts_dir / name).write_text("x", encoding="utf-8")
        assert list_versions() == ["v0", "v1", "v2"]

    def test_empty_dir_returns_empty(self, stub_prompts_dir: Path) -> None:
        assert list_versions() == []

    def test_missing_dir_returns_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(prompt_module, "PROMPTS_DIR", tmp_path / "does_not_exist")
        assert list_versions() == []
