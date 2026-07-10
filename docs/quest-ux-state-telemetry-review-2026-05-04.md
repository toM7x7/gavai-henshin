# Quest UX State Telemetry Review - 2026-05-04

Status: checklist for reviewing code changes after the physical Quest photo feedback.

Scope: documentation only. Use this after implementation changes that add or adjust
`uxState`, experience-state telemetry, mirror/observer behavior, armor-stand
preview, microphone mode reporting, or debug URL operation.

Primary premise:

- A Quest headset photo can show observer / armor-stand standby while
  `voiceState=complete` remains from a previous transformation.
- Therefore `voiceState` must not be treated as the current UX state.
- The current UX state must be derived from the live scene gates:
  `uxState`, `playing`, `armorStandPreview`, `xr.viewMode`,
  `playbackSource`, `progress`, and debug URL microphone flags.

## Review Goal

The review is accepted only when both audiences can make the same call:

- Exhibition operator: "What am I seeing in the headset, and what should I do
  next?"
- Developer: "Which state did telemetry report, and is it consistent with the
  render path and URL?"

Do not approve a change that merely renames telemetry while leaving the photo
case ambiguous. The specific ambiguity to eliminate is:

```text
Photo shows: observer / armor stand / waiting
Telemetry still includes: voiceState=complete
Correct interpretation: current uxState is armor-stand observer idle; voiceState
is historical voice/trigger phase, not the current experience state.
```

## Required State Model

### 1. `uxState` Is The Current Experience

`uxState` or `experienceState` must describe what the visitor/operator is
currently experiencing. It is not a voice recognition phase.

Required classification priority:

1. `armorStandPreview=true && playing=false` wins over any `voiceState`.
2. `playing=true && playbackSource=archive` is replay, not live voice.
3. `playing=true && playbackSource!=archive` is active transformation.
4. `xr.viewMode` splits self, mirror, and observer interpretations.
5. `voiceState` is supporting evidence only after the above gates are known.

### 2. `voiceState` Is A Voice / Trigger Phase

`voiceState` may remain `complete` after a successful run. That is valid only if
telemetry and UI make it clear that `complete` does not override `uxState`.

Review rule:

- OK: `uxState=armor_stand_observer_idle` and `voiceState=complete`.
- NG: dashboards, logs, or operator instructions label the same snapshot as
  "complete transformation" only because `voiceState=complete`.

### 3. Mirror, Observer, And Armor Stand Are Distinct

The review must preserve three different meanings:

| State | What operator sees | Telemetry gates |
| --- | --- | --- |
| mirror replay | replay result for confirmation | `playing=true`, `playbackSource=archive`, `xr.viewMode=mirror` |
| observer replay | third-person replay inspection | `playing=true`, `playbackSource=archive`, `xr.viewMode=observer`, `armorStandPreview=false` |
| armor stand preview | static standing suit / staging | `playing=false`, `armorStandPreview=true`, normally `xr.viewMode=observer` |

Do not collapse observer replay and armor stand preview. They can both use an
observer camera, but only replay has active progress.

## Canonical Classification Checklist

Use these names unless implementation explicitly documents compatible aliases.

| Classification | Required condition | Operator meaning |
| --- | --- | --- |
| `no_suit_idle` | `playing=false`, `meshes.loaded=0` | No recalled armor is available yet. Enter/load a code first. |
| `loaded_idle_self` | `playing=false`, `armorStandPreview=false`, `xr.viewMode=self`, `meshes.loaded>0` | Armor is loaded but hidden until preview or transform. |
| `mirror_idle` | `playing=false`, `armorStandPreview=false`, `xr.viewMode=mirror` | Mirror target is selected, but no replay is running. |
| `armor_stand_observer_idle` | `playing=false`, `armorStandPreview=true`, `xr.viewMode=observer` | Static armor-stand preview. Do not accept as transformation evidence. |
| `transform_active_self` | `playing=true`, `playbackSource!=archive`, `xr.viewMode=self` | First-person transformation is running. |
| `archive_replay_mirror_active` | `playing=true`, `playbackSource=archive`, `xr.viewMode=mirror` | Mirror replay is running. This is the main public confirmation path. |
| `archive_replay_observer_active` | `playing=true`, `playbackSource=archive`, `xr.viewMode=observer`, `armorStandPreview=false` | Observer replay inspection is running. |
| `completed_hold` | `playing=true` or completed frame is retained, `progress>=1`, no stand preview | Completed transform/replay hold. Must still keep view mode. |
| `voice_capture_active` | microphone is recording/analyzing before replay starts | Voice path is in progress; should not imply armor is visible yet. |
| `voice_rejected_idle` | `voiceState=rejected`, `playing=false` | Voice failed or timed out; retry or check mic URL. |

Reviewer note: if the code emits both `uxState` and lower-level fields, verify
the emitted `uxState` can be recomputed from the lower-level fields. If it
cannot, treat the snapshot as untrustworthy.

## Minimum Telemetry Fields

