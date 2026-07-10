# Current Progress And Next Schedule - 2026-05-04

North star: Webでスーツ成立、Questで変身試験、Replayで体験を残す。

## Current Progress

- Web Forge: 4桁コード発行、身長入力、variant選択、Quest導線は動作中。
- Quest: USB ADB接続、`5173`/`8010` reverse、Quest Browserへのfull query投入、Quest 3/Oculus Browser由来のdebug telemetry受信まで確認済み。
- Quest rendering: `liveBody=1` を明示しない限り、Quest XRでは固定body poseを使う。live body推定由来の小さい浮遊パーツを標準経路から外した。
- Quest mirror: XR内の簡易base suit shellはデフォルト非表示。診断時だけ `baseSuitGuide=1` で薄く出す。蒸着particle fieldはmirror viewでも薄く残し、鏡を塞がず粒子感を維持する。
- IWSDK/diagnostic: `debug=1` または `qa=...` のとき、Quest viewerが `/api/quest-debug` にruntime snapshotをPOSTする。履歴JSONLは展示PC保護のため上限付き。
- Runtime size: local `.glb` の `asset_ref` から隣接 `.modeler.json` をruntime package側で補完し、helmet/waistなどが `0.05m` 級fallbackへ落ちる退行を防ぐ。
- Runtime sidecar safety: inline `modeler_sidecar` もcontract/coordinate frameを検証し、古い座標系メタでQuest配置を壊す経路を塞いだ。
- Replay/Web verification: recall code `3601` のWeb replay alignmentは `ok=true`。`settledMaxExcessDistanceM=0`、console/page/trigger errorなし。

## Current Quest Blocker

Quest URLはADB Intentで正しく投入済み:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&mockTrigger=1&mic=0&qa=quest-iwdiag3&debug=1&t=...
```

Quest実機由来のsnapshotは受信済み。ただしそのsnapshotはページ表示段階で `record.payload.xr.session=false`。直近のADB状態は `mWakefulness=Asleep` のため、次の実機確認ではヘッドセットを被るか表示ONを維持し、VR開始後に `record.payload.xr.session=true` のsnapshotを取る。

Quest実機由来のsnapshot条件:

- `record.payload.query.href` が `http://localhost:5173/...`。
- `record.payload.query.userAgent` にQuest/Oculus Browser系の値が出る。
- `record.payload.query.code` が `3601`。
- XR開始後に `record.payload.xr.session` が `true`。
- 標準経路では `record.payload.xr.liveBodyPose` が `false`。
- XR mirror中は標準URLなら `record.payload.baseShell.visible` が `false`。`baseSuitGuide=1` は診断用。
- XR mirror中の `record.payload.depositionEffects.visible` は変身中なら `true` になり得るが、opacityはmirror用に減衰する。

`href` が `http://127.0.0.1:5173/...alignmentProbe...` の場合、それはPC上のPlaywright/Web replay確認であり、Quest実機確認ではない。

2026-05-04 15:11 JST update:

- API `8010` PID `70832` and Quest Vite `5173` PID `98052` are still running.
- `adb reverse` is active for `tcp:5173` and `tcp:8010`.
- Fresh Quest URL was sent:
  `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&mockTrigger=1&mic=0&debug=1&qa=quest-stand-yaw-base-guide&t=...`
- Current headset power state is still `mWakefulness=Asleep` and internal display state `OFF`; Oculus Browser activities are stopped.
- Therefore the latest `/api/quest-debug/latest` is still a PC-side `alignmentProbe` record, not the fresh physical headset URL. The next physical pass requires the headset to be worn/woken and Quest Browser brought to front, then page reload/Enter VR.

## Quest Photo Feedback - 2026-05-04

Detailed record: `docs/quest-photo-feedback-2026-05-04.md`. Next physical pass must label each headset photo with mode (`mirror`/`observer`/`self`), progress, URL flags, voice mode, and GLB load counts before judging fit.

UX state review checklist: `docs/quest-ux-state-telemetry-review-2026-05-04.md`.

Operator decision order for the next physical Quest pass:

1. Confirm the URL lane first.
   - Debug/recovery rendering lane: `mockTrigger=1&mic=0&debug=1`.
   - Exhibition real voice lane: no `mockTrigger=1`, no `mic=0`, and
     telemetry should show `realMicrophoneExpected=true`.
2. Confirm the latest telemetry comes from Quest Browser:
   `record.payload.query.userAgent` must be Quest/Oculus Browser and
   `record.payload.query.href` must be the headset URL, not a PC Playwright
   probe.
