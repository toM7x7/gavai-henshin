# Bounded mocopi-to-Quest Exhibition Spike - 2026-05-04

Goal: prove the Quest-facing demo can tell the operator whether archived motion
came from simulated body-sim data or mocopi-derived data, while keeping the
active visitor demo path unchanged.

2026-05-05 execution update: use
`docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md` for the current
external-PC and mocopi connection stage table. The assumed operator state is:
Windows PC, unknown GPU, Quest USB available, shared LAN available, and mocopi
hardware available but unused. Therefore mocopi begins as operator-only
`DEMO-ONLY` or `not-included`; BODY/static fallback must be proven first; Web
serviceization is an anshin lane rather than a show-floor dependency.

## Existing support inspected

- `src/henshin/iw_henshin.py` already accepts `IWSDKHenshinRequest.mocopi_payload`.
- `normalize_mocopi_frames()` accepts mocopi-like `frames` / `mocopi_frames`
  and `bones` aliases such as `RightHand`, then maps them into canonical body
  joints.
- `run_iwsdk_henshin()` writes `body-sim.json`, sets
  `source.tracking = mocopi`, stores normalized tracking frames, and references
  `deposition.body_sim_path` in the replay.
- `src/henshin/bodyfit.py` already turns normalized body frames into the
  body-sim segments consumed by the viewer.
- `viewer/quest-iw-demo/quest-demo.js` already has archive replay diagnostics
  for `BODY`, `LIVE`, `BODY+LIVE`, `SELF`, `CAPTURE`, and `STATIC`.
- `examples/mocopi_sequence.sample.json` is a mocopi-like alias fixture.
- `examples/body_sequence.sample.json` is the simulated body sequence baseline.

## Spike boundary

This spike adds diagnostic source discrimination only:

- Simulated body-sim archive motion should surface as `BODY <n>f`.
- Mocopi-derived archive motion should surface as `MOCOPI <n>f`.
- Mixed mocopi-derived body-sim plus live-pose should surface as `MOCOPI+LIVE`.
- The frame extraction and armor placement path remains the existing
  body-sim/replay path.

## Lane Policy

Required local preflight:

- `local-pass` is prerequisite for visitor operation.
- `local-pass cannot be overridden` by mocopi hardware success.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.

Optional enhancement preflight:

- mocopi exits as `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.
- mocopi cannot promote the visitor path unless the packaged-PC local baseline
  remains pass, Quest diagnostics show `MOCOPI`, latency/freeze thresholds pass,
  and BODY/static fallback is rehearsed.
- mocopi judgment requires saved real-device evidence packs from
  `tools/capture_quest_debug_snapshot.ps1`; a verbal "it worked" is not enough
  to move beyond `mocopi-DEMO-ONLY`.
- If mocopi is `DEMO-ONLY`, `NO-GO`, or `not-included`, the public route stays
  on BODY/static fallback and still may be `local-pass`.

## mocopi/BODY evidence pack gate

Run this gate only after the packaged exhibition PC is already `local-pass`.
The visitor baseline must stay BODY/static-capable before, during, and after the
mocopi rehearsal.

Preferred Quest route for evidence capture:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

Use the centerline QA lane when judging placement drift versus mocopi tracking:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&qa=centerline
```

Capture command:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

Add `-Screencap` for the final pass/fail folder or any failure that is visually
ambiguous:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

