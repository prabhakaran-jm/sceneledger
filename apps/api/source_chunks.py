"""Deterministic plain-text source chunking."""

import hashlib
import re

from models import SourceChunk


def _normalize_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    parts = re.split(r"\n\s*\n", normalized)
    return [part.strip() for part in parts if part.strip()]


def chunk_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_source_text(text: str, source_version: str) -> list[SourceChunk]:
    paragraphs = _normalize_paragraphs(text)
    chunks: list[SourceChunk] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        chunk_id = f"chunk-{index:03d}"
        chunks.append(
            SourceChunk(
                chunk_id=chunk_id,
                order=index,
                text=paragraph,
                sha256=chunk_sha256(paragraph),
                source_version=source_version,
            )
        )
    return chunks


def chunk_hash_map(chunks: list[SourceChunk]) -> dict[str, str]:
    return {chunk.chunk_id: chunk.sha256 for chunk in chunks}
