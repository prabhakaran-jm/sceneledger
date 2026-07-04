# SceneLedger Architecture

## Overview

SceneLedger connects source documents to generated training video scenes. When a source changes, only scenes backed by changed chunks become stale.

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Local storage  │
│  apps/web   │     │  apps/api    │     │  (B2 later)     │
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
                    ┌──────▼───────┐
                    │  Genblaze    │  (placeholder MVP)
                    │  pipeline    │
                    └──────────────┘
```

## Monorepo layout

| Path | Role |
|------|------|
| `apps/api` | FastAPI backend: chunking, planning, stale detection, manifests |
| `apps/web` | Next.js demo UI |
| `packages/pipeline` | Future shared Genblaze pipeline definitions |
| `demo/` | Sample source documents for the hackathon demo |
| `docs/` | Architecture and runbook notes |

## Core flow

1. **Upload source** — plain text split into ordered chunks with SHA-256 hashes.
2. **Plan scenes** — deterministic mock planner assigns chunks to 3 scenes.
3. **Compare source** — re-chunk updated text; scenes referencing changed chunk hashes are marked stale.
4. **Release** — JSON manifest lists scenes, stale IDs, and placeholder B2 / Genblaze keys.

## Storage abstraction

`storage.py` defines a `StorageBackend` interface. MVP uses `LocalFilesystemStorage` under `apps/api/data/`. Swap the factory to a B2 client without changing route handlers.

## Out of scope (MVP)

- Authentication
- Real Genblaze / provider calls
- PostgreSQL (project state is JSON on disk)
- FFmpeg composition
