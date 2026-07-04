"""M3 release manifest and verification models."""

from datetime import datetime

from pydantic import BaseModel, Field


RELEASE_MESSAGE_VERIFIED = "Release is current and all asset hashes verified."
RELEASE_MESSAGE_WARNING = "Release assets verify, but one or more scenes are stale."
RELEASE_MESSAGE_BLOCKED = (
    "Release cannot be verified because media is missing or hashes do not match."
)


class ReleaseRequest(BaseModel):
    source_version: str


class SourceChunkSummary(BaseModel):
    chunk_id: str
    order: int
    sha256: str
    text_preview: str


class ReleaseSourceSection(BaseModel):
    version: str
    chunk_count: int
    chunks: list[SourceChunkSummary]


class VerifiedAssetEntry(BaseModel):
    key: str
    sha256: str
    computed_sha256: str | None = None
    hash_verified: bool = False
    content_type: str
    generator: str
    playable: bool = True


class ReleaseSceneAssets(BaseModel):
    storyboard: VerifiedAssetEntry | None = None
    clip: VerifiedAssetEntry | None = None
    narration: VerifiedAssetEntry | None = None
    captions: VerifiedAssetEntry | None = None


class ReleaseSceneRecord(BaseModel):
    scene_id: str
    title: str
    status: str
    source_chunk_ids: list[str]
    source_chunk_hashes: dict[str, str]
    media_status: str
    media_mode: str
    assets: ReleaseSceneAssets
    scene_manifest_key: str | None = None
    genblaze_manifest_key: str | None = None
    genblaze_manifest_sha256: str | None = None
    genblaze_manifest_verified: bool | None = None
    verification_errors: list[str] = Field(default_factory=list)


class MediaModeSummary(BaseModel):
    placeholder: int = 0
    genblaze: int = 0
    mixed: bool = False


class GenblazeProvenance(BaseModel):
    present: bool = False
    run_ids: list[str] = Field(default_factory=list)
    manifest_keys: list[str] = Field(default_factory=list)
    manifest_hashes: list[str] = Field(default_factory=list)
    asset_count: int = 0


class ReleaseVerification(BaseModel):
    source_chunks_present: bool = False
    scene_plan_present: bool = True
    media_manifests_present: bool = False
    asset_hashes_verified: bool = False
    stale_report_applied: bool = False
    release_current: bool = False


class ReleaseManifestResponse(BaseModel):
    release_id: str
    project_id: str
    source_version: str
    created_at: datetime
    release_status: str
    message: str
    storage_backend: str
    media_mode_summary: MediaModeSummary
    genblaze_provenance: GenblazeProvenance
    source: ReleaseSourceSection
    scenes: list[ReleaseSceneRecord]
    stale_scene_ids: list[str] = Field(default_factory=list)
    missing_media_scene_ids: list[str] = Field(default_factory=list)
    invalid_asset_scene_ids: list[str] = Field(default_factory=list)
    release_superseded_by_source_version: str | None = None
    hash_verified: bool = False
    release_manifest_sha256: str = ""
    placeholder_genblaze_manifest: bool = True
    placeholder_b2_keys: list[str] = Field(default_factory=list)
    storage_keys: list[str] = Field(default_factory=list)
    verification: ReleaseVerification


class VerifyReleaseRequest(BaseModel):
    source_version: str
    update_manifest: bool = False


class VerifyReleaseResponse(BaseModel):
    project_id: str
    source_version: str
    release_id: str
    release_status: str
    message: str
    hash_verified: bool
    verification: ReleaseVerification
    errors: list[str] = Field(default_factory=list)