3. Read `uxState` before `voiceState`.
   - `voiceState=complete` is not the current experience state by itself.
   - It can remain from a previous run after the operator enters another mode.
4. If `uxState=armor_stand_observer_idle`, the headset is not in mirror replay.
   - This is armor-stand / observer standby.
   - Do not accept that photo as mirror transformation evidence.
   - Switch to mirror replay and start replay/transform again.
5. Target state for mirror visual acceptance:
   `uxState=archive_replay_mirror_active`.
   - Expected supporting fields: `xr.viewMode=mirror`,
     `playbackSource=archive`, `playing=true`,
     `armorStandPreview=false`, and `progress>0`.
6. Target state for real voice acceptance:
   `realMicrophoneExpected=true`.
   - Expected supporting fields: no mock trigger URL flag, no `mic=0`,
     microphone capture enabled during the voice flow, and voice-state movement
     through recording/analyzing/detected or rejected.
7. Only after the correct lane and `uxState` are pinned, judge mirror
   visibility, base-suit guide, armor attachment, part size, and photo evidence.

Observed from headset photos and `/api/quest-debug/latest`:

- Headset is in XR, but current snapshot is `viewMode=observer`, `playing=false`, `progress=0`, `armorStandPreview=true`相当の見え方。見えているのは装着中の鏡ではなく、鎧立て/観察モード。
- Mirror can look absent because observer mode hides `mirrorFrame`; mirror/replay view needs `archiveViewMode=mirror` and replay start.
- Armor parts are larger and GLB loading is healthy: `18 loaded`, `18 GLB`, `0 fallback`, `18 placed`.
- Real voice recognition is disabled on the current debug URL because it includes `mockTrigger=1&mic=0`. Exhibition voice test should use real microphone mode, not this recovery URL.

Immediate fixes applied:

- Right-hand henshin device colors are separated: green = ready/arming, orange = recording/speak now, purple = analyzing/recognizing, cyan = detected/complete, red = rejected.
- Quest debug telemetry now reports microphone capability and whether capture is actually enabled.
- XR transform/mirror replay suppresses the old capsule-like base suit shell by default to avoid the rugby-ball obstruction. `baseSuitGuide=1` remains as a diagnostic-only opt-in.
- Mirror glass/frame opacity was raised so mirror mode has a stronger visual target.
- Replay-view button now says the next action (`次: 鏡` / `次: 観察`) and the wrist menu uses `鏡へ` / `観察へ` to reduce mode confusion.
- Armor stand P0 interaction added: right trigger rotates the stand in 30 degree steps instead of starting voice recognition while stand preview is active.
- Armor stand P0 placement adjusted: stand pose is lifted by `0.24m`, and GLB assets with `runtime-render-placement.v1` no longer receive the legacy extra X=90度 base rotation.
- Mirror particle behavior adjusted: particles are no longer fully hidden in mirror view; they are moved slightly behind the mirror body target and dimmed to keep readability.

## Verification Done

```text
node --check viewer/quest-iw-demo/quest-demo.js
python -m pytest tests/test_quest_recall_render_contract.py -q
python -m pytest tests/test_dashboard_server.py -q
npx vite build --config vite.quest.config.js --outDir tests/.tmp/quest-vite-build-20260504-stand-yaw-base-guide --emptyOutDir
node tools/verify_replay_armor_alignment.mjs --code 3601 --trigger both --samples 0.25,0.5,0.75 --output-dir tests/.tmp/replay-armor-alignment-3601-stand-yaw-base-guide --max-settled-excess-m 0.05
python -m pytest -q
```

Result:

- `315 passed, 192 subtests passed`
- Quest Vite build success
- Replay alignment `ok=true`, `settledMaxExcessDistanceM=0`, console/page/trigger errorなし

## Next Schedule

### 1. Quest実機復旧確認

Owner: Quest lane

Acceptance:

- Headset display stays ON.
- `/api/quest-debug/latest` receives Quest-origin snapshot.
- Operator records which lane was used: debug/recovery rendering URL or
  exhibition real voice URL.
- `uxState` is recorded before visual judgment.
- If `uxState=armor_stand_observer_idle`, the pass is only armor-stand evidence;
  operator switches to mirror replay before judging the mirror.
- Mirror acceptance targets `uxState=archive_replay_mirror_active`, with
  `xr.viewMode=mirror`, `playbackSource=archive`, `playing=true`,
  `armorStandPreview=false`, and `progress>0`.
