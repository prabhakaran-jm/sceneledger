# SceneLedger

SceneLedger turns changing source documents into source-linked training videos.

**M0** proves the local loop: chunk a source, plan three scenes, detect stale scenes when the source changes, and produce a release manifest.

**M1** adds optional Backblaze B2 storage — same artifacts, durable object keys.

**M2** adds per-scene media generation: deterministic **placeholder mode** (default) and optional **Genblaze mode** for DALL-E storyboards when configured.

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (optional — enables valid `clip.mp4`; without it, scenes get `clip.placeholder.txt`)

### Backend (local mode — default)

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
set SCENELEDGER_STORAGE_BACKEND=local
set SCENELEDGER_MEDIA_MODE=placeholder
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Project data is stored under `.sceneledger/projects/` at the repo root.

### Backend (B2 mode — optional)

1. Copy `.env.example` to `.env` at the repo root
2. Set:

```env
SCENELEDGER_STORAGE_BACKEND=b2
SCENELEDGER_B2_TENANT_PREFIX=tenants/demo
B2_ENDPOINT=https://s3.<region>.backblazeb2.com
B2_REGION=<region>
B2_BUCKET=<your-bucket>
B2_KEY_ID=<your-key-id>
B2_APPLICATION_KEY=<your-application-key>
SCENELEDGER_MEDIA_MODE=placeholder
```

**Important:** `B2_ENDPOINT` is the S3-compatible endpoint **without** the bucket name (e.g. `https://s3.us-west-004.backblazeb2.com`).

3. Start the API from `apps/api`:

```bash
uvicorn main:app --reload --port 8000
```

4. Verify objects via `GET /projects/{project_id}/objects` or the Backblaze bucket browser under `tenants/demo/projects/...`

### Backend (Genblaze mode — optional)

```bash
pip install -r requirements-genblaze.txt
set SCENELEDGER_MEDIA_MODE=genblaze
set OPENAI_API_KEY=<your-key>
```

Without keys or packages, use `SCENELEDGER_MEDIA_MODE=placeholder` (default).

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Optional: `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local`

## Demo flow (UI)

1. Open http://localhost:3000/project
2. **Create Project**
3. **Upload Source v1** (pre-filled demo text)
4. **Generate Scene Plan** — three scenes with chunk IDs
5. **Generate Media** — placeholder assets for all 3 scenes (or Genblaze storyboard when configured)
6. **Upload Source v2** (only paragraph 3 changed: assembly point A → C)
7. **Compare Source Versions** — scene-003 stale, scenes 1–2 current
8. **Create Release Manifest** — JSON shows `stale_scene_ids: ["scene-003"]`
9. **Refresh Stored Objects** / **Refresh Media** — lists keys and per-scene asset metadata

Demo files: [`demo/source-v1.txt`](demo/source-v1.txt), [`demo/source-v2.txt`](demo/source-v2.txt)

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

curl -s "http://localhost:8000/projects/${PROJECT_ID}/media?source_version=v1"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/sources" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v2\",\"content\":\"Stop work when the alarm sounds.\n\nLeave through the nearest marked exit.\n\nReport to assembly point C.\"}"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/compare-source" \
  -H "Content-Type: application/json" \
  -d "{\"base_version\":\"v1\",\"candidate_version\":\"v2\"}"

curl -s "http://localhost:8000/projects/${PROJECT_ID}"

curl -s "http://localhost:8000/projects/${PROJECT_ID}/objects"

curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/release" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"
```

Expected compare result: `stale_scene_ids` is `["scene-003"]`.

## Manual verification

### Local placeholder (primary)

1. `SCENELEDGER_STORAGE_BACKEND=local`, `SCENELEDGER_MEDIA_MODE=placeholder`
2. Complete demo flow including **Generate Media**
3. Confirm files under `.sceneledger/projects/{project_id}/media/v1/scene-001/...`
4. Each `scene-asset-manifest.json` has `status: "complete"` and per-asset `sha256`, `content_type`, `generator`, `playable`
5. Re-run generate with `force: false` → scenes `skipped`
6. M0 compare/release still works

### B2 placeholder

1. Set B2 env vars and `SCENELEDGER_MEDIA_MODE=placeholder`
2. Same flow; verify bucket under `tenants/demo/projects/{id}/media/v1/...`

### Genblaze mode

1. `pip install -r requirements-genblaze.txt`
2. `SCENELEDGER_MEDIA_MODE=genblaze`, `OPENAI_API_KEY=...`
3. Generate media → storyboard has `generator: "genblaze"`; clip/narration/captions remain placeholder
4. Without key → `503` with clear message, no secrets

## What is mocked

- Scene planner (deterministic 3-scene mapping, no LLM)
- Placeholder narration (silent WAV) and captions (single VTT cue)
- Genblaze clip/narration/captions in genblaze mode (honest `generator: "placeholder"`)
- Final stitched video — **M3**

## Roadmap

| Milestone | Scope |
|-----------|--------|
| **M0** | Local filesystem, chunking, stale detection, release manifest |
| **M1** | Optional B2 backend, object listing, `storage_keys` on writes |
| **M2** (current) | Placeholder + optional Genblaze media pipeline |
| **M3** | Release manifest media keys, provenance, final compose |

See [`docs/b2-layout.md`](docs/b2-layout.md) and [`docs/genblaze-pipeline.md`](docs/genblaze-pipeline.md).

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (+ `storage_backend`, `media_mode`) |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Project summary |
| GET | `/projects/{id}/objects` | List stored object keys |
| POST | `/projects/{id}/sources` | Upload source version |
| POST | `/projects/{id}/plan` | Generate 3-scene plan |
| POST | `/projects/{id}/generate-media` | Generate per-scene media assets |
| GET | `/projects/{id}/media` | Load stored scene media manifests |
| POST | `/projects/{id}/compare-source` | Detect stale scenes |
| POST | `/projects/{id}/release` | Build release manifest |

## License

See [LICENSE](LICENSE).
