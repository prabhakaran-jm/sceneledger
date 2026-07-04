import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>SceneLedger</h1>
      <p className="subtitle">
        Turn changing source documents into source-linked training videos.
        Upload a procedure, generate scenes tied to source chunks, detect what
        went stale when the doc changes, and ship a verified release.
      </p>
      <div className="card">
        <p>
          Built for the Backblaze Generative Media Hackathon. This MVP scaffold
          uses local storage and mock scene planning — no real Genblaze or B2
          calls yet.
        </p>
        <div className="actions">
          <Link className="btn" href="/project">
            Open demo project
          </Link>
        </div>
      </div>
    </main>
  );
}