Every debug snapshot used for review must include enough information to classify
the current experience without reading UI text from a photo.

Required top-level or equivalent fields:

```json
{
  "uxState": "armor_stand_observer_idle",
  "event": "scene",
  "at": "2026-05-04T00:00:00.000Z",
  "route": {
    "recallCode": "3601",
    "activeSuitId": "...",
    "activeManifestId": "...",
    "trialId": "...",
    "voiceState": "complete",
    "playing": false,
    "armorStandPreview": true,
    "playbackSource": "archive",
    "progress": 0
  },
  "xr": {
    "session": true,
    "viewMode": "observer",
    "archiveViewMode": "mirror",
    "liveBodyPose": false
  },
  "microphone": {
    "captureEnabled": false,
    "mockTrigger": true,
    "secureContext": true,
    "hasMediaDevices": true,
    "hasMediaRecorder": true,
    "audioMode": "wav"
  },
  "query": {
    "href": "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&mockTrigger=1&mic=0&debug=1&t=...",
    "userAgent": "Quest Browser ...",
    "code": "3601",
    "mockTrigger": "1",
    "mic": "0",
    "debug": "1",
    "qa": ""
  },
  "meshes": {
    "loaded": 18,
    "visibleCount": 17
  }
}
```

Minimum field acceptance:

- `uxState` exists and is stable across snapshots while the same visible mode is
  unchanged.
- `route.voiceState` remains available, but dashboards do not sort or color the
  experience primarily by it.
- `route.playing`, `route.armorStandPreview`, `route.playbackSource`, and
  `route.progress` are present together.
- `xr.session`, `xr.viewMode`, and `xr.archiveViewMode` are present.
- `query.href`, `query.userAgent`, `query.code`, `query.mockTrigger`,
  `query.mic`, `query.debug`, and `query.qa` are present.
- `microphone.captureEnabled` and `microphone.mockTrigger` are present. Real mic
  acceptance also needs browser capability/permission evidence.
- `meshes.loaded` and `meshes.visibleCount` are present before judging whether a
  visible issue is a UX mode issue or asset load issue.

## Debug URL Operation

### Debug / Recovery URL

Use this to validate rendering, replay, mode classification, and telemetry
without real voice:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&mockTrigger=1&mic=0&debug=1&t=YYYYMMDD-HHMM
```

Expected interpretation:

- `mockTrigger=1`: voice trigger is bypassed.
- `mic=0`: real microphone capture is intentionally disabled.
- `microphone.captureEnabled=false`.
- A successful run may skip the full voice color path.
- This URL can approve `uxState` classification and mirror/stand transitions.
- This URL cannot approve real microphone capture or speech recognition.

### Real Mic URL

Use this to validate Quest Browser microphone permission and real recognition:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&replayView=mirror&debug=1&t=YYYYMMDD-HHMM
```

Expected interpretation:

- No `mockTrigger=1`.
- No `mic=0`.
- Quest Browser permission prompt is allowed.
- `microphone.captureEnabled=true` once the voice flow is attempted.
- Expected voice path is green -> orange -> purple -> cyan for success.

Review failure examples:

- NG: a real mic pass uses `mockTrigger=1` and is reported as voice accepted.
- NG: a debug/recovery URL photo is used as final public voice evidence.
- NG: telemetry lacks URL fields, so the reviewer cannot tell whether the pass
  was mock or real.

## Operator Acceptance Checklist

Use this at the exhibition PC/headset. Each item must be answerable without
opening source code.

### Before Entering XR

- The operator records the full Quest Browser URL.
- The URL includes the intended `code=...` and a fresh `t=...` value.
- The operator labels the pass as `debug mock` or `real mic`.
- The operator knows whether this pass is testing mirror/replay, armor stand,
  voice, or all of them.

### Inside XR

- The headset is awake and the scene is visible in Quest Browser.
- The current visible mode is recorded as self, mirror, observer, armor stand,
  or unknown.
- If a standing suit is visible at `progress=0`, the operator treats it as
  armor-stand/observer evidence until telemetry proves otherwise.
- If mirror acceptance is the goal, the operator switches out of armor stand and
  starts replay or transformation.
- A photo is accepted only when it is labeled with mode, progress, and URL type.

### After Capturing Evidence

- `/api/quest-debug/latest` is confirmed to come from Quest/Oculus Browser, not
  PC Playwright.
- The operator records:
  - `uxState`
  - `voiceState`
  - `xr.viewMode`
  - `playing`
  - `progress`
  - `armorStandPreview`
  - `playbackSource`
  - `microphone.captureEnabled`
  - `microphone.mockTrigger`
  - `query.href`
- For transformation acceptance, the evidence is not only
  `armor_stand_observer_idle`.
- For voice acceptance, the evidence is not from `mockTrigger=1&mic=0`.

## Developer Review Checklist

Use this after code changes before asking for a physical Quest recheck.

### State Derivation

- `uxState` is computed from live scene fields, not from `voiceState` alone.
- `armorStandPreview=true && playing=false` always classifies as armor stand,
  even if `voiceState=complete`.
