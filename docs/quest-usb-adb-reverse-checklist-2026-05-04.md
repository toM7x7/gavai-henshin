# Quest USB/ADB reverse checklist

Date: 2026-05-04  
Use case: exhibition operator check for Quest Browser access to the current Quest IW demo through USB ADB reverse.

## Goal

Open this URL in Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

This requires ADB reverse for both ports:

- `5173`: Quest Vite viewer
- `8010`: dashboard/API used by the viewer

## Current verified state - 2026-05-04

USB/ADB path is confirmed up to Quest Browser launch:

- `adb devices -l` showed `Quest_3 ... device`.
- `.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&code=3601"` completed successfully.
- `adb reverse --list` showed both `tcp:5173` and `tcp:8010`.
- `adb shell am start ... http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601` succeeded and sent the Intent to Oculus Browser.
- Quest Browser retained `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601`.
- `debug=1` URL produced `/api/quest-debug/latest` from Quest 3 / Oculus Browser for code `3601`.
- Latest confirmed Quest snapshot was still pre-XR with `record.payload.xr.session=false`; XR/mirror placement must be checked after entering VR.
- Current blocker seen in USB recovery: the headset can be `Asleep`; in that state `adb exec-out screencap -p` may produce an empty/black capture.
- Windows PowerShell redirection can corrupt binary PNG output from `adb exec-out`. Use `cmd /c "adb exec-out screencap -p > ..."` for Quest screenshots.

Not yet verified inside the headset after entering VR: equipment-complete state, audio, record/replay, mirror, and final armor placement.

## 1. Start the PC services

From the repo root:

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev
```

In a second PowerShell:

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev:quest
```

Expected:

- dashboard/API is available on PC port `8010`
- Quest viewer is available on PC port `5173`

## 2. Connect Quest by USB

1. Put the Quest on or keep it awake.
2. Connect USB from Quest to the PC.
3. In PowerShell, run:

```powershell
adb devices
```

If ready, the output contains:

```text
<serial>    device
```

If blocked, the output contains:

```text
<serial>    unauthorized
```

## 3. If `adb devices` says `unauthorized`

1. Put on the Quest headset.
2. Look for the USB debugging prompt.
3. Select the checkbox like "Always allow from this computer" if shown.
4. Press `Allow`.
5. Run again on PC:

```powershell
adb devices
```

Continue only when the Quest shows as `device`, not `unauthorized`.

If no prompt appears, unplug/replug USB, wake/unlock the headset, and try `adb devices` again.

## 4. Apply ADB reverse

From the repo root:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

Expected script output includes:

```text
ADB reverse is active:
  Quest localhost:5173 -> PC localhost:5173
  Quest localhost:8010 -> PC localhost:8010

Open this in Quest Browser:
  http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&t=...
```

Manual equivalent if needed:

```powershell
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010
```

Centerline QA lane for placement/anchor diagnosis:

```powershell
.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&liveBody=1" -RecallCode 3601 -CacheBust -LaunchBrowser
```

This opens a URL under:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&liveBody=1&code=3601&t=...
```

Use this lane for `centerlineQa` and anchor/GLB-origin diagnosis. Do not use it as real voice evidence.

Fast wake/reopen/reverse confirmation when the PC services are already running:

```powershell
adb devices
adb shell input keyevent KEYCODE_WAKEUP
adb reverse tcp:5173 tcp:5173
adb reverse tcp:8010 tcp:8010
adb reverse --list
adb shell am start -a android.intent.action.VIEW -d "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601"
```

Important: `KEYCODE_WAKEUP` only asks Android to wake. For reliable visual verification, put on the Quest or otherwise keep the proximity/display state ON before taking a screenshot.

## 5. Open in Quest Browser

For a normal load smoke, open exactly:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

Check:

- the page loads from `localhost:5173`
- the route includes `newRoute=1`
- the active code is `3601`
- the demo can reach API/dashboard data through reversed `localhost:8010`

Before judging the photo or voice behavior, choose the correct URL lane:

| Lane | URL flags | What it can prove | What it cannot prove |
| --- | --- | --- | --- |
| Debug/recovery rendering | `replayView=mirror&mockTrigger=1&mic=0&debug=1&t=...` | Quest-origin telemetry, `uxState`, mirror/observer/stand transitions, replay rendering | Real microphone capture or real speech recognition |
| Exhibition real voice | `replayView=mirror&debug=1&t=...` with no `mockTrigger=1` and no `mic=0` | Real mic permission, capture, voice-state transitions, and visitor voice path | Fast recovery from voice-disabled diagnostics |

Do not mix the two lanes in the operator report. If the URL contains
`mockTrigger=1&mic=0`, mark voice as "not tested" even if replay succeeds.

## 5a. Fast headset recovery when the display is broken

Assumption: `adb reverse` already succeeded and `adb reverse --list` still includes `tcp:5173` and `tcp:8010`.

Use a cache-busting URL first, so the headset does not keep an old Quest Browser bundle or stale route state:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&qa=quest-recovery&debug=1&t=20260504-REPLACE
```

