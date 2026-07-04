# SceneLedger Architecture

## Milestones

**M0** — local source → plan → compare → release loop.

**M1** — optional Backblaze B2 backend via the same storage interface (`SCENELEDGER_STORAGE_BACKEND=local|b2`).

**M2** — scene media generation: placeholder mode (default) and optional Genblaze adapter for storyboard.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Local: .sceneledger/       │
│  apps/web   │     │  apps/api    │     │  B2: tenants/demo/projects/ │
└─────────────┘     └──────┬───────┘     └─────────────────────────────┘
                           │
                    ┌──────▼───────┐
                    │ media_pipeline│
                    └──────┬───────┘
              ┌────────────┴────────────┐
              │                         │
     placeholder_adapter          genblaze_adapter
              │                         │
     media_placeholders.py      genblaze_core (optional)
```

## Monorepo layout

| Path | Role |
|------|------|
| `apps/api` | FastAPI: chunking, planning, stale detection, manifests, storage, media |
| `apps/web` | Next.js demo UI |
| `packages/pipeline` | Placeholder and Genblaze media adapters |
| `demo/` | Sample source documents |
| `docs/` | Architecture and runbook notes |

## Storage layout

**Local** (default): `.sceneledger/projects/{project_id}/...`

**B2** (optional): `{SCENELEDGER_B2_TENANT_PREFIX}/projects/{project_id}/...` (default prefix `tenants/demo`)

See [`b2-layout.md`](b2-layout.md) for the full object key map.

## Core flow

1. **Upload source** — split plain text into paragraph chunks with SHA-256 hashes.
2. **Plan scenes** — deterministic mock planner maps chunk-001/002/003 to scene-001/002/003.
3. **Generate media** — per-scene storyboard, clip, narration, captions + scene manifest.
4. **Compare** — load two uploaded versions; mark scenes stale when referenced chunk hashes differ.
5. **Release** — JSON manifest with scene IDs and stale IDs from the latest matching compare report.
6. **List objects** — `GET /projects/{id}/objects` returns stored keys for the active backend.

## Storage abstraction

[`apps/api/storage.py`](../apps/api/storage.py) defines `StorageBackend` with `write_text`, `write_bytes`, `read_json`, `list_project_objects`, etc. Route handlers use logical paths (`projects/{id}/...`); backends map to local files or B2 keys. B2 writes pass explicit `ContentType`. `get_storage()` is cached per process.

## Media modes

| Mode | Env | Notes |
|------|-----|-------|
| Placeholder | `SCENELEDGER_MEDIA_MODE=placeholder` | Pillow, wave, VTT, optional ffmpeg clip |
| Genblaze | `SCENELEDGER_MEDIA_MODE=genblaze` | DALL-E storyboard when configured; other assets placeholder |

## Out of scope (M2)

- Authentication
- Database
- Final stitched video
- Object Lock / C2PA

B2 and Genblaze are optional; local placeholder mode is the default demo path.
