# Exhibition PC Runbook - 2026-05-04

Goal: run the demo on a different PC at an external exhibition, not only on the development machine.

North star:

```text
Web establishes the suit.
Quest verifies the transformation.
Replay records the experience.
```

2026-05-05 carry-in update:

- Use `docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md` as the
  canonical stage table for the current Windows / GPU-unknown / Quest-USB /
  shared-network / mocopi-hardware-available situation.
- The required lane is still external-PC `local-pass` with BODY/static fallback.
  Web serviceization is an anshin lane, not the required show-floor dependency.
- mocopi starts `DEMO-ONLY` or `not-included`; it becomes `mocopi-GO` only after
  the stage plan's physical pairing, calibration, Quest diagnostic, latency,
  centerline, consent/retention, and 60-second fallback gates pass.

## Demo Target

Public flow:

1. Visitor/operator opens Web Forge on the exhibition PC.
2. Web Forge creates a suit and shows a 4-digit code.
3. Quest Browser opens the Quest runtime.
4. The same 4-digit code loads the same suit in VR.
5. Voice/trigger starts the transformation trial.
6. Replay keeps the trial as an artifact.

The exhibition PC must therefore be able to run:

- Web/API/static server on `8010`.
- Quest Vite server on `5173`.
- Quest connection through USB `adb reverse` first, with same-LAN URL only as a fallback.
- Local GLB/asset serving without missing files.
- A repeatable smoke check before doors open.

## Lane Policy

Required local preflight:

- The external PC local lane is the required baseline.
- `local-pass` is prerequisite for visitor operation.
- `local-pass cannot be overridden` by GCP, PlayCanvas, or mocopi results.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.

Optional enhancement preflight:

- GCP/service uses `service-pass/fail/not-included`. The service endpoint must
  pass the same forge, recall, replay, and no-local-path checks before it is
  used as a service rehearsal.
- PlayCanvas uses `playcanvas-pass/fail/not-included`. PlayCanvas must consume
  an exported runtime package snapshot and must not write canonical suit,
  placement, code, or Replay state.
- mocopi uses `mocopi-GO/DEMO-ONLY/NO-GO/not-included`. mocopi cannot promote
  the visitor path unless the packaged-PC local baseline remains pass and the
  BODY/static fallback is rehearsed.

## Exhibition PC Requirements

Install before venue setup:

- Windows 11 recommended.
- Python 3.11+ or current project Python.
- Node.js/npm with `npx`.
- Git or a prepared repo zip.
- Android Platform Tools or Meta Quest Developer Hub for `adb`.
- Chrome/Edge on the PC.
- Meta Quest Browser on the headset.
- USB-C data cable for the preferred Quest path.

Recommended hardware:

- Dedicated GPU if available.
- Stable AC power.
- At least 16 GB RAM.
- Wired internet if provider APIs are needed.
- Local Wi-Fi only if using LAN mode.

## Files To Bring

Minimum package:

- repo working tree or release zip
- `viewer/assets/armor-parts/**`
- `viewer/assets/vrm/**`
- `sessions/new-route/**` if pre-generated suits/codes are needed
- `examples/suitspec.sample.json`
- `.env.example`
- `.env.demo.example`
- this runbook
- `docs/modeler-fit-micro-adjustments-2026-05-04.md`
- `docs/modeler-exhibition-readiness-risks-2026-05-04.md` and any `qa/waivers/` records for bbox/fidelity demo exceptions

Do not depend on files outside the repo path. Paths in public/operator docs should be repo-relative unless explicitly marked as local machine examples.

## Setup On The Exhibition PC

From PowerShell:

```powershell
cd C:\path\to\gavai-henshin
npm install
python -m pip install -e ".[dev]"
python tools/validate_exhibition_release_package.py
python -m pytest tests/test_new_route_api.py tests/test_runtime_package.py tests/test_quest_recall_render_contract.py -q
npm test
```

If the exhibition PC needs explicit environment wiring, copy the local demo template:

```powershell
Copy-Item .env.demo.example .env
```

The demo template contains only local fallback values for `8010`, `5173`, JSON/local stores, and blank provider secrets. Do not put venue secrets or provider keys into a public commit.

If tests fail because Python cannot import local modules, use:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

## One Command Local Stack Helper

For show-floor setup, prefer the bundled local helper. It starts missing local
services, reuses already-listening ports with a warning, applies ADB reverse,
optionally launches the Quest Browser URL, runs the service deployment contract
in `local` mode, and writes reports under `qa\local-stack-*`.

