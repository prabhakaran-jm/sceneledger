"use client";

import { useEffect, useState } from "react";
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

const DEMO_V1 = `Stop work when the alarm sounds.

Leave through the nearest marked exit.

Report to assembly point A.`;

const DEMO_V2 = `Stop work when the alarm sounds.

Leave through the nearest marked exit.

Report to assembly point C.`;

function SceneCard({ scene }: { scene: Scene }) {
  const stale = scene.status === "stale";
  return (
    <div className={`card scene-card${stale ? " scene-card-stale" : ""}`}>
      <h3>
        {scene.title}
        <span className={`badge ${scene.status}`}>{scene.status}</span>
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
  const [showRawRelease, setShowRawRelease] = useState(false);
  const [storageBackend, setStorageBackend] = useState<string>("local");
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
      })
      .catch(() => setStorageBackend("unknown"));
  }, []);

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
      setMessage("Generated 3-scene plan.");
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
    <main>
      <p>
        <Link href="/">← Home</Link>
      </p>
      <h1>Demo Project</h1>
      <p className="subtitle">
        M0 loop: upload v1, plan scenes, upload v2, compare, release.
      </p>

      {project && (
        <p className="status-bar">
          Project: {project.project_id.slice(0, 8)}… · storage: {storageBackend}{" "}
          · versions: {project.uploaded_source_versions.join(", ") || "none"} ·
          plan: {project.has_plan ? "yes" : "no"}
          {project.latest_stale_scene_ids.length > 0 &&
            ` · stale: ${project.latest_stale_scene_ids.join(", ")}`}
        </p>
      )}

      {error && <p className="error">{error}</p>}
      {message && <p className="message">{message}</p>}

      <div className="card">
        <h2>Project</h2>
        <div className="actions">
          <button type="button" onClick={handleCreateProject} disabled={loading}>
            Create Project
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Source v1</h2>
        <textarea
          value={sourceV1}
          onChange={(e) => setSourceV1(e.target.value)}
          aria-label="Source document v1"
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
      </div>

      <div className="card">
        <h2>Source v2</h2>
        <textarea
          value={sourceV2}
          onChange={(e) => setSourceV2(e.target.value)}
          aria-label="Source document v2"
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

      <div className="card">
        <h2>Release</h2>
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
            onClick={handleVerifyRelease}
            disabled={loading || !project || !manifest}
          >
            Verify Release
          </button>
        </div>
      </div>

      {(manifest || verifyResult) && (
        <section className="card">
          <h2>Release Evidence</h2>
          {manifest && (
            <>
              <p>
                <span className={`badge release-${manifest.release_status}`}>
                  {manifest.release_status}
                </span>
              </p>
              <p className="meta">{manifest.message}</p>
              <p className="meta">
                source: {manifest.source_version} · release_id:{" "}
                {manifest.release_id.slice(0, 12)}… · hash_verified:{" "}
                {manifest.hash_verified ? "yes" : "no"}
              </p>
              {manifest.release_superseded_by_source_version && (
                <p className="meta">
                  superseded by source version:{" "}
                  {manifest.release_superseded_by_source_version}
                </p>
              )}
              <p className="meta">
                chunks: {manifest.source.chunk_count} · stale:{" "}
                {manifest.stale_scene_ids.join(", ") || "none"} · manifest
                sha256: {manifest.release_manifest_sha256.slice(0, 16)}…
              </p>
              {manifest.genblaze_provenance.present && (
                <p className="meta">
                  genblaze assets: {manifest.genblaze_provenance.asset_count} ·
                  run_ids: {manifest.genblaze_provenance.run_ids.join(", ") ||
                    "none"}
                </p>
              )}
              <ul className="checklist">
                {Object.entries(manifest.verification).map(([key, value]) => (
                  <li key={key}>
                    {key}: {value ? "yes" : "no"}
                  </li>
                ))}
              </ul>
              <ul className="media-list">
                {manifest.scenes.map((scene) => (
                  <li key={scene.scene_id} className="media-scene">
                    <strong>{scene.scene_id}</strong>
                    <span className={`badge ${scene.status}`}>
                      {scene.status}
                    </span>
                    <span className="meta">
                      {" "}
                      · media: {scene.media_status} · mode: {scene.media_mode}
                    </span>
                    <ul className="object-list">
                      {(
                        ["storyboard", "clip", "narration", "captions"] as const
                      ).map((role) => {
                        const asset = scene.assets[role];
                        if (!asset) return null;
                        return (
                          <li key={role}>
                            <code>{role}</code>
                            <span className="meta">
                              {" "}
                              · hash ok: {asset.hash_verified ? "yes" : "no"} ·{" "}
                              {asset.generator} · <code>{asset.key}</code>
                            </span>
                          </li>
                        );
                      })}
                    </ul>
                  </li>
                ))}
              </ul>
              <div className="actions">
                <button
                  type="button"
                  onClick={() => setShowRawRelease((v) => !v)}
                >
                  {showRawRelease ? "Hide" : "Show"} raw JSON
                </button>
              </div>
              {showRawRelease && (
                <pre className="manifest">
                  {JSON.stringify(manifest, null, 2)}
                </pre>
              )}
            </>
          )}
          {verifyResult && (
            <div className="verify-result">
              <p className="meta">
                Last verify: {verifyResult.release_status} ·{" "}
                {verifyResult.message}
              </p>
              {verifyResult.errors.length > 0 && (
                <ul className="object-list">
                  {verifyResult.errors.map((err) => (
                    <li key={err}>{err}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </section>
      )}

      <div className="card">
        <h2>Media</h2>
        <p className="meta">
          Current mode: {mediaMode}
          {projectMedia &&
            projectMedia.scenes.some(
              (scene) => scene.media_mode !== projectMedia.current_media_mode
            ) &&
            " · stored scenes may use a different mode"}
        </p>
        <div className="actions">
          <button
            type="button"
            onClick={handleRefreshMedia}
            disabled={loading || !project}
          >
            Refresh Media
          </button>
        </div>
        {projectMedia && projectMedia.scenes.length > 0 && (
          <ul className="media-list">
            {projectMedia.scenes.map((scene) => (
              <li key={scene.scene_id} className="media-scene">
                <strong>{scene.scene_id}</strong>
                <span className={`badge ${scene.status === "complete" || scene.status === "skipped" ? "current" : "stale"}`}>
                  {scene.status}
                </span>
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
                            · {asset.generator} · {asset.content_type} ·
                            playable: {asset.playable ? "yes" : "no"} · sha256:{" "}
                            {asset.sha256.slice(0, 12)}…
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

      <div className="card">
        <h2>Storage</h2>
        <p className="meta">Backend: {storageBackend}</p>
        <div className="actions">
          <button
            type="button"
            onClick={handleRefreshObjects}
            disabled={loading || !project}
          >
            Refresh Stored Objects
          </button>
        </div>
        {recentKeys.length > 0 && (
          <>
            <p className="meta">Keys written this session:</p>
            <ul className="object-list">
              {recentKeys.map((key) => (
                <li key={key}>
                  <code>{key}</code>
                </li>
              ))}
            </ul>
          </>
        )}
        {objectList.length > 0 && (
          <>
            <p className="meta">Stored objects ({objectList.length}):</p>
            <ul className="object-list">
              {objectList.map((obj) => (
                <li key={obj.key}>
                  <code>{obj.key}</code>
                  <span className="meta"> · {obj.kind}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {scenes.length > 0 && (
        <section>
          <h2>Scenes</h2>
          <div className="scene-grid">
            {scenes.map((scene) => (
              <SceneCard key={scene.scene_id} scene={scene} />
            ))}
          </div>
        </section>
      )}

    </main>
  );
}
