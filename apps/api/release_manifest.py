"""Build and load release manifest JSON for a project."""

from datetime import datetime

from models import Scene, SourceChunk, StaleReport
from release_models import ReleaseManifestResponse, VerifyReleaseResponse
from release_verifier import build_release_evidence, verify_stored_release
from storage import StorageBackend, project_key


def release_manifest_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "manifests", source_version, "release.json")


def _report_generated_at(report: StaleReport) -> datetime:
    return report.generated_at


def find_latest_stale_report(
    storage: StorageBackend,
    project_id: str,
    base_version: str | None = None,
) -> StaleReport | None:
    prefix = project_key(project_id, "compare")
    keys = storage.list_prefix(prefix)
    report_keys = [k for k in keys if k.endswith("stale-report.json")]

    candidates: list[tuple[datetime, StaleReport]] = []
    for key in report_keys:
        data = storage.read_json(key)
        report = StaleReport.model_validate(data)
        if base_version is not None and report.base_version != base_version:
            continue
        candidates.append((_report_generated_at(report), report))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def latest_stale_scene_ids(storage: StorageBackend, project_id: str) -> list[str]:
    report = find_latest_stale_report(storage, project_id, base_version=None)
    return list(report.stale_scene_ids) if report else []


def load_release_manifest(
    storage: StorageBackend, project_id: str, source_version: str
) -> ReleaseManifestResponse | None:
    key = release_manifest_key(project_id, source_version)
    if not storage.exists(key):
        return None
    return ReleaseManifestResponse.model_validate(storage.read_json(key))


def create_release_manifest(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    chunks: list[SourceChunk],
    plan_scenes: list[Scene],
) -> ReleaseManifestResponse:
    return build_release_evidence(
        storage, project_id, source_version, chunks, plan_scenes
    )


def run_verify_release(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    chunks: list[SourceChunk],
    plan_scenes: list[Scene],
    stored: ReleaseManifestResponse,
    *,
    update_manifest: bool = False,
) -> tuple[VerifyReleaseResponse, ReleaseManifestResponse | None]:
    return verify_stored_release(
        storage,
        project_id,
        source_version,
        stored,
        chunks,
        plan_scenes,
        update_manifest=update_manifest,
    )
