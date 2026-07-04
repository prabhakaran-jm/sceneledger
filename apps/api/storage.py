"""Storage abstraction: local filesystem now, Backblaze B2 later."""

from abc import ABC, abstractmethod
from pathlib import Path
import json
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENELEDGER_ROOT = REPO_ROOT / ".sceneledger"


class StorageBackend(ABC):
    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> str:
        """Write raw bytes; return storage key."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read raw bytes by key."""

    @abstractmethod
    def write_json(self, key: str, payload: dict[str, Any]) -> str:
        """Write JSON document; return storage key."""

    @abstractmethod
    def read_json(self, key: str) -> dict[str, Any]:
        """Read JSON document by key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if key exists."""

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]:
        """List keys under prefix."""


class LocalFilesystemStorage(StorageBackend):
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or SCENELEDGER_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def write_bytes(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.write_bytes(data)
        return key

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def write_json(self, key: str, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, indent=2, default=str).encode("utf-8")
        return self.write_bytes(key, data)

    def read_json(self, key: str) -> dict[str, Any]:
        return json.loads(self.read_bytes(key).decode("utf-8"))

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def list_keys(self, prefix: str) -> list[str]:
        base = self.root / prefix
        if not base.exists():
            return []
        keys: list[str] = []
        for path in base.rglob("*"):
            if path.is_file():
                keys.append(str(path.relative_to(self.root)).replace("\\", "/"))
        return sorted(keys)


def project_key(project_id: str, *parts: str) -> str:
    return "/".join(["projects", project_id, *parts])


def get_storage() -> StorageBackend:
    """Factory for the active storage backend (local for M0)."""
    return LocalFilesystemStorage()
