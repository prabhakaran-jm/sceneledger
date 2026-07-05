# SceneLedger

**Most AI media tools generate a video once. SceneLedger manages the media's useful lifetime: it generates source-linked training scenes with Genblaze, stores media and provenance on Backblaze B2, verifies hashes at release time, and warns when a source change makes only one scene stale.**

Built for the **Backblaze Generative Media Hackathon: Build with Genblaze on B2**.

---

## Problem

Training videos drift from the documents they're supposed to teach. When a procedure changes, teams can't tell which scenes are still current, can't prove what was released, and usually regenerate everything from scratch — losing the link between media and source.

## Solution

- **AI scene planning** — a Genblaze chat model turns source chunks into titled, narrated, storyboard-ready scenes, each strictly validated to link back to real source chunks
- **AI media generation** — Genblaze-mediated storyboards (`gpt-image-1`) and spoken narration (`gpt-4o-mini-tts`)
- **Durable provenance** — every Genblaze run's canonical SDK manifest is stored byte-exact on Backblaze B2 and re-verified at release time
- **Release evidence** — a manifest linking source hashes, media hashes, and Genblaze provenance, verified live with SHA-256
- **Stale detection** — upload a new source version and SceneLedger flags exactly which scenes went stale; the release turns to `warning`, not a rebuild

## What it does

1. Chunks a source document and hashes every chunk
2. Plans 3 scenes via Genblaze chat, each linked 1:1 to a source chunk (validated; deterministic fallback recorded honestly)
3. Generates per-scene media: Genblaze storyboard + TTS narration, plus captions and clip
4. Stores everything — source, chunks, plan, media, Genblaze manifests — under a B2 prefix
5. Builds release evidence with SHA-256 over every asset and every Genblaze manifest, optionally stitching `final.mp4`
6. On source change: detects the stale scene, re-verifies hashes, and downgrades the release to `warning`

## Demo flow

Open the app and follow the 8-step guided demo (`/project`):

1. **Create project**
2. **Upload source v1** (Warehouse Safety Demo — pre-filled)
3. **Generate scene plan** — Genblaze chat writes 3 scenes linked to chunks
4. **Generate media** — storyboards + narration via Genblaze, captions/clips as labeled placeholders
5. **Create release evidence** — `verified` manifest; Release Package shows previews and B2 keys
6. **Upload source v2** (assembly point A → C)
7. **Compare versions** — only scene-003 goes stale
8. **Recreate release evidence** — hashes still verify, release becomes `warning` (superseded by v2)

Script for judges: [`docs/demo-script.md`](docs/demo-script.md). Demo files: [`demo/source-v1.txt`](demo/source-v1.txt), [`demo/source-v2.txt`](demo/source-v2.txt).

---

## Architecture

```
Next.js (apps/web)  →  FastAPI (apps/api)  →  StorageBackend
                            │                     ├── B2: tenants/demo/projects/{id}/...
                            │                     └── local: .sceneledger/ (fallback)
                            └── Genblaze SDK
                                  ├── chat (scene planner, gpt-4o-mini)
                                  ├── DalleProvider (storyboards, gpt-image-1)
                                  └── OpenAITTSProvider (narration, gpt-4o-mini-tts)
```

Core modules: `genblaze_planner`, `genblaze_adapter`, `media_pipeline`, `release_verifier`, `stale_detector`, `release_video`. Details: [`docs/architecture.md`](docs/architecture.md).

## How SceneLedger uses Backblaze B2

B2 is the durable home for the whole lifecycle under one prefix (default `tenants/demo`):

```
tenants/demo/projects/{id}/sources/v1/{source.txt, chunks.json}
tenants/demo/projects/{id}/plans/v1/scenes.json
tenants/demo/projects/{id}/media/v1/scene-001/{storyboard.png, narration.mp3, captions.vtt, clip.mp4, scene-asset-manifest.json}
tenants/demo/projects/{id}/genblaze/v1/planner/manifest.json
tenants/demo/projects/{id}/genblaze/v1/scene-001/{manifest.json, tts-manifest.json}
tenants/demo/projects/{id}/compare/v1-v2/stale-report.json
tenants/demo/projects/{id}/manifests/v1/release.json
tenants/demo/projects/{id}/releases/v1/final.mp4        (when clips are stitchable)
```

- `POST /verify-release` re-reads every asset and manifest **from B2** and re-verifies SHA-256 live
- The UI object browser groups B2 keys by kind and highlights release + Genblaze manifests
- Only non-secret metadata (tenant prefix) is shown — never credentials

Full key map: [`docs/b2-layout.md`](docs/b2-layout.md)

## How SceneLedger uses Genblaze

Genblaze mediates **three generation steps**, each leaving a verifiable provenance trail:

| Step | Genblaze API | Output |
|------|--------------|--------|
| Scene planning | `genblaze_openai.chat()` with strict structured output | 3 validated, source-linked scenes |
| Storyboards | `Pipeline` + `DalleProvider` | `storyboard.png` per scene |
| Narration | `Pipeline` + `OpenAITTSProvider` | spoken `narration.mp3` per scene |

Every run's canonical SDK manifest (`Manifest`, schema 1.5) is stored **byte-exact** in B2. Release verification checks both SceneLedger's SHA-256 over the stored bytes **and** the SDK's own canonical hash (`parse_manifest().verify_hash()`). A tampered or missing claimed manifest blocks the release. Assets are marked `generator: "genblaze"` only after a real provider run — SceneLedger **never fakes** Genblaze output.

