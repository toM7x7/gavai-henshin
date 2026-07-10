# Quest Operator Recheck Shortlist - 2026-05-04

Purpose: Short physical Quest recheck list for operators. Do not judge from photos alone; record URL, code, voice mode, progress, right-hand device color, and telemetry together.

Scope: docs only. Code, tests, and assets are not changed.

Source: `docs/quest-photo-feedback-2026-05-04.md`, `docs/quest-usb-adb-reverse-checklist-2026-05-04.md`

## Exhibition PC Standard Flow

Use this section first on the exhibition PC or any external PC. The canonical non-debug Quest URL for code `3601` is:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

Expected terminal layout:

| Terminal | Keep open | Purpose |
| --- | --- | --- |
| A | yes | Web/API on `8010` via `npm run dev` or the release run command. |
| B | yes | Quest Vite on `5173` via `npm run dev:quest -- --port 5173`. |
| C | interactive | ADB reverse, Quest Browser launch, telemetry, screenshots, logs. |

Do not move to visual QA until A and B are still running and C confirms both reverse ports.

Operator order:

1. Put on the Quest or otherwise keep the proximity/display state ON.
2. Confirm USB/ADB is ready:

```powershell
adb devices -l
```

Expected state is `<serial>    device ...`. If the state is `unauthorized`, stop and allow USB debugging inside the headset. If no device appears, stop and fix USB/cable/Developer Mode before checking browser or code behavior.

3. From the repo root, run the helper:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

Expected:

- reverse is active for `Quest localhost:5173 -> PC localhost:5173`
- reverse is active for `Quest localhost:8010 -> PC localhost:8010`
- Quest Browser receives a URL under `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&t=...`

4. Confirm the reverse list:

```powershell
adb reverse --list
```

Required lines:

```text
tcp:5173 tcp:5173
tcp:8010 tcp:8010
```

5. In the headset, confirm Quest Browser actually shows code `3601` and not an old tab. ADB launch is only a navigation helper; it does not prove the display is awake, VR was entered, or the current tab accepted the new URL.
6. Enter VR/session from inside the headset.
7. If centerline or placement QA is needed, relaunch with the centerline lane:

```powershell
.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&liveBody=1" -RecallCode 3601 -CacheBust -LaunchBrowser
```

Then enter VR/session again and inspect `centerlineQa`.

8. Pull the latest telemetry:

```powershell
$latest = Invoke-RestMethod http://localhost:8010/api/quest-debug/latest
$p = $latest.record.payload
$p.query.href
$p.query.userAgent
$p.query.code
$p.xr.session
$p.uxState
$p.centerlineQa.displayLine
```

Minimum acceptance for physical Quest evidence:

- `query.href` starts with `http://localhost:5173/viewer/quest-iw-demo/`
- `query.href` includes `code=3601`
- `query.href` includes the latest cache-busting `t=...` from the helper run
- `query.userAgent` is Quest/Oculus Browser, not PC Playwright/browser
- `xr.session=true` after entering VR
- `uxState` is recorded before making a visual judgment
- if using `qa=centerline`, `centerlineQa.verdict` and `centerlineQa.classification` are recorded

## Exhibition Failure Split

Use this order. Do not jump to GLB/fit diagnosis until transport, URL freshness, Quest-origin telemetry, and XR session are pinned.

| Symptom | First check | Likely class | Immediate action |
| --- | --- | --- | --- |
| `adb` not found | `adb version` | PC setup | Install/fix Platform Tools or MQDH ADB path, reopen PowerShell. |
| `unauthorized` | `adb devices -l` | USB auth | Put on headset, allow USB debugging, rerun helper. |
| no device/offline | `adb devices -l` | USB transport | Wake headset, replug USB, try cable/port, restart ADB. |
| Browser cannot load `localhost:5173` | Terminal B and `adb reverse --list` | Quest viewer/reverse | Restart `5173`, rerun helper, close stale Browser tab. |
| Page loads but suit/API data missing | Terminal A and `tcp:8010` reverse | API/reverse | Restart `8010`, rerun helper, reload current timestamp URL. |
| `/api/quest-debug/latest` is 404 | URL lacks `debug=1`/`qa=...` or API reverse broken | telemetry path | Use centerline lane or debug lane, confirm `8010`, reload Quest tab. |
| telemetry `href` lacks latest `t=...` | `$p.query.href` | stale tab | Close old tab, rerun helper with `-CacheBust -LaunchBrowser`. |
| telemetry `userAgent` is not Quest/Oculus | `$p.query.userAgent` | wrong evidence source | Discard PC-side evidence; relaunch Quest Browser. |
| `xr.session=false` | `$p.xr.session` | not in VR/session | Put on headset, enter VR/session, then pull telemetry again. |
| `uxState=armor_stand_observer_idle` | `$p.uxState` | observer/stand lane | Do not accept as mirror transform; switch to mirror/replay. |
| `centerlineQa.classification=runtime_anchor` | `$p.centerlineQa` | anchor/rig | Recenter/re-enter VR/relaunch timestamp URL; do not tune parts. |
| `centerlineQa.classification=hard_sync_centerline` | `$p.centerlineQa` | Quest body/head sync | Save telemetry and photos; report centerline sync issue. |
| `centerlineQa.classification=part_anchor_runtime_offset` | `$p.centerlineQa.checks.partAnchorRuntimeOffset.parts` | runtime placement/part anchor | Save listed parts and offsets; route to runtime placement owner. |
| `centerlineQa.classification=glb_origin_bounds` | `$p.centerlineQa.checks.glbOriginBounds.parts` | GLB origin/bounds | Save listed parts; route to modeler/asset owner. |
| `centerlineQa.classification=mixed` | `$p.centerlineQa.flags` | multiple | If `runtime_anchor` is included, fix anchor first and retest. |

