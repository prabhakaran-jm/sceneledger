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
```

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
- Release manifests
- Per-scene media assets and `scene-asset-manifest.json` (M2)
