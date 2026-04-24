# Backend GCP Migration Notes

Date: 2026-04-24
Scope: Phase 0-1 boundary for moving the local dashboard/API surface toward a Cloud Run Hono backend.

## Source Read

- `src/henshin/dashboard_server.py`
- `package.json`
- `pyproject.toml`
- `docs/new-route-gcp-platform-plan.md`
- `examples/0423_gpt-pro/**/03_仕様書_GCP.md`
- `examples/0423_gpt-pro/**/04_データ契約_GCP.md`
- `examples/0423_gpt-pro/**/05_進捗差分とロードマップ_GCP.md`

The two GCP spec bundles under `examples/0423_gpt-pro` have identical `03`, `04`, and `05` documents.

## Current Local API Surface

`dashboard_server.py` is a local development server that combines static file serving, local repository JSON reads/writes, async part generation jobs, IWSDK voice trial simulation, and mocopi live bridge state.

Current endpoints:

- `GET /api/health`
- `GET /api/suitspecs`
- `GET /api/suitspec?path=...`
- `GET /api/generation-jobs/:jobId`
- `GET /api/generation-jobs/:jobId/events`
- `POST /api/generation-jobs`
- `POST /api/generation-jobs/:jobId/cancel`
- `POST /api/generate-parts`
- `POST /api/suitspec-save`
- `POST /api/iw-henshin/voice`
- `GET /api/iw-henshin/mocopi-live/latest`
- `POST /api/iw-henshin/mocopi-live/frame`
- `POST /api/iw-henshin/mocopi-live/bridge-status`

`package.json` currently has Vite/Three/IWSDK tooling, but no Hono, TypeScript backend, Prisma, or GCP SDK dependencies. `pyproject.toml` is intentionally small and only carries the Python CLI/package path plus Pillow.

## Move To Cloud Run Hono

Move these first because they define durable backend contracts instead of local tooling:

- Health: `GET /api/health` becomes `GET /health`.
- Suit persistence: replace path-based `GET /api/suitspec`, `POST /api/suitspec-save`, and local discovery with ID-based Suit/SuitVersion APIs.
- Manifest projection/persistence: add `POST /v1/suits/:suitId/manifest` and `GET /v1/manifests/:manifestId`.
- Catalog read: expose `GET /v1/catalog/parts` from the PartCatalog seed, not from ad hoc viewer constants at runtime.
- Later trial/event persistence: current IWSDK/mocopi outputs should become `TransformSession` and `TransformEvent` writes, but not in the first skeleton.

Do not move these directly as-is:

- Arbitrary repo path reads/writes. Cloud APIs should accept IDs and validated JSON, not local file paths.
- SSE generation job transport. Cloud Run should not clone the local in-memory job manager. Use Cloud Tasks plus persisted job state when async generation becomes real.
- Static file serving. Firebase Hosting or the existing local server should own that surface.

## API Cut

### Implement Now: Phase 1 Skeleton

- `GET /health`
- `GET /v1/catalog/parts`
- `POST /v1/suits`
- `GET /v1/suits/:suitId`
- `POST /v1/suits/:suitId/manifest`
- `GET /v1/manifests/:manifestId`

The important constraint: this skeleton should prove SQL canonical storage and GCS artifact placement. It does not need AI, Quest runtime, or a full operator UI.

### Defer

- `POST /v1/emotion/analyze`
- `POST /v1/design/vector`
- `POST /v1/part-plans`
- `POST /v1/part-plans/resolve`
- `POST /v1/suits/:suitId/send-to-quest`
- `POST /v1/trials`
- `POST /v1/trials/:trialId/events`
- `GET /v1/trials/:trialId/replay`
- `/v1/devices` registration/status APIs
- async job APIs for preview, blueprint, emblem, replay metadata, MP4/PDF/export

Reason: the data contracts say SuitManifest, PartCatalog, TransformSession, TransformEvent, and ReplayScript must be fixed first. AI and Quest APIs become useful only after the catalog/manifest and trial event model are not moving.

