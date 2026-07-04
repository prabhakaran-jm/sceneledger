import type { ReleaseManifest, VerifyReleaseResponse } from "@/lib/api";
import { sceneHashVerified } from "@/lib/demo";

type ReleaseEvidencePanelProps = {
  manifest: ReleaseManifest;
  verifyResult: VerifyReleaseResponse | null;
  showRawRelease: boolean;
  onToggleRaw: () => void;
};

export function ReleaseEvidencePanel({
  manifest,
  verifyResult,
  showRawRelease,
  onToggleRaw,
}: ReleaseEvidencePanelProps) {
  const isWarning = manifest.release_status === "warning";

  return (
    <section
      className={`card release-evidence${isWarning ? " release-warning-panel" : ""}`}
    >
      <h2>Release Evidence</h2>
      {isWarning && (
        <p className="warning-callout">
          Scene-003 is stale — release is no longer current for source v1.
          Superseded by source version{" "}
          <strong>{manifest.release_superseded_by_source_version}</strong>.
        </p>
      )}
      <p>
        <span className={`badge release-${manifest.release_status}`}>
          {manifest.release_status}
        </span>
      </p>
      <p className="meta">{manifest.message}</p>
      <p className="meta">
        source: {manifest.source_version} · release_id: {manifest.release_id} ·
        hash_verified: {manifest.hash_verified ? "yes" : "no"}
      </p>
      {manifest.release_superseded_by_source_version && (
        <p className="meta">
          release_superseded_by_source_version:{" "}
          {manifest.release_superseded_by_source_version}
        </p>
      )}
      <p className="hash-line">
        <span className="meta">release_manifest_sha256:</span>{" "}
        <code>{manifest.release_manifest_sha256}</code>
      </p>
      {manifest.genblaze_provenance.present && (
        <p className="meta">
          genblaze assets: {manifest.genblaze_provenance.asset_count} · run_ids:{" "}
          {manifest.genblaze_provenance.run_ids.join(", ") || "none"}
        </p>
      )}
      <ul className="checklist">
        {Object.entries(manifest.verification).map(([key, value]) => (
          <li key={key}>
            {key}: {value ? "yes" : "no"}
          </li>
        ))}
      </ul>
      <div className="table-wrap">
        <table className="evidence-table">
          <thead>
            <tr>
              <th>Scene</th>
              <th>Source chunks</th>
              <th>Status</th>
              <th>Media</th>
              <th>Hash verified</th>
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
                  <span className={`badge ${scene.status}`}>{scene.status}</span>
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
              </ul>
            </li>
          ))}
        </ul>
      </details>
      <div className="actions">
        <button type="button" onClick={onToggleRaw}>
          {showRawRelease ? "Hide" : "Show"} raw JSON
        </button>
      </div>
      {showRawRelease && (
        <pre className="manifest">{JSON.stringify(manifest, null, 2)}</pre>
      )}
      {verifyResult && (
        <div className="verify-result">
          <p>
            <span className={`badge release-${verifyResult.release_status}`}>
              {verifyResult.release_status}
            </span>
          </p>
          <p className="meta">
            Last verify · hash_verified:{" "}
            {verifyResult.hash_verified ? "yes" : "no"} ·{" "}
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
  );
}
