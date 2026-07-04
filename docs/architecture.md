# SceneLedger Architecture

## Milestones

**M0** — local source → plan → compare → release loop.

**M1** — optional Backblaze B2 backend via the same storage interface (`SCENELEDGER_STORAGE_BACKEND=local|b2`).

**M2** — Genblaze orchestration and media generation (not started).

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Local: .sceneledger/       │
│  apps/web   │     │  apps/api    │     │  B2: tenants/demo/projects/ │
└─────────────┘     └──────────────┘     └─────────────────────────────┘
```

## Monorepo layout

| Path | Role |
|------|------|
| `apps/api` | FastAPI: chunking, planning, stale detection, manifests, storage |
| `apps/web` | Next.js demo UI |
| `packages/pipeline` | Future Genblaze pipeline (M2) |
| `demo/` | Sample source documents |
| `docs/` | Architecture and runbook notes |

## Storage layout

**Local** (default): `.sceneledger/projects/{project_id}/...`

**B2** (optional): `{SCENELEDGER_B2_TENANT_PREFIX}/projects/{project_id}/...` (default prefix `tenants/demo`)

See [`b2-layout.md`](b2-layout.md) for the full object key map.

## Core flow

1. **Upload source** — split plain text into paragraph chunks with SHA-256 hashes.
2. **Plan scenes** — deterministic mock planner maps chunk-001/002/003 to scene-001/002/003.
3. **Compare** — load two uploaded versions; mark scenes stale when referenced chunk hashes differ.
4. **Release** — JSON manifest with scene IDs and stale IDs from the latest matching compare report.
5. **List objects** — `GET /projects/{id}/objects` returns stored keys for the active backend.

## Storage abstraction

[`apps/api/storage.py`](../apps/api/storage.py) defines `StorageBackend` with `write_text`, `read_json`, `list_project_objects`, etc. Route handlers use logical paths (`projects/{id}/...`); backends map to local files or B2 keys. `get_storage()` is cached per process.

## Out of scope (M1)

- Authentication
- Database
- Genblaze / provider calls
- FFmpeg / media generation

B2 is optional in M1; local mode remains the default for hackathon demos without credentials.
