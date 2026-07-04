"""Build release manifest JSON for a project."""

from datetime import datetime, timezone

from models import Project, ReleaseManifest


def build_release_manifest(project: Project) -> ReleaseManifest:
    scene_ids = [scene.scene_id for scene in project.scenes]
    stale_ids = list(project.stale_scene_ids)

    placeholder_b2_keys = [
        f"projects/{project.project_id}/sources/v{project.source_version}/source.txt",
        f"projects/{project.project_id}/manifests/release-v{project.source_version}.json",
    ]
    for scene in project.scenes:
        placeholder_b2_keys.extend(
            [
                f"projects/{project.project_id}/scenes/{scene.scene_id}/video.mp4",
                f"projects/{project.project_id}/scenes/{scene.scene_id}/narration.mp3",
                f"projects/{project.project_id}/scenes/{scene.scene_id}/captions.vtt",
            ]
        )

    return ReleaseManifest(
        project_id=project.project_id,
        source_version=project.source_version,
        scene_ids=scene_ids,
        stale_scene_ids=stale_ids,
        generated_at=datetime.now(timezone.utc),
        placeholder_genblaze_manifest={
            "pipeline": "sceneledger-mvp",
            "status": "placeholder",
            "steps": [
                "storyboard",
                "video",
                "narration",
                "captions",
                "compose",
            ],
            "note": "Genblaze orchestration not wired in MVP scaffold",
        },
        placeholder_b2_keys=placeholder_b2_keys,
    )
