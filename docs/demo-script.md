# Demo Script

~3 minute M0 walkthrough.

## Setup

1. Start API: `uvicorn main:app --reload --port 8000` from `apps/api`
2. Start web: `npm run dev` from `apps/web`
3. Open http://localhost:3000/project

## Script

1. **Intro** — "SceneLedger links training video scenes to source document chunks."
2. **Create Project** — click **Create Project**.
3. **Upload v1** — click **Upload Source v1** (pre-filled from `demo/source-v1.txt`).
4. **Plan** — click **Generate Scene Plan**. Show three scenes:
   - Scene 1 → `chunk-001` (stop work when alarm sounds)
   - Scene 2 → `chunk-002` (leave through nearest exit)
   - Scene 3 → `chunk-003` (report to assembly point A)
5. **Upload v2** — click **Upload Source v2** (paragraph 3 now says assembly point C).
6. **Compare** — click **Compare Source Versions**.
7. **Stale result** — Scene 3 is **stale**; Scenes 1 and 2 stay **current**.
8. **Release** — click **Create Release Manifest**; show JSON with `stale_scene_ids: ["scene-003"]`.
9. **Close** — "M1 adds B2 storage; M2 adds Genblaze media generation."

## Expected stale scene

Only paragraph 3 changed (assembly point A → C). That paragraph is `chunk-003`, which backs Scene 3.

## Backend-only alternative

See the curl sequence in [`README.md`](../README.md).
