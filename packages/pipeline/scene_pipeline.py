"""Scene media generator protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from models import Scene


@dataclass(frozen=True)
class GeneratedAsset:
    role: str
    filename: str
    data: bytes
    content_type: str
    generator: str
    playable: bool = True


@dataclass
class SceneMediaContext:
    project_id: str
    source_version: str
    media_mode: str
    temp_dir: str | None = None


@dataclass
class GeneratedSceneAssets:
    assets: list[GeneratedAsset] = field(default_factory=list)
    genblaze_run_id: str | None = None
    placeholder: bool = True
    # Genblaze provenance manifest — the SDK's canonical JSON bytes, stored
    # verbatim (never rewritten) so the SDK's own hash verification round-trips.
    genblaze_manifest_json: bytes | None = None
    genblaze_provider: str | None = None
    genblaze_model: str | None = None


class SceneMediaGenerator(Protocol):
    def generate_scene_assets(
        self, scene: Scene, ctx: SceneMediaContext
    ) -> GeneratedSceneAssets:
        """Generate all scene media assets in memory."""
