# SceneLedger

**Turn changing source documents into source-linked training videos with provenance you can verify.**

SceneLedger chunks policy text, links three training scenes to source paragraphs, generates per-scene media, stores everything on Backblaze B2, and produces a release manifest with SHA-256 verification — then detects exactly which scenes go stale when the source changes.

---

## Problem

Training videos drift from the documents they're supposed to teach. When a policy changes, teams can't tell which scenes are still current or prove what was released.

## Solution

- **Source linkage** — every scene references specific source chunks with SHA-256 hashes
- **Stale detection** — compare two source versions; mark scenes stale when chunks change
- **Media pipeline** — per-scene storyboard, clip, narration, captions (placeholder by default)
- **Release evidence** — manifest linking source, media, and live hash verification
- **Durable storage** — same artifacts on local disk or Backblaze B2

---

## Milestones

| Milestone | Scope |
|-----------|--------|
| **M0** | Local source → plan → compare → release loop |
| **M1** | Optional Backblaze B2 storage backend |
| **M2** | Placeholder + optional Genblaze media pipeline |
| **M3** | Release provenance, SHA-256 verification, verify-release |
| **M4** (current) | Demo polish and judge UI |
| **M5** (future) | Final stitched video compose |

---

## Demo flow (UI)

Recommended: **placeholder media + B2 storage**. Open http://localhost:3000/project

1. **Create project**
2. **Upload source v1** (Warehouse Safety Demo — pre-filled)
3. **Generate scene plan** — three scenes linked to chunks
4. **Generate media** — placeholder assets for all 3 scenes
5. **Create release evidence** — verified manifest, hash checklist
6. **Verify release** — same `release_id`, hashes confirmed
7. **Upload source v2** (assembly point A → C)
8. **Compare versions** — scene-003 stale; scenes 1–2 current
9. **Recreate release evidence** — warning, superseded by v2

Demo files: [`demo/source-v1.txt`](demo/source-v1.txt), [`demo/source-v2.txt`](demo/source-v2.txt)

---

## Architecture

```
Next.js (apps/web) → FastAPI (apps/api) → StorageBackend
                                              ├── local: .sceneledger/
                                              └── B2: tenants/demo/projects/
```

Core modules: `media_pipeline`, `release_verifier`, `stale_detector`. Details in [`docs/architecture.md`](docs/architecture.md).

---

## How SceneLedger uses Backblaze B2

Backblaze B2 stores all project artifacts under a tenant prefix (default `tenants/demo`):

```
tenants/demo/projects/{project_id}/sources/v1/chunks.json
tenants/demo/projects/{project_id}/media/v1/scene-001/storyboard.png
tenants/demo/projects/{project_id}/manifests/v1/release.json
```

- Same logical paths as local mode; B2 keys include the prefix
- Release manifest is the durable evidence record (`release_manifest` kind)
- `POST /verify-release` re-reads assets from B2 and confirms SHA-256 hashes
- UI shows tenant prefix (non-secret metadata only — never credentials)

Full key map: [`docs/b2-layout.md`](docs/b2-layout.md)

---

## How SceneLedger uses Genblaze

Genblaze is an **optional** integration for storyboard generation:

| Aspect | Detail |
|--------|--------|
| Mode | `SCENELEDGER_MEDIA_MODE=genblaze` |
| Scope | Storyboard image only (M2 partial integration) |
| Model | `gpt-image-1` via genblaze-openai |
| Other assets | Clip, narration, captions remain placeholder |
| Provenance | Manifests mark `generator: "genblaze"` or `"placeholder"` honestly |

**Primary judging path:** placeholder mode (no API keys, deterministic). If Genblaze is configured and stable, run Generate Media to show real `generator: "genblaze"` on storyboards. SceneLedger **never fakes** Genblaze output.

Details: [`docs/genblaze-pipeline.md`](docs/genblaze-pipeline.md)

---

## Providers and models

| Provider | Role | Model / tech |
|----------|------|--------------|
| Backblaze B2 | Object storage | S3-compatible API |
| Placeholder pipeline | All assets (default) | Pillow, ffmpeg, wave, VTT |
| Genblaze (optional) | Storyboard only | `gpt-image-1` |

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (optional — enables valid `clip.mp4`)

