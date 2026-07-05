type GenblazeProvenance = {
  present: boolean;
  run_ids: string[];
  manifest_keys: string[];
  manifest_hashes: string[];
  asset_count: number;
};

type PlannerProvenance = {
  planner: string;
  fallback_reason?: string | null;
  genblaze_manifest_key?: string | null;
  genblaze_manifest_verified?: boolean | null;
  genblaze_model?: string | null;
  genblaze_provider?: string | null;
};

type GenblazePanelProps = {
  mediaMode: string;
  hasGenblazeAsset: boolean;
  preferredProvider?: string;
  provenance?: GenblazeProvenance | null;
  plannerProvenance?: PlannerProvenance | null;
};

export function GenblazePanel({
  mediaMode,
  hasGenblazeAsset,
  preferredProvider,
  provenance,
  plannerProvenance,
}: GenblazePanelProps) {
  const isGenblazeMode = mediaMode === "genblaze";
  const providerLabel =
    preferredProvider === "gmi" ? "GMI Cloud (OpenAI fallback)" : "OpenAI";

  return (
    <div className="card genblaze-panel">
      <h2>Genblaze Integration</h2>
      <p className="meta">
        Scene planning, storyboards, and narration run through the Genblaze
        SDK when configured. Clips and captions are deterministic placeholders
        — not AI-generated. Narration falls back to a labeled placeholder if
        TTS is unavailable.
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
          <dt>Preferred provider</dt>
          <dd>{isGenblazeMode ? providerLabel : "—"}</dd>
        </div>
        <div className="fact">
          <dt>Scene planner</dt>
          <dd>
            {plannerProvenance
              ? plannerProvenance.planner === "genblaze-chat"
                ? `Genblaze chat via ${plannerProvenance.genblaze_provider ?? "provider"} (${plannerProvenance.genblaze_model ?? "chat model"})${
                    plannerProvenance.genblaze_manifest_verified != null
                      ? plannerProvenance.genblaze_manifest_verified
                        ? " · manifest verified"
                        : " · manifest FAILED verification"
                      : ""
                  }`
                : `Deterministic${plannerProvenance.fallback_reason ? ` — ${plannerProvenance.fallback_reason}` : ""}`
              : "Genblaze chat when configured; deterministic fallback"}
          </dd>
        </div>
        <div className="fact">
          <dt>Storyboard</dt>
          <dd>
            {preferredProvider === "gmi"
              ? "GMI Cloud image queue, OpenAI gpt-image-1 fallback"
              : "OpenAI gpt-image-1 via genblaze-openai"}{" "}
            (when Genblaze mode is active)
          </dd>
        </div>
        <div className="fact">
          <dt>Narration (TTS)</dt>
          <dd>
            {preferredProvider === "gmi"
              ? "GMI Cloud TTS queue, OpenAI gpt-4o-mini-tts fallback"
              : "OpenAI gpt-4o-mini-tts via genblaze-openai"}
            ; placeholder tone if all providers fail, labeled honestly
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
