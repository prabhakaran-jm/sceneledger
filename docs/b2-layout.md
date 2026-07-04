# Backblaze B2 Layout (M1 + M2)

SceneLedger uses Backblaze B2 as an optional durable store for the same artifacts written locally in M0/M1, plus generated media in M2.

## Why B2

- Durable project record for hackathon demos and judges
- Same artifact shapes as local mode (sources, plans, compare reports, manifests, media)
- S3-compatible API works with boto3

## Storage modes

| Mode | Env | Physical location |
|------|-----|-------------------|
| Local (default) | `SCENELEDGER_STORAGE_BACKEND=local` | `.sceneledger/projects/{project_id}/...` |
| B2 | `SCENELEDGER_STORAGE_BACKEND=b2` | B2 bucket under `{SCENELEDGER_B2_TENANT_PREFIX}/projects/{project_id}/...` |

`SCENELEDGER_B2_TENANT_PREFIX` defaults to `tenants/demo`. It is a **static key prefix**, not dynamic tenant management.

## B2 object key layout

```
{SCENELEDGER_B2_TENANT_PREFIX}/projects/{project_id}/project.json
{prefix}/projects/{project_id}/sources/v1/source.txt
{prefix}/projects/{project_id}/sources/v1/chunks.json
{prefix}/projects/{project_id}/plans/v1/scenes.json
{prefix}/projects/{project_id}/compare/v1-v2/stale-report.json
{prefix}/projects/{project_id}/manifests/v1/release.json
{prefix}/projects/{project_id}/media/v1/scene-001/storyboard.png
{prefix}/projects/{project_id}/media/v1/scene-001/clip.mp4
{prefix}/projects/{project_id}/media/v1/scene-001/clip.placeholder.txt
{prefix}/projects/{project_id}/media/v1/scene-001/narration.wav
{prefix}/projects/{project_id}/media/v1/scene-001/captions.vtt
{prefix}/projects/{project_id}/media/v1/scene-001/scene-asset-manifest.json
{prefix}/projects/{project_id}/genblaze/v1/planner/manifest.json
{prefix}/projects/{project_id}/genblaze/v1/scene-001/manifest.json
{prefix}/projects/{project_id}/genblaze/v1/scene-001/tts-manifest.json
```

The `genblaze/` objects (kind: `genblaze_manifest`) are written only when Genblaze mode runs: `planner/manifest.json` for the chat scene-planning run, `{scene_id}/manifest.json` for the storyboard run, and `{scene_id}/tts-manifest.json` for the TTS narration run. In Genblaze mode `narration.mp3` replaces `narration.wav`. It is the Genblaze SDK's canonical provenance manifest, stored byte-exact — SceneLedger never rewrites it, so both SceneLedger's sha256 (recorded in `scene-asset-manifest.json`) and the SDK's own canonical hash verify against the stored bytes. Note: the SDK manifest includes generation prompts as part of provenance — avoid uploading confidential source documents to a publicly visible demo bucket.

Example with default prefix:

```
tenants/demo/projects/{project_id}/media/v1/scene-001/storyboard.png
```

## Local ↔ B2 mapping

| Logical path (route code) | Local file | B2 object key |
|---------------------------|------------|---------------|
| `projects/{id}/project.json` | `.sceneledger/projects/{id}/project.json` | `tenants/demo/projects/{id}/project.json` |
| `projects/{id}/media/v1/scene-001/storyboard.png` | same under `.sceneledger/` | `tenants/demo/projects/{id}/media/v1/scene-001/storyboard.png` |

API `storage_keys` responses use logical paths in local mode and full B2 keys in B2 mode.

## B2 configuration

```env
SCENELEDGER_STORAGE_BACKEND=b2
SCENELEDGER_B2_TENANT_PREFIX=tenants/demo
B2_ENDPOINT=https://s3.us-west-004.backblazeb2.com
B2_REGION=us-west-004
B2_BUCKET=your-bucket-name
B2_KEY_ID=your-key-id
B2_APPLICATION_KEY=your-application-key
```

- **Endpoint** is the S3-compatible API URL — do **not** include the bucket name
- **Bucket** is passed separately on each boto3 call
- Binary media writes set explicit `ContentType` (`image/png`, `video/mp4`, `audio/wav`, `text/vtt`, `text/plain`)

## What is stored

- Project metadata (`project.json`)
- Source text and chunk JSON per version
- Scene plans
- Stale compare reports
- Release manifests (M3 provenance record with self-hash)
- Per-scene media assets and `scene-asset-manifest.json` (M2)

## Release manifest (M3)

Stored at `manifests/{source_version}/release.json`. Object kind: `release_manifest`.

The manifest is a durable evidence record that includes:

- Source chunk hashes and scene plan linkage
- Per-scene media assets with recorded and computed SHA-256
- Stale scene IDs and `release_superseded_by_source_version` when a compare report exists
- `genblaze_provenance` (`run_ids`, `manifest_keys`, `manifest_hashes`, `asset_count`) when any asset has `generator: "genblaze"`; verify-release re-reads each stored Genblaze manifest, checks its sha256, and re-runs the SDK's canonical hash verification — a failed or missing claimed manifest blocks the release
- `release_manifest_sha256` — canonical JSON hash of the manifest (excluding the hash field)

Use `POST /verify-release` to re-read assets from storage and confirm hashes still match.

## Demo visibility (M4)

During the judge demo, expect these keys under `tenants/demo/projects/{project_id}/`:

| Step | Keys to highlight |
|------|-------------------|
| After upload v1 | `sources/v1/source.txt`, `sources/v1/chunks.json` |
| After plan | `plans/v1/scenes.json` |
| After media | `media/v1/scene-*/` (storyboard, clip, narration, captions, scene-asset-manifest.json); in Genblaze mode also `genblaze/v1/scene-*/manifest.json` (**genblaze_manifest**) |
| After release | `manifests/v1/release.json` (**release_manifest**) |
| After compare | `compare/v1-v2/stale-report.json` |

The UI Storage panel groups objects by kind and highlights the release manifest key. Only non-secret metadata (`tenant_prefix`) is shown in the UI — never bucket credentials.
