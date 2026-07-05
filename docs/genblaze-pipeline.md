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

## Provider preference — GMI Cloud first, OpenAI fallback

Every Genblaze step runs through a provider chain built from:

```env
SCENELEDGER_GENBLAZE_PROVIDER=gmi          # preferred: gmi | openai
SCENELEDGER_GENBLAZE_FALLBACK_PROVIDER=openai
GMI_API_KEY=                                # enables GMI attempts
SCENELEDGER_GMI_CHAT_MODEL=deepseek-ai/DeepSeek-V3.2
SCENELEDGER_GMI_IMAGE_MODEL=seedream-4-0-250828
SCENELEDGER_GMI_TTS_MODEL=minimax-tts-speech-2.6-turbo
SCENELEDGER_GMI_TTS_VOICE=            # optional; empty = model default voice
```

The preferred provider is tried first; on any failure (provider error,
rejected structured output, failed validation) the fallback provider runs;
planning then falls back to the deterministic planner with the full reason
chain recorded. Storyboard failure of all providers is a clear media error;
TTS failure of all providers degrades to labeled placeholder narration.
Each asset and manifest records the provider (`gmi`/`openai`) and model
that actually ran. Live-verified GMI models: `deepseek-ai/DeepSeek-V3.2`
(chat, strict structured output), `seedream-4-0-250828` (image queue),
`minimax-tts-speech-2.6-turbo` (TTS queue, via a custom registry that maps
`prompt`→`text` — GMI's TTS payload contract). Known blockers: some GMI
chat models (e.g. Qwen3-Next) reject `json_schema` response_format, and
`elevenlabs-tts-v3` appears in the queue catalog but probes DEAD on the
hackathon account — both simply fall through the chain. Remote asset URLs
are scrubbed of signed-URL credentials before manifests are persisted
(URLs are excluded from the SDK's canonical hash, so stored manifests
still verify).

## Genblaze pipeline

When configured, Genblaze mediates **three** generation steps:

### 1. Scene planning (chat)

```python
from genblaze_openai import chat

chat("gpt-4o-mini", prompt=chunk_text, system=PLANNER_PROMPT,
     response_format=ScenePlanOutput)  # strict JSON schema
```

The LLM writes scene titles, narration, and visual prompts. Output is
strictly validated: exactly 3 scenes, every scene must reference existing
`source_chunk_ids` in the same 1:1 order the deterministic planner uses
(scene-00N ↔ chunk-00N), and no source-free scenes. Invalid output falls
back to the deterministic planner with the reason recorded in the plan
(`planner_fallback_reason`). Because `chat()` sits outside the SDK Pipeline,
the run is recorded with the SDK's own `Run`/`Step`/`Manifest.from_run`
models — the stored manifest hash-verifies with `parse_manifest()`.

### 2. Storyboard (image)

```python
from genblaze_core import Pipeline, Modality
from genblaze_openai import DalleProvider

Pipeline(f"sceneledger-{scene_id}").step(
    DalleProvider(output_dir=temp_dir),
    model="gpt-image-1",
    prompt=scene.visual_prompt,
    modality=Modality.IMAGE,
).run(raise_on_failure=True)
```

### 3. Narration (TTS)

```python
from genblaze_openai import OpenAITTSProvider

Pipeline(f"sceneledger-{scene_id}-tts").step(
    OpenAITTSProvider(output_dir=temp_dir),
    model="gpt-4o-mini-tts",   # SCENELEDGER_GENBLAZE_TTS_MODEL
    prompt=scene.narration,
    modality=Modality.AUDIO,
    voice="alloy",             # SCENELEDGER_GENBLAZE_TTS_VOICE
    response_format="mp3",
).run(raise_on_failure=True)
```

Narration is written as `narration.mp3` with `generator: "genblaze"` **only
when TTS actually succeeded**; any failure falls back to the placeholder
`narration.wav` marked `generator: "placeholder"`. Clips and captions remain
placeholder-generated. Manifests mark each asset's `generator` honestly.

### Provenance manifests

Every Genblaze run's canonical SDK manifest is stored byte-exact:

```
projects/{project_id}/genblaze/{source_version}/planner/manifest.json
projects/{project_id}/genblaze/{source_version}/{scene_id}/manifest.json      # storyboard
projects/{project_id}/genblaze/{source_version}/{scene_id}/tts-manifest.json  # narration
```

`verify-release` re-reads each claimed manifest, checks SceneLedger's
recorded SHA-256 over the stored bytes, and re-runs the SDK's canonical hash
verification. A claimed-but-missing, corrupted, or tampered manifest blocks
the release; scenes/plans without one are not required to have it.

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
- `genblaze_provenance` summarizes Genblaze run IDs, stored manifest keys/hashes (planner, storyboard, TTS), and asset counts when present
- `planner_provenance` records which planner produced the plan, any fallback reason, and planner-manifest verification
- `placeholder_genblaze_manifest` remains for backward compatibility (true when no Genblaze assets)
- Release status reflects stale scenes (`warning`) or hash/asset problems (`blocked`)

Final stitched video is **M5 (future)** — M3/M4 verify per-scene assets only.

## Modes

- **Genblaze:** `SCENELEDGER_MEDIA_MODE=genblaze` with `OPENAI_API_KEY` and `requirements-genblaze.txt` installed — AI scene plan via chat, `gpt-image-1` storyboards, `gpt-4o-mini-tts` narration, with SDK provenance manifests stored and verified in B2
- **Placeholder:** `SCENELEDGER_MEDIA_MODE=placeholder` — deterministic assets, no provider keys, so the provenance and B2 workflow can be tested offline
- The Genblaze Integration panel in the UI shows `media_mode`, configured status, planner used, and whether any manifest has `generator: "genblaze"`
- SceneLedger **never fakes** Genblaze output
