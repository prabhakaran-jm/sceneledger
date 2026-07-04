type GenblazeProvenance = {
  present: boolean;
  run_ids: string[];
  manifest_keys: string[];
  manifest_hashes: string[];
  asset_count: number;
};

type GenblazePanelProps = {
  mediaMode: string;
  hasGenblazeAsset: boolean;
  provenance?: GenblazeProvenance | null;
};

export function GenblazePanel({
  mediaMode,
  hasGenblazeAsset,
  provenance,
}: GenblazePanelProps) {
  const isGenblazeMode = mediaMode === "genblaze";

  return (
    <div className="card genblaze-panel">
      <h2>Genblaze Integration</h2>
      <p className="meta">
        Optional storyboard generation via the existing Genblaze adapter. Clip,
        narration, and captions remain placeholder-generated.
      </p>
      <ul className="checklist">
        <li>
          media_mode:{" "}
          <span className={`badge ${isGenblazeMode ? "verified" : "placeholder"}`}>
            {mediaMode}
          </span>
        </li>
        <li>
          Genblaze configured:{" "}
          {isGenblazeMode
            ? "yes (SCENELEDGER_MEDIA_MODE=genblaze + provider keys)"
            : "no — placeholder mode (recommended for judging)"}
        </li>
        <li>
          Storyboard model: <code>gpt-image-1</code> (when genblaze mode is active)
        </li>
        <li>
          Live proof in manifests:{" "}
          {hasGenblazeAsset
            ? 'storyboard shows generator: "genblaze"'
            : "not yet — run Generate Media in genblaze mode"}
        </li>
      </ul>
      {provenance?.present && (
        <div className="genblaze-provenance">
          <h3>Provenance manifests (stored in B2/storage)</h3>
          <ul className="checklist">
            <li>Genblaze-generated assets: {provenance.asset_count}</li>
            {provenance.run_ids.length > 0 && (
              <li>
                Run IDs:{" "}
                {provenance.run_ids.map((id) => (
                  <code key={id}>{id.slice(0, 8)}… </code>
                ))}
              </li>
            )}
            {provenance.manifest_keys.map((key, i) => (
              <li key={key}>
                <code>{key}</code>
                {provenance.manifest_hashes[i] && (
                  <span className="meta">
                    {" "}
                    sha256: <code>{provenance.manifest_hashes[i].slice(0, 12)}…</code>
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="meta">
            Each manifest is the Genblaze SDK&apos;s canonical run record, stored
            byte-exact and re-verified (our sha256 + the SDK&apos;s canonical
            hash) on every release verification.
          </p>
        </div>
      )}
      <p className="meta">
        SceneLedger never fakes Genblaze output. Assets are marked{" "}
        <code>generator: &quot;genblaze&quot;</code> only after a real provider
        run.
      </p>
    </div>
  );
}
