"""Storage abstraction: local filesystem (M0) and Backblaze B2 (M1)."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from functools import lru_cache
import json
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from models import StoredObjectRef

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENELEDGER_ROOT = REPO_ROOT / ".sceneledger"

load_dotenv(REPO_ROOT / ".env")

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


class StorageError(Exception):
    """Raised when storage operations fail. Messages must not contain secrets."""


def validate_logical_path(path: str) -> str:
    if not path or not path.strip():
        raise StorageError("Storage path cannot be empty")
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith("/"):
        raise StorageError("Storage path must be relative")
    if _DRIVE_PREFIX.match(normalized):
        raise StorageError("Storage path must be relative")
    parts = normalized.split("/")
    if ".." in parts:
        raise StorageError("Storage path must not contain '..'")
    return normalized


def infer_object_kind(key: str) -> str:
    normalized = key.replace("\\", "/")
    if normalized.endswith("/project.json") or normalized.endswith("project.json"):
        return "project"
    if normalized.endswith("/source.txt"):
        return "source"
    if normalized.endswith("/chunks.json"):
        return "chunks"
    if normalized.endswith("/scenes.json"):
        return "plan"
    if normalized.endswith("/stale-report.json"):
        return "compare"
    if normalized.endswith("/release.json"):
        return "manifest"
    if normalized.endswith("/storyboard.png"):
        return "media_storyboard"
    if normalized.endswith("/clip.mp4"):
        return "media_clip"
    if normalized.endswith("/clip.placeholder.txt"):
        return "media_clip_placeholder"
    if normalized.endswith("/narration.wav"):
        return "media_narration"
    if normalized.endswith("/captions.vtt"):
        return "media_captions"
    if normalized.endswith("/scene-asset-manifest.json"):
        return "media_manifest"
    return "other"


def project_key(project_id: str, *parts: str) -> str:
    return validate_logical_path("/".join(["projects", project_id, *parts]))


class StorageBackend(ABC):
    backend_name: str

    @abstractmethod
    def public_key(self, logical_path: str) -> str:
        """Return the public storage key for API responses."""

    @abstractmethod
    def write_text(self, path: str, content: str) -> str:
        """Write text; return public storage key."""

    @abstractmethod
    def read_text(self, path: str) -> str:
        """Read text by logical path."""

    @abstractmethod
    def write_json(self, path: str, payload: dict[str, Any]) -> str:
        """Write JSON; return public storage key."""

    @abstractmethod
    def write_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> str:
        """Write binary data; return public storage key."""

    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read binary data by logical path."""

    @abstractmethod
    def read_json(self, path: str) -> dict[str, Any]:
        """Read JSON by logical path."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Return True if logical path exists."""

    @abstractmethod
    def list_prefix(self, prefix: str) -> list[str]:
        """List logical paths under prefix."""

    @abstractmethod
    def list_project_objects(self, project_id: str) -> list[StoredObjectRef]:
        """List stored objects for a project using public keys."""


class LocalFilesystemStorage(StorageBackend):
    backend_name = "local"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or SCENELEDGER_ROOT
        self.root.mkdir(parents=True, exist_ok=True)

    def public_key(self, logical_path: str) -> str:
        return validate_logical_path(logical_path)

    def _file_path(self, logical_path: str) -> Path:
        path = validate_logical_path(logical_path)
        full = self.root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        return full

    def write_text(self, path: str, content: str) -> str:
        logical = validate_logical_path(path)
        self._file_path(logical).write_text(content, encoding="utf-8")
        return self.public_key(logical)

    def read_text(self, path: str) -> str:
        return self._file_path(path).read_text(encoding="utf-8")

    def write_json(self, path: str, payload: dict[str, Any]) -> str:
        data = json.dumps(payload, indent=2, default=str)
        return self.write_text(path, data)

    def write_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> str:
        logical = validate_logical_path(path)
        self._file_path(logical).write_bytes(data)
        return self.public_key(logical)

    def read_bytes(self, path: str) -> bytes:
        return self._file_path(path).read_bytes()

    def read_json(self, path: str) -> dict[str, Any]:
        return json.loads(self.read_text(path))

    def exists(self, path: str) -> bool:
        return self._file_path(path).exists()

    def list_prefix(self, prefix: str) -> list[str]:
        logical_prefix = validate_logical_path(prefix)
        base = self.root / logical_prefix
        if not base.exists():
            return []
        keys: list[str] = []
        for file_path in base.rglob("*"):
            if file_path.is_file():
                relative = str(file_path.relative_to(self.root)).replace("\\", "/")
                keys.append(relative)
        return sorted(keys)

    def list_project_objects(self, project_id: str) -> list[StoredObjectRef]:
        prefix = project_key(project_id)
        objects: list[StoredObjectRef] = []
        for logical_path in self.list_prefix(prefix):
            file_path = self.root / logical_path
            stat = file_path.stat()
            updated = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            objects.append(
                StoredObjectRef(
                    key=self.public_key(logical_path),
                    kind=infer_object_kind(logical_path),
                    size=stat.st_size,
                    updated_at=updated,
                )
            )
        return objects


def _require_b2_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise StorageError(
            f"B2 mode requires {name} to be set. "
            "Use SCENELEDGER_STORAGE_BACKEND=local for local development."
        )
    return value


