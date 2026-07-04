"""Compare source versions and mark stale scenes."""

from models import Scene, SourceChunk
from source_chunks import chunk_hash_map


def compare_scenes(
    scenes: list[Scene],
    base_chunks: list[SourceChunk],
    candidate_chunks: list[SourceChunk],
) -> tuple[list[Scene], list[str]]:
    base_hashes = chunk_hash_map(base_chunks)
    candidate_hashes = chunk_hash_map(candidate_chunks)

    updated_scenes: list[Scene] = []
    stale_ids: list[str] = []

    for scene in scenes:
        is_stale = False
        for chunk_id in scene.source_chunk_ids:
            base_hash = base_hashes.get(chunk_id)
            candidate_hash = candidate_hashes.get(chunk_id)
            if base_hash is None or candidate_hash is None:
                is_stale = True
                break
            if base_hash != candidate_hash:
                is_stale = True
                break

        status = "stale" if is_stale else "current"
        updated = scene.model_copy(update={"status": status})
        updated_scenes.append(updated)
        if is_stale:
            stale_ids.append(scene.scene_id)

    return updated_scenes, stale_ids
