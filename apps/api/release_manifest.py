"""Build release manifest JSON for a project."""

from datetime import datetime, timezone

from models import ReleaseManifestResponse, Scene, StaleReport
from storage import StorageBackend, project_key


def _report_generated_at(report: StaleReport) -> datetime:
    return report.generated_at


def find_latest_stale_report(
    storage: StorageBackend,
    project_id: str,
    base_version: str | None = None,
) -> StaleReport | None:
    prefix = project_key(project_id, "compare")
    keys = storage.list_keys(prefix)
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


def build_release_manifest(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    scenes: list[Scene],
) -> ReleaseManifestResponse:
    scene_ids = [scene.scene_id for scene in scenes]
    latest_report = find_latest_stale_report(storage, project_id, base_version=source_version)
    stale_ids = list(latest_report.stale_scene_ids) if latest_report else []

    return ReleaseManifestResponse(
        project_id=project_id,
        source_version=source_version,
        scene_ids=scene_ids,
        stale_scene_ids=stale_ids,
        generated_at=datetime.now(timezone.utc),
        placeholder_genblaze_manifest=True,
        placeholder_b2_keys=[],
    )


def latest_stale_scene_ids(storage: StorageBackend, project_id: str) -> list[str]:
    report = find_latest_stale_report(storage, project_id, base_version=None)
    return list(report.stale_scene_ids) if report else []
