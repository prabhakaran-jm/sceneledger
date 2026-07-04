"""Optional Genblaze adapter — DALL-E storyboard when configured; honest placeholders otherwise."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname, urlopen

from media_placeholders import (
    generate_captions_vtt,
    generate_clip_asset,
    generate_narration_wav,
)
from models import Scene

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "packages" / "pipeline"
import sys

if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from scene_pipeline import GeneratedAsset, GeneratedSceneAssets, SceneMediaContext


class MediaConfigurationError(Exception):
    """Raised when genblaze mode is misconfigured. Messages must not contain secrets."""


def is_configured() -> bool:
    if os.getenv("SCENELEDGER_MEDIA_MODE", "placeholder").strip().lower() != "genblaze":
        return False
    if not os.getenv("OPENAI_API_KEY", "").strip():
        return False
    try:
        import genblaze_core  # noqa: F401
        import genblaze_openai  # noqa: F401
    except ImportError:
        return False
    return True


def assert_configured() -> None:
    mode = os.getenv("SCENELEDGER_MEDIA_MODE", "placeholder").strip().lower()
    if mode != "genblaze":
        raise MediaConfigurationError(
            "Genblaze mode requires SCENELEDGER_MEDIA_MODE=genblaze"
        )
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise MediaConfigurationError(
            "Genblaze mode requires OPENAI_API_KEY to be set"
        )
    try:
        import genblaze_core  # noqa: F401
        import genblaze_openai  # noqa: F401
    except ImportError as exc:
        raise MediaConfigurationError(
            "Genblaze packages not installed. "
            "Install with: pip install -r requirements-genblaze.txt"
        ) from exc


def _image_model() -> str:
    return os.getenv("SCENELEDGER_GENBLAZE_IMAGE_MODEL", "gpt-image-1").strip()


def _file_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.netloc:
        # Genblaze on Windows: file://C%3A%5CUsers%5C... (path in netloc)
        path_str = unquote(parsed.netloc + parsed.path)
    else:
        path_str = unquote(url2pathname(parsed.path))
    return Path(path_str)


def _is_under(path: Path, root: Path) -> bool:
    path_res = path.resolve()
    root_res = root.resolve()
    if os.name == "nt":
        path_str = str(path_res).lower()
        root_str = str(root_res).lower()
        return path_str == root_str or path_str.startswith(root_str + "\\")
    try:
        path_res.relative_to(root_res)
        return True
    except ValueError:
        return path_res == root_res


def _read_file_asset(url: str, temp_root: Path) -> bytes:
    temp_resolved = temp_root.resolve()
    resolved = _file_url_to_path(url)
    if not resolved.is_absolute():
        resolved = (temp_resolved / resolved).resolve()
    else:
        resolved = resolved.resolve()

    if _is_under(resolved, temp_resolved) and resolved.is_file():
        return resolved.read_bytes()

    basename = _file_url_to_path(url).name
    if basename:
        for candidate in temp_resolved.rglob(basename):
            if candidate.is_file() and _is_under(candidate, temp_resolved):
                return candidate.read_bytes()

    raise MediaConfigurationError(
        "Genblaze asset path is outside temp output directory"
    )


def _read_asset_bytes(url: str, temp_root: Path, timeout: float = 30.0) -> bytes:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme == "file":
        return _read_file_asset(url, temp_root)

    if scheme == "https":
        with urlopen(url, timeout=timeout) as response:
            return response.read()

    raise MediaConfigurationError(f"Unsupported Genblaze asset URL scheme: {scheme}")


def _generate_genblaze_storyboard(
    scene: Scene, temp_dir: Path
) -> tuple[GeneratedAsset, str | None]:
    from genblaze_core import Modality, Pipeline
    from genblaze_core.exceptions import ProviderError
    from genblaze_openai import DalleProvider

    model = _image_model()
    output_dir = str(temp_dir.resolve())
    try:
        result = (
            Pipeline(f"sceneledger-{scene.scene_id}")
            .step(
                DalleProvider(output_dir=output_dir),
                model=model,
                prompt=scene.visual_prompt,
                modality=Modality.IMAGE,
            )
            .run()
        )
    except ProviderError as exc:
        raise MediaConfigurationError(
            f"Genblaze storyboard generation failed for model {model!r}: {exc}"
        ) from exc

    run_id: str | None = None
    if getattr(result, "manifest", None) is not None:
        run_id = getattr(result.manifest, "run_id", None) or getattr(
            result.manifest, "id", None
        )

    steps = getattr(result.run, "steps", None) or []
    if not steps:
        raise MediaConfigurationError("Genblaze pipeline returned no steps")
    assets = getattr(steps[0], "assets", None) or []
    if not assets:
        raise MediaConfigurationError("Genblaze pipeline returned no assets")

    asset = assets[0]
    asset_url = getattr(asset, "url", None)
    if not asset_url:
        raise MediaConfigurationError("Genblaze asset has no URL")

    data = _read_asset_bytes(asset_url, temp_dir)

    return (
        GeneratedAsset(
            role="storyboard",
            filename="storyboard.png",
            data=data,
            content_type="image/png",
            generator="genblaze",
            playable=True,
        ),
        run_id,
    )


class GenblazeAdapter:
    def generate_scene_assets(
        self, scene: Scene, ctx: SceneMediaContext
    ) -> GeneratedSceneAssets:
        del ctx
        assert_configured()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            storyboard, run_id = _generate_genblaze_storyboard(scene, temp_path)

            clip_item = generate_clip_asset(scene, storyboard.data)
            narration_item = generate_narration_wav(scene)
            captions_item = generate_captions_vtt(scene)

            assets = [
                storyboard,
                GeneratedAsset(
                    role=clip_item.role,
                    filename=clip_item.filename,
                    data=clip_item.data,
                    content_type=clip_item.content_type,
                    generator="placeholder",
                    playable=clip_item.playable,
                ),
                GeneratedAsset(
                    role=narration_item.role,
                    filename=narration_item.filename,
                    data=narration_item.data,
                    content_type=narration_item.content_type,
                    generator="placeholder",
                    playable=narration_item.playable,
                ),
                GeneratedAsset(
                    role=captions_item.role,
                    filename=captions_item.filename,
                    data=captions_item.data,
                    content_type=captions_item.content_type,
                    generator="placeholder",
                    playable=captions_item.playable,
                ),
            ]

            return GeneratedSceneAssets(
                assets=assets,
                genblaze_run_id=run_id,
                placeholder=True,
            )