Each run writes `qa\logs\quest-3601-<timestamp>\` with:

- `adb-devices.txt`: must show the headset as `device`, not `unauthorized`.
- `adb-reverse.txt`: must show active reverse mappings for `tcp:5173` and
  `tcp:8010` when USB is the selected path.
- `quest-debug-latest.json`: keep the raw Quest telemetry record for later
  review.
- `operator-summary.txt`: check `href`, `telemetryCode`, `xrSession`, `uxState`,
  `centerlineVerdict`, `centerlineClassification`, and `centerlineDisplayLine`.
- `screencap.png`: optional, but required for visual mismatch, left/right swap,
  frozen pose, or disputed mocopi token claims.

Current-PC preflight before touching mocopi sensors:

```powershell
python tools/prepare_mocopi_rehearsal_preflight.py --code 3601 --report-json
```

This writes `qa\mocopi-rehearsal-preflight-latest.json` and checks the repo
reception points, local ports, `adb`, reverse mappings, and Quest debug API. If
it reports `mocopi-NO-GO`, do not pair sensors yet; fix the blockers and rerun
the preflight. If it reports `mocopi-DEMO-ONLY`, start only an operator-led
rehearsal and capture BODY/MOCOPI/fallback packs. `mocopi-GO` requires the
three-pack evaluator plus the manual pairing, calibration, latency, left/right,
consent, retention, and 60-second fallback gates.

The preflight `motion_token` reader accepts both current Quest debug shapes:
top-level `replayMotion` and `route.replayMotionDiagnostic`. If both are
present, `replayMotion.token` is treated as the freshest replay token for this
report; if only the route diagnostic exists, that token is used.

Required evidence packs:

1. BODY fallback baseline pack: with mocopi off or ignored, Quest shows the
   existing BODY/static path and the operator can run the visitor route.
2. MOCOPI candidate pack: after imported mocopi or physical sensor rehearsal,
   Quest visibly reports `MOCOPI <n>f` or `MOCOPI+LIVE`, not `MOCOPI 0f`.
3. Fallback recovery pack: after disabling mocopi or switching away from the
   mocopi artifact, Quest returns to BODY/static within 60 seconds without
   changing the public visitor route.

Read these packs in order. If the BODY baseline pack is missing or failing, do
not start mocopi QA. If the MOCOPI candidate pack is present but centerline QA
classifies the run as `runtime_anchor`, `hard_sync_centerline`, or `mixed`,
label the mocopi lane `mocopi-DEMO-ONLY` until the Quest/runtime anchor issue is
separately cleared. If the fallback recovery pack is missing, mocopi is
`mocopi-NO-GO` for public operation even when the mocopi motion itself looks
good.

Decision materials:

- `mocopi-GO`: `local-pass` is already recorded; all three evidence packs
  exist; Quest shows usable `MOCOPI` frames; centerline QA does not indicate an
  unresolved runtime/hard-sync centerline problem; latency/freeze/left-right
  checks pass; consent and retention notes are recorded; BODY/static recovery is
  proven under 60 seconds.
- `mocopi-DEMO-ONLY`: `local-pass` and BODY fallback are intact, but mocopi is
  imported/replay-only, operator-assisted, latency-warn, centerline-warn, or
  otherwise not visitor-safe. It may be shown as an operator-led rehearsal, not
  the default visitor path.
- `mocopi-NO-GO`: `local-pass` is missing, Quest does not show usable `MOCOPI`
  frames, ADB reverse/debug telemetry cannot be captured, the headset enters
  `unauthorized`, fallback takes more than 60 seconds, left/right mapping swaps,
  freezes exceed the gate, consent/retention is absent, or the mocopi run breaks
  the BODY/static baseline.

Order that preserves the local baseline:

1. Start Web/API on `8010`, Quest Vite on `5173`, and USB ADB reverse.
2. Prove local Web -> Quest -> Replay with BODY/static only.
3. Capture the BODY fallback baseline pack.
4. Rehearse imported mocopi or physical sensors in an operator-only lane.
5. Capture the MOCOPI candidate pack.
6. Disable mocopi or switch back to the BODY/static artifact.
7. Capture the fallback recovery pack.
8. Write `mocopi-GO/DEMO-ONLY/NO-GO`; do not change the visitor URL or default
   route before `mocopi-GO`.

Automated pack evaluator:

```powershell
python tools/evaluate_mocopi_evidence_pack.py `
  --body-baseline qa\logs\quest-3601-<body-timestamp> `
  --mocopi-candidate qa\logs\quest-3601-<mocopi-timestamp> `
  --fallback-recovery qa\logs\quest-3601-<fallback-timestamp> `
  --report-json
```

The evaluator reads each pack's `operator-summary.txt` and
`quest-debug-latest.json`, then emits a JSON report with per-pack motion token,
centerline QA, Quest/ADB materials, reasons, warnings, and the current mocopi
label. Today it is intentionally conservative: if BODY baseline or fallback
does not prove BODY/static, or the candidate does not prove usable `MOCOPI`
frames, the result is `mocopi-NO-GO`; if all three packs pass the automatic
checks, the result is still `mocopi-DEMO-ONLY` until physical mocopi
pairing/calibration, latency/freeze thresholds, and consent/retention evidence
are recorded outside the snapshot pack.

Rehearsal plan exporter:

```powershell
python tools/export_mocopi_rehearsal_plan.py `
  --evaluation-json qa\mocopi-evidence-evaluation.json `
  --out qa\mocopi-rehearsal-plan-latest.json `
  --report-json
```

