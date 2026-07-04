# Demo Script

~3 minute walkthrough for judges.

## Setup

1. Start API: `uvicorn main:app --reload --port 8000` from `apps/api`
2. Start web: `npm run dev` from `apps/web`
3. Open http://localhost:3000/project

## Script

1. **Intro** — "SceneLedger links training video scenes to source document chunks."
2. **Upload v1** — Click **Upload source** (pre-filled from `demo/source-v1.txt`).
3. **Plan** — Click **Generate plan**. Show 3 scene cards, each with chunk IDs (`chunk-001`, `chunk-002`, `chunk-003`).
4. **Explain linkage** — Scene 2 maps to `chunk-002` (equipment checklist paragraph). Scenes 1 and 3 map to `chunk-001` and `chunk-003`.
5. **Compare v2** — Click **Compare source** (pre-filled from `demo/source-v2.txt`, one paragraph changed).
6. **Stale result** — Only Scene 2 shows **stale**; Scenes 1 and 3 stay **current**.
7. **Release** (optional curl):

   ```bash
   curl -X POST http://localhost:8000/projects/{project_id}/release
   ```

8. **Close** — "Next step: regenerate stale scenes via Genblaze and publish to B2."

## Expected stale scene

Only the middle paragraph changed (added "fire extinguisher tags are current"). That paragraph is `chunk-002`, which backs Scene 2.
