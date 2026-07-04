import type { ProjectMedia, ProjectSummary, ReleaseManifest } from "@/lib/api";
import type { StoredObject } from "@/lib/api";

export const DEMO_V1 = `Stop work when the alarm sounds.

Leave through the nearest marked exit.

Report to assembly point A.`;

export const DEMO_V2 = `Stop work when the alarm sounds.

Leave through the nearest marked exit.

Report to assembly point C.`;

export const RESET_DEMO_HELPER =
  "Clears the page state only. It does not delete objects from B2.";

export const STALE_HINT =
  "Only scene-003 should become stale (assembly point A → C).";

export type DemoStepId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export type DemoStep = {
  id: DemoStepId;
  label: string;
  helper?: string;
};

export const DEMO_STEPS: DemoStep[] = [
  { id: 1, label: "Create project" },
  { id: 2, label: "Upload source v1" },
  { id: 3, label: "Generate scene plan" },
  { id: 4, label: "Generate media" },
  {
    id: 5,
    label: "Create release evidence",
    helper: "Complete when manifest exists and hash_verified is true.",
  },
  { id: 6, label: "Upload source v2" },
  {
    id: 7,
    label: "Compare versions",
    helper: STALE_HINT,
  },
  {
    id: 8,
    label: "Recreate release evidence",
    helper: "Release should show warning after compare.",
  },
];

export type StepCompletionInput = {
  project: ProjectSummary | null;
  projectMedia: ProjectMedia | null;
  manifest: ReleaseManifest | null;
  releaseEvidenceCreated: boolean;
};

export function computeStepCompletion(
  input: StepCompletionInput
): Record<DemoStepId, boolean> {
  const { project, projectMedia, manifest, releaseEvidenceCreated } = input;
  const hasV1 = project?.uploaded_source_versions.includes("v1") ?? false;
  const hasV2 = project?.uploaded_source_versions.includes("v2") ?? false;
  const mediaComplete =
    (projectMedia?.scenes.filter((s) => s.status === "complete").length ?? 0) >=
    3;
  const step5 =
    releaseEvidenceCreated ||
    (manifest !== null && manifest.hash_verified === true);
  const hasStale = (project?.latest_stale_scene_ids.length ?? 0) > 0;
  const step8 = manifest?.release_status === "warning";

  return {
    1: project !== null,
    2: hasV1,
    3: project?.has_plan ?? false,
    4: mediaComplete,
    5: step5,
    6: hasV2,
    7: hasStale,
    8: step8,
  };
}

export type ObjectGroup =
  | "source"
  | "chunks"
  | "plan"
  | "compare"
  | "media"
  | "media_manifest"
  | "release_manifest"
  | "other";

export const OBJECT_GROUP_LABELS: Record<ObjectGroup, string> = {
  source: "Source",
  chunks: "Chunks",
  plan: "Plan",
  compare: "Compare",
  media: "Media assets",
  media_manifest: "Media manifests",
  release_manifest: "Release manifest",
  other: "Other",
};

const MEDIA_KINDS = new Set([
  "media_storyboard",
  "media_clip",
  "media_clip_placeholder",
  "media_narration",
  "media_captions",
]);

export function objectKindToGroup(kind: string): ObjectGroup {
  if (kind === "source") return "source";
  if (kind === "chunks") return "chunks";
  if (kind === "plan") return "plan";
  if (kind === "compare") return "compare";
  if (MEDIA_KINDS.has(kind)) return "media";
  if (kind === "media_manifest") return "media_manifest";
  if (kind === "release_manifest") return "release_manifest";
  return "other";
}

export function groupStoredObjects(
  objects: StoredObject[]
): Record<ObjectGroup, StoredObject[]> {
  const groups: Record<ObjectGroup, StoredObject[]> = {
    source: [],
    chunks: [],
    plan: [],
    compare: [],
    media: [],
    media_manifest: [],
    release_manifest: [],
    other: [],
  };
  for (const obj of objects) {
    groups[objectKindToGroup(obj.kind)].push(obj);
  }
  return groups;
}

export function sceneHashVerified(
  assets: ReleaseManifest["scenes"][0]["assets"]
): "yes" | "no" | "—" {
  const entries = (["storyboard", "clip", "narration", "captions"] as const)
    .map((role) => assets[role])
    .filter(Boolean);
  if (entries.length === 0) return "—";
  return entries.every((a) => a!.hash_verified) ? "yes" : "no";
}

export function hasGenblazeStoryboard(
  projectMedia: ProjectMedia | null
): boolean {
  if (!projectMedia) return false;
  return projectMedia.scenes.some(
    (scene) => scene.assets.storyboard?.generator === "genblaze"
  );
}
