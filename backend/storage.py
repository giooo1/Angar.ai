"""File storage abstraction. FilesystemStorage now; R2Storage later.

Storage is keyed by content-addressed paths shaped `{org_id}/{sha256}.pdf`
so dedup-within-org works the same way regardless of the backing store.
The same interface plugs into Cloudflare R2 (or any S3-compatible) when
the cloud deployment lands in step 5+ work.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from pathlib import Path


def content_key(org_id: str, content: bytes, extension: str = "pdf") -> str:
    """Compute the content-addressed storage key for a blob.

    Format: `{org_id}/{sha256-hex}.{extension}`. Same hash → same key,
    so re-uploading an identical PDF within the same org is a no-op at
    the storage layer.
    """
    sha = hashlib.sha256(content).hexdigest()
    return f"{org_id}/{sha}.{extension}"


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class StorageError(Exception):
    """Operation against the storage backend failed."""


class Storage(ABC):
    """Object-storage interface. Implementations: FilesystemStorage, R2Storage."""

    @abstractmethod
    def store(self, content: bytes, key: str) -> str:
        """Persist `content` under `key`. Return the storage path / object id.

        Idempotent: storing the same key+content twice is a no-op.
        Storing a DIFFERENT content at an existing key is an error (storage
        should never silently overwrite — caller must delete first).
        """

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Read content by key. Raises StorageError if not found."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete content by key. Idempotent — missing key is not an error."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """True iff content under `key` exists."""


class FilesystemStorage(Storage):
    """Stores blobs under a root directory. The "key" is a relative path.

    Used in local dev and tests. Swapped for an R2Storage later without
    callers caring.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Reject path traversal and absolute paths. Be platform-explicit:
        # `Path("/x").is_absolute()` is False on Windows but the leading
        # slash still resolves outside our root, so check the raw string.
        if (
            not key
            or key.startswith(("/", "\\"))
            or ":" in key
            or ".." in Path(key).parts
        ):
            raise StorageError(f"invalid storage key: {key!r}")
        # Belt and braces: resolve and verify the result is inside root.
        resolved = (self.root / key).resolve()
        try:
            resolved.relative_to(self.root.resolve())
        except ValueError as exc:
            raise StorageError(f"invalid storage key: {key!r}") from exc
        return resolved

    def store(self, content: bytes, key: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            existing = path.read_bytes()
            if existing != content:
                raise StorageError(
                    f"refusing to overwrite differing content at {key!r}"
                )
            return str(path.relative_to(self.root))
        path.write_bytes(content)
        return str(path.relative_to(self.root))

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError(f"key not found: {key!r}")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()
