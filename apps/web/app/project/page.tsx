"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  compareSource,
  createProject,
  generatePlan,
  uploadSource,
  type Project,
  type Scene,
} from "@/lib/api";

const DEMO_V1 = `Before entering the production floor, every team member must complete the daily safety briefing. Review the posted hazard map at the main entrance and confirm you are wearing required personal protective equipment including safety glasses, closed-toe shoes, and your assigned badge.

Inspect your workstation before starting any task. Verify that emergency stop buttons are accessible, guards are in place on moving parts, and all tools are in good working condition. Report damaged equipment to your supervisor immediately and do not operate machinery until it is cleared for use.

If you hear the facility alarm or observe an unsafe condition, stop work immediately. Move to the nearest marked exit route without running. Gather at your department assembly point and wait for further instructions from the safety coordinator. Do not re-enter the building until an all-clear is announced.`;

const DEMO_V2 = `Before entering the production floor, every team member must complete the daily safety briefing. Review the posted hazard map at the main entrance and confirm you are wearing required personal protective equipment including safety glasses, closed-toe shoes, and your assigned badge.

Inspect your workstation before starting any task. Verify that emergency stop buttons are accessible, guards are in place on moving parts, fire extinguisher tags are current, and all tools are in good working condition. Report damaged equipment to your supervisor immediately and do not operate machinery until it is cleared for use.

If you hear the facility alarm or observe an unsafe condition, stop work immediately. Move to the nearest marked exit route without running. Gather at your department assembly point and wait for further instructions from the safety coordinator. Do not re-enter the building until an all-clear is announced.`;

function SceneCard({ scene, index }: { scene: Scene; index: number }) {
  return (
    <div className="card scene-card">
      <h3>
        Scene {index + 1}: {scene.title}
        <span className={`badge ${scene.status}`}>{scene.status}</span>
      </h3>
      <p className="meta">
        Chunks: {scene.source_chunk_ids.join(", ") || "none"}
      </p>
      <p>{scene.narration.slice(0, 200)}…</p>
    </div>
  );
}

export default function ProjectPage() {
  const [project, setProject] = useState<Project | null>(null);
  const [sourceText, setSourceText] = useState(DEMO_V1);
  const [compareText, setCompareText] = useState(DEMO_V2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initProject = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await createProject("Demo Safety Training");
      setProject(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    initProject();
  }, [initProject]);

  async function handleUpload() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await uploadSource(project.project_id, sourceText);
      setProject(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  async function handlePlan() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await generatePlan(project.project_id);
      setProject(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Plan failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleCompare() {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const result = await compareSource(project.project_id, compareText);
      setProject({
        ...project,
        source_version: result.source_version,
        chunks: result.chunks,
        scenes: result.scenes,
        stale_scene_ids: result.stale_scene_ids,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <p>
        <Link href="/">← Home</Link>
      </p>
      <h1>Demo Project</h1>
      <p className="subtitle">
        Upload source v1, generate a 3-scene plan, then compare against v2 to
        see stale detection.
      </p>

      {project && (
        <p className="status-bar">
          Project: {project.project_id.slice(0, 8)}… · source v
          {project.source_version} · {project.scenes.length} scenes
          {project.stale_scene_ids.length > 0 &&
            ` · ${project.stale_scene_ids.length} stale`}
        </p>
      )}

      {error && <p className="error">{error}</p>}

      <div className="card">
        <h2>Source document (v1)</h2>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          aria-label="Source document v1"
        />
        <div className="actions">
          <button type="button" onClick={handleUpload} disabled={loading || !project}>
            Upload source
          </button>
          <button
            type="button"
            onClick={handlePlan}
            disabled={loading || !project || !project.chunks.length}
          >
            Generate plan
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Updated source (v2)</h2>
        <textarea
          value={compareText}
          onChange={(e) => setCompareText(e.target.value)}
          aria-label="Source document v2"
        />
        <div className="actions">
          <button
            type="button"
            onClick={handleCompare}
            disabled={loading || !project || !project.scenes.length}
          >
            Compare source
          </button>
        </div>
      </div>

      {project && project.scenes.length > 0 && (
        <section>
          <h2>Scenes</h2>
          <div className="scene-grid">
            {project.scenes.map((scene, index) => (
              <SceneCard key={scene.scene_id} scene={scene} index={index} />
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
