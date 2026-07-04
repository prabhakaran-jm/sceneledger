# Backblaze B2 Layout (planned)

MVP uses local filesystem keys that mirror the future B2 prefix layout.

## Prefix structure

```
projects/{project_id}/
  sources/
    v{version}/source.txt
  chunks/
    v{version}/chunks.json
  scenes/
    {scene_id}/
      video.mp4
      narration.mp3
      captions.vtt
      storyboard/
        frame-001.png
  manifests/
    release-v{version}.json
    genblaze-run-{run_id}.json
  provenance/
    {scene_id}.json
```

## Release manifest

Stored at `manifests/release-v{version}.json`:

- `project_id`, `source_version`, `scene_ids`, `stale_scene_ids`
- `generated_at`
- `placeholder_genblaze_manifest` — pipeline step metadata until Genblaze is wired
- `placeholder_b2_keys` — expected object keys for the release bundle

## MVP note

The API writes to `apps/api/data/` using the same key paths. Configure B2 via `.env` when implementing the B2 backend.