### Keep In Python For Now

- `POST /api/generate-parts`
- `POST /api/generation-jobs`
- `GET /api/generation-jobs/:jobId`
- `GET /api/generation-jobs/:jobId/events`
- `POST /api/generation-jobs/:jobId/cancel`
- `POST /api/iw-henshin/voice`
- `GET /api/iw-henshin/mocopi-live/latest`
- `POST /api/iw-henshin/mocopi-live/frame`
- `POST /api/iw-henshin/mocopi-live/bridge-status`
- local static viewer/dashboard serving

Reason: these are demo/adapter/runtime validation surfaces. They are valuable, but they should feed the new contracts later instead of defining them.

## Initial Write Path

### Cloud SQL: canonical

Phase 1 writes should be transaction-first:

1. `POST /v1/suits`
   - validate request against the current SuitSpec/Suit draft contract
   - insert `suits`
   - insert initial `suit_versions` row with `version = 1`, draft JSON, status such as `DRAFT`
   - optionally insert linked `emotion_profiles`, `design_vectors`, and `part_plans` only when supplied and already schema-valid
2. `POST /v1/suits/:suitId/manifest`
   - validate SuitManifest
   - verify part IDs/material slots against `part_catalog`
   - insert next `suit_versions` row with manifest JSON, status such as `READY_FOR_QUEST`
   - record artifact URIs, content hash, schema version, created_by, created_at
3. `GET` APIs read SQL metadata first. GCS is artifact delivery, not the primary query database.

Minimum tables for the first cut:

- `projects`
- `suits`
- `suit_versions`
- `part_catalog`
- `part_assets`
- `audit_logs`

Hold `transform_sessions`, `transform_events`, and `replay_scripts` for the first Trial API ticket unless the schema work has already landed.

### GCS: artifact

Write artifacts after the SQL transaction has allocated stable IDs/version numbers:

```text
gs://{bucket}/
  suits/{suitId}/versions/{version}/manifest.json
  suits/{suitId}/versions/{version}/preview.png
  suits/{suitId}/versions/{version}/blueprint.png
  suits/{suitId}/versions/{version}/emblem.png
  suits/{suitId}/versions/{version}/merged.glb
  catalogs/parts/{catalogVersion}/part-catalog.json
```

For Phase 1, `manifest.json` is required. Preview/blueprint/emblem/GLB can be nullable artifact slots.

### Firestore: live state only

Do not write canonical suit or manifest history to Firestore.

Initial write path should start when Trial/device flows begin:

- `quest_devices/{deviceId}`: connection state, `lastSeenAt`, `currentTrialId`, `operatorId`
- `live_trials/{trialId}`: current step, progress, fit score, connection state, updated timestamp
- `operator_dashboards/{operatorId}`: selected participant/device/trial summary for monitor UI

For Phase 1, define the Firestore client/repository interface and collection names, but avoid fake writes from `GET /health`. If a smoke write is required, keep it in a dev-only admin script, not a product API.

## Phase 1 First Tickets

1. Create Hono Cloud Run skeleton with `GET /health`, request logging, error envelope, and Firebase Auth verification stub.
2. Add shared API/schema package for `SuitManifest`, `PartCatalog`, `Suit`, and `SuitVersion` DTOs.
3. Draft SQL schema/migration for `projects`, `suits`, `suit_versions`, `part_catalog`, `part_assets`, and `audit_logs`.
4. Seed `part_catalog` from existing armor/viewer assets and expose `GET /v1/catalog/parts`.
5. Implement `POST /v1/suits` and `GET /v1/suits/:suitId` using local Postgres or Cloud SQL.
6. Implement `POST /v1/suits/:suitId/manifest` with PartCatalog validation and `manifest.json` upload to GCS.
7. Implement `GET /v1/manifests/:manifestId` returning SQL metadata plus GCS artifact URI.
8. Write the Firestore collection contract without product writes; schedule first live write for the Trial API ticket.
