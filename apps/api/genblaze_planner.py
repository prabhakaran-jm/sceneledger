"""Genblaze chat scene planner with strict validation and deterministic fallback.

The LLM writes scene content (title, narration, visual prompt); the
scene→chunk mapping is validated against the same deterministic mapping the
fallback planner uses, so the demo guarantee (scene-00N ↔ chunk-00N, only
scene-003 stale after a chunk-003 change) holds regardless of which planner
ran. Any deviation falls back to the deterministic planner with a recorded
reason.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from genblaze_providers import provider_chain
from models import Scene, SourceChunk
from scene_planner import plan_scenes

SCENE_COUNT = 3

_SYSTEM_PROMPT = (
    "You are a training-video scene planner. Given numbered source chunks "
    "from a procedure document, write one scene per chunk, in order. "
    f"Produce exactly {SCENE_COUNT} scenes. Scene N must cover chunk N only. "
    "For each scene write: a short imperative title (max 8 words), narration "
    "that faithfully restates the chunk's instruction in one or two clear "
    "spoken sentences without adding facts, and a visual_prompt describing a "
    "single storyboard frame for a workplace training video. Do not invent "
    "steps that are not in the source."
)


class PlannedSceneOutput(BaseModel):
    # extra="forbid" emits additionalProperties:false — required by OpenAI
    # strict json_schema mode.
    model_config = ConfigDict(extra="forbid")

    title: str
    narration: str
    visual_prompt: str
    source_chunk_ids: list[str]


class ScenePlanOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenes: list[PlannedSceneOutput]


@dataclass
class PlannerResult:
    scenes: list[Scene]
    planner: str  # "genblaze-chat" | "deterministic"
    fallback_reason: str | None = None
    # SDK canonical manifest bytes for the chat run — stored verbatim.
    manifest_json: bytes | None = None
    run_id: str | None = None
    model: str | None = None
    provider: str | None = None  # "gmi" | "openai" when planner ran


def _planner_enabled() -> tuple[bool, str | None]:
    """Genblaze planner runs only in genblaze mode with a configured provider."""
    mode = os.getenv("SCENELEDGER_MEDIA_MODE", "placeholder").strip().lower()
    if mode != "genblaze":
        return False, "media mode is placeholder"
    if not provider_chain("chat"):
        return False, "no Genblaze provider configured (set GMI_API_KEY or OPENAI_API_KEY)"
    return True, None


def _expected_chunk_ids(chunks: list[SourceChunk]) -> list[str]:
    """Deterministic scene→chunk mapping (mirrors scene_planner behavior)."""
    ids = []
    for index in range(SCENE_COUNT):
        chunk = chunks[index] if index < len(chunks) else chunks[-1]
        ids.append(chunk.chunk_id)
    return ids


def _validate_plan(
    output: ScenePlanOutput, chunks: list[SourceChunk]
) -> tuple[list[Scene] | None, str | None]:
    """Strictly validate LLM output. Returns (scenes, None) or (None, reason)."""
    if len(output.scenes) != SCENE_COUNT:
        return None, f"expected {SCENE_COUNT} scenes, got {len(output.scenes)}"

    known_ids = {chunk.chunk_id for chunk in chunks}
    expected = _expected_chunk_ids(chunks)
    scenes: list[Scene] = []
    for index, planned in enumerate(output.scenes):
        scene_num = index + 1
        if not planned.source_chunk_ids:
            return None, f"scene {scene_num} has no source_chunk_ids"
        unknown = [cid for cid in planned.source_chunk_ids if cid not in known_ids]
        if unknown:
            return None, f"scene {scene_num} references unknown chunks: {unknown}"
        if planned.source_chunk_ids != [expected[index]]:
            return None, (
                f"scene {scene_num} chunk mapping {planned.source_chunk_ids} "
                f"deviates from required [{expected[index]}]"
            )
        if not (
            planned.title.strip()
            and planned.narration.strip()
            and planned.visual_prompt.strip()
        ):
            return None, f"scene {scene_num} has an empty field"
        scenes.append(
            Scene(
                scene_id=f"scene-{scene_num:03d}",
                title=planned.title.strip(),
                narration=planned.narration.strip(),
                visual_prompt=planned.visual_prompt.strip(),
                source_chunk_ids=list(planned.source_chunk_ids),
                status="current",
            )
        )
    return scenes, None


def _build_planner_manifest(
    *,
    provider: str,
    model: str,
    prompt: str,
    scenes: list[Scene],
    plan_asset_url: str,
    tokens_in: int | None,
    tokens_out: int | None,
) -> tuple[bytes, str]:
    """Build a hash-verified Genblaze manifest for the chat planning run.

    chat() sits outside the SDK's Pipeline machinery and returns no manifest,
    so we record the run with the SDK's own Run/Step/Asset models and
    Manifest.from_run — the stored bytes verify with parse_manifest().
    The output asset's sha256 covers the canonical JSON of the generated
    scene list, so anyone can recompute it from the stored plan.
    """
    from genblaze_core.models.asset import Asset
    from genblaze_core.models.enums import Modality, RunStatus, StepStatus
    from genblaze_core.models.manifest import Manifest
    from genblaze_core.models.run import Run
    from genblaze_core.models.step import Step

    from media_placeholders import sha256_hex

    scenes_canonical = json.dumps(
        [scene.model_dump(mode="json") for scene in scenes],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    step = Step(
        provider=provider,
        model=model,
        modality=Modality.TEXT,
        prompt=prompt,
        status=StepStatus.SUCCEEDED,
        provider_payload={
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        },
        metadata={"sceneledger_step": "scene-planning"},
    )
    step.assets.append(
        Asset(
            url=plan_asset_url,
            media_type="application/json",
            sha256=sha256_hex(scenes_canonical),
            size_bytes=len(scenes_canonical),
        )
    )
    run = Run(
        name="sceneledger-scene-plan",
        status=RunStatus.COMPLETED,
        steps=[step],
    )
    manifest = Manifest.from_run(run)
    return manifest.to_canonical_json().encode("utf-8"), run.run_id


def plan_scenes_with_planner(
    chunks: list[SourceChunk], *, plan_asset_url: str
) -> PlannerResult:
    """Plan scenes via Genblaze chat when configured; deterministic otherwise.

    plan_asset_url: durable reference recorded in the provenance manifest
    for the stored plan document (e.g. "sceneledger://projects/.../scenes.json").
    """
    enabled, disabled_reason = _planner_enabled()
    if not enabled:
        return PlannerResult(
            scenes=plan_scenes(chunks),
            planner="deterministic",
            fallback_reason=disabled_reason,
        )

    from genblaze_core.exceptions import ProviderError

    chunk_lines = "\n".join(
        f"{chunk.chunk_id}: {chunk.text.strip()}" for chunk in chunks
    )
    prompt = f"Source chunks:\n{chunk_lines}"

    failure_chain: list[str] = []
    for choice in provider_chain("chat"):
        if choice.name == "gmi":
            from genblaze_gmicloud import chat

            step_provider = "gmicloud-chat"
        else:
            from genblaze_openai import chat

            step_provider = "openai-chat"

        try:
            response = chat(
                choice.model,
                prompt=prompt,
                system=_SYSTEM_PROMPT,
                response_format=ScenePlanOutput,
                temperature=0.3,
                timeout=60.0,
            )
        except ProviderError as exc:
            failure_chain.append(f"{choice.name} chat failed: {exc}")
            continue

        try:
            output = ScenePlanOutput.model_validate(json.loads(response.text))
        except (json.JSONDecodeError, ValidationError) as exc:
            failure_chain.append(
                f"{choice.name} output was not valid structured JSON: {type(exc).__name__}"
            )
            continue

        scenes, invalid_reason = _validate_plan(output, chunks)
        if scenes is None:
            failure_chain.append(
                f"{choice.name} output failed validation: {invalid_reason}"
            )
            continue

        manifest_json, run_id = _build_planner_manifest(
            provider=step_provider,
            model=response.model or choice.model,
            prompt=prompt,
            scenes=scenes,
            plan_asset_url=plan_asset_url,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
        )
        return PlannerResult(
            scenes=scenes,
            planner="genblaze-chat",
            manifest_json=manifest_json,
            run_id=run_id,
            model=response.model or choice.model,
            provider=choice.name,
        )

    return PlannerResult(
        scenes=plan_scenes(chunks),
        planner="deterministic",
        fallback_reason="; ".join(failure_chain) or "no provider attempt succeeded",
    )