It can also receive the same three evidence pack folders directly with
`--body-baseline`, `--mocopi-candidate`, and `--fallback-recovery`; in that mode
it runs the evaluator internally. The output JSON contains
`current_gate_label`, `rehearsal_steps`, `operator_script`, `risk_register`,
`fallback_trigger_points`, and `evidence_to_collect`. Use it as the show-floor
handoff: mocopi stays the ideal line, but `mocopi-DEMO-ONLY` and
`mocopi-NO-GO` plans explicitly keep BODY/static as the public fallback.

Share-safe evidence package:

```powershell
python tools/package_mocopi_evidence.py `
  --evaluation-json qa\mocopi-evidence-evaluation.json `
  --rehearsal-plan qa\mocopi-rehearsal-plan-latest.json `
  --evidence-dir qa\logs\quest-3601-<timestamp> `
  --out qa\mocopi-evidence-package-latest.json `
  --report-json
```

This manifest is the default file to share with another PC or GitHub. It keeps
raw `quest-debug-latest.json`, `operator-summary.txt`, ADB logs, screenshots,
images, raw mocopi captures, and large logs local by default, while sharing a
small summary of the current gate label, included evidence, redaction policy,
privacy notes, operator readiness, and required BODY/static fallback.

QA privacy pre-share gate:

```powershell
python tools/validate_qa_evidence_privacy.py `
  --qa-root qa `
  --mode share `
  --release-stage-manifest qa\release-stage-manifest-latest.json `
  --report-json
```

Run this before putting any `qa/` evidence on GitHub or another PC. `local` mode
allows `localhost` URLs as local evidence; `share` mode warns on localhost refs,
screenshots/images/video, raw logs, ADB/Quest dumps, and blocks secret-like JSON
keys until they are removed or redacted. Share the sanitized mocopi evidence
package manifest instead of raw `qa\logs\...` folders.

Shareable QA evidence manifest:

```powershell
python tools/export_shareable_qa_evidence_manifest.py `
  --qa-root qa `
  --out qa\shareable-qa-evidence-latest.json `
  --report-json
```

Use this output for the release stage manifest or transfer checklist. It
extracts curated JSON reports into `shareable_files` and
`recommended_git_stage_paths`, while keeping images/video, raw logs, Quest/ADB
dumps, unknown JSON, and blocker findings in `local_only_files` or
`blocked_files`.

## Non-goals

- No live mocopi WebSocket receiver.
- No production IK/VRM retargeting quality guarantee.
- No public UI controls for switching mocopi mode.
- No change to `DEFAULT_REPLAY`, the active Quest route, or the voice-triggered
  visitor path.
- No latency claim until real mocopi sensors, phone, PC, and headset are tested
  together.

## Validation fixture

`examples/quest-mocopi-motion-source.fixture.json` contains two archive-body
cases using the same playback shape:

- `simulated_body`: `playback.motion_source = body_sim`,
  `source.tracking = body_sim`, body-sim `source = body_sim`, expected `BODY 1f`.
- `mocopi_body`: `playback.motion_source = mocopi`,
  `source.tracking = mocopi`, mocopi provenance, body-sim `source = mocopi`,
  expected `MOCOPI 1f`.

The fixture is intentionally small so it can be reviewed before show setup and
used as a regression test without connecting the headset or mocopi sensors.

## Phase 0/1/2

### Phase 0: diagnostic-safe fallback

Scope:

- Quest may read `mocopi` provenance from replay/body-sim metadata.
- Quest only displays `MOCOPI` when replay/body-sim motion frames are present.
- If the mocopi-derived body-sim file is absent, unreadable, or empty, the
  viewer keeps running and falls back to replay motion or `STATIC`.
- The normal voice-triggered first-person transform remains the public default.

Acceptance gates:

- `tests/test_quest_mocopi_motion_source.py` passes.
- A replay that says `motion_source = mocopi` but has no usable motion frames
  does not surface a `MOCOPI 0f` claim.
- A missing `deposition.body_sim_path` or failed body-sim fetch does not reject
  `applyReplay`; operator diagnostics record the fallback.

### Phase 1: imported mocopi rehearsal

Scope:

- Import one known-good mocopi JSON/export into the existing `--mocopi` path.
- Normalize it through `normalize_mocopi_frames()` and `bodyfit.py`.
- Preserve provenance in replay fields: provider, source session, frame count,
  coordinate space, source artifact, derived body-sim artifact, consent, and
  retention class.
- Use BODY/static fallback for all public runs until the physical rehearsal
  passes.

Acceptance gates:

