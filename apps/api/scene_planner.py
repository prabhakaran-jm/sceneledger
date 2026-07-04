"""Deterministic mock scene planner (no AI calls)."""

from models import Scene, SourceChunk


def _chunk_for_scene(chunks: list[SourceChunk], index: int) -> SourceChunk:
    if not chunks:
        raise ValueError("Cannot plan scenes without source chunks")
    if index < len(chunks):
        return chunks[index]
    return chunks[-1]


def plan_scenes(chunks: list[SourceChunk]) -> list[Scene]:
    if not chunks:
        return []

    scenes: list[Scene] = []
    for index in range(3):
        scene_num = index + 1
        chunk = _chunk_for_scene(chunks, index)
        scenes.append(
            Scene(
                scene_id=f"scene-{scene_num:03d}",
                title=f"Scene {scene_num}",
                narration=chunk.text,
                visual_prompt=(
                    f"Training video frame for scene {scene_num}: "
                    f"{chunk.text[:80]}"
                ),
                source_chunk_ids=[chunk.chunk_id],
                status="current",
            )
        )
    return scenes