- Real voice acceptance targets `realMicrophoneExpected=true`; debug recovery
  URL with `mockTrigger=1&mic=0` cannot satisfy voice acceptance.
- `voiceState=complete` is treated as a voice/trigger phase only, not proof of
  current mirror or transformation state.
- In XR mirror, rugby-ball-like particle/body aggregate no longer blocks mirror.
- Armor reads as humanoid enough to continue part-by-part fit checks.
- If still broken, compare `depositionEffects`, `baseShell`, `meshes.visibleCount`, and each part position/scale from telemetry before changing visuals again.

### 2. Per-Part 3D Fit And Strengthening

Owner: 3D/model lane

Acceptance:

- Review helmet, chest, back, waist, shoulders, upperarms, forearms, hands, thighs, shins, boots.
- Record size/position/rotation issues per part.
- Use `runtime-render-placement.v1` as the only tuning source. Do not add a second Quest-only placement table unless a part is explicitly waived.
- Add front/side/back/3q evidence for the exact demo suit.

### 3. Modeler 30 Variant Fidelity Hold

Owner: modeler lane

Acceptance:

- Keep current status as technical pass / `fidelity_hold`.
- Review each part against front/side/back basis.
- Promote only variants that show line identity from more than the front view.
- P1 limb variants remain order/intake work until strict validation and human visual review pass.

### 4. Japanese UI And Visitor Path

Owner: WebUI/QuestUI lane

Acceptance:

- Public Web Forge first screen is visitor-focused: name, height, brief/style, generate, code, Quest link, preview.
- Debug tables, raw contracts, and modeler warnings move behind operator/debug view.
- Quest happy path labels are Japanese and action-oriented.

### 5. External Exhibition PC Baseline

Owner: external-PC lane

Acceptance:

- Clean Windows PC can run API `8010` and Quest viewer `5173`.
- USB ADB reverse and same-LAN URL are both rehearsed or one is formally rejected with reason.
- Offline/local fallback works without GCP, provider secrets, or mocopi.
- One smoke order proves Web -> Quest -> Replay.

### 6. Web Service / GCP Lane

Owner: service lane

Acceptance:

- Keep current `/v1` payload semantics.
- Map local JSON/file storage to Cloud SQL/GCS without exposing `C:\...`, `file://`, dev LAN URLs, or secrets in public responses.
- Cloud Run/GCP is not a show-floor dependency until external-PC local baseline passes.

### 7. mocopi Enhancement Lane

Owner: mocopi lane

Acceptance:

- Treat mocopi as optional until real hardware receiver, calibration, latency, left/right consistency, and fallback are proven.
- Imported mocopi JSON/body-sim path is Phase 1.
- Live receiver is Phase 2.
- Failure must fall back to BODY/static within 60 seconds.

## 2026-05-04 Late Update: Quest Workshop/Input And 3601 Fit

Status:

- Web/API is running on `http://127.0.0.1:8010` with PID `98384`.
- Quest viewer is running on `http://127.0.0.1:5173` with PID `42160`.
- ADB reverse is active for `tcp:5173` and `tcp:8010`.
- Quest device `2G0YC5ZF9P05Z2` is connected, but the headset was still `mWakefulness=Asleep` during the last automated launch attempt. Final physical XR judgment still requires the headset to be worn/woken and the URL reloaded.
- A timestamped `adb shell am start` launch returned `Status: ok`, but `/api/quest-debug/latest` stayed on the previous `alignmentProbe` URL. Treat the current Quest evidence as stale until `operatorProbe` or another fresh timestamp appears in telemetry.

Implemented since the photo feedback:

- Armor-stand right trigger now prioritizes part explode/return before wrist-menu hover actions, so it no longer steals voice/replay/view buttons while inspecting the stand.
- Armor-stand right-grip free rotation now has a 3mm deadzone and per-frame movement cap to reduce tracking jitter and accidental jumps.
- Armor-stand debug telemetry now records right/left trigger and grip mapping, gamepad presence, button counts, axes counts, pressed state, and active workshop mode.
- Code `3601` runtime placement now uses blueprint canonical target envelopes for `chest:sleek`, `back:sleek`, `left_shin:sleek`, and `right_shin:sleek` instead of raw sidecar bbox dimensions. This addresses the suspected y/z size-source mismatch behind the rugby-ball/deep-flat armor impression.

Verification:

