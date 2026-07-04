from pydantic import BaseModel, Field


class AssetEntry(BaseModel):
    key: str
    sha256: str
    content_type: str
    generator: str
    playable: bool = True


class SceneAssetRefs(BaseModel):
    storyboard: AssetEntry
    clip: AssetEntry
    narration: AssetEntry
    captions: AssetEntry
    manifest: str


class GenerateMediaRequest(BaseModel):
    source_version: str
    scene_ids: list[str] = Field(default_factory=list)
    force: bool = False


class SceneMediaResult(BaseModel):
    scene_id: str
    status: str
    media_mode: str
    assets: SceneAssetRefs
    storage_keys: list[str] = Field(default_factory=list)
    error: str | None = None


class GenerateMediaResponse(BaseModel):
    project_id: str
    source_version: str
    media_mode: str
    scenes: list[SceneMediaResult]
    storage_keys: list[str] = Field(default_factory=list)


class ProjectMediaResponse(BaseModel):
    project_id: str
    source_version: str
    current_media_mode: str
    scenes: list[SceneMediaResult] = Field(default_factory=list)
