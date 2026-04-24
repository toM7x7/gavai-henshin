# New Route GCP Readiness

## Scope

The first cloud step is not the full platform. It is the durable version of the route that already works locally:

```text
SuitSpec -> SuitManifest -> TransformSession -> TransformEvent -> ReplayScript
```

## Durable Split

- Cloud Run: API surface.
- Cloud SQL PostgreSQL: source rows, versions, trials, events, audit log.
- GCS: JSON artifacts, generated textures, previews, GLB, replay scripts, media.
- Firestore: live Quest/operator state only.
- Cloud Tasks: later async work such as previews, GLB merge, replay media, and heavy AI jobs.

## Required GCP Resources

Create or decide names for:

```text
GCP project
Cloud Run service
Artifact Registry repository
Cloud SQL PostgreSQL instance, database, and API user
GCS artifact bucket
Firestore database
Firebase Authentication project/config
Cloud Run service account
Secret Manager secrets for database credentials and optional API keys
```

Minimum IAM for the Cloud Run service account:

```text
Cloud SQL Client
Storage Object Admin or narrower bucket-scoped object role
Datastore User
Secret Manager Secret Accessor
```

## Seed Data

Initial local sources:

```text
config/new-route.canonical.json
examples/suitspec.sample.json
examples/partcatalog.seed.json
```

Initial cloud seed target:

```text
part_catalogs.catalog_json
suits
suit_versions.suitspec_json
suit_versions.manifest_json
```

GCS mirror target:

```text
gs://{bucket}/catalogs/parts/{catalogId}/part-catalog.json
gs://{bucket}/suits/{suitId}/versions/{version}/suitspec.json
gs://{bucket}/suits/{suitId}/versions/{version}/manifest.json
```

## Trial And Replay Target

The local Phase 2/3 API already writes the shape that should map to Cloud SQL:

```text
transform_sessions
transform_events
```

Replay artifacts should mirror to:

```text
gs://{bucket}/trials/{trialId}/transform-session.json
gs://{bucket}/trials/{trialId}/events.ndjson
gs://{bucket}/trials/{trialId}/replay/replay-script.json
```

## Firestore Rule

Firestore is a live mirror. Do not put durable source data there.

Allowed:

```text
quest_devices/{deviceId}
live_trials/{trialId}
operator_dashboards/{operatorId}
```

Not allowed as source of truth:

```text
SuitSpec
SuitManifest
TransformSession
TransformEvent
ReplayScript
```
