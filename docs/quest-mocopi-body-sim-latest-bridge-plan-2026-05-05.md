# Quest mocopi body-sim/latest bridge plan - 2026-05-05

## Current local truth

- `tools/serve_mocopi_body_sim_latest.py` already exposes the rehearsal adapter endpoint:
  - `GET http://127.0.0.1:8021/body-sim/latest`
  - `GET http://127.0.0.1:8021/api/mocopi/body-sim/latest`
  - `GET http://127.0.0.1:8021/api/mocopi/debug/latest`
- The adapter response is cache-safe for live polling because it returns `Cache-Control: no-store`.
- The adapter is cross-origin readable because it returns `Access-Control-Allow-Origin: *`.
- The adapter response carries `motion_source: mocopi` and `metadata.motion_source: mocopi` when the received UDP payload identifies mocopi.
- The adapter now accepts Sony mocopi Motion Serializer/MMF UDP packets in addition to the earlier privacy-minimized JSON rehearsal payloads. The parsed path is:
  - `head/ftyp/vrsn` confirms `sony motion format` v1.
  - `sndf` carries sender metadata.
  - `fram/btrs/btdt/bnid/tran` is mapped into mocopi-like joints and then into the existing `body-sim` contract.
  - `skdf/bons/bndt/bnid/tran` can produce a static skeleton-like body-sim if frame data has not arrived yet.
- Raw mocopi UDP motion payloads are not retained by the adapter; only derived latest body-sim state is kept in memory.
- `viewer/quest-iw-demo/quest-demo.js` already preserves absolute `http(s)` paths in `normalizePath`.
- Quest replay load already calls `loadBodySimRecord(replay.deposition.body_sim_path)` and then derives the diagnostic token through `replayMotionSourceFromRecord(replay, bodySim)`.
- `src/henshin/dashboard_server.py` currently has `/api/quest-debug/latest` but no dashboard-owned `/api/mocopi/body-sim/latest` bridge.

## Minimum live path without touching Quest JS

This is the fastest path for a local real-device test.

1. Start the dashboard and Quest viewer as usual.
2. Start the mocopi adapter on the PC:

   ```powershell
   python tools/serve_mocopi_body_sim_latest.py --bind-host 0.0.0.0 --udp-port 12351 --http-host 127.0.0.1 --http-port 8021
   ```

3. Make the adapter HTTP port visible to Quest over USB:

   ```powershell
   adb reverse tcp:8021 tcp:8021
   ```

4. Use or generate a replay record whose body-sim pointer is the live endpoint:

   ```json
   {
     "playback": { "motion_source": "mocopi" },
     "source": { "tracking": "mocopi" },
     "motion_provenance": { "primary_source": "mocopi" },
     "deposition": {
       "body_sim_path": "http://127.0.0.1:8021/body-sim/latest"
     }
   }
   ```

5. Load Quest viewer with the replay and archive autoplay:

   ```text
   http://127.0.0.1:5173/viewer/quest-iw-demo/?replay=<REPLAY_JSON_URL>&autoplayReplay=1&qaReplay=1
   ```

Expected result:

- `route.replayMotionDiagnostic.token` becomes `MOCOPI <n>f` once the adapter has received valid frames.
- Top-level `replayMotion.token` mirrors the same diagnostic.
- If the adapter has not received frames, Quest falls back through the existing body-sim unavailable path and the result is DEMO/BODY/static rather than a hard crash.

Important limitation:

- `http://127.0.0.1:8021` from the headset only reaches the PC when `adb reverse tcp:8021 tcp:8021` is active. Without USB reverse, use the PC LAN IP and bind the adapter HTTP host accordingly.
- mocopi app setup must use the PC IPv4 address, UDP port `12351` unless changed, and transmission format `mocopi (UDP)`. `localhost`/IPv6 are not valid mocopi app destinations.

## Safer dashboard-owned path for parent implementation

This is the recommended code change for the parent lane because Quest already depends on the dashboard port for the rest of the rehearsal stack.

Add a read-only dashboard proxy:

- `GET /api/mocopi/body-sim/latest`
- It forwards or mirrors the latest body-sim from `tools/serve_mocopi_body_sim_latest.py`.
- It returns the same JSON body shape as the adapter endpoint.
- It returns `404` with a JSON error before the first valid mocopi packet.
- It returns `Cache-Control: no-store`.
- It does not retain raw UDP payloads.

Then point replay records at:

