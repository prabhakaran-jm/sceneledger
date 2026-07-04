import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>SceneLedger</h1>
      <p className="subtitle">
        Turn changing source documents into source-linked training videos with
        provenance you can verify.
      </p>
      <p className="meta">
        In the demo you will: upload source v1, generate three linked scenes and
        media, create verified release evidence on Backblaze B2, upload v2, detect
        a stale scene, and see a release warning.
      </p>
      <p className="meta">
        Recommended for judging: placeholder media mode + B2 storage. Genblaze is
        optional for storyboard generation.
      </p>
      <div className="actions">
        <Link className="btn" href="/project">
          Open demo project
        </Link>
      </div>
    </main>
  );
}
