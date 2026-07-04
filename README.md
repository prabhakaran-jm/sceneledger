# SceneLedger

SceneLedger turns changing source documents into source-linked training videos.

**M0** proves the local loop: chunk a source, plan three scenes, detect stale scenes when the source changes, and produce a release manifest. No B2, Genblaze, database, auth, or real media generation yet.

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend

```bash
cd apps/api
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

Project data is stored under `.sceneledger/projects/` at the repo root.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Optional: `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local`

## M0 demo flow (UI)

1. Open http://localhost:3000/project
2. **Create Project**
3. **Upload Source v1** (pre-filled demo text)
4. **Generate Scene Plan** — three scenes with chunk IDs
5. **Upload Source v2** (only paragraph 3 changed: assembly point A → C)
6. **Compare Source Versions** — scene-003 stale, scenes 1–2 current
7. **Create Release Manifest** — JSON shows `stale_scene_ids: ["scene-003"]`

Demo files: [`demo/source-v1.txt`](demo/source-v1.txt), [`demo/source-v2.txt`](demo/source-v2.txt)

## M0 demo flow (curl)

Run the API first, then:

```bash
# 1. Health
curl http://localhost:8000/health

# 2. Create project
curl -s -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"Warehouse Safety Demo\"}"
# Copy project_id from response into PROJECT_ID below

PROJECT_ID="<your-project-id>"

# 3. Upload source v1
curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/sources" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\",\"content\":\"Stop work when the alarm sounds.\n\nLeave through the nearest marked exit.\n\nReport to assembly point A.\"}"

# 4. Generate scene plan
curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/plan" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"

# 5. Upload source v2
curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/sources" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v2\",\"content\":\"Stop work when the alarm sounds.\n\nLeave through the nearest marked exit.\n\nReport to assembly point C.\"}"

# 6. Compare versions
curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/compare-source" \
  -H "Content-Type: application/json" \
  -d "{\"base_version\":\"v1\",\"candidate_version\":\"v2\"}"

# 7. Get project summary
curl -s "http://localhost:8000/projects/${PROJECT_ID}"

# 8. Create release manifest
curl -s -X POST "http://localhost:8000/projects/${PROJECT_ID}/release" \
  -H "Content-Type: application/json" \
  -d "{\"source_version\":\"v1\"}"
```

Expected compare result: `stale_scene_ids` is `["scene-003"]`.

## What is mocked in M0

- Scene planner (deterministic 3-scene mapping, no LLM)
- Genblaze pipeline (`placeholder_genblaze_manifest: true`)
- Backblaze B2 storage (`placeholder_b2_keys: []`)
- Video, narration, captions, and media generation

## Roadmap

| Milestone | Scope |
|-----------|--------|
| **M0** (current) | Local filesystem, chunking, stale detection, release manifest |
| **M1** | Backblaze B2 storage backend and real object keys |
| **M2** | Genblaze orchestration and media generation |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Project summary |
| POST | `/projects/{id}/sources` | Upload source version |
| POST | `/projects/{id}/plan` | Generate 3-scene plan |
| POST | `/projects/{id}/compare-source` | Detect stale scenes |
| POST | `/projects/{id}/release` | Build release manifest |

## License

See [LICENSE](LICENSE).