```json
{
  "deposition": {
    "body_sim_path": "http://127.0.0.1:8010/api/mocopi/body-sim/latest"
  }
}
```

Why this lane is safer:

- Existing Quest USB setup commonly already includes the dashboard/API reverse port.
- It avoids adding a second Quest-facing HTTP port when show-floor recovery is tense.
- The dashboard can report one combined status page: Quest debug, adapter health, and latest mocopi body-sim availability.

Parent-side minimal code sketch:

1. Add a small `run_load_mocopi_body_sim_latest(root, adapter_url=...)` helper in dashboard API ownership.
2. In `DashboardHandler.do_GET`, handle `parsed.path == "/api/mocopi/body-sim/latest"` before static serving.
3. On success, proxy the adapter JSON as-is.
4. On connection refused, timeout, or adapter `404`, return JSON `{ "ok": false, "error": "...", "fallback": "BODY_OR_STATIC" }` with HTTP `404` or `503`.
5. Add tests that the endpoint preserves `motion_source`, `frames`, `contract_version`, `Cache-Control: no-store`, and does not expose raw UDP payloads.

## Optional Quest JS convenience

Quest JS does not need a structural motion-loader change for the replay-pointer lane. A convenience-only change could add a query parameter such as:

```text
?bodySimLatest=http://127.0.0.1:8010/api/mocopi/body-sim/latest
```

The parent implementation would override `replay.deposition.body_sim_path` before `applyReplay`. This is operationally nicer because the operator does not need to mint a special replay JSON, but it is not required for the first live test.

## Tests to keep this bridge stable

- Adapter endpoint test: `tests/test_serve_mocopi_body_sim_latest.py`.
- Quest loader contract test: verify `normalizePath` preserves `http(s)`, `loadJson` uses `cache: "no-store"`, and `loadBodySimRecord` reads `replay.deposition.body_sim_path`.
- Motion diagnostic test: verify `replayMotionSourceFromRecord` still reads `bodySim.motion_source` and `bodySim.metadata.motion_source`.
- Dashboard bridge test after parent implementation: verify `GET /api/mocopi/body-sim/latest` returns the adapter body-sim shape and fallback JSON when the adapter is unavailable.

## GO / DEMO / NO-GO interpretation

- GO: adapter receives valid mocopi frames, Quest can fetch `body-sim/latest`, Quest debug shows `MOCOPI <n>f`, and median operator-observed motion latency is acceptable for the exhibit.
- DEMO: adapter or Quest fetch fails, but existing BODY/static fallback renders and Quest debug evidence captures the fallback token.
- NO-GO: fallback also fails, Quest cannot load the viewer/replay, or debug capture cannot prove the route state.

## Implemented Cut - 2026-05-05

- Quest viewer now accepts `mocopiLive=1`, `liveBodySim=1`, `bodySimLive=1`, `bodySimLatest=...`, or `mocopiLatest=...`.
- Default live endpoint is `http://localhost:8021/body-sim/latest`, matching USB `adb reverse tcp:8021 tcp:8021`.
- Quest polls `body-sim/latest` at a bounded interval (`LIVE_BODY_SIM_DEFAULT_POLL_INTERVAL_MS`, overridable with `mocopiPollMs`) and updates `this.frames` without replacing the existing BODY/static fallback path.
- Quest debug snapshots now include `liveBodySim.enabled`, `latestPath`, `pollCount`, `frameCount`, `lastOkAgeMs`, `stale`, and `lastError`.
- `tools/start_quest_adb_reverse.ps1` now reverses the mocopi body-sim HTTP port in addition to Quest Vite and API ports.
- `tools/start_exhibition_local_stack.ps1 -EnableMocopiBodySim` starts `tools/serve_mocopi_body_sim_latest.py`, appends the live query params to the Quest URL, and passes the mocopi port to ADB reverse.
- `tools/serve_mocopi_body_sim_latest.py` now parses the official Sony mocopi Motion Serializer/MMF binary envelope, so real `mocopi (UDP)` packets no longer fail as non-UTF-8 JSON.
- Current adapter health states to distinguish:
  - `packet_count=0`: app is not currently sending to this PC/port.
  - `packet_count>0`, `valid_packet_count=0`: transport reaches PC but parser/format is rejected.
  - `valid_packet_count>0` and `/body-sim/latest` returns `motion_source=mocopi`: ready for Quest QA.

## Live Tracking Fix - 2026-05-05