Replace `t=20260504-REPLACE` with the current timestamp, for example `t=20260504-1530`.

Shortest recovery path:

1. Put on the Quest and keep the display awake.
2. If the page is visible, press browser reload once.
3. If the broken state remains, paste/open the cache-busting URL above.
4. If still broken, close the current Quest Browser tab, open a new tab, and enter the same cache-busting URL.
5. If WebXR/VR was already entered, exit VR back to the browser page, reload or reopen the cache-busting URL, then press the VR/session start control again.
6. If the browser still appears stale, force a fresh Intent from PC:

```powershell
adb shell am start -a android.intent.action.VIEW -d "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&qa=quest-recovery&debug=1&t=20260504-REPLACE"
```

If screenshots cannot be captured, report these text observations from inside the headset instead:

- Exact URL shown in Quest Browser, including `code=3601` and the cache-busting `t=...` value.
- Whether the page shows active code `3601` or a different/blank code.
- Whether there is a visible loading/error message, blank canvas, frozen old frame, or layout collapse.
- Whether reload changes the timestamped page state.
- Whether exiting VR and starting VR again changes the broken display.
- Whether `adb reverse --list` on PC still shows both `tcp:5173` and `tcp:8010`.

## 5b. PC-side Quest debug telemetry

When the Quest URL includes `debug=1` or `qa=...`, the Quest viewer posts a throttled runtime snapshot to the dashboard API. This is the fallback when remote DevTools or usable screenshots are unavailable.

Open the Quest with the debug/recovery rendering URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&mockTrigger=1&mic=0&debug=1&t=20260504-REPLACE
```

This URL intentionally disables real voice. It is the right lane for mode,
mirror, replay, and telemetry recovery. It is the wrong lane for exhibition voice
acceptance.

Then inspect the latest snapshot on the PC:

```powershell
Invoke-RestMethod http://localhost:8010/api/quest-debug/latest | ConvertTo-Json -Depth 12
```

当日ログを一発で残す場合:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

`-Screencap` はQuest表示がONの時だけ使う。表示が寝ている、またはUSB screenshotが不要な時は外す:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

保存先は `qa\logs\quest-3601-<timestamp>\`。中身は `adb-devices.txt`, `adb-reverse.txt`, `quest-debug-latest.json`, `operator-summary.txt` と、`-Screencap` 使用時の `screencap.png`。

Expected for the current safe Quest path:

- `record.payload.query.code` is `3601`.
- `record.payload.query.href` starts with `http://localhost:5173/viewer/quest-iw-demo/`.
- `record.payload.query.userAgent` includes Quest/Oculus Browser. If `href` starts with `http://127.0.0.1:5173/...alignmentProbe...`, the snapshot came from PC-side Playwright replay, not the Quest headset.
- Read `record.payload.uxState` before `record.payload.route.voiceState`.
- `voiceState=complete` must not be treated as the current UX state by itself.
- If `record.payload.uxState=armor_stand_observer_idle`, the headset is in
  armor-stand / observer standby, not mirror replay. Switch to mirror replay
  before accepting mirror evidence.
- The target for mirror replay acceptance is
  `record.payload.uxState=archive_replay_mirror_active`.
