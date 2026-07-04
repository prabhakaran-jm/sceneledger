"""Deterministic mock scene planner (no AI calls)."""

from models import Scene, SourceChunk


def _scene_titles() -> list[str]:
    return [
        "Opening overview",
        "Core procedure",
        "Wrap-up and next steps",
    ]


def plan_scenes(chunks: list[SourceChunk]) -> list[Scene]:
    if not chunks:
        return []

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assignments: list[list[str]] = []

    if len(chunk_ids) >= 3:
        assignments = [
            [chunk_ids[0]],
            [chunk_ids[1]],
            chunk_ids[2:],
        ]
    elif len(chunk_ids) == 2:
        assignments = [[chunk_ids[0]], [chunk_ids[1]], [chunk_ids[1]]]
    else:
        assignments = [chunk_ids[:], chunk_ids[:], chunk_ids[:]]

    scenes: list[Scene] = []
    titles = _scene_titles()
    for index in range(3):
        scene_num = index + 1
        assigned = assignments[index]
        narration = " ".join(
            chunk.text for chunk in chunks if chunk.chunk_id in assigned
        )
        scenes.append(
            Scene(
                scene_id=f"scene-{scene_num:03d}",
                title=titles[index],
                narration=narration[:500] if narration else f"Scene {scene_num} narration placeholder.",
                visual_prompt=(
                    f"Training video frame for scene {scene_num}: "
                    f"{titles[index].lower()}, professional workplace setting."
                ),
                source_chunk_ids=assigned,
                status="current",
            )
        )
    return scenes
