# SceneLedger Architecture

## Milestones

**M0** — local source → plan → compare → release loop.

**M1** — optional Backblaze B2 backend via the same storage interface (`SCENELEDGER_STORAGE_BACKEND=local|b2`).

**M2** — scene media generation: placeholder mode (default) and optional Genblaze adapter for storyboard.

**M3** — release provenance: links source chunks, scene plan, stale report, and M2 media manifests with live SHA-256 verification.

**M4** — demo polish for hackathon judging: guided UI stepper, B2 visibility, release evidence table, Devpost docs. No new backend architecture.

**M5 (future)** — final stitched training video compose.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Local: .sceneledger/       │
│  apps/web   │     │  apps/api    │     │  B2: tenants/demo/projects/ │
└─────────────┘     └──────┬───────┘     └─────────────────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       media_pipeline  release_verifier  stale_detector
              │            │            │
     placeholder/genblaze  release_manifest
              │            │
              └────────────┴──▶ manifests/{version}/release.json
                                (canonical SHA-256 self-hash)
```

## Monorepo layout

| Path | Role |
|------|------|
| `apps/api` | FastAPI: chunking, planning, stale detection, manifests, storage, media, release verification |
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
5. **Release** — provenance manifest linking source chunks, plan, stale report, and per-scene media with SHA-256 verification.
6. **Verify release** — re-read stored assets, recompute hashes, optionally update manifest in place (same `release_id`).
7. **List objects** — `GET /projects/{id}/objects` returns stored keys for the active backend.

## M3 release provenance

When `POST /release` runs, `release_verifier.py` loads:

- Source chunks (`chunks.json`) and scene plan (`scenes.json`)
- Latest stale report where `base_version == source_version` (if any)
- Each scene's `scene-asset-manifest.json` and underlying asset bytes

It computes `release_status` (`verified` | `warning` | `blocked`), a fixed `message`, per-scene asset hash results, and `release_manifest_sha256` (canonical JSON hash excluding the hash field itself). Missing source chunks or scene plan returns **400**; missing media or hash mismatch returns **200 + blocked**.

`POST /verify-release` preserves the stored `release_id` and re-runs verification without creating a new release.

## Storage abstraction

[`apps/api/storage.py`](../apps/api/storage.py) defines `StorageBackend` with `write_text`, `write_bytes`, `read_json`, `list_project_objects`, etc. Route handlers use logical paths (`projects/{id}/...`); backends map to local files or B2 keys. B2 writes pass explicit `ContentType`. `get_storage()` is cached per process.

## Media modes

| Mode | Env | Notes |
|------|-----|-------|
| Placeholder | `SCENELEDGER_MEDIA_MODE=placeholder` | Pillow, wave, VTT, optional ffmpeg clip |
| Genblaze | `SCENELEDGER_MEDIA_MODE=genblaze` | DALL-E storyboard when configured; other assets placeholder |

## Judge demo path (M4)

The web UI at `/project` guides judges through eight steps:

1. Create project → 2. Upload v1 → 3. Plan → 4. Media → 5. Release evidence (sticky when `hash_verified`) → 6. Upload v2 → 7. Compare → 8. Warning release

Recommended: **placeholder media + B2 storage**. Genblaze Integration panel explains optional storyboard path.

See [`deployment.md`](deployment.md).

## Out of scope (M4)

- Authentication
- Database
- Final stitched video (M5)
- Object Lock / C2PA
- New provider integrations beyond existing optional Genblaze storyboard path

B2 and Genblaze are optional; local placeholder mode is the default demo path.
