# SceneLedger Architecture

## M0 milestone

M0 proves the local **source → plan → compare → release** loop without external services.

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  .sceneledger/projects/  │
│  apps/web   │     │  apps/api    │     │  (B2 in M1)              │
└─────────────┘     └──────────────┘     └──────────────────────────┘
```

## Monorepo layout

| Path | Role |
|------|------|
| `apps/api` | FastAPI: chunking, planning, stale detection, manifests |
| `apps/web` | Next.js demo UI |
| `packages/pipeline` | Future Genblaze pipeline (M2) |
| `demo/` | Sample source documents |
| `docs/` | Architecture and demo notes |

## Local storage layout

```
.sceneledger/projects/{project_id}/
  project.json
  sources/{version}/source.txt
  sources/{version}/chunks.json
  plans/{version}/scenes.json
  compare/{base_version}-{candidate_version}/stale-report.json
  manifests/{version}/release.json
```

## Core flow

1. **Upload source** — split plain text into paragraph chunks with SHA-256 hashes.
2. **Plan scenes** — deterministic mock planner maps chunk-001/002/003 to scene-001/002/003.
3. **Compare** — load two uploaded versions; mark scenes stale when referenced chunk hashes differ.
4. **Release** — JSON manifest with scene IDs and stale IDs from the latest matching compare report.

## Storage abstraction

[`apps/api/storage.py`](../apps/api/storage.py) defines a `StorageBackend` interface. M0 uses `LocalFilesystemStorage` under `.sceneledger/`. M1 swaps in a B2 client without changing route handlers.

## Out of scope (M0)

- Authentication
- Database
- Genblaze / provider calls
- Backblaze B2
- FFmpeg / media generation