- `playbackSource=archive` separates replay from live voice transformation.
- `xr.viewMode=observer` is not enough to classify armor stand; `playing` and
  `armorStandPreview` are also checked.
- `progress=0` is not treated as completed evidence.
- `completed_hold` or equivalent keeps its view mode and does not erase whether
  the user is in mirror, observer, or self.

### Snapshot Contract

- `collectQuestDebugSnapshot` or equivalent emits all minimum fields.
- The emitted `uxState` is included in the same payload as its source fields.
- Snapshot throttling does not skip forced events such as start, armor load,
  view change, stand toggle, replay start, voice rejection, and completion.
- A stale `voiceState=complete` does not hide a later stand toggle in the latest
  snapshot.
- The payload is safe for operator logs: no source-code-only names are required
  to interpret the state.

### UI / Operator Label Contract

- The visible UI distinguishes armor stand, mirror replay, observer replay, and
  voice waiting.
- The view button label describes the destination or current mode clearly enough
  for a non-developer operator.
- The right-hand device color mapping remains:
  - green: ready / arming
  - orange: recording
  - purple: analyzing
  - cyan: detected / complete
  - red: rejected / error
- Color is not the only required evidence in debug mode; telemetry must carry
  the state.

### URL / Mic Contract

- `mockTrigger=1` and `mic=0` are represented explicitly in telemetry.
- Real mic acceptance has a separate URL path and cannot be inferred from the
  debug/recovery URL.
- `microphone.captureEnabled` means capture is intended/enabled, not merely that
  the browser has a microphone API.
- If Quest Browser origin policy blocks capture on one route, the report states
  the route: ADB reverse localhost, LAN HTTP, or HTTPS.

## Required Review Scenarios

Run or reason through these before approving the implementation.

### Scenario A: Photo Ambiguity Regression Guard

Setup:

- Previous transformation completed.
- `voiceState=complete` remains.
- Operator toggles armor stand.

Expected:

- `uxState=armor_stand_observer_idle`.
- `voiceState=complete` remains visible as a separate field.
- `playing=false`.
- `progress=0`.
- `armorStandPreview=true`.
- `xr.viewMode=observer`.
- Dashboard/operator text does not call this "completed transformation evidence."

### Scenario B: Mirror Replay Acceptance

Setup:

- Debug/recovery URL is open.
- Replay is started in mirror mode.

Expected:

- `uxState=archive_replay_mirror_active` while replay is running.
- `playbackSource=archive`.
- `xr.viewMode=mirror`.
- `playing=true`.
- `progress` advances above zero.
- `armorStandPreview=false`.
- Mirror photo can be used for visual replay acceptance.

### Scenario C: Observer Replay Is Not Armor Stand

Setup:

- Replay is started in observer mode.

Expected:

- `uxState=archive_replay_observer_active`.
- `playing=true`.
- `playbackSource=archive`.
- `armorStandPreview=false`.
- The observer view is accepted only as replay inspection, not mirror public
  confirmation.

### Scenario D: Debug URL Is Not Real Voice

Setup:

- URL includes `mockTrigger=1&mic=0`.

Expected:

- `microphone.mockTrigger=true`.
- `microphone.captureEnabled=false`.
- Voice acceptance is marked "not tested".
- State/replay classification can still be accepted if the scene fields are
  correct.

### Scenario E: Real Mic Path

Setup:

- URL omits `mockTrigger=1` and `mic=0`.
- Operator grants microphone permission.

Expected:

- `microphone.mockTrigger=false`.
- `microphone.captureEnabled=true` during capture.
- `voiceState` transitions through recording/analyzing/detected or rejected.
- A voice failure reports URL, permission result, and final `voiceState`.

## Acceptance Summary

Approve the code change only if all of these are true:

- A stale `voiceState=complete` can no longer cause photo evidence in observer
  armor-stand standby to be reported as current transformation completion.
- `uxState` is present or an equivalent experience-state field is present with a
  documented mapping.
- The minimum telemetry fields are present in the same snapshot.
- Operators have a clear split between debug/recovery URL and real mic URL.
- Mirror replay, observer replay, and armor stand preview are separately named
  in telemetry and operator language.
- At least one regression test or static contract test covers the photo
  ambiguity case.
- Documentation and UI language tell reviewers to classify from current scene
  gates first, then interpret `voiceState`.

## NG Report Shape

If a review fails, file it with this compact shape:

```text
Quest UX telemetry NG

time:
operator/reviewer:
URL:
code:
test type: debug mock / real mic
expected uxState:
actual uxState:
voiceState:
xr.viewMode:
playing:
progress:
armorStandPreview:
playbackSource:
microphone.captureEnabled:
microphone.mockTrigger:
photo/screenshot:

failure:
- stale voiceState misread / mirror-vs-stand ambiguity / missing telemetry field /
  debug URL used as real mic / observer replay collapsed into armor stand /
  other

requested fix:
```