- PC smoke tests pass on the exhibition PC, not only the development machine.
- The local external-PC smoke already has `preflight_gate.operator_label =
  local-pass`.
- BODY fallback baseline evidence pack is captured before any mocopi promotion
  attempt.
- Quest archive replay shows `MOCOPI <n>f` for the imported mocopi run.
- MOCOPI candidate evidence pack is captured from the Quest with
  `capture_quest_debug_snapshot.ps1`.
- Quest archive replay shows `BODY <n>f` for the simulated fallback run.
- Operator can switch back to BODY/static within 60 seconds without changing the
  visitor URL.
- Fallback recovery evidence pack is captured after switching back to
  BODY/static.

### Phase 2: live receiver candidate

Scope:

- Add the narrowest live receiver/import bridge after Phase 1 proves the shape:
  mocopi app/export bridge, local WebSocket receiver, or operator-triggered file
  drop.
- Keep the Quest viewer consuming derived replay/body-sim frames unless live
  retargeting quality and latency beat the gate.
- Record receiver failures as operator diagnostics, not public errors.

Acceptance gates:

- Six sensors stay paired for at least 60 seconds before calibration.
- Median visible mocopi-to-Quest latency is `<= 120 ms`; p95 is `<= 250 ms`.
- No left/right limb swap during slow arm raise and weight shift checks.
- Frozen/dropped motion stays below `2%` and no freeze exceeds `500 ms`.
- The latency/freeze verdict is backed by the MOCOPI candidate evidence pack,
  optional `screencap.png`, and operator notes from the same 60-second
  rehearsal.
- If any gate fails, label the lane `mocopi-DEMO-ONLY` or `mocopi-NO-GO` and run
  BODY/static fallback.

## Wear-following reality check

This section is the mocopi/equipped-following owner note for the exhibition
decision. The important distinction is source truth versus visual fit: mocopi
can improve the body-motion source, but it does not automatically solve armor
coordinate placement, GLB envelope sizing, or Quest view-mode anchoring.

### Why armor does not follow the body yet

Current Quest runtime has three different motion/placement paths:

- Live self-view armor uses Quest HMD and controller estimates only when
  `liveBody=1` and self view are active. `updateLiveBodyAnchors()`,
  `getLiveBodyPartPosition()`, and `applyLiveSuitPose()` estimate torso, hips,
  legs, and missing hands from head/controller offsets. The captured payload
  itself says hips, torso twist, and feet are estimated until mocopi/IK/VRM
  retargeting is connected.
- Archive mirror/observer replay consumes derived body-sim or replay
  `motion_frame` data through `currentReplayMotionFrame()` and
  `applyMotionSuitPose()`. When Quest is in fixed-body XR mode, centered replay
  uses `questAssemblyPoseForPart()` instead of per-frame limb positions, so the
  public mirror route may intentionally align to the static body shell rather
  than to mocopi-like limb motion.
- Standby/armor-stand preview uses `armorStandPoseForPart()` and runtime
  placements. It is useful for checking loaded parts and placement, but it is
  not evidence that archive mirror or live self-view follow the participant.

The remaining visual mismatch therefore has several causes:

- The current mocopi spike proves provenance (`MOCOPI`, `MOCOPI+LIVE`) and
  body-sim replay availability, not live Quest skeletal retargeting.
- `bodyfit.py` is 2D segment-following over normalized joints. It generates
  segment positions/scales for replay, but it does not produce a full 3D
  humanoid skeleton with hip, chest, head, foot orientation, twist, floor
  contact, or calibrated body proportions.
- Quest runtime still applies part-specific runtime placement offsets,
  rotations, GLB target envelopes, and view-mode anchors after motion is chosen.
  A correct mocopi body source can still look wrong if a GLB sidecar envelope,
  coordinate-space sign, runtime offset, or mirror/observer anchor is wrong.
- Standard Quest XR without `liveBody=1` uses fixed-body placement for safer
  exhibition viewing. That deliberately prevents noisy live HMD/controller
  estimates from making armor drift, but it also means the armor is not truly
  attached to the visitor body in the public mirror path.

### What mocopi solves, and what remains

mocopi can solve or improve:

- Provenance truth: Quest can honestly show that replay motion came from
  mocopi-derived data instead of simulated body-sim.
- Better offline rehearsal motion: imported mocopi JSON can drive the existing
  `--mocopi` -> normalized frames -> body-sim -> archive replay path.
- Limb source quality for arms/legs: six sensors should reduce dependence on
  guessed knees, ankles, wrists, and torso yaw compared with HMD/controllers
  alone, if calibration and left/right mapping are stable.
