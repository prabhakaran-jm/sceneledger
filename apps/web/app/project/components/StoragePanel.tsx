import type { StoredObject } from "@/lib/api";
import {
  OBJECT_GROUP_LABELS,
  groupStoredObjects,
  type ObjectGroup,
} from "@/lib/demo";

type StoragePanelProps = {
  storageBackend: string;
  tenantPrefix: string | null;
  objects: StoredObject[];
  recentKeys: string[];
  releaseManifestKey: string | null;
  onRefresh?: () => void;
  refreshDisabled?: boolean;
};

const GROUP_ORDER: ObjectGroup[] = [
  "source",
  "chunks",
  "plan",
  "compare",
  "media",
  "media_manifest",
  "genblaze_manifest",
  "release_manifest",
  "other",
];

const HIGHLIGHT_GROUPS: Set<ObjectGroup> = new Set([
  "release_manifest",
  "genblaze_manifest",
]);

export function StoragePanel({
  storageBackend,
  tenantPrefix,
  objects,
  recentKeys,
  releaseManifestKey,
  onRefresh,
  refreshDisabled,
}: StoragePanelProps) {
  const grouped = groupStoredObjects(objects);
  const isB2 = storageBackend === "b2";

  return (
    <div className="card">
      <h2>Storage</h2>
      <div className="storage-header">
        <span className={`badge ${isB2 ? "b2" : "neutral"}`}>
          {isB2 ? "Backblaze B2" : storageBackend}
        </span>
        <span className="badge neutral">{objects.length} objects</span>
        {tenantPrefix && (
          <span className="meta">
            prefix: <code>{tenantPrefix}</code>
          </span>
        )}
      </div>
      {onRefresh && (
        <div className="actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={onRefresh}
            disabled={refreshDisabled}
          >
            Refresh Stored Objects
          </button>
        </div>
      )}
      {releaseManifestKey && (
        <p className="release-key-highlight">
          <span className="meta">Release manifest key:</span>{" "}
          <code>{releaseManifestKey}</code>
        </p>
      )}
      {objects.length === 0 && recentKeys.length === 0 && (
        <p className="empty-state">
          No stored objects yet — create a project and upload a source, then
          refresh to see the object layout.
        </p>
      )}
      {recentKeys.length > 0 && (
        <details className="asset-details">
          <summary>Keys written this session ({recentKeys.length})</summary>
          <ul className="object-list compact-list">
            {recentKeys.map((key) => (
              <li key={key}>
                <code>{key}</code>
              </li>
            ))}
          </ul>
        </details>
      )}
      {objects.length > 0 && (
        <div className="storage-groups">
          {GROUP_ORDER.map((group) => {
            const items = grouped[group];
            if (items.length === 0) return null;
            const highlight = HIGHLIGHT_GROUPS.has(group);
            return (
              <div
                key={group}
                className={`storage-group${highlight ? " storage-group-highlight" : ""}`}
              >
                <h3>
                  {OBJECT_GROUP_LABELS[group]} ({items.length})
                </h3>
                <ul className="object-list compact-list">
                  {items.map((obj) => (
                    <li key={obj.key}>
                      <code>{obj.key}</code>
                      {obj.size != null && (
                        <span className="meta"> · {obj.size} bytes</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
