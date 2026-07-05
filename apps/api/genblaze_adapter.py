"""Optional Genblaze adapter — DALL-E storyboard when configured; honest placeholders otherwise."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname, urlopen

from genblaze_providers import gmi_tts_voice, openai_tts_voice, provider_chain
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
    try:
        import genblaze_core  # noqa: F401
    except ImportError:
        return False
    return bool(provider_chain("image"))


def assert_configured() -> None:
    mode = os.getenv("SCENELEDGER_MEDIA_MODE", "placeholder").strip().lower()
    if mode != "genblaze":
        raise MediaConfigurationError(
            "Genblaze mode requires SCENELEDGER_MEDIA_MODE=genblaze"
        )
    try:
        import genblaze_core  # noqa: F401
    except ImportError as exc:
        raise MediaConfigurationError(
            "Genblaze packages not installed. "
            "Install with: pip install -r requirements-genblaze.txt"
        ) from exc
    if not provider_chain("image"):
        raise MediaConfigurationError(
            "Genblaze mode requires a configured provider: set GMI_API_KEY "
            "(preferred via SCENELEDGER_GENBLAZE_PROVIDER=gmi) or OPENAI_API_KEY"
        )


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


@dataclass(frozen=True)
class GenblazeRunProvenance:
    """SDK provenance captured from a pipeline run — canonical bytes, untouched
    except for scrubbing signed-URL credentials (excluded from the canonical
    hash, so the stored manifest still verifies)."""

    run_id: str | None
    manifest_json: bytes | None
    provider: str | None
    model: str | None
    provider_name: str | None = None  # short name: "gmi" | "openai"


@dataclass(frozen=True)
class _PipelineOutput:
    data: bytes
    media_type: str | None
    provenance: GenblazeRunProvenance


def _run_generation_step(
    *,
    pipeline_name: str,
    provider_obj,
    provider_name: str,
    model: str,
    prompt: str,
    modality,
    temp_dir: Path,
    **params,
) -> _PipelineOutput:
    """Run one Genblaze pipeline step and capture bytes + provenance.

    Raises MediaConfigurationError on any failure so callers can try the
    next provider in the chain.
    """
    from genblaze_core import Pipeline
    from genblaze_core._asset_url import strip_asset_url_credentials
    from genblaze_core.exceptions import PipelineError, ProviderError

    try:
        result = (
            Pipeline(pipeline_name)
            .step(
                provider_obj,
                model=model,
                prompt=prompt,
                modality=modality,
                **params,
            )
            .run(raise_on_failure=True)
        )
    except (ProviderError, PipelineError) as exc:
        raise MediaConfigurationError(
            f"Genblaze {provider_name} generation failed for model {model!r}: {exc}"
        ) from exc

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

    # Scrub signed-URL credentials before persisting the manifest. Asset URLs
    # are excluded from the schema-1.5 canonical hash, so verify_hash() still
    # round-trips on the stored bytes.
    manifest_json: bytes | None = None
    if getattr(result, "manifest", None) is not None:
        for step in result.run.steps:
            for run_asset in list(step.assets) + list(step.inputs):
                url = getattr(run_asset, "url", None)
                if url and url.startswith("http"):
                    run_asset.url = strip_asset_url_credentials(url)
        manifest_json = result.manifest.to_canonical_json().encode("utf-8")

    return _PipelineOutput(
        data=data,
        media_type=getattr(asset, "media_type", None),
        provenance=GenblazeRunProvenance(
            run_id=getattr(result.run, "run_id", None),
            manifest_json=manifest_json,
            provider=getattr(steps[0], "provider", None),
            model=getattr(steps[0], "model", None) or model,
            provider_name=provider_name,
        ),
    )


def _generate_genblaze_storyboard(
    scene: Scene, temp_dir: Path
) -> tuple[GeneratedAsset, GenblazeRunProvenance]:
    """Generate the storyboard via the preferred provider chain (gmi → openai)."""
    from genblaze_core import Modality

    failures: list[str] = []
    for choice in provider_chain("image"):
        if choice.name == "gmi":
            from genblaze_gmicloud import GMICloudImageProvider

            provider_obj = GMICloudImageProvider()
        else:
            from genblaze_openai import DalleProvider

            provider_obj = DalleProvider(output_dir=str(temp_dir.resolve()))

        try:
            output = _run_generation_step(
                pipeline_name=f"sceneledger-{scene.scene_id}",
                provider_obj=provider_obj,
                provider_name=choice.name,
                model=choice.model,
                prompt=scene.visual_prompt,
                modality=Modality.IMAGE,
                temp_dir=temp_dir,
            )
        except MediaConfigurationError as exc:
            failures.append(str(exc))
            continue

        is_jpeg = (output.media_type or "").lower() == "image/jpeg"
        return (
            GeneratedAsset(
                role="storyboard",
                filename="storyboard.jpg" if is_jpeg else "storyboard.png",
                data=output.data,
                content_type="image/jpeg" if is_jpeg else "image/png",
                generator="genblaze",
                playable=True,
                provider=choice.name,
                model=output.provenance.model,
            ),
            output.provenance,
        )

    raise MediaConfigurationError(
        "Genblaze storyboard generation failed for all configured providers: "
        + "; ".join(failures)
    )


def _gmi_tts_registry():
    """Registry for GMI TTS with the prompt→text payload mapping.

    GMI's TTS queue requires the input under ``text`` (and voices under
    ``voice_id``); the SDK's stock audio family only aliases voice. Passing
    a custom ModelRegistry is the documented override (live-verified with
    minimax-tts-speech-2.6-turbo).
    """
    import re

    from genblaze_core.models.enums import Modality
    from genblaze_core.providers import ModelFamily, ModelRegistry, ModelSpec
    from genblaze_core.providers.params import ParamSurface

    surface = ParamSurface.for_modality(Modality.AUDIO).with_aliases(
        voice="voice_id", prompt="text"
    )
    family = ModelFamily(
        name="sceneledger-gmi-tts",
        pattern=re.compile(
            r"^(?:elevenlabs-tts|minimax-tts|inworld-tts)", re.IGNORECASE
        ),
        spec_template=ModelSpec(
            model_id="*",
            modality=Modality.AUDIO,
            extras={"envelope_key": "payload", "is_music": False},
            **surface.build(),
        ),
        description="SceneLedger GMI TTS family with prompt→text mapping",
        canonical_slug=str.lower,
    )
    return ModelRegistry(
        provider_families=(family,),
        fallback=ModelSpec(model_id="*", modality=Modality.AUDIO),
    )


def _generate_genblaze_narration(
    scene: Scene, temp_dir: Path
) -> tuple[GeneratedAsset, GenblazeRunProvenance]:
    """Generate narration via the preferred provider chain (gmi → openai).

    Raises MediaConfigurationError when every provider fails — the caller
    falls back to placeholder narration and marks it honestly.
    """
    from genblaze_core import Modality

    failures: list[str] = []
    for choice in provider_chain("tts"):
        if choice.name == "gmi":
            from genblaze_gmicloud import GMICloudAudioProvider

            provider_obj = GMICloudAudioProvider(models=_gmi_tts_registry())
            # Empty voice = the model's default; GMI voice ids are model-specific.
            voice = gmi_tts_voice()
            params = {"voice": voice} if voice else {}
        else:
            from genblaze_openai import OpenAITTSProvider

            provider_obj = OpenAITTSProvider(output_dir=str(temp_dir.resolve()))
            params = {"voice": openai_tts_voice(), "response_format": "mp3"}

        try:
            output = _run_generation_step(
                pipeline_name=f"sceneledger-{scene.scene_id}-tts",
                provider_obj=provider_obj,
                provider_name=choice.name,
                model=choice.model,
                prompt=scene.narration,
                modality=Modality.AUDIO,
                temp_dir=temp_dir,
                **params,
            )
        except MediaConfigurationError as exc:
            failures.append(str(exc))
            continue

        is_wav = (output.media_type or "").lower() == "audio/wav"
        return (
            GeneratedAsset(
                role="narration",
                filename="narration.wav" if is_wav else "narration.mp3",
                data=output.data,
                content_type="audio/wav" if is_wav else "audio/mpeg",
                generator="genblaze",
                playable=True,
                provider=choice.name,
                model=output.provenance.model,
            ),
            output.provenance,
        )

    raise MediaConfigurationError(
        "Genblaze TTS narration failed for all configured providers: "
        + "; ".join(failures)
    )


class GenblazeAdapter:
    def generate_scene_assets(
        self, scene: Scene, ctx: SceneMediaContext
    ) -> GeneratedSceneAssets:
        del ctx
        assert_configured()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            storyboard, provenance = _generate_genblaze_storyboard(scene, temp_path)

            # TTS narration: real speech when the provider succeeds; honest
            # placeholder fallback otherwise. Never fake speech generation.
            tts_provenance: GenblazeRunProvenance | None = None
            try:
                narration_asset, tts_provenance = _generate_genblaze_narration(
                    scene, temp_path
                )
            except MediaConfigurationError:
                item = generate_narration_wav(scene)
                narration_asset = GeneratedAsset(
                    role=item.role,
                    filename=item.filename,
                    data=item.data,
                    content_type=item.content_type,
                    generator="placeholder",
                    playable=item.playable,
                )

            clip_item = generate_clip_asset(scene, storyboard.data)
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
                narration_asset,
                GeneratedAsset(
                    role=captions_item.role,
                    filename=captions_item.filename,
                    data=captions_item.data,
                    content_type=captions_item.content_type,
                    generator="placeholder",
                    playable=captions_item.playable,
                ),
            ]

            tts_voice = None
            if tts_provenance:
                tts_voice = (
                    (gmi_tts_voice() or None)
                    if tts_provenance.provider_name == "gmi"
                    else openai_tts_voice()
                )
            return GeneratedSceneAssets(
                assets=assets,
                genblaze_run_id=provenance.run_id,
                placeholder=True,
                genblaze_manifest_json=provenance.manifest_json,
                genblaze_provider=provenance.provider,
                genblaze_model=provenance.model,
                genblaze_tts_manifest_json=(
                    tts_provenance.manifest_json if tts_provenance else None
                ),
                genblaze_tts_run_id=(
                    tts_provenance.run_id if tts_provenance else None
                ),
                genblaze_tts_model=(
                    tts_provenance.model if tts_provenance else None
                ),
                genblaze_tts_voice=tts_voice,
                genblaze_tts_provider=(
                    tts_provenance.provider if tts_provenance else None
                ),
            )