```powershell
.\tools\start_exhibition_local_stack.ps1 -RecallCode 3601 -LaunchQuest -RequireAdbReverseSmoke
```

For a PC-only dry run without a headset:

```powershell
.\tools\start_exhibition_local_stack.ps1 -SkipAdbReverse -SkipSmoke
```

The helper does not kill existing processes. If `8010` or `5173` is occupied
by the wrong service, stop that process manually, then rerun the helper.

## Start Servers

Use two terminals.

Terminal A, Web/API/static:

```powershell
cd C:\path\to\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"
```

Terminal B, Quest runtime:

```powershell
cd C:\path\to\gavai-henshin
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Confirm ports:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

Expected:

```text
0.0.0.0:8010
0.0.0.0:5173
```

If `5173` is already occupied, the Quest Vite server fails fast. Stop the conflicting process and restart; Quest setup assumes `5173` for USB ADB reverse and headset URLs.

## Preferred Quest Path: USB ADB Reverse

Use this path even when the venue Wi-Fi is unavailable, client-isolated, or not trusted. USB ADB reverse makes the Quest Browser see the exhibition PC services as Quest-local `localhost`.

1. Confirm both local services are listening on fixed ports:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

Expected fixed ports:

```text
8010 Web/API/static
5173 Quest viewer
```

2. Connect the Quest by USB-C data cable.
3. Put on the headset and accept the USB debugging prompt. If shown, enable "Always allow from this computer".
4. Check the device state from PowerShell:

```powershell
adb devices -l
```

Expected good state:

```text
<device_id>    device ...
```

Blocked state:

```text
<device_id>    unauthorized ...
```

If the state is `unauthorized`, do not run the demo yet. Recover in this order:

1. Put on the headset and accept the "Allow USB debugging?" prompt.
2. Unplug/replug USB, then run `adb devices -l` again.
3. If no prompt appears, run:

```powershell
adb kill-server
adb start-server
adb devices -l
```

4. If it is still `unauthorized`, change USB port/cable, confirm Quest Developer Mode is enabled in the Meta Quest mobile app or Meta Quest Developer Hub, then reconnect.

Only continue when `adb devices -l` shows `device`.

5. Apply reverse port forwarding:

```powershell
npm run dev:quest:adb
```

For a fixed-code QA pass that also opens a fresh Quest Browser tab, run:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

For a fresh visitor code, replace `3601` with the newest 4-digit Web Forge code. `-CacheBust` prevents stale Quest Browser tabs from reusing an old viewer state. `-LaunchBrowser` sends an Android browser intent to the headset, but it still does not prove the headset is awake, worn, or visibly in WebXR; the operator must confirm the headset view.

This script forwards both required local services:

```text
Quest localhost:5173 -> PC localhost:5173
Quest localhost:8010 -> PC localhost:8010
```

6. Open this exact baseline URL in Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

For a fresh visitor run, replace `code=3601` with the newest 4-digit code generated by Web Forge. If opening without a code is needed for manual entry, use `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1` and enter the newest code in Quest.

This is the preferred exhibition path because it avoids venue Wi-Fi surprises. The PC browser still uses `http://127.0.0.1:8010/viewer/armor-forge/`; the Quest Browser uses `http://localhost:5173/...` after ADB reverse.

## Fallback Quest Path: Same LAN

Use this only when USB is unavailable and the PC/Quest can actually reach each other on the same Wi-Fi/LAN. If the venue Wi-Fi blocks client-to-client traffic, return to USB ADB reverse.

1. Put PC and Quest on the same network.
2. Allow Windows firewall prompts for Python/Node.
3. Find the PC LAN IP:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

4. Open in Quest Browser:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=3601
```

For a fresh visitor run, replace `code=3601` with the newest Web Forge code.

For microphone/WebXR policies, HTTPS LAN mode may be required:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp <PC_LAN_IP>
.\tools\start_quest_lan_https.ps1 -ApiTarget http://127.0.0.1:8010
```

Install/trust `config\quest-lan-root-ca.cer` on the Quest before relying on this path.

## Smoke Check

