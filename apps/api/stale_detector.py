"""Compare source versions and mark stale scenes."""

from models import CompareSourceResponse, Project, Scene, SourceChunk
from source_chunks import chunk_hash_map, chunk_source_text


def _chunk_text_map(chunks: list[SourceChunk]) -> dict[str, str]:
    return {chunk.chunk_id: chunk.text for chunk in chunks}


def compare_source_versions(
    project: Project,
    previous_chunks: list[SourceChunk],
    new_text: str,
) -> CompareSourceResponse:
    new_version = project.source_version + 1
    new_chunks = chunk_source_text(new_text, new_version)
    previous_hashes = chunk_hash_map(previous_chunks)
    new_hashes = chunk_hash_map(new_chunks)

    updated_scenes: list[Scene] = []
    stale_scenes: list[Scene] = []
    stale_ids: list[str] = []

    for scene in project.scenes:
        is_stale = False
        for chunk_id in scene.source_chunk_ids:
            old_hash = previous_hashes.get(chunk_id)
            new_hash = new_hashes.get(chunk_id)
            if old_hash is None or new_hash is None:
                is_stale = True
                break
            if old_hash != new_hash:
                is_stale = True
                break

        status = "stale" if is_stale else "current"
        updated = scene.model_copy(update={"status": status})
        updated_scenes.append(updated)
        if is_stale:
            stale_scenes.append(updated)
            stale_ids.append(scene.scene_id)

    return CompareSourceResponse(
        scenes=updated_scenes,
        stale_scenes=stale_scenes,
        stale_scene_ids=stale_ids,
        source_version=new_version,
        chunks=new_chunks,
    )


def apply_compare_result(project: Project, result: CompareSourceResponse) -> Project:
    project.source_version = result.source_version
    project.chunks = result.chunks
    project.scenes = result.scenes
    project.stale_scene_ids = result.stale_scene_ids
    return project
