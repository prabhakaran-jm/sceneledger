# Deployment Notes

Simple deployment path for hackathon judging. No platform-specific config files are required in the repo.

---

## Recommended stack

| Component | Option |
|-----------|--------|
| Frontend | [Vercel](https://vercel.com) or Render (Next.js) |
| Backend | Render, Railway, or Fly.io (FastAPI + uvicorn) |
| Storage | Backblaze B2 (recommended for judge-visible durability) |

---

## Backend deployment

1. Deploy `apps/api` as a Python web service
2. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. Set environment variables (see below)
4. Confirm health: `GET https://your-api.example.com/health`

### Required env vars (B2 mode — recommended for judging)

```env
SCENELEDGER_STORAGE_BACKEND=b2
SCENELEDGER_B2_TENANT_PREFIX=tenants/demo
SCENELEDGER_MEDIA_MODE=placeholder
B2_ENDPOINT=https://s3.<region>.backblazeb2.com
B2_REGION=<region>
B2_BUCKET=<your-bucket>
B2_KEY_ID=<server-side only>
B2_APPLICATION_KEY=<server-side only>
```

### Optional env vars

```env
SCENELEDGER_MEDIA_MODE=genblaze
OPENAI_API_KEY=<only if using Genblaze mode>
SCENELEDGER_CORS_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
```

**Security:** Never expose `B2_KEY_ID`, `B2_APPLICATION_KEY`, or `OPENAI_API_KEY` to the frontend. `/health` returns only non-secret metadata (`tenant_prefix`, not bucket credentials).

---

## Frontend deployment

1. Deploy `apps/web` (Next.js)
2. Set build env:

```env
NEXT_PUBLIC_API_URL=https://your-api.example.com
```

3. Confirm the demo page loads at `/project`

---

## CORS

The API defaults to `http://localhost:3000`. For hosted frontend:

1. Set `SCENELEDGER_CORS_ORIGINS` to your frontend URL(s), comma-separated
2. Only add this if browser requests fail with CORS errors

---

## Smoke test (required before sharing demo URL)

Run from a **clean browser** (incognito, no cached state):

| # | Check | Pass criteria |
|---|-------|---------------|
| 1 | Hosted frontend loads | `/project` renders without console errors |
| 2 | Hosted backend `/health` | Returns `status: ok`, `api_version: 0.5.0-m4` |
| 3 | Frontend → backend | Create Project succeeds (no CORS/network failure) |
| 4 | Full 8-step demo | All stepper steps completable end-to-end |
| 5 | B2 mode (if used) | Storage panel shows grouped keys; release manifest in bucket |

Quick curl smoke test:

```bash
curl -s https://your-api.example.com/health | jq .
curl -s -X POST https://your-api.example.com/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Smoke Test"}'
```

---

## Local vs hosted

| Mode | When to use |
|------|-------------|
| Local API + local storage | Offline development |
| Local API + B2 | Development with real bucket |
| Hosted API + B2 + hosted web | Judge-facing demo URL |

Placeholder mode works without any AI provider keys.

---

## Known limitations

- No authentication — demo only
- No database — all state in B2 or local filesystem
- CORS must be configured for non-localhost frontends
- Genblaze mode requires provider keys and optional pip packages on the server
