"""SceneLedger API — MVP scaffold."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CompareSourceRequest,
    CreateProjectRequest,
    Project,
    ReleaseManifest,
    UploadSourceRequest,
)
from release_manifest import build_release_manifest
from scene_planner import plan_scenes
from source_chunks import chunk_source_text
from stale_detector import apply_compare_result, compare_source_versions
from storage import get_storage, project_key

app = FastAPI(title="SceneLedger API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()


def _project_path(project_id: str) -> str:
    return project_key("projects", project_id, "project.json")


def _load_project(project_id: str) -> Project:
    key = _project_path(project_id)
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="Project not found")
    data = storage.read_json(key)
    return Project.model_validate(data)


def _save_project(project: Project) -> None:
    storage.write_json(_project_path(project.project_id), project.model_dump(mode="json"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/projects", response_model=Project)
def create_project(body: CreateProjectRequest) -> Project:
    project_id = str(uuid.uuid4())
    project = Project(
        project_id=project_id,
        name=body.name,
        created_at=datetime.now(timezone.utc),
    )
    _save_project(project)
    return project


@app.post("/projects/{project_id}/sources", response_model=Project)
def upload_source(project_id: str, body: UploadSourceRequest) -> Project:
    project = _load_project(project_id)
    version = body.source_version if body.source_version is not None else project.source_version + 1
    if version < 1:
        raise HTTPException(status_code=400, detail="source_version must be >= 1")

    chunks = chunk_source_text(body.text, version)
    source_key = project_key("projects", project_id, "sources", f"v{version}", "source.txt")
    storage.write_bytes(source_key, body.text.encode("utf-8"))

    project.source_version = version
    project.chunks = chunks
    project.scenes = []
    project.stale_scene_ids = []
    _save_project(project)
    return project


@app.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: str) -> Project:
    return _load_project(project_id)


@app.post("/projects/{project_id}/plan", response_model=Project)
def generate_plan(project_id: str) -> Project:
    project = _load_project(project_id)
    if not project.chunks:
        raise HTTPException(status_code=400, detail="Upload a source document first")

    project.scenes = plan_scenes(project.chunks)
    project.stale_scene_ids = []
    _save_project(project)
    return project


@app.post("/projects/{project_id}/compare-source")
def compare_source(project_id: str, body: CompareSourceRequest) -> dict:
    project = _load_project(project_id)
    if not project.scenes:
        raise HTTPException(status_code=400, detail="Generate a scene plan first")

    previous_chunks = list(project.chunks)
    result = compare_source_versions(project, previous_chunks, body.text)

    source_key = project_key(
        "projects", project_id, "sources", f"v{result.source_version}", "source.txt"
    )
    storage.write_bytes(source_key, body.text.encode("utf-8"))

    apply_compare_result(project, result)
    _save_project(project)

    return {
        "scenes": [scene.model_dump() for scene in result.scenes],
        "stale_scenes": [scene.model_dump() for scene in result.stale_scenes],
        "stale_scene_ids": result.stale_scene_ids,
        "source_version": result.source_version,
        "chunks": [chunk.model_dump() for chunk in result.chunks],
    }


@app.post("/projects/{project_id}/release", response_model=ReleaseManifest)
def create_release(project_id: str) -> ReleaseManifest:
    project = _load_project(project_id)
    if not project.scenes:
        raise HTTPException(status_code=400, detail="Generate a scene plan first")

    manifest = build_release_manifest(project)
    manifest_key = project_key(
        "projects",
        project_id,
        "manifests",
        f"release-v{project.source_version}.json",
    )
    storage.write_json(manifest_key, manifest.model_dump(mode="json"))
    return manifest
