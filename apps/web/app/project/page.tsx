"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  compareSource,
  createProject,
  createRelease,
  generatePlan,
  getHealth,
  getProject,
  getProjectObjects,
  uploadSource,
  type ProjectObjects,
  type ProjectSummary,
  type ReleaseManifest,
  type Scene,
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
  const [storageBackend, setStorageBackend] = useState<string>("local");
  const [recentKeys, setRecentKeys] = useState<string[]>([]);
  const [storedObjects, setStoredObjects] = useState<ProjectObjects | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((health) => setStorageBackend(health.storage_backend))
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

  async function handleRelease() {
    if (!project) return;
    const result = await run(() => createRelease(project.project_id, "v1"));
    if (result) {
      setManifest(result);
      setRecentKeys((keys) => mergeKeys(keys, result.storage_keys));
      setMessage("Release manifest created.");
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
        </div>
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

      {manifest && (
        <section>
          <h2>Release Manifest</h2>
          <pre className="manifest">{JSON.stringify(manifest, null, 2)}</pre>
        </section>
      )}
    </main>
  );
}
