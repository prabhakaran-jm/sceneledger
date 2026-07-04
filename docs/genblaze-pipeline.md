# Genblaze Pipeline (placeholder)

Real Genblaze orchestration is not implemented in the MVP scaffold. This doc describes the intended pipeline.

## Target steps

1. **Storyboard** — image frames from `visual_prompt` per scene
2. **Video** — short clips from storyboard frames
3. **Narration** — TTS from `narration` text
4. **Captions** — VTT aligned to narration
5. **Compose** — FFmpeg merge into final scene clip

## Provenance

Each run should record:

- Source chunk IDs and hashes used
- Model / provider IDs
- Output B2 keys
- Genblaze run ID

## MVP behavior

`release_manifest.py` emits a `placeholder_genblaze_manifest` with step names and status `"placeholder"`. Wire Genblaze in `packages/pipeline` when provider keys are available.

## Environment

See `.env.example` for `GMI_API_KEY`, `GENBLAZE_STORAGE_PROVIDER`, and related vars. Do not commit real keys.
