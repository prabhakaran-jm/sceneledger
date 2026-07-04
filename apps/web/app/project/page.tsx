"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  compareSource,
  createProject,
  createRelease,
  generateMedia,
  generatePlan,
  getHealth,
  getProject,
  getProjectMedia,
  getProjectObjects,
  uploadSource,
  verifyRelease,
  type ProjectMedia,
  type ProjectObjects,
  type ProjectSummary,
  type ReleaseManifest,
  type Scene,
  type VerifyReleaseResponse,
} from "@/lib/api";
import {
  DEMO_V1,
  DEMO_V2,
  RESET_DEMO_HELPER,
  STALE_HINT,
  computeStepCompletion,
  hasGenblazeStoryboard,
} from "@/lib/demo";
import { DemoStepper } from "./components/DemoStepper";
import { GenblazePanel } from "./components/GenblazePanel";
import { ReleaseEvidencePanel } from "./components/ReleaseEvidencePanel";
import { StoragePanel } from "./components/StoragePanel";
import { Icon, Spinner, StatusBadge } from "./components/ui";

function SceneCard({ scene }: { scene: Scene }) {
  const stale = scene.status === "stale";
  return (
    <div className={`card scene-card${stale ? " scene-card-stale" : ""}`}>
      <h3>
        {scene.title}
        <StatusBadge status={scene.status} />
      </h3>
      <p className="meta">
        Chunks: {scene.source_chunk_ids.join(", ") || "none"}
      </p>
      <p>{scene.narration}</p>
    </div>
  );
}

function mergeKeys(existing: string[], incoming: string[] = []) {
  return [...new Set([...existing, ...incoming])];
}

