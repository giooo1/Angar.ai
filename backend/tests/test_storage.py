"""Unit tests for backend.storage.

Covers the FilesystemStorage round-trip, dedup-within-key,
overwrite-refusal, path-traversal rejection, and the content-key helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.storage import (
    FilesystemStorage,
    StorageError,
    content_key,
    sha256_hex,
)


# ---------------------------------------------------------------------------
# content_key
# ---------------------------------------------------------------------------

class TestContentKey:
    def test_same_content_same_key(self) -> None:
        a = content_key("demo-org", b"hello")
        b = content_key("demo-org", b"hello")
        assert a == b

    def test_different_content_different_key(self) -> None:
        a = content_key("demo-org", b"hello")
        b = content_key("demo-org", b"world")
        assert a != b

    def test_different_orgs_different_key(self) -> None:
        a = content_key("org-a", b"hello")
        b = content_key("org-b", b"hello")
        assert a != b

    def test_format_is_org_slash_sha_dot_ext(self) -> None:
        key = content_key("demo-org", b"hello", extension="pdf")
        assert key.startswith("demo-org/")
        assert key.endswith(".pdf")
        assert len(sha256_hex(b"hello")) == 64
        assert sha256_hex(b"hello") in key


# ---------------------------------------------------------------------------
# FilesystemStorage
# ---------------------------------------------------------------------------

class TestFilesystemStorage:
    def test_store_and_get_round_trip(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        key = "demo-org/abc.pdf"
        store.store(b"content", key)
        assert store.get(key) == b"content"

    def test_exists_reflects_state(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        assert not store.exists("demo-org/x.pdf")
        store.store(b"x", "demo-org/x.pdf")
        assert store.exists("demo-org/x.pdf")

    def test_delete_removes_file(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        store.store(b"x", "k.pdf")
        store.delete("k.pdf")
        assert not store.exists("k.pdf")

    def test_delete_missing_key_is_noop(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        store.delete("never-stored.pdf")  # must not raise

    def test_get_missing_key_raises(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        with pytest.raises(StorageError, match="key not found"):
            store.get("missing.pdf")

    def test_store_same_content_twice_is_idempotent(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        a = store.store(b"x", "k.pdf")
        b = store.store(b"x", "k.pdf")
        assert a == b
        assert store.get("k.pdf") == b"x"

    def test_store_different_content_at_existing_key_raises(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        store.store(b"x", "k.pdf")
        with pytest.raises(StorageError, match="refusing to overwrite"):
            store.store(b"y", "k.pdf")

    def test_rejects_absolute_path_keys(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        with pytest.raises(StorageError, match="invalid storage key"):
            store.store(b"x", "/absolute/path.pdf")

    def test_rejects_path_traversal(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        with pytest.raises(StorageError, match="invalid storage key"):
            store.store(b"x", "../escape.pdf")

    def test_creates_nested_dirs(self, tmp_path: Path) -> None:
        store = FilesystemStorage(tmp_path)
        store.store(b"x", "a/b/c/file.pdf")
        assert (tmp_path / "a" / "b" / "c" / "file.pdf").is_file()