- Supporting mirror replay fields should be:
  `record.payload.xr.viewMode=mirror`,
  `record.payload.route.playbackSource=archive`,
  `record.payload.route.playing=true`,
  `record.payload.route.armorStandPreview=false`, and
  `record.payload.route.progress>0`.
- For this debug/recovery URL, `record.payload.realMicrophoneExpected` should be
  `false` or absent by design; do not use it as real voice evidence.
- `record.payload.xr.liveBodyPose` is `false` unless deliberately testing `liveBody=1`.
- `record.payload.xr.session` becomes `true` after entering VR.
- `record.payload.baseShell.visible` is `false` inside XR, so the base capsule/sphere body shell should not block the mirror.
- `record.payload.depositionEffects.visible` is `false` in Quest XR mirror view, so the蒸着particle field should not sit in front of the mirror.
- `record.payload.meshes.loaded` is the number of loaded armor parts, and `record.payload.meshes.visibleCount` rises during transform/replay.
- `record.payload.runtimeDiagnostic` includes `RUNTIME DIAGNOSTIC`, placement counts, GLB/fallback counts, and missing-part status.

If `/api/quest-debug/latest` returns `404`, either the Quest page has not loaded the debug URL yet, `debug=1`/`qa=...` is missing, or the `8010` reverse/API path is broken.

If ADB reports `mWakefulness=Asleep` or Browser windows show `NO_SURFACE`, telemetry can be stale and screenshots can be empty. Put on the headset, keep the display ON, reload the debug URL, then enter VR again.

## 5c. Exhibition real voice telemetry