Details: [`docs/genblaze-pipeline.md`](docs/genblaze-pipeline.md)

## Providers and models

| Provider | Role | Model / tech |
|----------|------|--------------|
| **Backblaze B2** | Durable object storage for media + provenance | S3-compatible API |
| **Genblaze SDK** | Generation orchestration + canonical provenance manifests | `genblaze` 0.4.x |
| **OpenAI via Genblaze** | Scene planner (chat) | `gpt-4o-mini` (`SCENELEDGER_GENBLAZE_CHAT_MODEL`) |
| **OpenAI via Genblaze** | Storyboard images | `gpt-image-1` (`SCENELEDGER_GENBLAZE_IMAGE_MODEL`) |
| **OpenAI via Genblaze** | TTS narration | `gpt-4o-mini-tts`, voice `alloy` (`SCENELEDGER_GENBLAZE_TTS_MODEL/VOICE`) |
| Placeholder generators (fallback) | Deterministic offline assets | Pillow (storyboard), ffmpeg (clip), wave (narration), VTT (captions) |

---

## Setup

### Prerequisites

- Python 3.11+, Node.js 18+
- ffmpeg on PATH (optional — enables `clip.mp4` and `final.mp4`)

### 1. Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
pip install -r requirements-genblaze.txt   # Genblaze mode
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs · Health: http://localhost:8000/health

### 2. B2 setup (intended hackathon path)

1. Create a B2 bucket and an application key scoped to it
2. Copy `.env.example` to `.env` at the repo root
3. Set `SCENELEDGER_STORAGE_BACKEND=b2`, `B2_ENDPOINT` (S3-compatible, **without** bucket name), `B2_REGION`, `B2_BUCKET`, `B2_KEY_ID`, `B2_APPLICATION_KEY`

### 3. Genblaze setup (intended hackathon path)

1. `pip install -r apps/api/requirements-genblaze.txt`
2. Set `SCENELEDGER_MEDIA_MODE=genblaze` and `OPENAI_API_KEY` in `.env`
3. Optional model overrides: see [`.env.example`](.env.example)

### 4. Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000. For a hosted backend set `NEXT_PUBLIC_API_URL` in `apps/web/.env.local`.

### Placeholder fallback

SceneLedger includes placeholder mode so the provenance and B2 workflow can be tested without provider keys — set `SCENELEDGER_MEDIA_MODE=placeholder` (and optionally `SCENELEDGER_STORAGE_BACKEND=local` for fully offline use). Assets are deterministic and always labeled `generator: "placeholder"`; the scene planner falls back to a deterministic 3-scene mapping with the reason recorded in the plan. The intended hackathon path uses Genblaze for generation and B2 for durable media/provenance storage.

---

## Deployment

Backend on Render/Railway/Fly.io, frontend on Vercel. Exact steps, env vars, CORS (`SCENELEDGER_CORS_ORIGINS`), and the hosted smoke test: [`docs/deployment.md`](docs/deployment.md).

Quick check on any deployment:

```bash
curl https://your-api.example.com/health
# {"status":"ok","api_version":...,"storage_backend":"b2","media_mode":"genblaze","tenant_prefix":"tenants/demo"}
```

---

## Known limitations

- No authentication or multi-tenant isolation (single demo tenant prefix)
- No database — all state lives in B2 or the local filesystem
- Clips and captions are deterministic placeholders (labeled as such); `final.mp4` concatenates clips when they're real MP4s and is skipped cleanly otherwise
- No Object Lock or C2PA content credentials
- Genblaze manifests include generation prompts as part of provenance — avoid uploading confidential documents to a public demo bucket

## Roadmap

- Genblaze-generated scene clips (video models) feeding a fully AI `final.mp4`
- Regenerate-only-stale-scenes workflow (the payoff of scene-level provenance)
- B2 Object Lock for immutable release evidence; C2PA embedding via the SDK's manifest embedder
- Auth, projects-per-team, and a real database

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `api_version`, `storage_backend`, `media_mode`, `tenant_prefix` |
| POST | `/projects` | Create project |
| GET | `/projects/{id}` | Project summary |
| GET | `/projects/{id}/objects` | List stored object keys (grouped kinds) |
| GET | `/projects/{id}/asset?key=` | Stream a stored object for preview |
| POST | `/projects/{id}/sources` | Upload source version |
| POST | `/projects/{id}/plan` | Plan scenes (Genblaze chat / deterministic fallback) |
| POST | `/projects/{id}/generate-media` | Generate per-scene media + provenance |
| GET | `/projects/{id}/media` | Load scene media manifests |
| POST | `/projects/{id}/compare-source` | Detect stale scenes |
| POST | `/projects/{id}/release` | Build release evidence (+ optional final.mp4) |
| GET | `/projects/{id}/release` | Load stored release manifest |
| POST | `/projects/{id}/verify-release` | Re-verify all hashes + Genblaze manifests |

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/demo-script.md`](docs/demo-script.md) | 3-minute judge demo script |
| [`docs/devpost.md`](docs/devpost.md) | Devpost submission copy |
| [`docs/deployment.md`](docs/deployment.md) | Hosting, env vars, smoke test |
| [`docs/final-checklist.md`](docs/final-checklist.md) | Submission checklist |
| [`docs/architecture.md`](docs/architecture.md) | System overview |
| [`docs/b2-layout.md`](docs/b2-layout.md) | B2 object key map |
| [`docs/genblaze-pipeline.md`](docs/genblaze-pipeline.md) | Genblaze integration details |

## License

See [LICENSE](LICENSE).
