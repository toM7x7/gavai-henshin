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

Why this uses the previous Quest mock:

- The previous Quest/IWSDK demo is now the integration harness for the new route.
- The goal is not to re-evaluate the old mock itself; the goal is to verify that Quest can drive `TransformSession`, canonical events, and `ReplayScript`.
- Once the event/API loop is stable, the visible experience can be replaced or upgraded without changing the data contract.

Start the API server:

```powershell
npm run dev
```

Start the Quest/Vite server in another terminal:

```powershell
npm run dev:quest -- --host 0.0.0.0
```

HTTP LAN smoke URL:

```text
http://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

Expected behavior over HTTP:

- The demo saves the canonical `SuitSpec`.
- It projects a `SuitManifest`.
- It creates a `TransformSession`.
- The Quest page shows a `New Route` status panel for route mode, API step, trial id, and replay generation.
- `Replay`, `Pause`, and `Reset` work in the page.
- With `mockTrigger=1`, `Voice` uses synthetic mock audio and does not require microphone permission.
- Voice/mock trigger events are appended to `/v1/trials/{trialId}/events`.
- ReplayScript can be generated from `/v1/trials/{trialId}/replay`.

After a Quest smoke test, confirm the latest recorded trial:

```powershell
Invoke-RestMethod http://localhost:8010/v1/trials/latest
```

The important fields are `summary.state`, `summary.event_count`, and `summary.replay_script_path`.
The PC dashboard also shows the same latest trial in the `Quest実機ログ` card.

Expected limitation over HTTP:

- `Enter VR` and real microphone capture may be blocked because Quest Browser requires a secure context.

## Real Voice And Enter VR

Use one of these paths.

### ADB Reverse Path

This is the fastest local route if the Quest is connected by USB with Developer Mode enabled.

Start the API and Quest/Vite servers:

```powershell
npm run dev
npm run dev:quest -- --host 0.0.0.0
```

In a third terminal:

```powershell
npm run dev:quest:adb
```

Open in Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

The `localhost` origin on the headset is the important part; it is treated as a local secure context by browser APIs more reliably than raw LAN HTTP.

### LAN HTTPS Path

Create a local certificate:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp {PC_LAN_IP}
```

Install or trust `config/quest-lan-root-ca.cer` on the Quest device, then run:

```powershell
npm run dev
npm run dev:quest:lan
```

Open:

```text
https://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```
