"""Media generation orchestration for M2."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from media_placeholders import sha256_hex
from media_models import (
    AssetEntry,
    GenerateMediaRequest,
    GenerateMediaResponse,
    ProjectMediaResponse,
    SceneAssetRefs,
    SceneMediaResult,
)
from models import Scene
from storage import StorageBackend, project_key

from genblaze_adapter import GenblazeAdapter, MediaConfigurationError

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "packages" / "pipeline"
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from placeholder_adapter import PlaceholderAdapter  # noqa: E402


class MediaError(Exception):
    """Raised when media operations fail. Messages must not contain secrets."""


def get_media_mode() -> str:
    mode = os.getenv("SCENELEDGER_MEDIA_MODE", "placeholder").strip().lower()
    if mode in {"", "placeholder"}:
        return "placeholder"
    if mode == "genblaze":
        return "genblaze"
    raise MediaError(
        f"Unknown SCENELEDGER_MEDIA_MODE: {mode!r}. Use 'placeholder' or 'genblaze'."
    )


def media_asset_key(
    project_id: str, source_version: str, scene_id: str, filename: str
) -> str:
    return project_key(
        project_id, "media", source_version, scene_id, filename
    )


def scene_manifest_key(project_id: str, source_version: str, scene_id: str) -> str:
    return media_asset_key(
        project_id, source_version, scene_id, "scene-asset-manifest.json"
    )


def _get_adapter():
    mode = get_media_mode()
    if mode == "placeholder":
        return PlaceholderAdapter()
    if mode == "genblaze":
        return GenblazeAdapter()
    raise MediaError(f"Unsupported media mode: {mode}")


def _manifest_is_complete(storage: StorageBackend, manifest_key: str) -> bool:
    if not storage.exists(manifest_key):
        return False
    try:
        manifest = storage.read_json(manifest_key)
    except Exception:
        return False
    return manifest.get("status") == "complete"


def _build_manifest_payload(
    *,
    media_mode: str,
    storage: StorageBackend,
    written_assets: dict[str, AssetEntry],
    genblaze_run_id: str | None,
    placeholder: bool,
) -> dict:
    return {
        "status": "complete",
        "media_mode": media_mode,
        "placeholder": placeholder,
        "genblaze_run_id": genblaze_run_id,
        "assets": {
            role: entry.model_dump(mode="json")
            for role, entry in written_assets.items()
        },
    }


def _write_scene_media(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    scene: Scene,
    force: bool,
) -> SceneMediaResult:
    manifest_key_logical = scene_manifest_key(project_id, source_version, scene.scene_id)
    manifest_public = storage.public_key(manifest_key_logical)

    if not force and _manifest_is_complete(storage, manifest_key_logical):
        manifest = storage.read_json(manifest_key_logical)
        assets = _assets_from_manifest(manifest, manifest_public)
        return SceneMediaResult(
            scene_id=scene.scene_id,
            status="skipped",
            media_mode=manifest.get("media_mode", get_media_mode()),
            assets=assets,
            storage_keys=[manifest_public],
        )

    media_mode = get_media_mode()
    if media_mode == "genblaze":
        try:
            adapter = _get_adapter()
        except MediaConfigurationError as exc:
            raise MediaError(str(exc)) from exc
    else:
        adapter = _get_adapter()

    from scene_pipeline import SceneMediaContext

    ctx = SceneMediaContext(
        project_id=project_id,
        source_version=source_version,
        media_mode=media_mode,
    )
    try:
        generated = adapter.generate_scene_assets(scene, ctx)
    except MediaConfigurationError as exc:
        raise MediaError(str(exc)) from exc

    written_assets: dict[str, AssetEntry] = {}
    storage_keys: list[str] = []

    for asset in generated.assets:
        logical = media_asset_key(
            project_id, source_version, scene.scene_id, asset.filename
        )
        public_key = storage.write_bytes(
            logical, asset.data, content_type=asset.content_type
        )
        storage_keys.append(public_key)
        written_assets[asset.role] = AssetEntry(
            key=public_key,
            sha256=sha256_hex(asset.data),
            content_type=asset.content_type,
            generator=asset.generator,
            playable=asset.playable,
        )

    manifest_payload = _build_manifest_payload(
        media_mode=media_mode,
        storage=storage,
        written_assets=written_assets,
        genblaze_run_id=generated.genblaze_run_id,
        placeholder=generated.placeholder,
    )
    manifest_written = storage.write_json(manifest_key_logical, manifest_payload)
    storage_keys.append(manifest_written)

    assets = SceneAssetRefs(
        storyboard=written_assets["storyboard"],
        clip=written_assets["clip"],
        narration=written_assets["narration"],
        captions=written_assets["captions"],
        manifest=manifest_written,
    )

    return SceneMediaResult(
        scene_id=scene.scene_id,
        status="complete",
        media_mode=media_mode,
        assets=assets,
        storage_keys=storage_keys,
    )


def _assets_from_manifest(
    manifest: dict, manifest_public_key: str
) -> SceneAssetRefs:
    assets = manifest.get("assets", {})

    def _entry(role: str) -> AssetEntry:
        raw = assets[role]
        return AssetEntry.model_validate(raw)

    return SceneAssetRefs(
        storyboard=_entry("storyboard"),
        clip=_entry("clip"),
        narration=_entry("narration"),
        captions=_entry("captions"),
        manifest=manifest_public_key,
    )


def generate_project_media(
    storage: StorageBackend,
    project_id: str,
    request: GenerateMediaRequest,
    scenes: list[Scene],
) -> GenerateMediaResponse:
    if request.scene_ids:
        scene_map = {scene.scene_id: scene for scene in scenes}
        missing = [sid for sid in request.scene_ids if sid not in scene_map]
        if missing:
            raise MediaError(f"Unknown scene IDs: {', '.join(missing)}")
        target_scenes = [scene_map[sid] for sid in request.scene_ids]
    else:
        target_scenes = scenes

    media_mode = get_media_mode()
    if media_mode == "genblaze":
        try:
            from genblaze_adapter import assert_configured

            assert_configured()
        except MediaConfigurationError as exc:
            raise MediaError(str(exc)) from exc

    results: list[SceneMediaResult] = []
    all_keys: list[str] = []

    for scene in target_scenes:
        result = _write_scene_media(
            storage, project_id, request.source_version, scene, request.force
        )
        results.append(result)
        all_keys.extend(result.storage_keys)

    return GenerateMediaResponse(
        project_id=project_id,
        source_version=request.source_version,
        media_mode=media_mode,
        scenes=results,
        storage_keys=sorted(set(all_keys)),
    )


def load_project_media(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
) -> ProjectMediaResponse:
    prefix = project_key(project_id, "media", source_version)
    keys = storage.list_prefix(prefix)
    manifest_keys = sorted(k for k in keys if k.endswith("/scene-asset-manifest.json"))

    scenes: list[SceneMediaResult] = []
    for manifest_logical in manifest_keys:
        manifest = storage.read_json(manifest_logical)
        parts = manifest_logical.split("/")
        scene_id = parts[-2] if len(parts) >= 2 else "unknown"
        manifest_public = storage.public_key(manifest_logical)
        assets = _assets_from_manifest(manifest, manifest_public)
        scenes.append(
            SceneMediaResult(
                scene_id=scene_id,
                status=manifest.get("status", "unknown"),
                media_mode=manifest.get("media_mode", "placeholder"),
                assets=assets,
                storage_keys=[manifest_public],
            )
        )

    return ProjectMediaResponse(
        project_id=project_id,
        source_version=source_version,
        current_media_mode=get_media_mode(),
        scenes=sorted(scenes, key=lambda item: item.scene_id),
    )
