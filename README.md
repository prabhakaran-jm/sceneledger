# SceneLedger

SceneLedger turns changing source documents into source-linked training videos.

It generates short training scenes from a source document, records which source chunks support each scene, detects when the source changes, and regenerates only the scenes that became stale.

## What it does

- Upload a procedure, policy, manual, or product guide
- Split the source into stable chunks
- Generate a source-linked scene plan
- Create storyboard frames, video clips, narration, and captions
- Store generated media, metadata, logs, and manifests in Backblaze B2
- Use Genblaze to orchestrate the media pipeline
- Track provenance for each generated scene
- Detect stale scenes when the source document changes
- Regenerate only outdated scenes
- Produce a verified final release package

## Hackathon

Built for the Backblaze Generative Media Hackathon.

## Core demo

1. Upload source document version 1
2. Generate a 3-scene training video
3. Show each scene linked to source chunks
4. Upload source document version 2
5. Detect that only one scene is stale
6. Regenerate that scene
7. Publish a new verified release

## Tech stack

- Frontend: Next.js
- Backend: FastAPI
- Media pipeline: Genblaze
- Storage: Backblaze B2
- Database: SQLite for MVP, PostgreSQL later
- Video composition: FFmpeg