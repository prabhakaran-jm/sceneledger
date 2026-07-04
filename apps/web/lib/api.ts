const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SourceChunk = {
  chunk_id: string;
  order: number;
  text: string;
  sha256: string;
  source_version: string;
};

export type Scene = {
  scene_id: string;
  title: string;
  narration: string;
  visual_prompt: string;
  source_chunk_ids: string[];
  status: string;
};

export type ProjectSummary = {
  project_id: string;
  name: string;
  uploaded_source_versions: string[];
  has_plan: boolean;
  latest_stale_scene_ids: string[];
};

export type ReleaseVerification = {
  source_chunks_present: boolean;
  scene_plan_present: boolean;
  media_manifests_present: boolean;
  asset_hashes_verified: boolean;
  stale_report_applied: boolean;
  release_current: boolean;
};

export type VerifiedAssetEntry = {
  key: string;
  sha256: string;
  computed_sha256?: string | null;
  hash_verified: boolean;
  content_type: string;
  generator: string;
  playable: boolean;
};

export type ReleaseSceneRecord = {
  scene_id: string;
  title: string;
  status: string;
  source_chunk_ids: string[];
  source_chunk_hashes: Record<string, string>;
  media_status: string;
  media_mode: string;
  assets: {
    storyboard?: VerifiedAssetEntry | null;
    clip?: VerifiedAssetEntry | null;
    narration?: VerifiedAssetEntry | null;
    captions?: VerifiedAssetEntry | null;
  };
  scene_manifest_key?: string | null;
  genblaze_manifest_key?: string | null;
  genblaze_manifest_sha256?: string | null;
  genblaze_manifest_verified?: boolean | null;
  genblaze_tts_manifest_key?: string | null;
  genblaze_tts_manifest_sha256?: string | null;
  genblaze_tts_manifest_verified?: boolean | null;
  verification_errors: string[];
};

export type PlannerProvenance = {
  planner: string;
  fallback_reason?: string | null;
  genblaze_manifest_key?: string | null;
  genblaze_manifest_sha256?: string | null;
  genblaze_manifest_verified?: boolean | null;
  genblaze_run_id?: string | null;
  genblaze_model?: string | null;
  verification_errors: string[];
};

export type ReleaseManifest = {
  release_id: string;
  project_id: string;
  source_version: string;
  created_at: string;
  release_status: string;
  message: string;
  storage_backend: string;
  media_mode_summary: {
    placeholder: number;
    genblaze: number;
    mixed: boolean;
  };
  genblaze_provenance: {
    present: boolean;
    run_ids: string[];
    manifest_keys: string[];
    manifest_hashes: string[];
    asset_count: number;
  };
  planner_provenance?: PlannerProvenance | null;
  source: {
    version: string;
    chunk_count: number;
    chunks: Array<{
      chunk_id: string;
      order: number;
      sha256: string;
      text_preview: string;
    }>;
  };
  scenes: ReleaseSceneRecord[];
  stale_scene_ids: string[];
  missing_media_scene_ids: string[];
  invalid_asset_scene_ids: string[];
  release_superseded_by_source_version: string | null;
  hash_verified: boolean;
  release_manifest_sha256: string;
  placeholder_genblaze_manifest: boolean;
  placeholder_b2_keys: string[];
  storage_keys: string[];
  verification: ReleaseVerification;
};

export type VerifyReleaseResponse = {
  project_id: string;
  source_version: string;
  release_id: string;
  release_status: string;
  message: string;
  hash_verified: boolean;
  verification: ReleaseVerification;
  errors: string[];
};

export type StoredObject = {
  key: string;
  kind: string;
  size?: number | null;
  updated_at?: string | null;
};

export type ProjectObjects = {
  project_id: string;
  storage_backend: string;
  objects: StoredObject[];
};

export type HealthResponse = {
  status: string;
  service: string;
  api_version?: string;
  storage_backend: string;
  media_mode: string;
  tenant_prefix?: string | null;
};

export type AssetEntry = {
  key: string;
  sha256: string;
  content_type: string;
  generator: string;
  playable: boolean;
};

