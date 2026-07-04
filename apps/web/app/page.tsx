import Link from "next/link";

function ValueIcon({ path }: { path: string }) {
  return (
    <svg
      width={28}
      height={28}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export default function HomePage() {
  return (
    <main id="main-content">
      <section className="hero">
        <h1>SceneLedger</h1>
        <p className="subtitle">
          Turn changing source documents into source-linked training scenes —
          with media and provenance stored on Backblaze B2, and release
          evidence you can verify.
        </p>
        <div className="hero-actions">
          <Link className="btn" href="/project">
            Start the demo
          </Link>
          <a
            className="btn btn-secondary"
            href="https://github.com/prabhakaran-jm/sceneledger"
            target="_blank"
            rel="noreferrer"
          >
            View on GitHub
          </a>
        </div>
      </section>

      <section className="value-grid" aria-label="Key capabilities">
        <div className="card value-card">
          <ValueIcon path="M9 12h6m-6 4h4M7 3h10a2 2 0 012 2v14a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2zm2 5h6" />
          <h2>Source-linked scenes</h2>
          <p>
            Every scene links to the exact source chunks that support it, so
            you always know where a claim came from.
          </p>
        </div>
        <div className="card value-card">
          <ValueIcon path="M12 3l8 3.5V12c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6.5L12 3zm-3 9l2.5 2.5L16 10" />
          <h2>B2-backed provenance</h2>
          <p>
            Media, manifests, and Genblaze provenance records live in
            Backblaze B2 with SHA-256 verification at release time.
          </p>
        </div>
        <div className="card value-card">
          <ValueIcon path="M12 8v4m0 4h.01M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" />
          <h2>Stale-scene detection</h2>
          <p>
            When the source changes, SceneLedger flags exactly which scenes
            went stale — and the release status warns you.
          </p>
        </div>
      </section>

      <p className="hero-footnote">
        The guided demo walks through the full lifecycle: upload source v1,
        generate three linked scenes and media, create verified release
        evidence on B2, upload v2, and watch a single scene go stale — turning
        the release into a warning. Placeholder media mode lets the workflow
        run without provider keys; assets are labeled honestly either way.
      </p>
    </main>
  );
}
