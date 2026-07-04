import type { ReleaseManifest, VerifyReleaseResponse } from "@/lib/api";
import { sceneHashVerified } from "@/lib/demo";
import { Icon, StatusBadge } from "./ui";

type ReleaseEvidencePanelProps = {
  manifest: ReleaseManifest;
  verifyResult: VerifyReleaseResponse | null;
  showRawRelease: boolean;
  onToggleRaw: () => void;
};

const VERIFICATION_LABELS: Record<string, string> = {
  source_chunks_present: "Source chunks present",
  scene_plan_present: "Scene plan present",
  media_manifests_present: "Media manifests present",
  asset_hashes_verified: "Asset hashes verified",
  stale_report_applied: "Stale report applied",
  release_current: "Release current",
};

function StatusBanner({
  status,
  message,
}: {
  status: string;
  message: string;
}) {
  const icon =
    status === "verified" ? "check" : status === "warning" ? "warning" : "cross";
  return (
    <div className={`status-banner status-banner-${status}`} role="status">
      <Icon name={icon} size={20} />
      <div>
        <strong>{status}</strong>
        <p>{message}</p>
      </div>
    </div>
  );
}

export function ReleaseEvidencePanel({
  manifest,
  verifyResult,
  showRawRelease,
  onToggleRaw,
}: ReleaseEvidencePanelProps) {
  const status = manifest.release_status;
  const panelClass =
    status === "warning"
      ? " release-warning-panel"
      : status === "blocked"
        ? " release-blocked-panel"
        : "";

  return (
    <section className={`card release-evidence${panelClass}`}>
      <h2>
        <Icon name="shield" size={18} /> Release Evidence
      </h2>

      <StatusBanner status={status} message={manifest.message} />

      {status === "warning" &&
        manifest.release_superseded_by_source_version && (
          <p className="meta">
            Asset hashes still verify, but the release is no longer current:
            source version{" "}
            <strong>{manifest.release_superseded_by_source_version}</strong>{" "}
            superseded it and made scene(s){" "}
            <strong>{manifest.stale_scene_ids.join(", ")}</strong> stale.
          </p>
        )}

      <dl className="fact-grid">
        <div className="fact">
          <dt>Source version</dt>
          <dd>{manifest.source_version}</dd>
        </div>
        <div className="fact">
          <dt>Release ID</dt>
          <dd>
            <code>{manifest.release_id}</code>
          </dd>
        </div>
        <div className="fact">
          <dt>Hash verified</dt>
          <dd>{manifest.hash_verified ? "Yes — all SHA-256 checks pass" : "No"}</dd>
        </div>
        <div className="fact">
          <dt>Superseded by</dt>
          <dd>{manifest.release_superseded_by_source_version ?? "—"}</dd>
        </div>
        <div className="fact">
          <dt>Release manifest SHA-256</dt>
          <dd>
            <code title={manifest.release_manifest_sha256}>
              {manifest.release_manifest_sha256}
            </code>
          </dd>
        </div>
        {manifest.genblaze_provenance.present && (
          <div className="fact">
            <dt>Genblaze provenance</dt>
            <dd>
              {manifest.genblaze_provenance.asset_count} asset(s) ·{" "}
              {manifest.genblaze_provenance.manifest_keys.length} manifest(s) ·
              run IDs: {manifest.genblaze_provenance.run_ids.join(", ") || "—"}
            </dd>
          </div>
        )}
      </dl>

      <h3>Verification checks</h3>
      <ul className="checklist">
        {Object.entries(manifest.verification).map(([key, value]) => (
          <li key={key}>
            <span className={value ? "check-yes" : "check-no"}>
              <Icon name={value ? "check" : "cross"} size={14} />
            </span>
            {VERIFICATION_LABELS[key] ?? key}
            <span className="visually-hidden">{value ? ": yes" : ": no"}</span>
          </li>
        ))}
      </ul>

      <h3>Scenes</h3>
      <div className="table-wrap">
        <table className="evidence-table">
          <thead>
            <tr>
              <th scope="col">Scene</th>
              <th scope="col">Source chunks</th>
              <th scope="col">Status</th>
              <th scope="col">Media</th>
              <th scope="col">Hashes</th>
            </tr>
          </thead>
          <tbody>
            {manifest.scenes.map((scene) => (
              <tr
                key={scene.scene_id}
                className={scene.status === "stale" ? "scene-row-stale" : ""}
              >
                <td>{scene.scene_id}</td>
                <td>{scene.source_chunk_ids.join(", ")}</td>
                <td>
                  <StatusBadge status={scene.status} />
                </td>
                <td>{scene.media_status}</td>
                <td>{sceneHashVerified(scene.assets)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <details className="asset-details">
        <summary>Per-asset hash details</summary>
        <ul className="media-list">
          {manifest.scenes.map((scene) => (
            <li key={scene.scene_id} className="media-scene">
              <strong>{scene.scene_id}</strong>
              <ul className="object-list">
                {(["storyboard", "clip", "narration", "captions"] as const).map(
                  (role) => {
                    const asset = scene.assets[role];
                    if (!asset) return null;
                    return (
                      <li key={role}>
                        <code>{role}</code>
                        <span className="meta">
                          {" "}
                          · hash ok: {asset.hash_verified ? "yes" : "no"} ·{" "}
                          {asset.generator}
                        </span>
                      </li>
                    );
                  }
                )}
                {scene.genblaze_manifest_key && (
                  <li>
                    <code>genblaze manifest</code>
                    <span className="meta">
                      {" "}
                      · verified:{" "}
                      {scene.genblaze_manifest_verified ? "yes" : "no"} ·{" "}
                      <code>{scene.genblaze_manifest_key}</code>
                    </span>
                  </li>
                )}
              </ul>
            </li>
          ))}
        </ul>
      </details>

      <details
        className="raw-json-details"
        open={showRawRelease}
        onToggle={(e) => {
          if (e.currentTarget.open !== showRawRelease) onToggleRaw();
        }}
      >
        <summary>Raw release manifest JSON</summary>
        <pre className="manifest">{JSON.stringify(manifest, null, 2)}</pre>
      </details>

      {verifyResult && (
        <div className="verify-result">
          <h3>Last verification run</h3>
          <StatusBanner
            status={verifyResult.release_status}
            message={verifyResult.message}
          />
          <p className="meta">
            hash_verified: {verifyResult.hash_verified ? "yes" : "no"}
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
  );
}