### Backend (local mode)

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
set SCENELEDGER_STORAGE_BACKEND=local
set SCENELEDGER_MEDIA_MODE=placeholder
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Backend (B2 mode — recommended for judging)

1. Copy `.env.example` to `.env` at repo root
2. Set B2 credentials and `SCENELEDGER_STORAGE_BACKEND=b2`
3. Start API from `apps/api`

See [`.env.example`](.env.example) for all variables.

### Backend (Genblaze mode — optional)

```bash
pip install -r requirements-genblaze.txt
set SCENELEDGER_MEDIA_MODE=genblaze
set OPENAI_API_KEY=<your-key>
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Optional: `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local`

---

## Placeholder mode

Default and recommended for judging. Generates deterministic assets per scene:

- `storyboard.png` (Pillow)
- `clip.mp4` or `clip.placeholder.txt` (ffmpeg if available)
- `narration.wav` (silent WAV)
- `captions.vtt` (single cue)

Each scene gets `scene-asset-manifest.json` with `status: "complete"` and per-asset SHA-256.

---

## Demo flow (curl)

```bash
curl http://localhost:8000/health

curl -s -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Warehouse Safety Demo\"}"
# Set PROJECT_ID from response

PROJECT_ID="<your-project-id>"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/sources" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\",\"content\":\"Stop work when the alarm sounds.\n\nLeave through the nearest marked exit.\n\nReport to assembly point A.\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/plan" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/generate-media" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\",\"force\":false}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/release" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/sources" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v2\",\"content\":\"Stop work when the alarm sounds.\n\nLeave through the nearest marked exit.\n\nReport to assembly point C.\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/compare-source" \
  -H "Content-Type: application/json" \
  -d "{\"base_version\":\"v1\",\"candidate_version\":\"v2\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/release" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"
```

Expected: first release `verified`; after compare, second release `warning` with `release_superseded_by_source_version: "v2"`.

---

## Manual verification

### B2 placeholder (primary judging path)

1. Configure B2 env vars, `SCENELEDGER_MEDIA_MODE=placeholder`
2. Complete 8-step UI demo
3. Storage panel: B2 badge, tenant prefix, grouped keys, release manifest highlighted
4. Verify Release re-reads from B2

### Tamper testing

**Local:** Edit one byte in a storyboard → Verify Release → `blocked`

**B2:** Delete/replace a media object in bucket UI → Verify Release → `blocked`

### Deployment smoke test

See [`docs/deployment.md`](docs/deployment.md).

---

## Screenshots

Capture during demo polish. Place files in [`docs/screenshots/`](docs/screenshots/):

- `01-stepper-verified.png` — stepper through Step 5
- `02-media-assets-b2.png` — grouped B2 object keys
- `03-release-evidence-verified.png` — verified release card
- `04-scene-003-stale.png` — stale scene highlight
- `05-release-warning.png` — warning release after compare

---

## Known limitations

- No authentication or multi-tenant isolation
- No database — all state in filesystem or B2
- No final stitched training video (M5)
- No Object Lock or C2PA content credentials
- Genblaze generates storyboards only; other assets are placeholder
- Scene planner is deterministic (no LLM)

## What is mocked

- Scene planner (deterministic 3-scene mapping)
- Placeholder narration and captions
- Genblaze clip/narration/captions in genblaze mode

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + `api_version`, `storage_backend`, `media_mode`, `tenant_prefix` |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Project summary |
| GET | `/projects/{id}/objects` | List stored object keys |
| POST | `/projects/{id}/sources` | Upload source version |
| POST | `/projects/{id}/plan` | Generate 3-scene plan |
| POST | `/projects/{id}/generate-media` | Generate per-scene media |
| GET | `/projects/{id}/media` | Load scene media manifests |
| POST | `/projects/{id}/compare-source` | Detect stale scenes |
| POST | `/projects/{id}/release` | Build release manifest |
| GET | `/projects/{id}/release` | Load stored release manifest |
| POST | `/projects/{id}/verify-release` | Re-verify asset hashes |

---

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/deployment.md`](docs/deployment.md) | Hosting and smoke test |
| [`docs/architecture.md`](docs/architecture.md) | System overview |
| [`docs/b2-layout.md`](docs/b2-layout.md) | B2 object key map |
| [`docs/genblaze-pipeline.md`](docs/genblaze-pipeline.md) | Genblaze integration |

---

## License

See [LICENSE](LICENSE).