## Log Capture Pack

When a pass/fail decision matters, save a local log pack before changing tabs, restarting servers, or re-running the helper.

Standard one-shot capture:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

If the headset display is asleep or screenshots are not needed, omit `-Screencap`:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

The script writes:

```text
qa\logs\quest-3601-<timestamp>\
  adb-devices.txt
  adb-reverse.txt
  quest-debug-latest.json
  operator-summary.txt
  screencap.png  # only with -Screencap
```

Manual equivalent, only if the helper script cannot be used:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logRoot = "qa\logs\quest-3601-$stamp"
New-Item -ItemType Directory -Force $logRoot | Out-Null

adb devices -l | Tee-Object "$logRoot\adb-devices.txt"
adb reverse --list | Tee-Object "$logRoot\adb-reverse.txt"

$latest = Invoke-RestMethod http://localhost:8010/api/quest-debug/latest
$latest | ConvertTo-Json -Depth 24 | Set-Content -Encoding UTF8 "$logRoot\quest-debug-latest.json"

cmd /c "adb exec-out screencap -p > qa\logs\quest-3601-$stamp\screencap.png"
```

Record in the operator note:

```text
logRoot:
helper command:
Quest URL in telemetry:
Quest userAgent:
xr.session:
uxState:
centerlineQa.verdict/classification/displayLine:
visible symptom:
action taken after log capture:
```

Do not commit raw `qa\logs\**` by default. If a log must become handoff evidence, promote only the small JSON summary or named screenshot to a curated docs/QA location.

## 0. First Gate

- Confirm the Quest Browser URL includes `code=3601` and the latest cache-busting `t=...` value.
- Wear the Quest or otherwise confirm the headset display is ON. Do not make the final call from ADB screenshot alone.
- Even if armor is visible, do not count it as transformation success while the headset is still in `observer` / armor-stand preview.
- When using `/api/quest-debug/latest`, confirm `record.payload.query.userAgent` is from Quest/Oculus Browser. Do not treat a PC Playwright snapshot as physical Quest evidence.

## 1. Debug URL vs Real Mic URL

### Debug / Recovery URL

Use this when checking rendering, replay flow, mode state, and telemetry without real voice input:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&mockTrigger=1&mic=0&debug=1&t=YYYYMMDD-HHMM
```

- `mockTrigger=1`: real speech is bypassed by a fake trigger.
- `mic=0`: microphone capture is intentionally disabled.
- Expected voice evidence: mock trigger only. This URL cannot prove real mic permission, real capture, or real speech recognition.
- Expected right-hand color path on success: `green -> cyan` or similarly skipped intermediate voice states.

### Real Mic URL

