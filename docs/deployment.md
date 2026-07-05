# Deployment Notes

Simple deployment path for hackathon judging. No platform-specific config files are required in the repo.

---

## Recommended stack

| Component | Option |
|-----------|--------|
| Frontend | [Vercel](https://vercel.com) (Next.js) |
| Backend | Render, Railway, or Fly.io (FastAPI + uvicorn) |
| Storage | Backblaze B2 |
| Generation | Genblaze SDK + OpenAI key |

---

## Backend deployment

1. Deploy `apps/api` as a Python web service
2. Build: `pip install -r requirements.txt -r requirements-genblaze.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables (below)
5. Confirm health: `GET https://your-api.example.com/health`

### Required env vars (B2 + Genblaze — intended hackathon path)

```env
SCENELEDGER_STORAGE_BACKEND=b2
SCENELEDGER_B2_TENANT_PREFIX=tenants/demo
B2_ENDPOINT=https://s3.<region>.backblazeb2.com
B2_REGION=<region>
B2_BUCKET=<your-bucket>
B2_KEY_ID=<server-side only>
B2_APPLICATION_KEY=<server-side only>
SCENELEDGER_MEDIA_MODE=genblaze
OPENAI_API_KEY=<server-side only>
SCENELEDGER_CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

### Optional env vars

```env
SCENELEDGER_GENBLAZE_CHAT_MODEL=gpt-4o-mini
SCENELEDGER_GENBLAZE_IMAGE_MODEL=gpt-image-1
SCENELEDGER_GENBLAZE_TTS_MODEL=gpt-4o-mini-tts
SCENELEDGER_GENBLAZE_TTS_VOICE=alloy
# Offline fallback instead of genblaze:
# SCENELEDGER_MEDIA_MODE=placeholder
```

**Notes**

- `SCENELEDGER_CORS_ORIGINS` is a comma-separated list of allowed browser origins; the API defaults to `http://localhost:3000` only.
- ffmpeg is not present on most default Python images — scene clips and `final.mp4` degrade cleanly to labeled placeholders / a skip message. Install ffmpeg in the image if you want them.
- **Security:** never expose `B2_KEY_ID`, `B2_APPLICATION_KEY`, or `OPENAI_API_KEY` to the frontend. `/health` returns only non-secret metadata.

### B2 setup

1. Create a B2 bucket (private is fine — the API streams previews via `/projects/{id}/asset`)
2. Create an application key scoped to that bucket
3. Use the S3-compatible endpoint **without** the bucket name

### Genblaze / OpenAI setup

1. `pip install -r requirements-genblaze.txt` (installs `genblaze`, `genblaze-openai`)
2. Set `OPENAI_API_KEY` and `SCENELEDGER_MEDIA_MODE=genblaze`
3. Without a key, `/plan` falls back to the deterministic planner (reason recorded) and `/generate-media` returns a clear 503

---

## Frontend deployment

1. Deploy `apps/web` on Vercel (root directory: `apps/web`)
2. Set build env:

```env
NEXT_PUBLIC_API_URL=https://your-api.example.com
```

3. Confirm the demo page loads at `/project`
4. Add the Vercel URL to the backend's `SCENELEDGER_CORS_ORIGINS`

---

## Health check

```bash
curl -s https://your-api.example.com/health
```

Expected: `{"status":"ok","service":"sceneledger-api","api_version":"0.7.0","storage_backend":"b2","media_mode":"genblaze","tenant_prefix":"tenants/demo"}`

---

## Hosted smoke test (required before sharing the demo URL)

Run from a **clean browser** (incognito, no cached state):

| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | Frontend loads | `/project` renders without console errors |
| 2 | `/health` | `status: ok`, `storage_backend: b2`, `media_mode: genblaze` |
| 3 | Frontend → backend | Create Project succeeds (no CORS/network failure) |
| 4 | Plan | Toast shows "planned by Genblaze chat" (or a recorded fallback reason) |
| 5 | Media | Storyboards render, narration plays in the Release Package panel |
| 6 | B2 | Storage panel shows grouped keys incl. `genblaze/` manifests; release.json in bucket |
| 7 | Full 8-step demo | verified → v2 → only scene-003 stale → warning |

Quick curl smoke test:

```bash
curl -s https://your-api.example.com/health
curl -s -X POST https://your-api.example.com/projects \
  -H "Content-Type: application/json" -d '{"name":"Smoke Test"}'
```

---

## Known limitations

- No authentication — demo only
- No database — all state in B2 or local filesystem
- Genblaze media generation takes ~2 minutes for 3 scenes (image generation dominates); pre-generate before live demos
- CORS must be configured for non-localhost frontends