After both servers are running:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools/smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
python tools/exhibition_smoke_check.py --forge
```

After the Quest is connected and `npm run dev:quest:adb` has been run, use the stronger show-floor gate:

```powershell
python tools/exhibition_smoke_check.py --forge --require-adb-reverse
```

Expected result:

- `validate_exhibition_release_package.py` has `missing_count=0` and `pattern_gap_count=0`.
- If the package still has a `.git` directory, `untracked_count=0` unless this is an explicitly approved working-tree snapshot.
- `smoke_web_glb_load.py` has no failures and `previewFallbackParts=0`.
- Web/API health OK.
- Quest page OK.
- New 4-digit code generated.
- Recall returns `runtime-render-placement.v1`.
- 18 render placements.
- `missing_selected_variant_key_count == 0`.
- `runtime_surface_failure_count == 0`.
- `preflight_gate.operator_label == local-pass`.
- When `--require-adb-reverse` is used, `preflight_gate.checks.adb_reverse_ok == true` and the JSON includes both `tcp:5173` and `tcp:8010` reverse mappings.
- Optional lanes remain `not-included` unless a separate GCP, PlayCanvas, or
  mocopi rehearsal has passed after the local smoke.

Then open Web Forge:

```text
http://127.0.0.1:8010/viewer/armor-forge/
```

Generate one fresh code and use that same code in Quest.

## Day-Of Schedule

Use concrete checkpoints.

### T-2 days: 2026-05-06

- Freeze the demo branch or release zip.
- Confirm all required GLBs/assets are present.
- Run full test gate on the exhibition PC or a matching spare.
- Confirm the headset can load through USB ADB reverse.
- Prepare one fallback code and one fresh-code demo path.

### T-1 day: 2026-05-07

- Dry-run the full visitor flow twice.
- Check power, cable strain relief, headset battery, controllers, and audio.
- Clear stale Quest Browser tabs/site data.
- Save screenshots of Web/Quest success states.
- Print or pin this runbook.

### Show Day: 2026-05-08

- Start Web/API server.
- Start Quest Vite server on `5173`.
- Connect Quest by USB, confirm `adb devices -l` shows `device`, then run ADB reverse.
- Run `python tools/exhibition_smoke_check.py --forge`.
- Confirm the smoke result is `local-pass`.
- Generate a fresh visitor code.
- Confirm Quest loads that code.
- Record optional lane labels after local pass only:
  `service-pass/fail/not-included`, `playcanvas-pass/fail/not-included`, and
  `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.
- Keep the two terminal windows visible to the operator.

## Recovery

If Quest cannot open `localhost:5173`:

```powershell
adb devices -l
npm run dev:quest:adb
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 5173,8010 }
```

If `adb devices -l` shows `unauthorized`, the PC is not trusted by the headset yet. Put on the headset, accept USB debugging, then rerun `adb devices -l`. If no prompt appears, unplug/replug USB and restart the ADB server:

```powershell
adb kill-server
adb start-server
adb devices -l
```

If Web Forge works but Quest cannot recall the code:

- Confirm Web/API server is still on `8010`.
- Generate a new 4-digit code.
- Close old Quest Browser tabs.
- Reopen the Quest URL and enter the new code.

If the Quest page shows old armor:

- Close the Quest Browser tab.
- Clear site data if needed.
- Reopen the Quest URL.
- Use only the newest code generated during the current run.

If GLB or runtime gate fails:

```powershell
python tools/smoke_web_glb_load.py
python tools/validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

Do not treat fallback/proxy rendering as a public-demo pass.

If the validator fails only on untracked files in the development checkout, do not hide that with `--skip-git-tracking`. Either track the files before creating a git/archive release, or make an explicit local working-tree snapshot:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json --allow-untracked-for-local-snapshot > qa\exhibition_release_package_snapshot_report.json
```

The snapshot report must travel with the package. The `untracked` list is the operator's audit checklist for files that a normal git-only archive would miss.

## Current Known Risks

Use `docs/modeler-exhibition-readiness-risks-2026-05-04.md` as the owner record for bbox/fidelity public-demo risk, waiver protocol, and QA evidence packaging.

- Physical Quest hand/controller clearance still needs a headset pass.
- Web service/GCP hosting is a later readiness lane; the exhibition fallback must still run entirely from the local PC package.
- mocopi is a hardware-enhancement lane, not a show-blocking dependency until a headset-and-sensor rehearsal passes.
- BBox warnings remain for chest, waist, upperarm, and shin.
- P1 limb line variants for upperarm, forearm, hand, and thigh are still ordered but not delivered.
- Some older docs contain mojibake and should not be used as the operator-facing runbook.

## Exit Criteria For Exhibition Readiness

- External PC setup succeeds from this runbook without dev-machine-only paths.
- `exhibition_smoke_check.py --forge` passes.
- Web generates a fresh code.
- Quest loads that fresh code.
- 18 GLB requests return 200.
- Operator can recover from server restart, Quest tab reset, and stale code.
- Replay artifact path is defined and exportable.
