"""SceneLedger API — M0 loop with M1 optional B2 storage and M2 media pipeline."""

import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from media_models import GenerateMediaRequest, GenerateMediaResponse, ProjectMediaResponse
from media_pipeline import MediaError, generate_project_media, get_media_mode, load_project_media
from models import (
    CompareSourceRequest,
    CompareSourceResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    GetProjectResponse,
    PlanRequest,
    PlanResponse,
    ProjectObjectsResponse,
    ProjectState,
    ReleaseRequest,
    Scene,
    SourceChunk,
    StaleReport,
    UploadSourceRequest,
    UploadSourceResponse,
)
from release_manifest import (
    create_release_manifest,
    latest_stale_scene_ids,
    load_release_manifest,
    release_manifest_key,
    run_verify_release,
)
from release_models import ReleaseManifestResponse, VerifyReleaseRequest, VerifyReleaseResponse
from genblaze_planner import plan_scenes_with_planner
from media_pipeline import genblaze_planner_manifest_key
from media_placeholders import sha256_hex
from release_video import maybe_stitch_final_video
from source_chunks import chunk_source_text
from stale_detector import compare_scenes
from storage import B2Storage, StorageError, get_storage, project_key

APP_VERSION = "0.7.0"

app = FastAPI(title="SceneLedger API", version=APP_VERSION)