- Operator confidence: sensor pairing, calibration, latency, and fallback can be
  measured before any public claim.

mocopi does not automatically solve:

- Armor-to-body coordinate mismatch caused by `VR_BODY_PART_POSES`,
  `questAssemblyPoseForPart()`, runtime placement offsets/rotations, GLB target
  sizing, or mirror/observer anchoring.
- 3D retargeting quality. The existing imported path is not a VRM/IK skeleton;
  it is normalized mocopi-like joints collapsed into 2D body-sim segments.
- Live Quest transport. There is no production live mocopi WebSocket receiver in
  the public route yet, and the current Quest viewer does not consume raw
  mocopi bones directly.
- Exhibition safety fallback. Even if mocopi connects, BODY/static fallback
  remains mandatory because pairing, phone transport, Bluetooth drift, and
  calibration can fail on the show floor.

## Exhibition-stage mocopi linkage plan

### Stage A: Claim-safe mocopi replay

Use for the exhibition baseline.

Scope:

- Keep the public visitor route on the existing Quest recall/replay path.
- Import or fixture mocopi data before the show and convert it through the
  existing `--mocopi` and body-sim path.
- Quest may say `MOCOPI <n>f` only when usable mocopi-derived body-sim/replay
  frames are loaded.
- Operator script says "mocopi-derived replay" rather than "live body tracking".

Exit label:

- `mocopi-DEMO-ONLY` if the replay is mocopi-derived but not live.
- `mocopi-NO-GO` if Quest does not show `MOCOPI` or fallback is not rehearsed.

### Stage B: Sensor rehearsal without public promotion

Use only after Stage A passes on the exhibition PC.

Scope:

- Pair real mocopi sensors and capture a short known-good export or local bridge
  sample.
- Convert that capture into the same body-sim/replay artifact shape.
- Compare the Quest mirror/observer output against the BODY fallback with the
  same suit.
- Record whether the observed problem is tracking-source quality, body-sim
  retargeting, GLB/runtime placement, or Quest view-mode anchoring.

Acceptance:

- Quest diagnostic shows `MOCOPI`.
- Left/right arm raise and weight shift stay correct.
- The operator can fall back to BODY/static within 60 seconds.
- No public wording claims live attachment unless the live receiver gate also
  passes.

### Stage C: Narrow live candidate

Treat this as a stretch goal, not the exhibition baseline.

Scope:

- Add the smallest local receiver/import bridge that can produce the same
  normalized body frame shape repeatedly.
- Keep Quest consuming derived body/replay frames until a separate live
  retargeting path exists.
- If a live path is tested, gate it behind `liveBody=1` or an operator-only URL,
  never the default visitor URL.

Acceptance:

- Median visible mocopi-to-Quest latency `<= 120 ms`; p95 `<= 250 ms`.
- No freeze above `500 ms`; dropped/frozen frames below `2%`.
- The same suit passes placement sanity in BODY/static and MOCOPI replay before
  live mode is considered.
- Failures are labeled `mocopi-DEMO-ONLY` or `mocopi-NO-GO`, not hidden.

### Stage D: True equipped-following, post-exhibition unless already proven

This is the real "armor follows the body" milestone.

Required work:

- Define a 3D body skeleton contract with root, hips, chest, head, shoulders,
  elbows, wrists, knees, ankles, feet, orientations, confidence, and coordinate
  space.
- Retarget mocopi sensor data into that skeleton with calibration, height/body
  proportion scaling, floor contact, smoothing, and left/right validation.
- Make Quest armor placement consume that skeleton consistently across self,
  mirror, observer, and stand paths.
- Revalidate runtime placement offsets, GLB target envelopes, and
  `questGlbScaleForPart()` against the same skeleton.

Exhibition implication:

- Do not promise true equipped-following for the public route unless Stage D is
  physically rehearsed on the exhibition PC, with the target Quest headset and
  the actual suit assets.

## External Exhibition PC Plan

Use the exhibition PC as the source of truth. Do not depend on files or servers
from the development machine.

### PC setup

Install on the exhibition PC:

- Windows 11 or equivalent exhibition PC image.
- Node.js/npm with `npx`.
- Python 3.11+.
- Android Platform Tools or Meta Quest Developer Hub for `adb`.
- Chrome or Edge for PC-side smoke checks.
- Meta Quest Browser on the headset.
- A USB-C data cable for the preferred Quest path.

From PowerShell:

