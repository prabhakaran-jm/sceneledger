"""Optional final.mp4 composition — concatenate scene clips at release time.

Never blocks release evidence: any failure records a skip reason in a
sidecar (releases/{version}/final-video.json) and the release proceeds.
The sidecar is the recorded-hash home for verification, mirroring how
scene-asset-manifest.json anchors per-scene asset hashes.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from media_pipeline import scene_manifest_key
from media_placeholders import sha256_hex
from models import Scene
from storage import StorageBackend, project_key

SKIP_NOT_PLAYABLE = (
    "Final stitched video skipped because one or more scene clips are not playable."
)
SKIP_NO_FFMPEG = "Final stitched video skipped because ffmpeg is not available."


def final_video_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "releases", source_version, "final.mp4")


def final_video_record_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "releases", source_version, "final-video.json")


def load_final_video_record(
    storage: StorageBackend, project_id: str, source_version: str
) -> dict[str, Any] | None:
    key = final_video_record_key(project_id, source_version)
    if not storage.exists(key):
        return None
    try:
        return storage.read_json(key)
    except Exception:
        return None


def _collect_clip_keys(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    scenes: list[Scene],
) -> list[str] | None:
    """Return playable mp4 clip public keys for all scenes, or None."""
    keys: list[str] = []
    for scene in scenes:
        manifest_logical = scene_manifest_key(
            project_id, source_version, scene.scene_id
        )
        if not storage.exists(manifest_logical):
            return None
        manifest = storage.read_json(manifest_logical)
        clip = (manifest.get("assets") or {}).get("clip") or {}
        key = clip.get("key", "")
        if not (clip.get("playable") and key.endswith(".mp4")):
            return None
        keys.append(key)
    return keys


def _write_record(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    payload: dict[str, Any],
) -> None:
    storage.write_json(
        final_video_record_key(project_id, source_version), payload
    )


def maybe_stitch_final_video(
    storage: StorageBackend,
    project_id: str,
    source_version: str,
    scenes: list[Scene],
) -> dict[str, Any]:
    """Stitch scene clips into final.mp4 when safe; record outcome either way.

    Returns the sidecar record: {"key", "sha256", "skipped_reason"}.
    """
    skipped = {"key": None, "sha256": None, "skipped_reason": SKIP_NOT_PLAYABLE}

    clip_keys = _collect_clip_keys(storage, project_id, source_version, scenes)
    if not clip_keys:
        _write_record(storage, project_id, source_version, skipped)
        return skipped

    if shutil.which("ffmpeg") is None:
        skipped["skipped_reason"] = SKIP_NO_FFMPEG
        _write_record(storage, project_id, source_version, skipped)
        return skipped

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            list_lines = []
            for index, public_key in enumerate(clip_keys):
                clip_path = temp_path / f"clip-{index:03d}.mp4"
                clip_path.write_bytes(storage.read_bytes_public(public_key))
                list_lines.append(f"file '{clip_path.as_posix()}'")
            list_file = temp_path / "concat.txt"
            list_file.write_text("\n".join(list_lines), encoding="utf-8")
            out_path = temp_path / "final.mp4"

            # Clips come from the same generator/codec settings, so a
            # stream-copy concat is safe and fast.
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c",
                    "copy",
                    str(out_path),
                ],
                capture_output=True,
                timeout=120,
            )
            if result.returncode != 0 or not out_path.is_file():
                raise RuntimeError("ffmpeg concat failed")

            data = out_path.read_bytes()
    except Exception:
        # ponytail: any composition failure degrades to a clean skip —
        # final video must never block release evidence.
        skipped["skipped_reason"] = (
            "Final stitched video skipped because clip concatenation failed."
        )
        _write_record(storage, project_id, source_version, skipped)
        return skipped

    public_key = storage.write_bytes(
        final_video_key(project_id, source_version),
        data,
        content_type="video/mp4",
    )
    record = {
        "key": public_key,
        "sha256": sha256_hex(data),
        "skipped_reason": None,
    }
    _write_record(storage, project_id, source_version, record)
    return record
