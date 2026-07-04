type GenblazePanelProps = {
  mediaMode: string;
  hasGenblazeAsset: boolean;
};

export function GenblazePanel({ mediaMode, hasGenblazeAsset }: GenblazePanelProps) {
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
      <p className="meta">
        SceneLedger never fakes Genblaze output. Assets are marked{" "}
        <code>generator: &quot;genblaze&quot;</code> only after a real provider
        run.
      </p>
    </div>
  );
}
