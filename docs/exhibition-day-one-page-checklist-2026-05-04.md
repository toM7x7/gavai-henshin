# Exhibition Day One-Page Operator Checklist - 2026-05-04

Audience: venue operator. Do not edit code during the demo. Use the frozen package and this checklist.

## Goal

Show one full loop:

```text
Web Forge creates a fresh 4-digit code -> Quest recalls the same suit -> transformation runs -> Replay proof is recorded.
```

Mode order:

1. Required baseline: local external-PC fallback. Run Web/API and Quest viewer from this PC.
2. Later service lane: GCP/web service. Use only if it has a separate green service smoke; do not block the local demo on it.
3. Optional adapter lane: PlayCanvas. Use only if it is consuming an exported runtime package snapshot.
4. Optional hardware lane: mocopi. Use only if the hardware gate is marked `GO` or `DEMO-ONLY`; otherwise use the normal simulated/body replay path.

Required local preflight:

- `local-pass` is prerequisite for visitor operation.
- `local-pass cannot be overridden` by GCP, PlayCanvas, or mocopi.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.

Optional enhancement preflight:

- GCP/service: `service-pass/fail/not-included`.
- PlayCanvas: `playcanvas-pass/fail/not-included`; PlayCanvas must consume an
  exported runtime package snapshot.
- mocopi: `mocopi-GO/DEMO-ONLY/NO-GO/not-included`; mocopi cannot promote the
  visitor path unless the packaged-PC local baseline remains pass.

## 1. Start Servers

Open PowerShell in the release folder, for example:

```powershell
cd C:\henshin-demo\gavai-henshin
```

Terminal A, Web/API:

```powershell
npm run dev
```

Expected port: `8010`.

Terminal B, Quest viewer:

```powershell
npm run dev:quest -- --port 5173
```

Keep both terminal windows open. Do not close them during the demo. Port `5173` is fixed; if it is already busy, the Quest server should fail instead of moving to another port.

Confirm both ports:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

## 2. Run Smoke

In a third PowerShell window:

```powershell
python tools/exhibition_smoke_check.py --forge
```

OK means the smoke output says the Web/API is reachable, a fresh code was generated, recall works, render placements are present, and asset failures are `0`.
The JSON should also show `preflight_gate.operator_label = local-pass`.

## 3. Generate Fresh Code

On the PC browser, open:

```text
http://127.0.0.1:8010/viewer/armor-forge/
```

Enter the visitor/demo values, click generate, and write down the new 4-digit code.

Important: use the newest code only. Do not reuse an old code from a previous run.

## 4. Open Quest

Primary USB ADB path, preferred for exhibition stability:

```powershell
adb devices -l
npm run dev:quest:adb
```

Good `adb devices -l` state:

```text
<device_id>    device ...
```

Current 2026-05-04 baseline status for the fixed code path:

- CONFIRMED: `adb devices -l` reached `Quest_3 ... device`.
- CONFIRMED: `tools/start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1&code=3601"` succeeded.
- CONFIRMED: `tools/start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser` is the preferred fresh-launch command for QA handoff.
- CONFIRMED: `adb reverse --list` included `tcp:5173` and `tcp:8010`.
- CONFIRMED: `adb shell am start ... http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601` launched an Oculus Browser Intent.
- UNVERIFIED: headset-visible demo state after the Browser opens.

If it says `unauthorized`, stop here. Put on the Quest, accept the "Allow USB debugging?" prompt, unplug/replug USB if needed, then run `adb devices -l` again. Only continue when the state is `device`.

Then open this exact baseline URL in Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

If stale armor, old code, or old UI state appears, close the Quest Browser tab and relaunch with:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

For a fresh visitor run, replace `3601` with the newest 4-digit code from Web Forge. If using manual entry, open `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1` and enter the newest code in Quest.

After ADB reverse is active, run the headset-path smoke once:

```powershell
python tools/exhibition_smoke_check.py --code 3601 --require-adb-reverse
```

For a fresh visitor run, replace `3601` with the newest code. The result should keep `preflight_gate.operator_label = local-pass` and `preflight_gate.checks.adb_reverse_ok = true`.

LAN fallback, when PC and Quest are on the same network:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

Do not use LAN fallback if the venue Wi-Fi blocks device-to-device access. Use USB ADB reverse instead.

Verify the Quest URL contains the fresh 4-digit code. If using the manual-entry URL, enter the fresh code in Quest.

## 5. What OK Looks Like

For the current fixed-code Quest pass, check these in the headset first:

| Item | Pass condition | Status |
| --- | --- | --- |
| Code `3601` | Quest shows code `3601` and recalls the intended suit. | UNVERIFIED |
| Equipment complete | Operator can see the equipment-complete/ready state. | UNVERIFIED |
| VR start | VR start enters the demo flow without blocking. | UNVERIFIED |
| Audio | Audio/voice cue is audible on Quest. | UNVERIFIED |
| Record/replay | Recording and replay controls respond, and playback can be started. | UNVERIFIED |
| Mirror | Mirror view is visible and useful for checking the visitor look. | UNVERIFIED |
| Armor position | Armor is attached to the body with no obvious major offset, float, or scale break. | UNVERIFIED |

Then confirm the broader show-day pass:

- PC Web Forge shows a fresh 4-digit code and Quest link.
- Quest page shows the same code as Web Forge after URL recall or manual entry.
- When opened without `code=...`, Quest does not show armor before recall.
- Runtime/route status says OK, with `runtime-render-placement.v1`.
- Armor appears with no obvious missing major parts.
- Japanese UI labels/status are visible for the visitor/operator happy path.
- Quest transform shows deposition particles, short light trails, and part reveal shine; it must not read as a simple fade-in.
- Existing 3D model quality check is `pass` or has a written show-day waiver; no unreviewed GLB is being shown.
- Major armor parts look attached to the body, not floating, oversized, or badly shifted.
- The frozen package has passed tri-view-conscious cool-suit QA or has a written show-day waiver.
- Transform/replay controls respond.
- Replay proof or latest trial record is created.
- The demo is still OK if GCP is not used and mocopi is disabled. Those are enhancement lanes, not the baseline pass.
- Record optional labels only after the local result: `service-pass/fail/not-included`,
  `playcanvas-pass/fail/not-included`, and
  `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.

## 6. If Something Fails

### Failure 1: Server Will Not Start Or Port Is Busy

Do this:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

Close old demo terminals, then restart Terminal A and Terminal B. If `5173` is busy, stop the conflicting process and restart on `5173`.

### Failure 2: Quest Cannot Open The URL

Try ADB fallback:

```powershell
adb devices -l
npm run dev:quest:adb
```

If `adb devices -l` shows `unauthorized`, put on the headset and accept USB debugging. If the prompt does not appear, run:

```powershell
adb kill-server
adb start-server
adb devices -l
```

Then reconnect USB or change cable/port until the state is `device`. After `npm run dev:quest:adb` succeeds, open `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601` or replace `3601` with the fresh Web Forge code.

### Failure 3: Quest Shows Old Armor Or Code Recall Fails

Do this in order:

1. Close the Quest Browser tab.
2. Generate a new code on Web Forge.
3. Reopen the Quest URL.
4. Enter only the newest code.
5. If it still looks stale, clear Quest Browser site data for the demo URL and retry.

## 7. Escalate

If the same failure happens twice, stop changing settings. Save the terminal output, write down the code used, take a photo/screenshot of the Quest state, and switch to the last-known-good package or offline fallback.
