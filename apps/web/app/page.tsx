import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <h1>SceneLedger</h1>
      <p className="subtitle">
        Turn changing source documents into source-linked training videos.
      </p>
      <div className="actions">
        <Link className="btn" href="/project">
          Open demo project
        </Link>
      </div>
    </main>
  );
}