_cors_origins = os.getenv(
    "SCENELEDGER_CORS_ORIGINS", "http://localhost:3000"
).strip()
_cors_origin_list = [
    origin.strip() for origin in _cors_origins.split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origin_list or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = get_storage()


@app.exception_handler(StorageError)
async def storage_error_handler(_request: Request, exc: StorageError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(MediaError)
async def media_error_handler(_request: Request, exc: MediaError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


def _project_meta_key(project_id: str) -> str:
    return project_key(project_id, "project.json")


def _load_project_state(project_id: str) -> ProjectState:
    key = _project_meta_key(project_id)
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectState.model_validate(storage.read_json(key))


def _save_project_state(state: ProjectState) -> str:
    return storage.write_json(
        _project_meta_key(state.project_id),
        state.model_dump(mode="json"),
    )


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
    return release_manifest_key(project_id, source_version)


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
    keys = storage.list_prefix(prefix)
    versions: set[str] = set()
    for key in keys:
        if key.endswith("/chunks.json"):
            parts = key.split("/")
            if len(parts) >= 4:
                versions.add(parts[-2])
    return sorted(versions)


def _has_plan(project_id: str) -> bool:
    prefix = project_key(project_id, "plans")
    return any(k.endswith("/scenes.json") for k in storage.list_prefix(prefix))


@app.get("/health")
def health() -> dict[str, str | None]:
    tenant_prefix: str | None = None
    if isinstance(storage, B2Storage):
        tenant_prefix = storage.tenant_prefix
    return {
        "status": "ok",
        "service": "sceneledger-api",
        "api_version": APP_VERSION,
        "storage_backend": storage.backend_name,
        "media_mode": get_media_mode(),
        "tenant_prefix": tenant_prefix,
    }


@app.post("/projects", response_model=CreateProjectResponse)
def create_project(body: CreateProjectRequest) -> CreateProjectResponse:
    project_id = str(uuid.uuid4())
    state = ProjectState(project_id=project_id, name=body.name)
    project_key_written = _save_project_state(state)
    return CreateProjectResponse(
        project_id=project_id,
        name=body.name,
        storage_keys=[project_key_written],
    )


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


@app.get("/projects/{project_id}/objects", response_model=ProjectObjectsResponse)
def list_project_objects(project_id: str) -> ProjectObjectsResponse:
    _load_project_state(project_id)
    return ProjectObjectsResponse(
        project_id=project_id,
        storage_backend=storage.backend_name,
        objects=storage.list_project_objects(project_id),
    )


@app.post("/projects/{project_id}/sources", response_model=UploadSourceResponse)
def upload_source(project_id: str, body: UploadSourceRequest) -> UploadSourceResponse:
    _load_project_state(project_id)
    chunks = chunk_source_text(body.content, body.source_version)

    source_key = storage.write_text(
        _source_text_key(project_id, body.source_version),
        body.content,
    )
    chunks_key = storage.write_json(
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
        storage_keys=[source_key, chunks_key],
    )


@app.post("/projects/{project_id}/plan", response_model=PlanResponse)
def generate_plan(project_id: str, body: PlanRequest) -> PlanResponse:
    _load_project_state(project_id)
    chunks = _load_chunks(project_id, body.source_version)

    plan_logical = _plan_key(project_id, body.source_version)
    result = plan_scenes_with_planner(
        chunks,
        plan_asset_url=f"sceneledger://{storage.public_key(plan_logical)}",
    )

    storage_keys: list[str] = []
    planner_manifest_public: str | None = None
    planner_manifest_sha256: str | None = None
    if result.manifest_json:
        # Store the SDK's canonical manifest bytes exactly (never rewritten).
        planner_manifest_public = storage.write_bytes(
            genblaze_planner_manifest_key(project_id, body.source_version),
            result.manifest_json,
            content_type="application/json",
        )
        planner_manifest_sha256 = sha256_hex(result.manifest_json)
        storage_keys.append(planner_manifest_public)

    plan_key = storage.write_json(
        plan_logical,
        {
            "source_version": body.source_version,
            "planner": result.planner,
            "planner_fallback_reason": result.fallback_reason,
            "genblaze_planner": (
                {
                    "manifest_key": planner_manifest_public,
                    "manifest_sha256": planner_manifest_sha256,
                    "run_id": result.run_id,
                    "model": result.model,
                }
                if planner_manifest_public
                else None
            ),
            "scenes": [scene.model_dump(mode="json") for scene in result.scenes],
        },
    )
    storage_keys.append(plan_key)

    return PlanResponse(
        project_id=project_id,
        source_version=body.source_version,
        scenes=result.scenes,
        storage_keys=storage_keys,
        planner=result.planner,
        planner_fallback_reason=result.fallback_reason,
        genblaze_planner_manifest_key=planner_manifest_public,
        genblaze_planner_manifest_sha256=planner_manifest_sha256,
        genblaze_planner_run_id=result.run_id,
        genblaze_planner_model=result.model,
    )


@app.post("/projects/{project_id}/compare-source", response_model=CompareSourceResponse)
def compare_source(project_id: str, body: CompareSourceRequest) -> CompareSourceResponse:
    _load_project_state(project_id)

    plan_path = _plan_key(project_id, body.base_version)
    if not storage.exists(plan_path):
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
    report_key = storage.write_json(
        _stale_report_key(project_id, body.base_version, body.candidate_version),
        report.model_dump(mode="json"),
    )

    return CompareSourceResponse(
        project_id=project_id,
        base_version=body.base_version,
        candidate_version=body.candidate_version,
        stale_scene_ids=stale_ids,
        scenes=updated_scenes,
        storage_keys=[report_key],
    )


@app.post("/projects/{project_id}/release", response_model=ReleaseManifestResponse)
def create_release(project_id: str, body: ReleaseRequest) -> ReleaseManifestResponse:
    _load_project_state(project_id)
    chunks = _load_chunks(project_id, body.source_version)
    scenes = _load_scenes(project_id, body.source_version)

    # Optional final.mp4 — records a clean skip reason instead of failing.
    maybe_stitch_final_video(storage, project_id, body.source_version, scenes)

    manifest = create_release_manifest(
        storage, project_id, body.source_version, chunks, scenes
    )
    manifest_key = storage.write_json(
        _manifest_key(project_id, body.source_version),
        manifest.model_dump(mode="json"),
    )
    manifest.storage_keys = [manifest_key]
    if storage.backend_name == "b2":
        manifest.placeholder_b2_keys = [manifest_key]
    return manifest


@app.get("/projects/{project_id}/release", response_model=ReleaseManifestResponse)
def get_release(project_id: str, source_version: str) -> ReleaseManifestResponse:
    _load_project_state(project_id)
    manifest = load_release_manifest(storage, project_id, source_version)
    if manifest is None:
        raise HTTPException(status_code=404, detail="Release manifest not found")
    return manifest


@app.post("/projects/{project_id}/verify-release", response_model=VerifyReleaseResponse)
def verify_release(project_id: str, body: VerifyReleaseRequest) -> VerifyReleaseResponse:
    _load_project_state(project_id)
    stored = load_release_manifest(storage, project_id, body.source_version)
    if stored is None:
        raise HTTPException(status_code=404, detail="Release manifest not found")
    chunks = _load_chunks(project_id, body.source_version)
    scenes = _load_scenes(project_id, body.source_version)

    response, updated = run_verify_release(
        storage,
        project_id,
        body.source_version,
        chunks,
        scenes,
        stored,
        update_manifest=body.update_manifest,
    )
    if updated is not None:
        manifest_key = storage.write_json(
            _manifest_key(project_id, body.source_version),
            updated.model_dump(mode="json"),
        )
        if storage.backend_name == "b2":
            updated.placeholder_b2_keys = [manifest_key]
    return response


@app.post(
    "/projects/{project_id}/generate-media",
    response_model=GenerateMediaResponse,
)
def generate_media(
    project_id: str, body: GenerateMediaRequest
) -> GenerateMediaResponse:
    _load_project_state(project_id)
    scenes = _load_scenes(project_id, body.source_version)
    try:
        return generate_project_media(storage, project_id, body, scenes)
    except MediaError as exc:
        if "Unknown scene IDs" in str(exc):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise


_ASSET_CONTENT_TYPES = {
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".vtt": "text/vtt",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
}


@app.get("/projects/{project_id}/asset")
def get_project_asset(project_id: str, key: str) -> Response:
    """Serve a stored object for in-browser preview (release package view).

    Only objects under this project's own prefix are reachable — the key is
    normalized through the storage backend and prefix-checked, so no
    cross-project or path-traversal reads are possible.
    """
    _load_project_state(project_id)
    try:
        logical = storage.logical_path(key)
    except StorageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not logical.startswith(f"projects/{project_id}/"):
        raise HTTPException(status_code=404, detail="Object not found")
    if not storage.exists(logical):
        raise HTTPException(status_code=404, detail="Object not found")

    suffix = "." + logical.rsplit(".", 1)[-1] if "." in logical else ""
    content_type = _ASSET_CONTENT_TYPES.get(suffix, "application/octet-stream")
    return Response(content=storage.read_bytes(logical), media_type=content_type)


@app.get(
    "/projects/{project_id}/media",
    response_model=ProjectMediaResponse,
)
def get_project_media(
    project_id: str, source_version: str
) -> ProjectMediaResponse:
    _load_project_state(project_id)
    return load_project_media(storage, project_id, source_version)
