# Genblaze Pipeline (M2)

SceneLedger M2 adds per-scene media generation with two modes:

| Mode | Env | Dependencies |
|------|-----|--------------|
| **Placeholder** (default) | `SCENELEDGER_MEDIA_MODE=placeholder` | `apps/api/requirements.txt` only |
| **Genblaze** (optional) | `SCENELEDGER_MEDIA_MODE=genblaze` | `pip install -r requirements-genblaze.txt` + `OPENAI_API_KEY` |

## Placeholder pipeline

Deterministic assets per scene under:

```
projects/{project_id}/media/{source_version}/{scene_id}/
  storyboard.png
  clip.mp4              # if ffmpeg on PATH
  clip.placeholder.txt  # if ffmpeg missing (playable: false)
  narration.wav
  captions.vtt
  scene-asset-manifest.json
```

Each manifest includes `status: "complete"`, `media_mode`, and per-asset metadata (`sha256`, `content_type`, `generator`, `playable`).

## Genblaze pipeline (partial M2 scope)

When configured, Genblaze generates the **storyboard** via documented APIs:

```python
from genblaze_core import Pipeline, Modality
from genblaze_openai import DalleProvider

Pipeline(f"sceneledger-{scene_id}").step(
    DalleProvider(output_dir=temp_dir),
    model="gpt-image-1",
    prompt=scene.visual_prompt,
    modality=Modality.IMAGE,
).run()
```

Clip, narration, and captions remain placeholder-generated until provider keys and adapters are wired. Manifests mark each asset's `generator` honestly (`genblaze` vs `placeholder`).

### Asset read rules

The Genblaze adapter reads provider output bytes only from:

- `file://` URLs under the adapter temp directory
- `https://` URLs with timeout

Bytes are re-hashed locally with SHA-256. Signed URLs and secrets are never logged.

## Out of scope (M2)

- Final stitched video
- Real voiceover quality
- Auth, database, Object Lock, C2PA
- Fake "all-genblaze" completion when providers are missing

## Environment

See [`.env.example`](../.env.example). Do not commit real keys.

Optional install:

```bash
cd apps/api
pip install -r requirements-genblaze.txt
```

## Provenance (M3)

M3 consumes M2 scene manifests honestly and embeds them in the release manifest:

- Each scene's `scene-asset-manifest.json` is loaded and asset bytes are re-hashed
- `genblaze_provenance` summarizes Genblaze run IDs and asset counts when present
- `placeholder_genblaze_manifest` remains for backward compatibility (true when no Genblaze assets)
- Release status reflects stale scenes (`warning`) or hash/asset problems (`blocked`)

Final stitched video is **M4** — M3 verifies per-scene assets only.
