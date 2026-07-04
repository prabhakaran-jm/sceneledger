from datetime import datetime

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    order: int
    text: str
    sha256: str
    source_version: str


class Scene(BaseModel):
    scene_id: str
    title: str
    narration: str
    visual_prompt: str
    source_chunk_ids: list[str]
    status: str = "current"


class ProjectState(BaseModel):
    project_id: str
    name: str


class StoredObjectRef(BaseModel):
    key: str
    kind: str
    size: int | None = None
    updated_at: datetime | None = None


class CreateProjectRequest(BaseModel):
    name: str


class CreateProjectResponse(BaseModel):
    project_id: str
    name: str
    storage_keys: list[str] = Field(default_factory=list)


class UploadSourceRequest(BaseModel):
    source_version: str
    content: str


class UploadSourceResponse(BaseModel):
    project_id: str
    source_version: str
    chunks: list[SourceChunk]
    storage_keys: list[str] = Field(default_factory=list)


class PlanRequest(BaseModel):
    source_version: str


class PlanResponse(BaseModel):
    project_id: str
    source_version: str
    scenes: list[Scene]
    storage_keys: list[str] = Field(default_factory=list)
    # Planner provenance (additive): which planner produced the scenes.
    planner: str = "deterministic"
    planner_fallback_reason: str | None = None
    genblaze_planner_manifest_key: str | None = None
    genblaze_planner_manifest_sha256: str | None = None
    genblaze_planner_run_id: str | None = None
    genblaze_planner_model: str | None = None


class CompareSourceRequest(BaseModel):
    base_version: str
    candidate_version: str


class CompareSourceResponse(BaseModel):
    project_id: str
    base_version: str
    candidate_version: str
    stale_scene_ids: list[str]
    scenes: list[Scene]
    storage_keys: list[str] = Field(default_factory=list)


class StaleReport(BaseModel):
    project_id: str
    base_version: str
    candidate_version: str
    stale_scene_ids: list[str]
    scenes: list[Scene]
    generated_at: datetime


class ReleaseRequest(BaseModel):
    source_version: str


class GetProjectResponse(BaseModel):
    project_id: str
    name: str
    uploaded_source_versions: list[str]
    has_plan: bool
    latest_stale_scene_ids: list[str]


class ProjectObjectsResponse(BaseModel):
    project_id: str
    storage_backend: str
    objects: list[StoredObjectRef]