Operator report: Quest received particles and mocopi appeared connected, but armor did not visibly follow the wearer.

Root cause:

- The adapter was parsing Sony mocopi MMF `tran` records but only used the position fields.
- In real mocopi streaming, those bone positions can remain effectively static while the actual pose is carried by rotation quaternions.
- As a result, `/body-sim/latest` refreshed every packet but emitted near-identical segment transforms, so Quest looked frozen.

Current fix:

- `tools/serve_mocopi_body_sim_latest.py` now uses the official bone ids from the Sony Unity receiver mapping:
  - arms: shoulder / upper arm / lower arm chains
  - legs: hips / upper leg / lower leg chains
- The adapter composes the parsed quaternions and reconstructs normalized shoulder-elbow-wrist and hip-knee-ankle points before calling the existing body-sim path.
- `/body-sim/latest` still preserves the existing privacy rule: raw UDP bytes are not retained.
- Freshness metadata is now attached to live responses:
  - `adapter_packet_age_ms`
  - `adapter_stale`
  - `adapter_stale_after_ms`
- Regression test: fixed-position MMF packets with different right-arm quaternions must produce different `right_upperarm` / `right_forearm` body-sim transforms.

Remaining caveat:

- This is still a pragmatic exhibition retargeter, not a full humanoid solver.
- If the Quest page shows `MOCOPI` frames but the motion feels weak, the next tuning point is rotation amplification/calibration per limb, not transport.

## Live Quest Projection Tune - 2026-05-05

Operator report: mocopi packets were reflected in Quest, but the suit lagged, sat upper-left from the wearer, and appeared front/back reversed.

Immediate fix:

- Quest live mocopi rendering now uses a dedicated render profile instead of reusing archived/replay body-sim placement.
- Default polling was lowered from 250 ms to 90 ms, with URL tuning through `mocopiPollMs` / `bodySimPollMs`.
- Live mocopi placement no longer subtracts the replay-oriented `0.55` x offset. The default y/z offsets are lowered so the generated body plane lands closer to the headset-centered suit area.
- Live mocopi no longer applies the 2D `rotation_z` segment angle as the whole armor front/back rotation. That value is a bone-line angle, not a reliable horizontal yaw.
- URL-tunable live projection parameters:
  - `mocopiX`, `mocopiY`, `mocopiZ`
  - `mocopiXSign`, `mocopiYSign`, `mocopiZSign`
  - `mocopiScale`
  - `mocopiYawDeg`
- Quest debug snapshots now include `liveBodySim.pollIntervalMs`, `liveBodySim.renderProfile`, and live calibration metadata.
- The XR wrist menu now has a `補正` action. It reads the latest `chest_core` segment and aligns the armor root so the chest part lands on the Quest human chest anchor.

Current QA baseline:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&mocopiLive=1&bodySimLatest=http%3A%2F%2Flocalhost%3A8021%2Fbody-sim%2Flatest&autoplayReplay=1&qaReplay=1&qa=1&debug=1&mocopiPollMs=60&mocopiYawDeg=0&mocopiX=0.05&mocopiY=-0.76&mocopiZ=-0.20
```

Operator QA flow:

1. Stand upright and face the Quest forward direction.
2. Start mocopi UDP and confirm Quest debug shows fresh `MOCOPI` frames.
3. Open the XR wrist menu and press `補正`.
4. If left/right is mirrored after calibration, test `mocopiXSign=-1`. If the whole suit still sits high/low, adjust `mocopiY` in 0.08 steps.

Operator URL shape:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&mocopiLive=1&bodySimLatest=http%3A%2F%2Flocalhost%3A8021%2Fbody-sim%2Flatest&autoplayReplay=1&qaReplay=1
```

## Official References Checked

- Sony mocopi technical specification: IPv4, UDP, default app port `12351`, local-network/no-encryption cautions, and 27-bone skeleton.
- Sony mocopi Receiver Plugin "Sending Data from a mocopi App": Motion Send flow and selecting `mocopi (UDP)` as the transmission format.
- Sony mocopi SDK download page: the official open-source Motion Serializer and Receiver Plugin repositories.
- `sony/mocopi-motion-serializer`: the MMF serializer/deserializer box model and API names used by the adapter.
- `sony/mocopi-receiver-plugin-unity`: reference path from UDP bytes through `IsMmfBytes`, `ConvertBytesToFrameData`, and avatar bone mapping.
