"""Placeholder media adapter — deterministic assets without provider keys."""

from __future__ import annotations

from media_placeholders import generate_placeholder_assets

from models import Scene
from scene_pipeline import (
    GeneratedAsset,
    GeneratedSceneAssets,
    SceneMediaContext,
)


class PlaceholderAdapter:
    def generate_scene_assets(
        self, scene: Scene, ctx: SceneMediaContext
    ) -> GeneratedSceneAssets:
        del ctx
        assets = [
            GeneratedAsset(
                role=item.role,
                filename=item.filename,
                data=item.data,
                content_type=item.content_type,
                generator=item.generator,
                playable=item.playable,
            )
            for item in generate_placeholder_assets(scene)
        ]
        return GeneratedSceneAssets(
            assets=assets,
            genblaze_run_id=None,
            placeholder=True,
        )