class B2Storage(StorageBackend):
    backend_name = "b2"

    def __init__(self) -> None:
        from botocore.exceptions import ClientError, NoCredentialsError

        self._client_error = ClientError
        self._no_credentials_error = NoCredentialsError

        self.endpoint = _require_b2_env("B2_ENDPOINT")
        self.region = _require_b2_env("B2_REGION")
        self.bucket = _require_b2_env("B2_BUCKET")
        self.key_id = _require_b2_env("B2_KEY_ID")
        self.application_key = _require_b2_env("B2_APPLICATION_KEY")
        self.tenant_prefix = os.getenv("SCENELEDGER_B2_TENANT_PREFIX", "tenants/demo").strip().strip("/")

        try:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                region_name=self.region,
                aws_access_key_id=self.key_id,
                aws_secret_access_key=self.application_key,
            )
        except ImportError as exc:
            raise StorageError(
                "boto3 is required for B2 mode. Install with: pip install boto3"
            ) from exc
        except NoCredentialsError as exc:
            raise StorageError("B2 credentials are invalid or missing") from exc
        except Exception as exc:
            raise StorageError(f"Failed to initialize B2 client: {exc}") from exc

    def _object_key(self, logical_path: str) -> str:
        logical = validate_logical_path(logical_path)
        return f"{self.tenant_prefix}/{logical}"

    def public_key(self, logical_path: str) -> str:
        return self._object_key(logical_path)

    def _run(self, operation: str, func: Any) -> Any:
        try:
            return func()
        except self._client_error as exc:
            code = exc.response.get("Error", {}).get("Code", "Unknown")
            raise StorageError(f"B2 {operation} failed: {code}") from exc
        except self._no_credentials_error as exc:
            raise StorageError("B2 credentials are invalid or missing") from exc

    def write_text(self, path: str, content: str) -> str:
        key = self._object_key(path)

        def _put() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/plain; charset=utf-8",
            )

        self._run("write", _put)
        return key

    def write_bytes(
        self, path: str, data: bytes, content_type: str | None = None
    ) -> str:
        key = self._object_key(path)
        resolved_type = content_type or "application/octet-stream"

        def _put() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=resolved_type,
            )

        self._run("write", _put)
        return key

    def read_bytes(self, path: str) -> bytes:
        key = self._object_key(path)

        def _get() -> bytes:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

        return self._run("read", _get)

    def read_text(self, path: str) -> str:
        key = self._object_key(path)

        def _get() -> str:
            response = self._client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")

        return self._run("read", _get)

    def write_json(self, path: str, payload: dict[str, Any]) -> str:
        key = self._object_key(path)
        body = json.dumps(payload, indent=2, default=str)

        def _put() -> None:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=body.encode("utf-8"),
                ContentType="application/json",
            )

        self._run("write", _put)
        return key

    def read_json(self, path: str) -> dict[str, Any]:
        return json.loads(self.read_text(path))

    def exists(self, path: str) -> bool:
        key = self._object_key(path)

        def _head() -> bool:
            try:
                self._client.head_object(Bucket=self.bucket, Key=key)
                return True
            except self._client_error as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise StorageError(f"B2 exists check failed: {code}") from exc

        return _head()

    def _paginate_list(self, object_prefix: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        continuation: str | None = None

        while True:
            params: dict[str, Any] = {
                "Bucket": self.bucket,
                "Prefix": object_prefix,
            }
            if continuation:
                params["ContinuationToken"] = continuation

            try:
                response = self._client.list_objects_v2(**params)
            except self._client_error as exc:
                code = exc.response.get("Error", {}).get("Code", "Unknown")
                raise StorageError(f"B2 list failed: {code}") from exc
            except self._no_credentials_error as exc:
                raise StorageError("B2 credentials are invalid or missing") from exc

            items.extend(response.get("Contents", []))
            if not response.get("IsTruncated"):
                break
            continuation = response.get("NextContinuationToken")

        return items

    def list_prefix(self, prefix: str) -> list[str]:
        logical_prefix = validate_logical_path(prefix)
        object_prefix = f"{self.tenant_prefix}/{logical_prefix}"
        logical_paths: list[str] = []

        for item in self._paginate_list(object_prefix):
            object_key = item["Key"]
            if object_key.startswith(f"{self.tenant_prefix}/"):
                logical_paths.append(object_key[len(self.tenant_prefix) + 1 :])

        return sorted(logical_paths)

    def list_project_objects(self, project_id: str) -> list[StoredObjectRef]:
        prefix = self._object_key(project_key(project_id))
        objects: list[StoredObjectRef] = []

        for item in self._paginate_list(prefix):
            object_key = item["Key"]
            logical = object_key[len(self.tenant_prefix) + 1 :]
            last_modified = item["LastModified"]
            if last_modified.tzinfo is None:
                last_modified = last_modified.replace(tzinfo=timezone.utc)
            else:
                last_modified = last_modified.astimezone(timezone.utc)
            objects.append(
                StoredObjectRef(
                    key=object_key,
                    kind=infer_object_kind(logical),
                    size=item.get("Size"),
                    updated_at=last_modified,
                )
            )

        return sorted(objects, key=lambda obj: obj.key)


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """Return cached storage backend for the process."""
    backend = os.getenv("SCENELEDGER_STORAGE_BACKEND", "local").strip().lower()
    if backend in {"", "local"}:
        return LocalFilesystemStorage()
    if backend == "b2":
        return B2Storage()
    raise StorageError(
        f"Unknown SCENELEDGER_STORAGE_BACKEND: {backend!r}. Use 'local' or 'b2'."
    )
