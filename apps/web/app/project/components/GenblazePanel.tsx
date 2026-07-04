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
        Storyboard generation runs through the Genblaze SDK when configured.
        Clip, narration, and captions are deterministic placeholders — not
        AI-generated.
      </p>
      <dl className="fact-grid">
        <div className="fact">
          <dt>Media mode</dt>
          <dd>
            <span
              className={`badge ${isGenblazeMode ? "verified" : "placeholder"}`}
            >
              {mediaMode}
            </span>
          </dd>
        </div>
        <div className="fact">
          <dt>Genblaze configured</dt>
          <dd>
            {isGenblazeMode
              ? "Yes — SCENELEDGER_MEDIA_MODE=genblaze with provider keys"
              : "No — running in deterministic placeholder mode"}
          </dd>
        </div>
        <div className="fact">
          <dt>Storyboard model</dt>
          <dd>
            <code>gpt-image-1</code> via genblaze-openai (when Genblaze mode is
            active)
          </dd>
        </div>
        <div className="fact">
          <dt>Live proof in manifests</dt>
          <dd>
            {hasGenblazeAsset
              ? 'Storyboard assets show generator: "genblaze"'
              : "Not yet — run Generate Media in Genblaze mode"}
          </dd>
        </div>
      </dl>
      {provenance?.present && (
        <div className="genblaze-provenance">
          <h3>Provenance manifests (stored in B2/storage)</h3>
          <ul className="object-list compact-list">
            <li>
              <span className="meta">Genblaze-generated assets:</span>{" "}
              {provenance.asset_count}
            </li>
            {provenance.run_ids.length > 0 && (
              <li>
                <span className="meta">Run IDs:</span>{" "}
                {provenance.run_ids.map((id) => (
                  <code key={id} title={id}>
                    {id.slice(0, 8)}…{" "}
                  </code>
                ))}
              </li>
            )}
            {provenance.manifest_keys.map((key, i) => (
              <li key={key}>
                <code>{key}</code>
                {provenance.manifest_hashes[i] && (
                  <span className="meta" title={provenance.manifest_hashes[i]}>
                    {" "}
                    · sha256:{" "}
                    <code>{provenance.manifest_hashes[i].slice(0, 12)}…</code>
                  </span>
                )}
              </li>
            ))}
          </ul>
          <p className="meta">
            Each manifest is the Genblaze SDK&apos;s canonical run record,
            stored byte-exact and re-verified (SceneLedger&apos;s SHA-256 plus
            the SDK&apos;s canonical hash) on every release verification.
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
