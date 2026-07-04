# Backblaze B2 Layout (M1)

SceneLedger uses Backblaze B2 as an optional durable store for the same JSON artifacts written locally in M0. Genblaze and generated media are **not** stored in M1 — those arrive in M2.

## Why B2

- Durable project record for hackathon demos and judges
- Same artifact shapes as local mode (sources, plans, compare reports, manifests)
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
{prefix}/projects/{project_id}/sources/v2/source.txt
{prefix}/projects/{project_id}/sources/v2/chunks.json
{prefix}/projects/{project_id}/plans/v1/scenes.json
{prefix}/projects/{project_id}/compare/v1-v2/stale-report.json
{prefix}/projects/{project_id}/manifests/v1/release.json
```

Example with default prefix:

```
tenants/demo/projects/{project_id}/sources/v1/source.txt
```

## Local ↔ B2 mapping

| Logical path (route code) | Local file | B2 object key |
|---------------------------|------------|---------------|
| `projects/{id}/project.json` | `.sceneledger/projects/{id}/project.json` | `tenants/demo/projects/{id}/project.json` |

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
- Credentials map to boto3 as `aws_access_key_id` / `aws_secret_access_key`

## What M1 stores

- Project metadata (`project.json`)
- Source text and chunk JSON per version
- Scene plans
- Stale compare reports
- Release manifests

## What M2 will add

- Genblaze run manifests under `manifests/genblaze-run-{run_id}.json`
- Generated media under `scenes/{scene_id}/` (video, narration, captions, storyboard)
- Provenance records per scene
