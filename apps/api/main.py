"""SceneLedger API — M0 local source-to-stale-scene loop."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    CompareSourceRequest,
    CompareSourceResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    GetProjectResponse,
    PlanRequest,
    PlanResponse,
    ProjectState,
    ReleaseManifestResponse,
    ReleaseRequest,
    Scene,
    SourceChunk,
    StaleReport,
    UploadSourceRequest,
    UploadSourceResponse,
)
from release_manifest import build_release_manifest, latest_stale_scene_ids
from scene_planner import plan_scenes
from source_chunks import chunk_source_text
from stale_detector import compare_scenes
from storage import get_storage, project_key

app = FastAPI(title="SceneLedger API", version="0.1.0-m0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()


def _project_meta_key(project_id: str) -> str:
    return project_key(project_id, "project.json")


def _load_project_state(project_id: str) -> ProjectState:
    key = _project_meta_key(project_id)
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectState.model_validate(storage.read_json(key))


def _save_project_state(state: ProjectState) -> None:
    storage.write_json(_project_meta_key(state.project_id), state.model_dump(mode="json"))


def _chunks_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "sources", source_version, "chunks.json")


def _source_text_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "sources", source_version, "source.txt")


def _plan_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "plans", source_version, "scenes.json")


def _stale_report_key(project_id: str, base_version: str, candidate_version: str) -> str:
    return project_key(
        project_id,
        "compare",
        f"{base_version}-{candidate_version}",
        "stale-report.json",
    )


def _manifest_key(project_id: str, source_version: str) -> str:
    return project_key(project_id, "manifests", source_version, "release.json")


def _load_chunks(project_id: str, source_version: str) -> list[SourceChunk]:
    key = _chunks_key(project_id, source_version)
    if not storage.exists(key):
        raise HTTPException(
            status_code=400,
            detail=f"Source version {source_version} not uploaded",
        )
    data = storage.read_json(key)
    return [SourceChunk.model_validate(item) for item in data["chunks"]]


def _load_scenes(project_id: str, source_version: str) -> list[Scene]:
    key = _plan_key(project_id, source_version)
    if not storage.exists(key):
        raise HTTPException(
            status_code=400,
            detail=f"Scene plan for {source_version} not found",
        )
    data = storage.read_json(key)
    return [Scene.model_validate(item) for item in data["scenes"]]


def _uploaded_source_versions(project_id: str) -> list[str]:
    prefix = project_key(project_id, "sources")
    keys = storage.list_keys(prefix)
    versions: set[str] = set()
    for key in keys:
        if key.endswith("/chunks.json"):
            parts = key.split("/")
            if len(parts) >= 4:
                versions.add(parts[-2])
    return sorted(versions)


def _has_plan(project_id: str) -> bool:
    prefix = project_key(project_id, "plans")
    return any(k.endswith("/scenes.json") for k in storage.list_keys(prefix))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sceneledger-api"}


@app.post("/projects", response_model=CreateProjectResponse)
def create_project(body: CreateProjectRequest) -> CreateProjectResponse:
    project_id = str(uuid.uuid4())
    state = ProjectState(project_id=project_id, name=body.name)
    _save_project_state(state)
    return CreateProjectResponse(project_id=project_id, name=body.name)


@app.get("/projects/{project_id}", response_model=GetProjectResponse)
def get_project(project_id: str) -> GetProjectResponse:
    state = _load_project_state(project_id)
    return GetProjectResponse(
        project_id=state.project_id,
        name=state.name,
        uploaded_source_versions=_uploaded_source_versions(project_id),
        has_plan=_has_plan(project_id),
        latest_stale_scene_ids=latest_stale_scene_ids(storage, project_id),
    )


@app.post("/projects/{project_id}/sources", response_model=UploadSourceResponse)
def upload_source(project_id: str, body: UploadSourceRequest) -> UploadSourceResponse:
    _load_project_state(project_id)
    chunks = chunk_source_text(body.content, body.source_version)

    storage.write_bytes(
        _source_text_key(project_id, body.source_version),
        body.content.encode("utf-8"),
    )
    storage.write_json(
        _chunks_key(project_id, body.source_version),
        {
            "source_version": body.source_version,
            "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
        },
    )

    return UploadSourceResponse(
        project_id=project_id,
        source_version=body.source_version,
        chunks=chunks,
    )


@app.post("/projects/{project_id}/plan", response_model=PlanResponse)
def generate_plan(project_id: str, body: PlanRequest) -> PlanResponse:
    _load_project_state(project_id)
    chunks = _load_chunks(project_id, body.source_version)
    scenes = plan_scenes(chunks)

    storage.write_json(
        _plan_key(project_id, body.source_version),
        {
            "source_version": body.source_version,
            "scenes": [scene.model_dump(mode="json") for scene in scenes],
        },
    )

    return PlanResponse(
        project_id=project_id,
        source_version=body.source_version,
        scenes=scenes,
    )


@app.post("/projects/{project_id}/compare-source", response_model=CompareSourceResponse)
def compare_source(project_id: str, body: CompareSourceRequest) -> CompareSourceResponse:
    _load_project_state(project_id)

    plan_key = _plan_key(project_id, body.base_version)
    if not storage.exists(plan_key):
        raise HTTPException(
            status_code=400,
            detail=f"Scene plan for base version {body.base_version} not found",
        )

    base_chunks = _load_chunks(project_id, body.base_version)
    candidate_chunks = _load_chunks(project_id, body.candidate_version)
    base_scenes = _load_scenes(project_id, body.base_version)

    updated_scenes, stale_ids = compare_scenes(base_scenes, base_chunks, candidate_chunks)

    report = StaleReport(
        project_id=project_id,
        base_version=body.base_version,
        candidate_version=body.candidate_version,
        stale_scene_ids=stale_ids,
        scenes=updated_scenes,
        generated_at=datetime.now(timezone.utc),
    )
    storage.write_json(
        _stale_report_key(project_id, body.base_version, body.candidate_version),
        report.model_dump(mode="json"),
    )

    return CompareSourceResponse(
        project_id=project_id,
        base_version=body.base_version,
        candidate_version=body.candidate_version,
        stale_scene_ids=stale_ids,
        scenes=updated_scenes,
    )


@app.post("/projects/{project_id}/release", response_model=ReleaseManifestResponse)
def create_release(project_id: str, body: ReleaseRequest) -> ReleaseManifestResponse:
    _load_project_state(project_id)
    scenes = _load_scenes(project_id, body.source_version)

    manifest = build_release_manifest(
        storage, project_id, body.source_version, scenes
    )
    storage.write_json(
        _manifest_key(project_id, body.source_version),
        manifest.model_dump(mode="json"),
    )
    return manifest