```powershell
cd C:\path\to\gavai-henshin
npm ci
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
python -m pytest tests/test_iw_henshin.py tests/test_quest_mocopi_motion_source.py -q
```

### Start servers

Terminal A, Web/API/static on `8010`:

```powershell
cd C:\path\to\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"
```

Terminal B, Quest Vite runtime on `5173`:

```powershell
cd C:\path\to\gavai-henshin
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Confirm both listeners:

```powershell
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 5173,8010 }
```

Expected ports:

```text
0.0.0.0:5173
0.0.0.0:8010
```

### Preferred headset path: USB adb reverse

Use USB adb reverse first. It avoids venue same Wi-Fi, captive portal, subnet,
and firewall surprises.

1. Connect Quest to the exhibition PC with the USB-C data cable.
2. In the headset, accept the USB debugging prompt.
3. In PowerShell:

```powershell
adb devices
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

Expected `adb devices` state:

```text
<device_id>    device
```

Headset Browser URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

### Fallback headset path: same Wi-Fi / LAN

Use same Wi-Fi only if USB adb reverse is unavailable.

1. Put PC and Quest on the same Wi-Fi or wired/LAN subnet.
2. Accept the Windows Firewall prompt for Node/Vite and Python when the servers
   first bind to the network.
3. If no prompt appears, allow the app manually or temporarily use a trusted
   private network profile for the exhibition LAN.
4. LAN IP discovery:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

Headset Browser URL:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

If Quest Browser blocks microphone/WebXR features on HTTP LAN, use HTTPS/cert
mode before showtime:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp <PC_LAN_IP>
.\tools\start_quest_lan_https.ps1 -ApiTarget http://127.0.0.1:8010
```

Install/trust `config\quest-lan-root-ca.cer` on the Quest. Then use:

```text
https://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

## Smoke checklist

PC-side:

- `python -m pytest tests/test_iw_henshin.py tests/test_quest_mocopi_motion_source.py -q`
- `python -m pytest tests/test_quest_recall_render_contract.py -q`
- `npx vite build --config vite.quest.config.js --outDir %TEMP%\gavai-quest-vite-build-mocopi-spike --emptyOutDir`
- `Get-NetTCPConnection` shows `5173` and `8010` listening.
- Web Forge opens at `http://127.0.0.1:8010/viewer/armor-forge/`.
- Quest page opens at the selected Headset Browser URL.

Quest-side:

- Load or generate a normal simulated-body replay and confirm debug/status
  motion token includes `BODY`.
- Load a mocopi-derived replay or fixture-generated replay where
  `source.tracking` or `playback.motion_source` is `mocopi` and confirm
  debug/status motion token includes `MOCOPI`.
- Confirm armor still appears through the existing archive/body-sim path.
- Confirm no public-facing mocopi selector or extra debug panel was added.
- Confirm a normal visitor voice/trigger flow still starts from the same Quest
  URL.

## Show-floor mocopi acceptance checklist

Run this checklist after the PC/Quest smoke check and before letting visitors
use mocopi-driven motion. The pass condition is not "mocopi is connected"; it is
"the operator can repeatedly see `MOCOPI` motion in Quest at acceptable latency,
with a known fallback path."

### Pairing

- Charge the six mocopi sensors before setup.
- Pair and label every sensor in the mocopi app: `head`, `hip`, `left_wrist`,
  `right_wrist`, `left_ankle`, `right_ankle`.
- Confirm all six sensors show connected/green in the mocopi app for at least
  60 seconds.
- Confirm straps are snug enough that wrist/ankle sensors do not rotate during
  the visitor pose.
- If any sensor disconnects twice during setup, stop mocopi acceptance and use
  the `BODY` fallback for public runs.

### Calibration pose

- Clear a safe standing area before calibration.
- Participant stands upright, feet hip-width, facing the Quest/exhibition-PC
  origin.
- Arms stay relaxed at the sides unless the mocopi app explicitly prompts a
  T-pose or another calibration pose.
- Recalibrate after changing participant, changing straps, headset recentering,
  or any visible left/right limb swap.
- Calibration passes only when a slow arm raise and slow weight shift keep the
  expected left/right side in the mocopi app and the Quest diagnostic still
  resolves to `MOCOPI`.

### Quest URL and transport path

- Preferred path: USB `adb reverse`.
- Confirm `adb devices` shows `<device_id>    device`.
- Run
  `.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser`.
- Headset Browser URL for USB:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

- Fallback path: same Wi-Fi / LAN.
- Confirm PC and Quest are on the same Wi-Fi or subnet.
- Accept the Windows Firewall prompt for Node/Vite and Python.
- Run LAN IP discovery:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