Use this when validating Quest Browser microphone permission and real voice recognition:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&debug=1&t=YYYYMMDD-HHMM
```

- Do not include `mockTrigger=1`.
- Do not include `mic=0`.
- If Quest Browser asks for microphone permission, allow it.
- Expected right-hand color path on success: `green -> orange -> purple -> cyan`.
- If the mic does not work, record whether the URL is `localhost` over ADB reverse, LAN HTTP, or HTTPS. The origin can affect permission behavior.

## 2. Return From Armor Stand To Mirror Replay

If the headset shows a standing suit, inspection pose, or static armor instead of mirror transformation, first assume it may be in armor-stand / observer preview.

Fields that indicate stand/observer state:

```text
viewMode=observer
armorStandPreview=true
playing=false
progress=0
```

Recheck operation:

1. Confirm the current headset label and URL before touching controls.
2. Use the wrist/menu view control to switch to `mirror` / replay view.
3. Trigger replay or transformation again.
4. Confirm either `playing=true` or `progress>0`.
5. Take the acceptance photo only after mirror/replay is visible, not while still in stand preview.

OK:

- `viewMode` is mirror/replay equivalent.
- Mirror target is visible enough for operator confirmation.
- Replay or transformation progress is advancing or completed.
- Armor reads as attached to the replay/body pose, not only as a freestanding suit.

NG:

- Only armor stand is visible.
- `progress=0` remains unchanged.
- `armorStandPreview=true` remains after attempting to switch.
- Mirror is absent or cannot be used for visitor/operator confirmation.

## 3. Right-Hand Device Color Contract

Use the right-hand device as a compact status indicator. Record the observed sequence, not only the final color.

| Color | Meaning | Operator note |
| --- | --- | --- |
| green | ready / arming | Waiting for trigger or ready to start. |
| orange | recording / speak now | Real mic capture is active; speak now. |
| purple | analyzing / recognizing | Recognition is processing; wait briefly. |
| cyan | detected / complete | Trigger detected or transformation command accepted. |
| red | rejected / error | Failure, timeout, blocked mic, or rejected phrase. |

Interpretation:

- Debug URL may jump from green to cyan because it uses mock trigger.
- Real mic pass should show the longer voice path: green, orange, purple, cyan.
- Red requires an NG report with URL, mic permission, and telemetry.

## 4. Values To Record With Photos / Telemetry

For every Quest photo or ADB screenshot, attach this minimum note:

```text
time:
operator:
helper command:
Quest URL:
cache-busting t:
code:
connection: adb reverse localhost / LAN / HTTPS
test type: debug mock / real mic
mode seen: self / mirror / observer / unknown
progress:
playing:
armorStandPreview:
uxState:
right-hand color:
mic permission: allowed / blocked / not asked / unknown
centerlineQa verdict/classification/displayLine:
visual note:
photo filename or timestamp:
```

If PC-side telemetry is available, record these values from:

```powershell
Invoke-RestMethod http://localhost:8010/api/quest-debug/latest | ConvertTo-Json -Depth 12
```

Telemetry fields:

```text
record.payload.query.href
record.payload.query.userAgent
record.payload.query.code
record.payload.xr.session
record.payload.xr.liveBodyPose
record.payload.xr.viewMode
record.payload.route.playing
record.payload.route.progress
record.payload.route.armorStandPreview
record.payload.uxState
record.payload.centerlineQa.verdict
record.payload.centerlineQa.classification
record.payload.centerlineQa.displayLine
record.payload.meshes.loaded
record.payload.meshes.visibleCount
record.payload.runtimeDiagnostic
record.payload.microphone.captureEnabled
record.payload.microphone.mockTrigger
```

Expected anchors:

- `href` starts with the Quest Browser URL under `http://localhost:5173/viewer/quest-iw-demo/` when using ADB reverse.
- `query.code` is `3601`.
- `xr.session=true` after entering VR.
- Standard stable path should usually have `xr.liveBodyPose=false` unless deliberately testing `liveBody=1`.
- Before judging part size, confirm armor load is healthy: `18 loaded`, `18 GLB`, `0 fallback`, `18 placed`.

## 5. NG Report Template

Use this exact shape when the Quest pass fails. Do not over-diagnose from memory; report the observed state and the immediate actions already tried.

```text
Quest NG report - 2026-05-04

time:
operator:
helper command:
Quest URL:
cache-busting t:
code:
connection: adb reverse localhost / LAN / HTTPS
test type: debug mock / real mic
mode seen: self / mirror / observer / unknown
progress:
playing:
armorStandPreview:
uxState:
right-hand color:
mic permission: allowed / blocked / not asked / unknown
XR session: true / false / unknown
GLB counts: loaded __ / GLB __ / fallback __ / placed __
centerlineQa:
- verdict:
- classification:
- displayLine:
- top parts:

visible symptom:
- mirror absent / armor stand only / tracking drift / voice failed / wrong color / base suit issue / part size issue / stale URL / blank page

photo evidence:
- filename or timestamp:

telemetry evidence:
- latest snapshot time:
- href:
- userAgent:

immediate action already tried:
- reload / new tab / cache-busting URL / switched to mirror / restarted replay / re-granted mic / re-ran adb reverse / none

request to dev team:
- Need mode-state check / mic-origin check / mirror visibility check / tracking check / per-part fit check / stale-cache check
```

Report examples:

- `mirror absent`: include `mode seen`, `viewMode`, `progress`, `playing`, and `armorStandPreview`.
- `voice failed`: include whether the URL was debug mock or real mic, the permission prompt result, and right-hand color sequence.
- `armor stand only`: include the operation attempted to return to mirror and whether `progress` changed.
- `part size issue`: include GLB counts, mode, progress, and front/side/3Q photo angles. Do not request size tuning from stand-preview evidence alone.
