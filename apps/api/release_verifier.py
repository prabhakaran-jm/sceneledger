"""Release evidence building and hash verification for M3."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from media_placeholders import sha256_hex
from media_pipeline import scene_manifest_key
from models import Scene, SourceChunk, StaleReport
from release_models import (
    RELEASE_MESSAGE_BLOCKED,
    RELEASE_MESSAGE_VERIFIED,
    RELEASE_MESSAGE_WARNING,
    FinalVideoEntry,
    GenblazeProvenance,
    MediaModeSummary,
    PlannerProvenance,
    ReleaseManifestResponse,
    ReleaseSceneAssets,
    ReleaseSceneRecord,
    ReleaseSourceSection,
    ReleaseVerification,
    SourceChunkSummary,
    VerifiedAssetEntry,
    VerifyReleaseResponse,
)
from source_chunks import chunk_hash_map
from storage import StorageBackend, StorageError, project_key

ASSET_ROLES = ("storyboard", "clip", "narration", "captions")


def _text_preview(text: str, limit: int = 80) -> str:
    normalized = text.replace("\n", " ").strip()
    if len(normalized) > limit:
        return normalized[:limit] + "…"
    return normalized


def manifest_content_hash(manifest_dict: dict) -> str:
    payload = {
        key: value
        for key, value in manifest_dict.items()
        if key != "release_manifest_sha256"
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return sha256_hex(canonical.encode("utf-8"))


def finalize_manifest(manifest: ReleaseManifestResponse) -> ReleaseManifestResponse:
    data = manifest.model_dump(mode="json")
    data["release_manifest_sha256"] = manifest_content_hash(data)
    return ReleaseManifestResponse.model_validate(data)


def _scene_media_mode(generators: set[str]) -> str:
    has_placeholder = "placeholder" in generators
    has_genblaze = "genblaze" in generators
    if has_placeholder and has_genblaze:
        return "mixed"
    if has_genblaze:
        return "genblaze"
    return "placeholder"


def _verify_genblaze_manifest(
    storage: StorageBackend,
    scene_id: str,
    manifest_key: str,
    recorded_sha256: str | None,
) -> tuple[bool, list[str]]:
    """Verify a stored Genblaze provenance manifest.

    Checks: object exists, sha256 over stored canonical bytes matches the
    scene manifest record, and the SDK's own canonical hash verifies.
    A scene that claims a Genblaze manifest but fails any check blocks the
    release; scenes without one are not required to have it.
    """
    errors: list[str] = []
    try:
        data = storage.read_bytes_public(manifest_key)
    except (StorageError, FileNotFoundError, OSError):
        errors.append(f"Genblaze manifest missing for {scene_id}: {manifest_key}")
        return False, errors

    if not recorded_sha256:
        errors.append(
            f"Genblaze manifest for {scene_id} has no recorded sha256"
        )
        return False, errors
    if sha256_hex(data) != recorded_sha256:
        errors.append(f"Genblaze manifest hash mismatch for {scene_id}")
        return False, errors

    try:
        from genblaze_core.models.manifest import parse_manifest
    except ImportError:
        errors.append(
            f"Genblaze SDK not installed but release contains a Genblaze "
            f"manifest for {scene_id}. Install requirements-genblaze.txt "
            f"to verify provenance."
        )
        return False, errors

    try:
        manifest = parse_manifest(json.loads(data))
    except Exception:
        errors.append(f"Genblaze manifest for {scene_id} is corrupted or invalid")
        return False, errors
    if not manifest.verify_hash():
        errors.append(
            f"Genblaze manifest canonical hash verification failed for {scene_id}"
        )
        return False, errors

    return True, errors


def _verify_asset_entry(
    storage: StorageBackend, raw: dict
) -> tuple[VerifiedAssetEntry, list[str], bool]:
    errors: list[str] = []
    recorded_sha = raw.get("sha256", "")
    public_key = raw.get("key", "")
    entry = VerifiedAssetEntry(
        key=public_key,
        sha256=recorded_sha,
        content_type=raw.get("content_type", ""),
        generator=raw.get("generator", "placeholder"),
        playable=bool(raw.get("playable", True)),
    )
    try:
        if not public_key or not storage.exists(storage.logical_path(public_key)):
            errors.append(f"Asset missing: {public_key or 'unknown key'}")
            return entry, errors, False
        data = storage.read_bytes_public(public_key)
        computed = sha256_hex(data)
        entry.computed_sha256 = computed
        entry.hash_verified = computed == recorded_sha
        if not entry.hash_verified:
            errors.append(f"Hash mismatch for asset {public_key}")
        return entry, errors, entry.hash_verified
    except StorageError as exc:
        errors.append(f"Failed to read asset: {exc}")
        return entry, errors, False


def _verify_scene_media(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    scene: Scene,
) -> tuple[ReleaseSceneRecord, list[str], bool, set[str], list[str | None]]:
    errors: list[str] = []
    manifest_logical = scene_manifest_key(project_id, source_version, scene.scene_id)
    manifest_public = storage.public_key(manifest_logical)
    generators: set[str] = set()
    genblaze_run_id: str | None = None

    assets = ReleaseSceneAssets()
    media_status = "missing"
    all_hashes_ok = True

    if not storage.exists(manifest_logical):
        errors.append(f"Scene media manifest missing for {scene.scene_id}")
        return (
            ReleaseSceneRecord(
                scene_id=scene.scene_id,
                title=scene.title,
                status=scene.status,
                source_chunk_ids=scene.source_chunk_ids,
                source_chunk_hashes={},
                media_status="missing",
                media_mode="placeholder",
                assets=assets,
                scene_manifest_key=None,
                verification_errors=errors,
            ),
            errors,
            False,
            generators,
            [],
        )

    manifest = storage.read_json(manifest_logical)
    if manifest.get("status") != "complete":
        errors.append(f"Scene media manifest incomplete for {scene.scene_id}")
        return (
            ReleaseSceneRecord(
                scene_id=scene.scene_id,
                title=scene.title,
                status=scene.status,
                source_chunk_ids=scene.source_chunk_ids,
                source_chunk_hashes={},
                media_status="missing",
                media_mode=manifest.get("media_mode", "placeholder"),
                assets=assets,
                scene_manifest_key=manifest_public,
                verification_errors=errors,
            ),
            errors,
            False,
            generators,
            [manifest.get("genblaze_run_id")],
        )

    genblaze_run_id = manifest.get("genblaze_run_id")
    genblaze_manifest_key = manifest.get("genblaze_manifest_key")
    genblaze_manifest_sha256 = manifest.get("genblaze_manifest_sha256")
    genblaze_manifest_verified: bool | None = None
    if genblaze_manifest_key:
        genblaze_manifest_verified, gb_errors = _verify_genblaze_manifest(
            storage, scene.scene_id, genblaze_manifest_key, genblaze_manifest_sha256
        )
        errors.extend(gb_errors)
        if not genblaze_manifest_verified:
            all_hashes_ok = False

    genblaze_tts_manifest_key = manifest.get("genblaze_tts_manifest_key")
    genblaze_tts_manifest_sha256 = manifest.get("genblaze_tts_manifest_sha256")
    genblaze_tts_manifest_verified: bool | None = None
    if genblaze_tts_manifest_key:
        genblaze_tts_manifest_verified, tts_errors = _verify_genblaze_manifest(
            storage,
            f"{scene.scene_id} (TTS)",
            genblaze_tts_manifest_key,
            genblaze_tts_manifest_sha256,
        )
        errors.extend(tts_errors)
        if not genblaze_tts_manifest_verified:
            all_hashes_ok = False

    raw_assets = manifest.get("assets", {})
    scene_assets_invalid = False

    for role in ASSET_ROLES:
        raw = raw_assets.get(role)
        if not raw:
            errors.append(f"Missing {role} entry in scene manifest for {scene.scene_id}")
            scene_assets_invalid = True
            continue
        verified, asset_errors, asset_ok = _verify_asset_entry(storage, raw)
        errors.extend(asset_errors)
        if not asset_ok:
            scene_assets_invalid = True
            all_hashes_ok = False
        generators.add(verified.generator)
        setattr(assets, role, verified)

    if scene_assets_invalid:
        media_status = "invalid"
    else:
        media_status = "complete"

    return (
        ReleaseSceneRecord(
            scene_id=scene.scene_id,
            title=scene.title,
            status=scene.status,
            source_chunk_ids=scene.source_chunk_ids,
            source_chunk_hashes={},
            media_status=media_status,
            media_mode=_scene_media_mode(generators),
            assets=assets,
            scene_manifest_key=manifest_public,
            genblaze_manifest_key=genblaze_manifest_key,
            genblaze_manifest_sha256=genblaze_manifest_sha256,
            genblaze_manifest_verified=genblaze_manifest_verified,
            genblaze_tts_manifest_key=genblaze_tts_manifest_key,
            genblaze_tts_manifest_sha256=genblaze_tts_manifest_sha256,
            genblaze_tts_manifest_verified=genblaze_tts_manifest_verified,
            verification_errors=errors,
        ),
        errors,
        all_hashes_ok and media_status == "complete",
        generators,
        [genblaze_run_id, manifest.get("genblaze_tts_run_id")],
    )


def _verify_final_video(
    storage: StorageBackend, project_id: str, source_version: str
) -> tuple[FinalVideoEntry | None, str | None, bool]:
    """Verify final.mp4 against its sidecar record when one was stitched.

    A skipped final video never affects the release; a stitched-but-missing
    or tampered final.mp4 fails verification (it is part of the evidence).
    Returns (entry, skipped_reason, ok).
    """
    from release_video import load_final_video_record

    record = load_final_video_record(storage, project_id, source_version)
    if record is None:
        return None, None, True
    if not record.get("key"):
        return None, record.get("skipped_reason"), True

    entry = FinalVideoEntry(key=record["key"], sha256=record.get("sha256", ""))
    try:
        data = storage.read_bytes_public(entry.key)
    except (StorageError, FileNotFoundError, OSError):
        entry.hash_verified = False
        return entry, None, False
    entry.computed_sha256 = sha256_hex(data)
    entry.hash_verified = entry.computed_sha256 == entry.sha256
    return entry, None, entry.hash_verified


def _verify_planner_provenance(
    storage: StorageBackend, project_id: str, source_version: str
) -> PlannerProvenance:
    """Load planner metadata from the stored plan and verify its Genblaze manifest.

    Plans without a claimed Genblaze planner manifest need no verification;
    a claimed-but-missing/corrupt/failed manifest blocks the release via
    verification_errors (caller folds them into hash_verified).
    """
    plan_key = project_key(project_id, "plans", source_version, "scenes.json")
    if not storage.exists(plan_key):
        return PlannerProvenance()
    plan = storage.read_json(plan_key)

    provenance = PlannerProvenance(
        planner=plan.get("planner", "deterministic"),
        fallback_reason=plan.get("planner_fallback_reason"),
    )
    genblaze_planner = plan.get("genblaze_planner")
    if not genblaze_planner:
        return provenance

    provenance.genblaze_manifest_key = genblaze_planner.get("manifest_key")
    provenance.genblaze_manifest_sha256 = genblaze_planner.get("manifest_sha256")
    provenance.genblaze_run_id = genblaze_planner.get("run_id")
    provenance.genblaze_model = genblaze_planner.get("model")

    if provenance.genblaze_manifest_key:
        verified, errors = _verify_genblaze_manifest(
            storage,
            "scene planner",
            provenance.genblaze_manifest_key,
            provenance.genblaze_manifest_sha256,
        )
        provenance.genblaze_manifest_verified = verified
        provenance.verification_errors = errors
    return provenance


def _resolve_scenes(
    plan_scenes: list[Scene], stale_report: StaleReport | None
) -> list[Scene]:
    if stale_report is not None:
        return stale_report.scenes
    return plan_scenes


def _build_media_mode_summary(scenes: list[ReleaseSceneRecord]) -> MediaModeSummary:
    placeholder = sum(1 for s in scenes if s.media_mode == "placeholder")
    genblaze = sum(1 for s in scenes if s.media_mode == "genblaze")
    mixed_scenes = sum(1 for s in scenes if s.media_mode == "mixed")
    has_placeholder_assets = any(
        getattr(s.assets, role) and getattr(s.assets, role).generator == "placeholder"
        for s in scenes
        for role in ASSET_ROLES
    )
    has_genblaze_assets = any(
        getattr(s.assets, role) and getattr(s.assets, role).generator == "genblaze"
        for s in scenes
        for role in ASSET_ROLES
    )
    return MediaModeSummary(
        placeholder=placeholder,
        genblaze=genblaze,
        mixed=mixed_scenes > 0 or (has_placeholder_assets and has_genblaze_assets),
    )


def _build_genblaze_provenance(
    scenes: list[ReleaseSceneRecord], run_ids: list[str | None]
) -> GenblazeProvenance:
    asset_count = 0
    manifest_keys: list[str] = []
    manifest_hashes: list[str] = []
    for scene in scenes:
        for role in ASSET_ROLES:
            asset = getattr(scene.assets, role)
            if asset and asset.generator == "genblaze":
                asset_count += 1
        if scene.genblaze_manifest_key:
            manifest_keys.append(scene.genblaze_manifest_key)
            if scene.genblaze_manifest_sha256:
                manifest_hashes.append(scene.genblaze_manifest_sha256)
        if scene.genblaze_tts_manifest_key:
            manifest_keys.append(scene.genblaze_tts_manifest_key)
            if scene.genblaze_tts_manifest_sha256:
                manifest_hashes.append(scene.genblaze_tts_manifest_sha256)
    deduped = sorted({run_id for run_id in run_ids if run_id})
    return GenblazeProvenance(
        present=asset_count > 0 or bool(manifest_keys),
        run_ids=deduped,
        manifest_keys=sorted(manifest_keys),
        manifest_hashes=sorted(manifest_hashes),
        asset_count=asset_count,
    )


def _compute_release_status(
    *,
    hash_verified: bool,
    media_complete: bool,
    stale_scene_ids: list[str],
) -> str:
    if not hash_verified or not media_complete:
        return "blocked"
    if stale_scene_ids:
        return "warning"
    return "verified"


def _status_message(release_status: str) -> str:
    if release_status == "verified":
        return RELEASE_MESSAGE_VERIFIED
    if release_status == "warning":
        return RELEASE_MESSAGE_WARNING
    return RELEASE_MESSAGE_BLOCKED


def build_release_evidence(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    chunks: list[SourceChunk],
    plan_scenes: list[Scene],
    *,
    release_id: str | None = None,
    created_at: datetime | None = None,
) -> ReleaseManifestResponse:
    from release_manifest import find_latest_stale_report

    stale_report = find_latest_stale_report(
        storage, project_id, base_version=source_version
    )
    scenes_for_release = _resolve_scenes(plan_scenes, stale_report)
    chunk_map = chunk_hash_map(chunks)

    scene_records: list[ReleaseSceneRecord] = []
    all_errors: list[str] = []
    all_hashes_ok = True
    media_complete = True
    missing_media: list[str] = []
    invalid_asset_scenes: list[str] = []
    genblaze_run_ids: list[str | None] = []

    for scene in scenes_for_release:
        record, scene_errors, scene_ok, _generators, run_ids = _verify_scene_media(
            storage, project_id, source_version, scene
        )
        record.source_chunk_hashes = {
            chunk_id: chunk_map.get(chunk_id, "")
            for chunk_id in scene.source_chunk_ids
        }
        scene_records.append(record)
        all_errors.extend(scene_errors)
        genblaze_run_ids.extend(run_ids)
        if record.media_status == "missing":
            media_complete = False
            missing_media.append(scene.scene_id)
        if record.media_status == "invalid":
            media_complete = False
            invalid_asset_scenes.append(scene.scene_id)
        if not scene_ok:
            all_hashes_ok = False

    planner_provenance = _verify_planner_provenance(
        storage, project_id, source_version
    )
    if planner_provenance.genblaze_manifest_verified is False:
        all_hashes_ok = False
        all_errors.extend(planner_provenance.verification_errors)

    final_video, final_video_skipped_reason, final_video_ok = _verify_final_video(
        storage, project_id, source_version
    )
    if not final_video_ok:
        all_hashes_ok = False
        if final_video is not None:
            all_errors.append(f"Final video hash mismatch: {final_video.key}")

    stale_scene_ids = [
        scene.scene_id for scene in scenes_for_release if scene.status == "stale"
    ]
    hash_verified = all_hashes_ok and media_complete
    release_status = _compute_release_status(
        hash_verified=hash_verified,
        media_complete=media_complete,
        stale_scene_ids=stale_scene_ids,
    )
    if planner_provenance.genblaze_run_id:
        genblaze_run_ids.append(planner_provenance.genblaze_run_id)
    genblaze_provenance = _build_genblaze_provenance(scene_records, genblaze_run_ids)
    if planner_provenance.genblaze_manifest_key:
        genblaze_provenance.manifest_keys = sorted(
            genblaze_provenance.manifest_keys
            + [planner_provenance.genblaze_manifest_key]
        )
        if planner_provenance.genblaze_manifest_sha256:
            genblaze_provenance.manifest_hashes = sorted(
                genblaze_provenance.manifest_hashes
                + [planner_provenance.genblaze_manifest_sha256]
            )
        genblaze_provenance.present = True
    verification = ReleaseVerification(
        source_chunks_present=True,
        scene_plan_present=True,
        media_manifests_present=all(
            record.media_status == "complete" for record in scene_records
        )
        and len(scene_records) == len(plan_scenes),
        asset_hashes_verified=hash_verified,
        stale_report_applied=stale_report is not None,
        release_current=release_status == "verified",
    )

    manifest = ReleaseManifestResponse(
        release_id=release_id or f"rel-{uuid.uuid4()}",
        project_id=project_id,
        source_version=source_version,
        created_at=created_at or datetime.now(timezone.utc),
        release_status=release_status,
        message=_status_message(release_status),
        storage_backend=storage.backend_name,
        media_mode_summary=_build_media_mode_summary(scene_records),
        genblaze_provenance=genblaze_provenance,
        planner_provenance=planner_provenance,
        final_video=final_video,
        final_video_skipped_reason=final_video_skipped_reason,
        source=ReleaseSourceSection(
            version=source_version,
            chunk_count=len(chunks),
            chunks=[
                SourceChunkSummary(
                    chunk_id=chunk.chunk_id,
                    order=chunk.order,
                    sha256=chunk.sha256,
                    text_preview=_text_preview(chunk.text),
                )
                for chunk in chunks
            ],
        ),
        scenes=scene_records,
        stale_scene_ids=stale_scene_ids,
        missing_media_scene_ids=missing_media,
        invalid_asset_scene_ids=invalid_asset_scenes,
        release_superseded_by_source_version=(
            stale_report.candidate_version if stale_report else None
        ),
        hash_verified=hash_verified,
        placeholder_genblaze_manifest=not genblaze_provenance.present,
        verification=verification,
    )
    return finalize_manifest(manifest)


def verify_stored_release(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    stored: ReleaseManifestResponse,
    chunks: list[SourceChunk],
    plan_scenes: list[Scene],
    *,
    update_manifest: bool = False,
) -> tuple[VerifyReleaseResponse, ReleaseManifestResponse | None]:
    refreshed = build_release_evidence(
        storage,
        project_id,
        source_version,
        chunks,
        plan_scenes,
        release_id=stored.release_id,
        created_at=stored.created_at,
    )

    response = VerifyReleaseResponse(
        project_id=project_id,
        source_version=source_version,
        release_id=stored.release_id,
        release_status=refreshed.release_status,
        message=refreshed.message,
        hash_verified=refreshed.hash_verified,
        verification=refreshed.verification,
        errors=(
            list(refreshed.planner_provenance.verification_errors)
            + [
                error
                for scene in refreshed.scenes
                for error in scene.verification_errors
            ]
        ),
    )

    updated_manifest: ReleaseManifestResponse | None = None
    if update_manifest:
        updated_manifest = refreshed
    return response, updated_manifest