- Headset Browser URL for LAN:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

- If mic/WebXR is blocked on LAN HTTP, switch to HTTPS/cert setup before the
  public demo window. Do not debug cert prompts with a visitor waiting.

### mocopi UDP reachability probe

Before trying to connect mocopi motion to Quest, verify that the mocopi phone
app can reach the exhibition PC over UDP. The official mocopi receiver path
sends motion data from the mocopi app to the PC by UDP, with the documented
default port `12351`; the phone must target the PC IPv4 address, not
`localhost` or IPv6. Treat this as a transport check only: it does not mean the
Quest viewer is using live mocopi bones yet.

PC-side:

```powershell
python tools/probe_mocopi_udp.py --port 12351 --seconds 20 --out qa\mocopi-udp-probe-latest.json
```

mocopi app-side:

- Open the mocopi app after sensor pairing/calibration.
- Switch to Motion mode.
- Switch from Save to Send.
- Set the destination to the exhibition PC IPv4 address and UDP port `12351`.
- Start Capture/Send.

Interpretation:

- `udp-received`: the phone can reach the PC; continue to BODY baseline,
  MOCOPI-derived replay, and fallback evidence capture.
- `udp-no-packets`: check Windows Firewall, same LAN, PC IPv4 address, port
  number, and Motion Send mode before debugging Quest.
- The probe does not store raw motion payloads by default.

### UDP to body-sim/latest adapter candidate

The next narrow live-link step is a PC-local adapter, not a Quest JS change:

```text
mocopi app UDP
  -> tools/serve_mocopi_body_sim_latest.py
  -> in-memory derived body-sim
  -> http://127.0.0.1:8021/body-sim/latest
  -> Web/Quest rehearsal can reference that JSON from a replay/body-sim URL
```

Adapter command:

```powershell
python tools/serve_mocopi_body_sim_latest.py --udp-port 12351 --http-port 8021
```

Read-only endpoints:

- `GET /health`
- `GET /api/mocopi/debug/latest`
- `GET /body-sim/latest`
- `GET /api/mocopi/body-sim/latest`

Minimum accepted UDP payloads:

- UTF-8 JSON with `body_sim.frames[].segments`, already in Quest body-sim shape.
- UTF-8 JSON with mocopi-like `frames` or `mocopi_frames` using aliases such as
  `LeftShoulder`, `RightHand`, `LeftFoot`; the adapter normalizes this through
  the existing body-sim path.

Rejected payloads:

- Binary/unknown mocopi packets until the exact protocol/parser is explicitly
  implemented.
- JSON without body-sim frames or mocopi-like frames.

Privacy and safety boundary:

- Raw UDP payloads are not retained.
- Only the derived latest body-sim state is kept in memory.
- This endpoint may support operator rehearsal and debug replay references, but
  it is not a public `mocopi-GO` signal by itself.
- `mocopi-GO` still requires BODY baseline, MOCOPI candidate, fallback recovery,
  latency/freeze/left-right/consent evidence, and centerline review.

Test plan:

1. Unit-test fixture JSON -> derived `body-sim/latest` with `motion_source =
   mocopi`.
2. Unit-test embedded body-sim JSON passthrough.
3. Unit-test binary/unknown UDP payload rejection.
4. HTTP-test `/body-sim/latest` returns 404 before first valid packet and JSON
   after ingest.
5. UDP-loopback test confirms a packet updates the in-memory latest body-sim.
6. Quest rehearsal test, later: create or select a replay whose
   `deposition.body_sim_path` points to the local latest endpoint, then capture
   Quest debug and fallback packs.

### Latency thresholds

Measure over a 60-second rehearsal while the participant performs three slow
arm raises and three weight shifts.

- Pass: median mocopi-to-Quest visible update latency is `<= 120 ms`, p95 is
  `<= 250 ms`, dropped/frozen motion is below `2%`, and no freeze exceeds
  `500 ms`.
- Warning: median is `<= 180 ms` and p95 is `<= 350 ms`; use mocopi only for
  operator-led demos, not unattended visitor flow.
- Fail: p95 is `> 350 ms`, any freeze exceeds `1000 ms`, left/right sides swap,
  or Quest stops showing `MOCOPI`. Switch to fallback.

### Evidence pack capture

Capture the BODY baseline before mocopi, the MOCOPI candidate during mocopi, and
the fallback recovery after mocopi is disabled:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
```

Use `-Screencap` when the visual state matters:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
```