- `node --check viewer\quest-iw-demo\quest-demo.js`: pass.
- `python -m pytest tests\test_quest_recall_render_contract.py -q`: `33 passed, 131 subtests passed`.
- `npx vite build --config vite.quest.config.js --outDir tests\.tmp\quest-vite-build-20260504-workshop-input --emptyOutDir`: pass.
- `node tools\verify_replay_armor_alignment.mjs --code 3601 --trigger both --samples 0.25,0.5,0.75 --output-dir tests\.tmp\replay-armor-alignment-3601-workshop-input --max-settled-excess-m 0.05 --timeout-ms 120000`: pass, `settledMaxExcessDistanceM=0.02321`.

Next physical Quest pass:

- Open `http://127.0.0.1:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&debug=1&qa=1` inside Quest Browser after the headset is awake.
- Enter VR, select armor stand, then confirm right grip rotates freely, both grips scale, and right trigger toggles part explode/return.
- Check `/api/quest-debug/latest` and confirm `armorStand.input.rightGrip.gamepad=true` or record the mapping failure if grip controls do not work.
- Switch back to mirror/replay before judging wearing fit. Armor-stand preview is inspection evidence, not proof of body-worn alignment.

## 2026-05-04 Final Late Update: One-Rig Workshop, Exit Chord, Human Anchors

Implemented:

- Armor stand inspection now treats the armor as one humanoid rig. Right grip moves the assembled suit root, both grips scale/yaw/move the whole rig, and right trigger explodes/returns parts only when grip is not held.
- Right grip + trigger now exits armor stand before any hovered UI action can fire. This is the primary P0 recovery path when the visitor feels trapped in stand mode.
- Workshop movement is converted from controller world-space into the Quest rig's local-space offset, so the suit follows the user's intended grab direction even when observer yaw changes.
- Controller lookup no longer reuses one stale controller as both hands. Missing hand input remains missing and is visible in `armorStand.input`.
- `audit_quest_armor_whole_suit.py` now reads `QUEST_HUMAN_ANCHOR_CONTRACT.center_m` from the Quest runtime and checks left/right signs, centerline, vertical body-chain order, and chest/back front-depth meaning.

Verification:

- `node --check viewer\quest-iw-demo\quest-demo.js`: pass.
- `python -m pytest tests\test_quest_recall_render_contract.py tests\test_quest_armor_whole_suit_audit.py -q`: `42 passed, 131 subtests passed`.
- `python -m pytest -q`: `325 passed, 192 subtests passed`.
- `python tools\audit_quest_armor_whole_suit.py --compact --fail-on fail`: pass, `runtime_anchor_center_count=18`, `semantic_failures=[]`.
- `npx vite build --config vite.quest.config.js --outDir tests\.tmp\quest-vite-build-20260504-rig-exit-final --emptyOutDir`: pass.
- `node tools\verify_replay_armor_alignment.mjs --code 3601 --trigger both --samples 0.25,0.5,0.75 --output-dir tests\.tmp\replay-armor-alignment-3601-rig-exit-final --max-settled-excess-m 0.05 --timeout-ms 120000`: pass, `settledMaxExcessDistanceM=0`.
- Latest workshop truth note: `docs/quest-workshop-current-implemented-truth-2026-05-04.md`.

Next Quest operator pass:

- Wake/wear Quest and load `http://127.0.0.1:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&debug=1&qa=1`.
- Latest ADB launch attempt used `operatorProbe=1777883357527`; `adb` returned `Status: ok`, but the headset reported `mWakefulness=Asleep` and `/api/quest-debug/latest` still showed the older `alignmentProbe=1777883132226` URL. Treat this as stale telemetry, not a real physical pass.
- In armor stand: verify right grip moves the whole humanoid rig, both grips scale/yaw/move it, right trigger explodes/returns, and right grip + trigger exits within 10 seconds.
- After exit, judge wearing fit in mirror/replay, not in armor stand.
- Save `/api/quest-debug/latest` with fresh timestamp if any control fails, especially `armorStand.input.rightGrip`, `leftGrip`, `rightTrigger`, and `rightTriggerMode`.

Roadmap after this Quest foundation:

- Close `quest-foundation-pass/fail` on physical Quest telemetry and photos.
- Then run external exhibition PC `local-pass` from a clean clone and exact commit.
- Only after local external-PC baseline passes, proceed to Web service/GCP staging, PlayCanvas adapter, and mocopi enhancement as optional lanes.