export type SceneAssetRefs = {
  storyboard: AssetEntry;
  clip: AssetEntry;
  narration: AssetEntry;
  captions: AssetEntry;
  manifest: string;
};

export type SceneMediaResult = {
  scene_id: string;
  status: string;
  media_mode: string;
  assets: SceneAssetRefs;
  storage_keys: string[];
  error?: string | null;
};

export type GenerateMediaResponse = {
  project_id: string;
  source_version: string;
  media_mode: string;
  scenes: SceneMediaResult[];
  storage_keys: string[];
};

export type ProjectMedia = {
  project_id: string;
  source_version: string;
  current_media_mode: string;
  scenes: SceneMediaResult[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      detail = await response.text();
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return response.json() as Promise<T>;
}

export function getHealth() {
  return request<HealthResponse>("/health");
}

export function createProject(name: string) {
  return request<{ project_id: string; name: string; storage_keys: string[] }>(
    "/projects",
    {
      method: "POST",
      body: JSON.stringify({ name }),
    }
  );
}

export function getProject(projectId: string) {
  return request<ProjectSummary>(`/projects/${projectId}`);
}

export function getProjectObjects(projectId: string) {
  return request<ProjectObjects>(`/projects/${projectId}/objects`);
}

export function uploadSource(
  projectId: string,
  sourceVersion: string,
  content: string
) {
  return request<{
    project_id: string;
    source_version: string;
    chunks: SourceChunk[];
    storage_keys: string[];
  }>(`/projects/${projectId}/sources`, {
    method: "POST",
    body: JSON.stringify({ source_version: sourceVersion, content }),
  });
}

export function generatePlan(projectId: string, sourceVersion: string) {
  return request<{
    project_id: string;
    source_version: string;
    scenes: Scene[];
    storage_keys: string[];
    planner: string;
    planner_fallback_reason?: string | null;
    genblaze_planner_manifest_key?: string | null;
    genblaze_planner_manifest_sha256?: string | null;
    genblaze_planner_run_id?: string | null;
    genblaze_planner_model?: string | null;
  }>(`/projects/${projectId}/plan`, {
    method: "POST",
    body: JSON.stringify({ source_version: sourceVersion }),
  });
}

export function compareSource(
  projectId: string,
  baseVersion: string,
  candidateVersion: string
) {
  return request<{
    project_id: string;
    base_version: string;
    candidate_version: string;
    stale_scene_ids: string[];
    scenes: Scene[];
    storage_keys: string[];
  }>(`/projects/${projectId}/compare-source`, {
    method: "POST",
    body: JSON.stringify({
      base_version: baseVersion,
      candidate_version: candidateVersion,
    }),
  });
}

export function createRelease(projectId: string, sourceVersion: string) {
  return request<ReleaseManifest>(`/projects/${projectId}/release`, {
    method: "POST",
    body: JSON.stringify({ source_version: sourceVersion }),
  });
}

export function getRelease(projectId: string, sourceVersion: string) {
  return request<ReleaseManifest>(
    `/projects/${projectId}/release?source_version=${encodeURIComponent(sourceVersion)}`
  );
}

export function verifyRelease(
  projectId: string,
  sourceVersion: string,
  updateManifest = false
) {
  return request<VerifyReleaseResponse>(
    `/projects/${projectId}/verify-release`,
    {
      method: "POST",
      body: JSON.stringify({
        source_version: sourceVersion,
        update_manifest: updateManifest,
      }),
    }
  );
}

export function generateMedia(
  projectId: string,
  sourceVersion: string,
  sceneIds: string[] = [],
  force = false
) {
  return request<GenerateMediaResponse>(
    `/projects/${projectId}/generate-media`,
    {
      method: "POST",
      body: JSON.stringify({
        source_version: sourceVersion,
        scene_ids: sceneIds,
        force,
      }),
    }
  );
}

export function getProjectMedia(projectId: string, sourceVersion: string) {
  return request<ProjectMedia>(
    `/projects/${projectId}/media?source_version=${encodeURIComponent(sourceVersion)}`
  );
}
