# New Route Operator Checklist

## 2. First Canonical SuitSpec

For now, the first canonical suit is fixed in:

```text
config/new-route.canonical.json
```

Current provisional source:

```text
examples/suitspec.sample.json
VDA-AXIS-OP-00-0001
```

What you need to do:

1. Review `examples/suitspec.sample.json` as the first official suit seed.
2. If it is acceptable, no action is required.
3. If another suit should become the first official seed, replace `suitspec_path` and `canonical_suit_id` in `config/new-route.canonical.json`.

Decision standard:

- Keep the first seed small enough to verify Web, Quest, and Replay repeatedly.
- Prefer a complete `SuitSpec` with all required core modules over a more ambitious but incomplete concept.
- Treat this as the first route marker, not the final armor identity.

## 3. Platform Preparation

You do not need to create everything immediately. The local route can keep moving while the cloud side is prepared.

Prepare next:

1. GCP project name.
2. Artifact bucket name.
3. Cloud SQL PostgreSQL instance name.
4. Firebase project or confirmation that the same GCP project will host Firebase Auth and Firestore.
5. Quest 3 local test path: same LAN HTTPS or `adb reverse`.

Reference files:

```text
infra/gcp/env.example
infra/gcp/cloudsql/schema.sql
infra/gcp/firestore-live-state.json
docs/new-route-gcp-readiness.md
```

## Local Quest Trial Smoke

After starting the dashboard server:

```powershell
python -m henshin serve-dashboard --port 8010
```

Open:

```text
http://localhost:8010/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

Expected behavior:

- The demo saves the canonical `SuitSpec`.
- It projects a `SuitManifest`.
- It creates a `TransformSession`.
- Voice/mock trigger events are appended to `/v1/trials/{trialId}/events`.
- ReplayScript can be generated from `/v1/trials/{trialId}/replay`.