Do not label the run `mocopi-GO` unless all three folders exist under
`qa\logs\quest-3601-<timestamp>\` and the operator can point to the matching
BODY, MOCOPI, and recovery moments. If `quest-debug-latest.json` cannot be read
from `http://127.0.0.1:8010/api/quest-debug/latest`, treat the result as
`mocopi-DEMO-ONLY` at best because the show-floor state cannot be audited.

### 2026-05-05 current-PC Quest replay evidence

Current verified evidence:

- Quest URL:
  `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&autoplayReplay=1&replayView=mirror&replay=/sessions/S-IW-MOCOPI-TEST-3601-OK/artifacts/iwsdk-deposition-replay.json&code=3601`
- Evidence folder:
  `qa\logs\quest-3601-20260505-035451`
- `uxState`: `browser_archive_replay_mirror_active`
- `replayMotion.token`: `MOCOPI 7f`
- `replayMotion.bodySimFrames`: `7`
- `replayMotion.replayMotionSource`: `mocopi`
- `centerlineQa`: still `fail/runtime_anchor`; treat this as armor placement
  work, not as a mocopi transport failure.

Root cause fixed in this pass:

- Old replay files could store `deposition.body_sim_path` as a Windows absolute
  path such as `C:\dev\...\sessions\...\body-sim.json`.
- Quest Browser then fetched `/C:/dev/...` and fell back to `STATIC`.
- New replay files store portable session paths such as
  `sessions/S-IW-MOCOPI-TEST-3601-OK/body-sim.json`.
- Quest viewer also normalizes old absolute paths containing `/sessions/` so
  stale rehearsal files can still be loaded from the browser.

Use `autoplayReplay=1&replayView=mirror` only for QA. The visitor route should
still be voice/Quest operated unless the operator explicitly wants a replay
diagnostic lane.

### Fallback to BODY/static

- First fallback: use simulated body-sim playback and confirm Quest shows
  `BODY`.
- Second fallback: if body-sim/replay cannot load, use static/standby display
  and confirm Quest shows `STATIC` or no live mocopi claim is made.
- Do not tell operators mocopi is active unless the Quest diagnostic shows
  `MOCOPI`.
- If fallback is used, announce it internally as "BODY fallback" or
  "static fallback"; do not present raw mocopi as verified.

### Privacy and operator notes

- Get operator/participant consent before capturing mocopi motion.
- Treat raw mocopi streams and retained motion files as identifying motion data.
- Do not show raw sensor IDs, phone IDs, filenames, or participant names on the
  public screen.
- Store only derived body-sim/replay artifacts unless raw mocopi retention has
  explicit operator approval.
- Delete rehearsal raw captures from the exhibition PC after acceptance unless
  they are intentionally archived under the replay/privacy policy.

## Wrong 5173/8010 Recovery

If Quest cannot open `localhost:5173` over USB:

```powershell
adb devices
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
Get-NetTCPConnection -State Listen |
  Where-Object { $_.LocalPort -in 5173,8010 }
```

If `5173` is missing:

- Restart Terminal B with `npm run dev:quest -- --host 0.0.0.0 --port 5173`.
- If Vite reports the port is busy, stop the conflicting process or choose a
  new port and update the Headset Browser URL and adb reverse command together.
- Do not keep an old headset URL after changing the Vite port.

If `8010` is missing:

- Restart Terminal A with
  `python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"`.
- Web Forge and Quest recall will not agree on generated codes without this
  API/static server.

If LAN mode fails:

- Re-run LAN IP discovery.
- Confirm PC and Quest are on the same Wi-Fi/subnet.
- Accept or manually add Windows Firewall rules for Node/Vite and Python.
- Try the HTTPS/cert path if browser policy blocks mic/WebXR.
- Fall back to USB adb reverse when venue networking is unstable.

## Residual hardware risks

- Real Quest headset not exercised by this fixture; it validates code and
  browser-build behavior only.
- Real mocopi sensors, phone app, Bluetooth pairing, calibration pose, and drift
  are not validated.
- Mocopi coordinate space and body proportions may still need retargeting before
  the visual motion looks correct.
- Network latency from mocopi phone/receiver to exhibition PC is unknown.
- If raw mocopi frames are retained, they should be treated as identifying
  motion data and handled under the replay/privacy policy.
- If `source.tracking` / `playback.motion_source` is omitted by a future mocopi
  adapter, Quest can still animate through body-sim but will fall back to `BODY`
  instead of `MOCOPI`.
