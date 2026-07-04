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


class CreateProjectRequest(BaseModel):
    name: str


class CreateProjectResponse(BaseModel):
    project_id: str
    name: str


class UploadSourceRequest(BaseModel):
    source_version: str
    content: str


class UploadSourceResponse(BaseModel):
    project_id: str
    source_version: str
    chunks: list[SourceChunk]


class PlanRequest(BaseModel):
    source_version: str


class PlanResponse(BaseModel):
    project_id: str
    source_version: str
    scenes: list[Scene]


class CompareSourceRequest(BaseModel):
    base_version: str
    candidate_version: str


class CompareSourceResponse(BaseModel):
    project_id: str
    base_version: str
    candidate_version: str
    stale_scene_ids: list[str]
    scenes: list[Scene]


class StaleReport(BaseModel):
    project_id: str
    base_version: str
    candidate_version: str
    stale_scene_ids: list[str]
    scenes: list[Scene]
    generated_at: datetime


class ReleaseRequest(BaseModel):
    source_version: str


class ReleaseManifestResponse(BaseModel):
    project_id: str
    source_version: str
    scene_ids: list[str]
    stale_scene_ids: list[str]
    generated_at: datetime
    placeholder_genblaze_manifest: bool = True
    placeholder_b2_keys: list[str] = Field(default_factory=list)


class GetProjectResponse(BaseModel):
    project_id: str
    name: str
    uploaded_source_versions: list[str]
    has_plan: bool
    latest_stale_scene_ids: list[str]