Use this lane only when validating the public voice path. Open the Quest with no
mock trigger and no mic disable flag:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&debug=1&t=20260504-REPLACE
```

Expected order:

1. Put on the Quest and keep the display awake.
2. Grant microphone permission if Quest Browser asks.
3. Enter VR.
4. Press/start the voice flow.
5. Speak the target phrase when the UI/device indicates recording.
6. Inspect `/api/quest-debug/latest`.

Expected telemetry:

- `record.payload.query.href` does not include `mockTrigger=1`.
- `record.payload.query.href` does not include `mic=0`.
- `record.payload.realMicrophoneExpected=true`.
- Microphone capture becomes enabled during the voice flow.
- `voiceState` moves through recording/analyzing/detected on success, or ends in
  `rejected` with a reason.
- After a successful voice-triggered transform or replay confirmation, use
  `uxState` to judge the current scene. `voiceState=complete` still does not
  prove the current mode.

Real voice acceptance is NG if:

- the URL contains `mockTrigger=1`;
- the URL contains `mic=0`;
- `realMicrophoneExpected` is missing or false;
- the report has no Quest Browser telemetry;
- only `voiceState=complete` is provided without `uxState` and scene fields.

## 6. Take a reliable Quest screenshot over USB

Use this only after `adb devices` shows `device` and the headset display is visibly ON.

1. Put on the headset and confirm the Quest Browser page is visible. If the headset is `Asleep`, the screencap can be empty even when ADB is connected.
2. Keep the display awake, then run from the repo root:

```powershell
New-Item -ItemType Directory -Force tests\.tmp | Out-Null
cmd /c "adb exec-out screencap -p > tests\.tmp\gavai-quest-3601.png"
Get-Item tests\.tmp\gavai-quest-3601.png
```

Do not use this PowerShell form for binary screenshot output:

```powershell
adb exec-out screencap -p > tests\.tmp\gavai-quest-3601.png
```

That can write a corrupted PNG through PowerShell's output pipeline. If the file is `0` bytes, tiny, black, or unreadable, first assume the Quest display slept or the PNG was redirected through PowerShell. Put the headset on, confirm the display is ON, and retake with the `cmd /c` command above.

Optional helper script idea only, if this becomes repetitive:

```powershell
# tools/capture_quest_screenshot.cmd
@echo off
if "%~1"=="" (
  echo Usage: capture_quest_screenshot.cmd output.png
  exit /b 2
)
adb exec-out screencap -p > "%~1"
```

## 7. One-page Quest in-headset check

Use this after the ADB/Intent launch has succeeded. Mark only what is actually seen in the headset.

Check in this order:

1. URL lane: debug/recovery rendering or exhibition real voice.
2. Quest-origin telemetry: `href` and `userAgent` must come from Quest Browser.
3. `uxState`: classify the current scene before reading `voiceState`.
4. Mirror target: accept mirror only when
   `uxState=archive_replay_mirror_active`.
5. Armor stand: if `uxState=armor_stand_observer_idle`, mark "not mirror";
   switch to mirror replay before judging transformation visuals.
6. Voice: accept real voice only when `realMicrophoneExpected=true` and the URL
   has no `mockTrigger=1` or `mic=0`.
7. Visual fit: judge armor/base-suit/part size only after the correct lane and
   `uxState` are pinned.

| Check | Expected for code `3601` | Status |
| --- | --- | --- |
| Code recall | Quest UI shows active code `3601` and recalled suit data, not a stale/blank run. | UNVERIFIED |
| URL lane | Operator marks debug/recovery rendering or exhibition real voice. Debug URL with `mockTrigger=1&mic=0` is not voice evidence. | UNVERIFIED |
| Quest telemetry source | `/api/quest-debug/latest` comes from Quest/Oculus Browser, not PC Playwright. | UNVERIFIED |
| Current UX state | `uxState` is recorded. `voiceState=complete` is not treated as current state by itself. | UNVERIFIED |
| Armor stand state | If `uxState=armor_stand_observer_idle`, this is observer/standby, not mirror. | UNVERIFIED |
| Mirror replay target | Mirror acceptance targets `uxState=archive_replay_mirror_active`, `xr.viewMode=mirror`, `playing=true`, `progress>0`, and `armorStandPreview=false`. | UNVERIFIED |
| Real voice target | Real voice acceptance targets `realMicrophoneExpected=true`, no mock URL flags, and microphone capture enabled during the voice flow. | UNVERIFIED |
| Equipment complete | Equipment/ready/completion state reaches the operator-ready condition. | UNVERIFIED |
| VR start | VR/session start control enters the intended immersive demo flow. | UNVERIFIED |
| Audio | Demo audio or voice cue is audible in the Quest. | UNVERIFIED |
| Record/replay | Recording starts/stops and replay playback can be triggered. | UNVERIFIED |
| Mirror | Mirror/reflection view appears and is usable for operator/visitor confirmation. | UNVERIFIED |
| Armor position | Helmet, chest, waist, limbs, hands, boots stay attached with no obvious float, scale error, or severe offset. | UNVERIFIED |

If any item fails, record the visible code, URL lane, `uxState`, `voiceState`,
headset state, and whether ports `5173`/`8010` still appear in
`adb reverse --list`.

## Quick failure triage

### `adb` command is not found

Android Platform Tools or Meta Quest Developer Hub ADB is not on `PATH`. Open a new PowerShell after installing/fixing `PATH`, then run:

```powershell
adb version
```

### `adb devices` shows `unauthorized`

The PC is connected but the headset has not authorized USB debugging. Accept the prompt inside the Quest, then re-run:

```powershell
adb devices
```

### `adb devices` shows no device

Wake the headset, reconnect USB, try another cable/port, confirm Quest Developer Mode is enabled, then run:

```powershell
adb devices
```

### Reverse script says no device is ready

Do not debug the browser yet. First make `adb devices` show:

```text
<serial>    device
```

Then re-run:

```powershell
.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&code=3601"
```

### Quest Browser cannot open `localhost:5173`

Check in order:

1. `npm run dev:quest` is still running.
2. `adb devices` shows `device`.
3. `adb reverse --list` includes `tcp:5173 tcp:5173`.
4. Re-run the reverse script.
5. Close and reopen the Quest Browser tab.

### Page loads but API/data fails

Check in order:

1. `npm run dev` is still running for port `8010`.
2. `adb reverse --list` includes `tcp:8010 tcp:8010`.
3. Re-run the reverse script.
4. Reload the Quest Browser page.

### Wrong or stale demo appears

Close the Quest Browser tab and open the exact URL again. If stale state remains, clear the Quest Browser site data for `localhost`, then reopen:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```
