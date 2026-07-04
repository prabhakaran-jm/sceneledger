from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    order: int
    text: str
    hash: str
    source_version: int


class Scene(BaseModel):
    scene_id: str
    title: str
    narration: str
    visual_prompt: str
    source_chunk_ids: list[str]
    status: str = "current"


class Project(BaseModel):
    project_id: str
    name: str
    created_at: datetime
    source_version: int = 0
    chunks: list[SourceChunk] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    stale_scene_ids: list[str] = Field(default_factory=list)


class CreateProjectRequest(BaseModel):
    name: str


class UploadSourceRequest(BaseModel):
    text: str
    source_version: int | None = None


class CompareSourceRequest(BaseModel):
    text: str


class CompareSourceResponse(BaseModel):
    scenes: list[Scene]
    stale_scenes: list[Scene]
    stale_scene_ids: list[str]
    source_version: int
    chunks: list[SourceChunk]


class ReleaseManifest(BaseModel):
    project_id: str
    source_version: int
    scene_ids: list[str]
    stale_scene_ids: list[str]
    generated_at: datetime
    placeholder_genblaze_manifest: dict[str, Any]
    placeholder_b2_keys: list[str]