export default function ProjectPage() {
  const [project, setProject] = useState<ProjectSummary | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [sourceV1, setSourceV1] = useState(DEMO_V1);
  const [sourceV2, setSourceV2] = useState(DEMO_V2);
  const [manifest, setManifest] = useState<ReleaseManifest | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyReleaseResponse | null>(
    null
  );
  const [releaseEvidenceCreated, setReleaseEvidenceCreated] = useState(false);
  const [showRawRelease, setShowRawRelease] = useState(false);
  const [storageBackend, setStorageBackend] = useState<string>("local");
  const [tenantPrefix, setTenantPrefix] = useState<string | null>(null);
  const [apiVersion, setApiVersion] = useState<string>("");
  const [recentKeys, setRecentKeys] = useState<string[]>([]);
  const [storedObjects, setStoredObjects] = useState<ProjectObjects | null>(
    null
  );
  const [mediaMode, setMediaMode] = useState<string>("placeholder");
  const [projectMedia, setProjectMedia] = useState<ProjectMedia | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((health) => {
        setStorageBackend(health.storage_backend);
        setMediaMode(health.media_mode);
        setTenantPrefix(health.tenant_prefix ?? null);
        setApiVersion(health.api_version ?? "");
      })
      .catch(() => setStorageBackend("unknown"));
  }, []);

  const stepCompletion = useMemo(
    () =>
      computeStepCompletion({
        project,
        projectMedia,
        manifest,
        releaseEvidenceCreated,
      }),
    [project, projectMedia, manifest, releaseEvidenceCreated]
  );

  const releaseManifestKey = useMemo(() => {
    if (manifest?.placeholder_b2_keys?.[0]) return manifest.placeholder_b2_keys[0];
    const fromObjects = storedObjects?.objects.find(
      (o) => o.kind === "release_manifest"
    );
    if (fromObjects) return fromObjects.key;
    const fromKeys = recentKeys.find((k) => k.endsWith("release.json"));
    return fromKeys ?? null;
  }, [manifest, storedObjects, recentKeys]);

  async function run<T>(action: () => Promise<T>): Promise<T | null> {
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      return await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function refreshProject(projectId: string) {
    const summary = await getProject(projectId);
    setProject(summary);
    return summary;
  }

  function handleResetDemo() {
    setProject(null);
    setScenes([]);
    setSourceV1(DEMO_V1);
    setSourceV2(DEMO_V2);
    setManifest(null);
    setVerifyResult(null);
    setReleaseEvidenceCreated(false);
    setProjectMedia(null);
    setStoredObjects(null);
    setRecentKeys([]);
    setShowRawRelease(false);
    setError(null);
    setMessage("Demo reset. Click Create Project to start again.");
  }

  function handleLoadDemo() {
    setSourceV1(DEMO_V1);
    setSourceV2(DEMO_V2);
    setMessage("Loaded Warehouse Safety Demo text.");
  }

  async function handleRefreshObjects() {
    if (!project) return;
    const result = await run(() => getProjectObjects(project.project_id));
    if (result) {
      setStoredObjects(result);
      setStorageBackend(result.storage_backend);
      setMessage(`Listed ${result.objects.length} stored objects.`);
    }
  }

  async function handleCreateProject() {
    const created = await run(() => createProject("Warehouse Safety Demo"));
    if (created) {
      setProject({
        project_id: created.project_id,
        name: created.name,
        uploaded_source_versions: [],
        has_plan: false,
        latest_stale_scene_ids: [],
      });
      setScenes([]);
      setManifest(null);
      setVerifyResult(null);
      setReleaseEvidenceCreated(false);
      setProjectMedia(null);
      setStoredObjects(null);
      setRecentKeys(created.storage_keys ?? []);
      setMessage("Project created.");
    }
  }

  async function handleUploadV1() {
    if (!project) return;
    const result = await run(() =>
      uploadSource(project.project_id, "v1", sourceV1)
    );
    if (result) {
      await refreshProject(project.project_id);
      setScenes([]);
      setManifest(null);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      setMessage(`Uploaded v1 with ${result.chunks.length} chunks.`);
    }
  }

  async function handleGeneratePlan() {
    if (!project) return;
    const result = await run(() => generatePlan(project.project_id, "v1"));
    if (result) {
      await refreshProject(project.project_id);
      setScenes(result.scenes);
      setManifest(null);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      const plannerNote =
        result.planner === "genblaze-chat"
          ? `planned by Genblaze chat${result.genblaze_planner_model ? ` · ${result.genblaze_planner_model}` : ""}`
          : `deterministic planner${result.planner_fallback_reason ? ` — ${result.planner_fallback_reason}` : ""}`;
      setMessage(`Generated 3-scene plan (${plannerNote}).`);
    }
  }

  async function handleUploadV2() {
    if (!project) return;
    const result = await run(() =>
      uploadSource(project.project_id, "v2", sourceV2)
    );
    if (result) {
      await refreshProject(project.project_id);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      setMessage(`Uploaded v2 with ${result.chunks.length} chunks.`);
    }
  }

  async function handleCompare() {
    if (!project) return;
    const result = await run(() =>
      compareSource(project.project_id, "v1", "v2")
    );
    if (result) {
      await refreshProject(project.project_id);
      setScenes(result.scenes);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      setMessage(
        `Compare complete. Stale: ${result.stale_scene_ids.join(", ") || "none"}.`
      );
    }
  }

  async function handleGenerateMedia() {
    if (!project) return;
    const result = await run(() =>
      generateMedia(project.project_id, "v1")
    );
    if (result) {
      setProjectMedia({
        project_id: result.project_id,
        source_version: result.source_version,
        current_media_mode: result.media_mode,
        scenes: result.scenes,
      });
      setMediaMode(result.media_mode);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      const complete = result.scenes.filter((s) => s.status === "complete").length;
      const skipped = result.scenes.filter((s) => s.status === "skipped").length;
      setMessage(
        `Media generation: ${complete} complete, ${skipped} skipped (${result.media_mode}).`
      );
    }
  }

  async function handleRefreshMedia() {
    if (!project) return;
    const result = await run(() => getProjectMedia(project.project_id, "v1"));
    if (result) {
      setProjectMedia(result);
      setMediaMode(result.current_media_mode);
      setMessage(`Loaded media for ${result.scenes.length} scene(s).`);
    }
  }

  async function handleRelease() {
    if (!project) return;
    const result = await run(() => createRelease(project.project_id, "v1"));
    if (result) {
      setManifest(result);
      setVerifyResult(null);
      if (result.hash_verified) {
        setReleaseEvidenceCreated(true);
      }
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      setMessage(
        `Release ${result.release_status}: ${result.message}`
      );
    }
  }

  async function handleVerifyRelease() {
    if (!project) return;
    const result = await run(() =>
      verifyRelease(project.project_id, "v1", false)
    );
    if (result) {
      setVerifyResult(result);
      setMessage(
        `Verify ${result.release_status}: hash_verified=${result.hash_verified}`
      );
    }
  }

  const objectList = storedObjects?.objects ?? [];

  return (
    <>
      <header className="app-bar">
        <div className="app-bar-inner">
          <Link href="/" className="app-bar-brand">
            <Icon name="shield" size={18} />
            SceneLedger
          </Link>
          <div className="app-bar-meta">
            <span className={`badge ${storageBackend === "b2" ? "b2" : "neutral"}`}>
              {storageBackend === "b2" ? "Backblaze B2" : storageBackend}
            </span>
            <span
              className={`badge ${mediaMode === "genblaze" ? "verified" : "placeholder"}`}
            >
              {mediaMode}
            </span>
            {apiVersion && <span>API {apiVersion}</span>}
          </div>
        </div>
      </header>

      <main id="main-content">
        <h1>Guided demo</h1>
        <p className="subtitle">
          Source-linked training scenes with provenance, stale detection, and
          verifiable release evidence — media and manifests stored on{" "}
          {storageBackend === "b2" ? "Backblaze B2" : "local storage"}.
        </p>

        <DemoStepper completion={stepCompletion} />

        {loading && (
          <div className="toast toast-success" role="status">
            <Spinner />
            <span>Working…</span>
          </div>
        )}
        {error && (
          <div className="toast toast-error" role="alert">
            <Icon name="cross" size={16} />
            <span>{error}</span>
          </div>
        )}
        {message && !loading && (
          <div className="toast toast-success" role="status" aria-live="polite">
            <Icon name="check" size={16} />
            <span>{message}</span>
          </div>
        )}

        <div className="card step-card">
          <h2>
            <span className="step-badge">1</span> Project
          </h2>
          <div className="actions">
            <button type="button" onClick={handleCreateProject} disabled={loading}>
              Create Project
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleLoadDemo}
              disabled={loading}
            >
              Load Warehouse Safety Demo
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleResetDemo}
              disabled={loading}
            >
              Reset Demo
            </button>
          </div>
          <p className="helper-text">{RESET_DEMO_HELPER}</p>
          {project && (
            <div className="project-facts">
              <span>
                Project:{" "}
                <code title={project.project_id}>
                  {project.project_id.slice(0, 8)}…
                </code>
              </span>
              {tenantPrefix && (
                <span>
                  prefix: <code>{tenantPrefix}</code>
                </span>
              )}
              <span>
                versions: {project.uploaded_source_versions.join(", ") || "none"}
              </span>
              <span>plan: {project.has_plan ? "yes" : "no"}</span>
              {project.latest_stale_scene_ids.length > 0 && (
                <span>
                  <StatusBadge status="stale" />{" "}
                  {project.latest_stale_scene_ids.join(", ")}
                </span>
              )}
            </div>
          )}
        </div>

        <div className="card step-card">
          <h2>
            <span className="step-badge">2–4</span> Source v1 · Plan · Media
          </h2>
          <label className="field-label" htmlFor="source-v1">
            Source document v1
          </label>
          <textarea
            id="source-v1"
            value={sourceV1}
            onChange={(e) => setSourceV1(e.target.value)}
          />
          <div className="actions">
            <button
              type="button"
              onClick={handleUploadV1}
              disabled={loading || !project}
            >
              Upload Source v1
            </button>
            <button
              type="button"
              onClick={handleGeneratePlan}
              disabled={loading || !project}
            >
              Generate Scene Plan
            </button>
            <button
              type="button"
              onClick={handleGenerateMedia}
              disabled={loading || !project || !project.has_plan}
            >
              Generate Media
            </button>
          </div>
          {!project && (
            <p className="helper-text">Create a project first (step 1).</p>
          )}
          {scenes.length > 0 && (
            <div className="scene-grid">
              {scenes.map((scene) => (
                <SceneCard key={scene.scene_id} scene={scene} />
              ))}
            </div>
          )}
        </div>

        <div className="card step-card">
          <h2>
            <span className="step-badge">5</span> Release evidence
          </h2>
          <p className="meta">
            Create a verified release manifest linking source chunks, media
            assets, and SHA-256 hashes.
          </p>
          <div className="actions">
            <button
              type="button"
              onClick={handleRelease}
              disabled={loading || !project}
            >
              Create Release Manifest
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleVerifyRelease}
              disabled={loading || !project || !manifest}
            >
              Verify Release
            </button>
          </div>
        </div>

        {manifest && (
          <ReleaseEvidencePanel
            manifest={manifest}
            verifyResult={verifyResult}
            showRawRelease={showRawRelease}
            onToggleRaw={() => setShowRawRelease((v) => !v)}
          />
        )}

        <div className="card step-card">
          <h2>
            <span className="step-badge">6–7</span> Source v2 · Compare
          </h2>
          <p className="meta">{STALE_HINT}</p>
          <label className="field-label" htmlFor="source-v2">
            Source document v2
          </label>
          <textarea
            id="source-v2"
            value={sourceV2}
            onChange={(e) => setSourceV2(e.target.value)}
          />
          <div className="actions">
            <button
              type="button"
              onClick={handleUploadV2}
              disabled={loading || !project}
            >
              Upload Source v2
            </button>
            <button
              type="button"
              onClick={handleCompare}
              disabled={loading || !project}
            >
              Compare Source Versions
            </button>
          </div>
        </div>

        <div className="card step-card">
          <h2>
            <span className="step-badge">8</span> Recreate release evidence
          </h2>
          <p className="meta">
            After compare, recreate the release: hashes still verify, but the
            release becomes a <StatusBadge status="warning" /> because v2
            superseded scene-003.
          </p>
          <div className="actions">
            <button
              type="button"
              onClick={handleRelease}
              disabled={loading || !project}
            >
              Recreate Release Evidence
            </button>
          </div>
        </div>

        <GenblazePanel
          mediaMode={mediaMode}
          hasGenblazeAsset={hasGenblazeStoryboard(projectMedia)}
          provenance={manifest?.genblaze_provenance ?? null}
          plannerProvenance={manifest?.planner_provenance ?? null}
        />

        <div className="card">
          <h2>Media</h2>
          <p className="meta">
            Current mode:{" "}
            <span
              className={`badge ${mediaMode === "genblaze" ? "verified" : "placeholder"}`}
            >
              {mediaMode}
            </span>
          </p>
          <div className="actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleRefreshMedia}
              disabled={loading || !project}
            >
              Refresh Media
            </button>
          </div>
          {(!projectMedia || projectMedia.scenes.length === 0) && (
            <p className="empty-state">
              No media yet — generate a scene plan, then click Generate Media
              (step 4).
            </p>
          )}
          {projectMedia && projectMedia.scenes.length > 0 && (
            <ul className="media-list">
              {projectMedia.scenes.map((scene) => (
                <li key={scene.scene_id} className="media-scene">
                  <strong>{scene.scene_id}</strong>{" "}
                  <StatusBadge status={scene.status} />
                  <span className="meta"> · mode: {scene.media_mode}</span>
                  <ul className="object-list">
                    {(["storyboard", "clip", "narration", "captions"] as const).map(
                      (role) => {
                        const asset = scene.assets[role];
                        return (
                          <li key={role}>
                            <code>{role}</code>
                            <span className="meta">
                              {" "}
                              · {asset.generator} · sha256:{" "}
                              <span title={asset.sha256}>
                                {asset.sha256.slice(0, 12)}…
                              </span>
                            </span>
                          </li>
                        );
                      }
                    )}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </div>

        <StoragePanel
          storageBackend={storageBackend}
          tenantPrefix={tenantPrefix}
          objects={objectList}
          recentKeys={recentKeys}
          releaseManifestKey={releaseManifestKey}
          onRefresh={handleRefreshObjects}
          refreshDisabled={loading || !project}
        />
      </main>
    </>
  );
}
