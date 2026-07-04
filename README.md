# SceneLedger

SceneLedger turns changing source documents into source-linked training videos.

It generates short training scenes from a source document, records which source chunks support each scene, detects when the source changes, and regenerates only the scenes that became stale.

## What it does

- Upload a procedure, policy, manual, or product guide
- Split the source into stable chunks
- Generate a source-linked scene plan
- Create storyboard frames, video clips, narration, and captions (planned via Genblaze)
- Store generated media, metadata, logs, and manifests in Backblaze B2 (planned)
- Detect stale scenes when the source document changes
- Produce a verified final release package

## Hackathon

Built for the Backblaze Generative Media Hackathon.

## Tech stack

- Frontend: Next.js (`apps/web`)
- Backend: FastAPI (`apps/api`)
- Media pipeline: Genblaze (placeholder in MVP)
- Storage: local filesystem now, Backblaze B2 later

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

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

Optional: set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `apps/web/.env.local` if the API runs elsewhere.

### Demo flow

1. Open http://localhost:3000/project
2. Click **Upload source** (uses demo v1 text)
3. Click **Generate plan** — three scenes appear with chunk IDs
4. Click **Compare source** (uses demo v2 text with one changed paragraph)
5. Scene 2 should show **stale**; Scenes 1 and 3 stay **current**

Demo source files: `demo/source-v1.txt`, `demo/source-v2.txt`

See `docs/demo-script.md` for a full walkthrough.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/projects` | Create project |
| POST | `/projects/{id}/sources` | Upload source text |
| GET | `/projects/{id}` | Get project state |
| POST | `/projects/{id}/plan` | Generate 3-scene plan |
| POST | `/projects/{id}/compare-source` | Detect stale scenes |
| POST | `/projects/{id}/release` | Build release manifest |

## Environment

Copy `.env.example` to `.env` when wiring B2 and Genblaze. No real provider keys are required for the MVP scaffold.

## License

See [LICENSE](LICENSE).
