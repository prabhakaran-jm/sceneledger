import type { ReleaseManifest } from "@/lib/api";
import { assetUrl } from "@/lib/api";
import { Icon, StatusBadge } from "./ui";

type ReleasePackagePanelProps = {
  manifest: ReleaseManifest;
  releaseManifestKey: string | null;
  onVerify: () => void;
  verifyDisabled: boolean;
};

function keyOf(entry: { key: string } | null | undefined) {
  return entry?.key ?? null;
}

export function ReleasePackagePanel({
  manifest,
  releaseManifestKey,
  onVerify,
  verifyDisabled,
}: ReleasePackagePanelProps) {
  const pid = manifest.project_id;

  return (
    <section className="card release-package">
      <h2>
        <Icon name="check" size={18} /> Release Package
      </h2>
      <p className="meta">
        The final deliverable: every scene&apos;s media, its Genblaze
        provenance, and the verified release evidence — all stored under this
        project&apos;s B2 prefix.
      </p>

      <dl className="fact-grid">
        <div className="fact">
          <dt>Source version</dt>
          <dd>{manifest.source_version}</dd>
        </div>
        <div className="fact">
          <dt>Release status</dt>
          <dd>
            <StatusBadge
              status={manifest.release_status}
              className={`badge release-${manifest.release_status}`}
            />
          </dd>
        </div>
        <div className="fact">
          <dt>Release manifest SHA-256</dt>
          <dd>
            <code title={manifest.release_manifest_sha256}>
              {manifest.release_manifest_sha256}
            </code>
          </dd>
        </div>
        <div className="fact">
          <dt>B2 release manifest key</dt>
          <dd>
            <code>{releaseManifestKey ?? "—"}</code>
          </dd>
        </div>
      </dl>

      {manifest.final_video ? (
        <div className="final-video">
          <h3>Final stitched video</h3>
          <video
            controls
            preload="metadata"
            src={assetUrl(pid, manifest.final_video.key)}
            aria-label="Final stitched training video"
          />
          <p className="meta">
            <code>{manifest.final_video.key}</code> · sha256{" "}
            <code title={manifest.final_video.sha256}>
              {manifest.final_video.sha256.slice(0, 16)}…
            </code>{" "}
            · hash {manifest.final_video.hash_verified ? "verified" : "FAILED"}
          </p>
        </div>
      ) : (
        manifest.final_video_skipped_reason && (
          <p className="meta">{manifest.final_video_skipped_reason}</p>
        )
      )}

      <div className="package-scenes">
        {manifest.scenes.map((scene) => {
          const storyboardKey = keyOf(scene.assets.storyboard);
          const narrationKey = keyOf(scene.assets.narration);
          const narrationPlayable =
            scene.assets.narration?.playable &&
            (narrationKey?.endsWith(".mp3") || narrationKey?.endsWith(".wav"));
          return (
            <div key={scene.scene_id} className="package-scene card">
              <h3>
                {scene.scene_id} <StatusBadge status={scene.status} />
              </h3>
              {storyboardKey && (
                <img
                  className="storyboard-preview"
                  src={assetUrl(pid, storyboardKey)}
                  alt={`Storyboard for ${scene.title}`}
                  loading="lazy"
                />
              )}
              <p className="meta">{scene.title}</p>
              {narrationPlayable && narrationKey && (
                <audio
                  controls
                  preload="none"
                  src={assetUrl(pid, narrationKey)}
                  aria-label={`Narration for ${scene.title}`}
                />
              )}
              <ul className="object-list compact-list">
                {narrationKey && (
                  <li>
                    <span className="meta">narration:</span>{" "}
                    <code>{narrationKey}</code>
                  </li>
                )}
                {keyOf(scene.assets.captions) && (
                  <li>
                    <span className="meta">captions:</span>{" "}
                    <code>{keyOf(scene.assets.captions)}</code>
                  </li>
                )}
                {keyOf(scene.assets.clip) && (
                  <li>
                    <span className="meta">clip:</span>{" "}
                    <code>{keyOf(scene.assets.clip)}</code>
                  </li>
                )}
                {scene.genblaze_manifest_key && (
                  <li>
                    <span className="meta">genblaze manifest:</span>{" "}
                    <code>{scene.genblaze_manifest_key}</code>
                  </li>
                )}
                {scene.genblaze_tts_manifest_key && (
                  <li>
                    <span className="meta">genblaze TTS manifest:</span>{" "}
                    <code>{scene.genblaze_tts_manifest_key}</code>
                  </li>
                )}
              </ul>
            </div>
          );
        })}
      </div>

      <div className="actions">
        <button type="button" onClick={onVerify} disabled={verifyDisabled}>
          Verify Release
        </button>
      </div>
    </section>
  );
}
