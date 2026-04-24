# New Route Phase 1 Implementation Plan

## Lore Standard

The route remains `Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す`.
`SuitSpec` is the authoring source. `SuitManifest` is the runtime contract consumed by Web preview, Quest, and Replay.

## Phase 1: Webでスーツ成立

Current local API contract:

```text
GET /health
GET /v1/catalog/parts
POST /v1/suits
GET /v1/suits/{suitId}
POST /v1/suits/{suitId}/manifest
GET /v1/suits/{suitId}/manifest
GET /v1/manifests/{manifestId}
```

Implementation boundary:

- `POST /v1/suits` validates and saves a `SuitSpec`.
- `POST /v1/suits/{suitId}/manifest` projects the saved `SuitSpec` into a `SuitManifest` using `PartCatalog`.
- Local storage is JSON under `sessions/new-route/suits/...`.
- The API surface should stay stable when local JSON storage is replaced with Cloud SQL and GCS.

Done condition:

- A single suit can be saved as `SuitSpec`.
- The same suit can produce a schema-valid `SuitManifest`.
- Manifest parts include catalog references needed by Web, Quest, and Replay.

## Phase 2: Questで変身試験

Target contract:

```text
POST /v1/trials
GET /v1/trials/{trialId}
POST /v1/trials/{trialId}/events
POST /v1/suits/{suitId}/send-to-quest
```

Current local contract implemented:

- `POST /v1/trials` creates a `TransformSession v0.1` from a saved suit manifest or a direct `manifest_id`.
- `GET /v1/trials/{trialId}` reads the saved `TransformSession`.
- `POST /v1/trials/{trialId}/events` appends canonical transform events and updates the session state.

Storage split:

- Cloud SQL: trial history and transform events.
- Firestore: live Quest/operator state only.
- GCS: manifest, generated assets, and replay artifacts.

First implementation lane:

- Use the existing Quest Browser/IWSDK demo to fetch a `SuitManifest`.
- Append transform events during a mock or voice-triggered trial.
- Keep Unity/OpenXR as the later runtime lane after the manifest contract stabilizes.

## Phase 3: Replayで体験を残す

Target contract:

```text
GET /v1/trials/{trialId}/replay
```

Replay source of truth:

- `TransformEvent` plus `SuitManifest` produces `ReplayScript`.
- MP4/audio outputs are derived artifacts, not the primary record.
- The replay player should be able to jump, pause, and restart from event boundaries.

## Platform Notes

- PlayCanvas can be introduced as a manifest preview/editor surface, but it should not become the source of truth.
- GCP should carry durable boundaries: Cloud Run for API, Cloud SQL for source/version rows, GCS for artifacts, Firestore for live state, Cloud Tasks for heavy async work.
- Quest Browser/IWSDK is the fastest validation path. Unity/OpenXR should follow once manifest runtime behavior is stable.
- 3D model work should stay `VRM first -> armor authoring -> parametric variation`; GLB is a derived runtime artifact.

## User Preparation

- GCP project with Cloud Run, Cloud SQL PostgreSQL, GCS, Firebase Auth, and Firestore.
- Deploy service account and bucket/database naming decision.
- Meta Quest 3 on the same LAN, with HTTPS or `adb reverse` available for WebXR/microphone tests.
- Baseline VRM, existing armor mesh/texture license status, and the first official `SuitSpec` to treat as the canonical suit.
