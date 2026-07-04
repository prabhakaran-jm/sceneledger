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
  "release_manifest",
  "other",
];

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
        <span className={`badge ${isB2 ? "b2" : "current"}`}>
          {isB2 ? "B2" : storageBackend}
        </span>
        {tenantPrefix && (
          <span className="meta">
            tenant prefix: <code>{tenantPrefix}</code>
          </span>
        )}
        <span className="meta">objects: {objects.length}</span>
      </div>
      {onRefresh && (
        <div className="actions">
          <button type="button" onClick={onRefresh} disabled={refreshDisabled}>
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
      {recentKeys.length > 0 && (
        <>
          <p className="meta">Keys written this session:</p>
          <ul className="object-list compact-list">
            {recentKeys.map((key) => (
              <li key={key}>
                <code>{key}</code>
              </li>
            ))}
          </ul>
        </>
      )}
      {objects.length > 0 && (
        <div className="storage-groups">
          {GROUP_ORDER.map((group) => {
            const items = grouped[group];
            if (items.length === 0) return null;
            return (
              <div key={group} className="storage-group">
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
