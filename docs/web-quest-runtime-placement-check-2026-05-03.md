# Web/Quest Runtime Placement Check - 2026-05-03

North star: lore stays intact while the new route proves "Web establishes the suit, Quest verifies the transformation, Replay records the experience."

## Scope

This check verifies the current Web Forge -> 4-digit recall code -> Quest viewer path after adding `runtime-render-placement.v1`.

Focus areas:

- Web Forge can generate a recall code from name, height, brief, and variant selection.
- Quest can load the same code and request the same runtime package.
- Web/Quest placement data shares part size, offset, rotation, and selected variant identity.
- Remaining drift is recorded instead of hidden by fallback rendering.

## Local Servers

Observed running listeners:

```powershell
0.0.0.0:8010  # Web Forge/API, PID 74456
0.0.0.0:5173  # Quest Vite viewer, PID 89248
```

Runtime endpoint:

```text
http://127.0.0.1:8010/api/runtime-info
```

Quest LAN URL reported by the API:

```text
http://192.168.1.4:5173/viewer/quest-iw-demo/?newRoute=1
```

## Shared Code Check - Initial

Generated Web Forge code:

```text
0331
```

Input:

- display name: `Codex 0503`
- height: `182`
- archetype: `city`
- temperament: `swift`
- brief: `Web establishes the suit, Quest verifies the transformation, Replay records the experience. Cyan rescue armor with compact back and grounded boots.`

Web result:

- status: `生成完了 / Quest入力準備OK`
- Quest URL: `http://192.168.1.4:5173/viewer/quest-iw-demo/?newRoute=1&code=0331`

Quest result:

- recall input: `0331`
- recall state: `呼び出しOK: 0331 / VDA-AXIS-WEB-00-0111`
- route API: `適合監査: CODE 0331`
- route contract: `RUNTIME: 装備OK / armor-body-fit.v1 182cm / visible 18/3 / TEX palette_material / palette`
- canvas count: `1`
- WebGL/XR root children: `1`
- console warnings/errors: `0 warnings / 0 errors`
- GLB network fetches: all 18 visible armor GLBs returned `200`

Screenshots:

- `output/playwright/forge-0331-result.png`
- `output/playwright/quest-0331-recall.png`

## Shared Code Check - Post-Fix

Generated Web Forge code:

```text
3601
```

Input:

- display name: `Codex 0503 Postfix`
- height: `182`
- archetype: `city`
- temperament: `swift`
- brief included runtime placement rotation, selected variants, Quest verification, and Replay recording.

API result:

```json
{
  "placement_count": 18,
  "missing_selected_variant_key_count": 0,
  "selected_mismatch_count": 0,
  "runtime_surface_failure_count": 0,
  "invalid_overlay_parts": [],
  "sample_chest": ["chest:sleek", "chest:sleek"]
}
```

Quest browser result:

- recall input: `3601`
- recall state: `呼び出しOK: 3601 / VDA-AXIS-WEB-00-0112`
- route API: `適合監査: CODE 3601`
- route contract: `RUNTIME: 装備OK / armor-body-fit.v1 182cm / visible 18/3 / TEX palette_material / palette`
- canvas count: `1`
- console warnings/errors: `0 warnings / 0 errors`
- GLB network fetches: all 18 visible armor GLBs returned `200`

Screenshot:

- `output/playwright/quest-3601-recall.png`

## Runtime Contract Snapshot

Recall API facts for `0331`:

```json
{
  "height": 182.0,
  "overlay": 18,
  "placementContract": "runtime-render-placement.v1",
  "renderPlacementCount": 18,
  "assetPipelineMatches": true,
  "runtimeMatches": true,
  "placementParts": "back,chest,helmet,left_boot,left_forearm,left_hand,left_shin,left_shoulder,left_thigh,left_upperarm,right_boot,right_forearm,right_hand,right_shin,right_shoulder,right_thigh,right_upperarm,waist"
}
```

Representative placement values:

```text
back.target_size_m      = 0.244 / 0.224 / 0.227
back.quest_rig_offset_m = 0.000 / 0.002 / 0.070
boot.target_size_m      = 0.158 / 0.050 / 0.085
waist.target_size_m     = 0.050 / 0.050 / 0.050
```

## Fixes From This Check

1. `get_quest_recall` now re-syncs `asset_pipeline.visual_layers` and `asset_pipeline.render_contract` after runtime package normalization.
   - This fixed a regression where the top-level recall contract had `runtime-render-placement.v1`, but nested `asset_pipeline.render_contract` stayed stale.

2. `runtime_package.build_render_placements` now carries `selected_variant_key`.
   - Source priority: `generation.selected_variant_keys`, `generation.variant_asset_resolution`, module fields, sidecar `variant_key`, then variant path inference.
   - This closes the review finding where runtime placement was not self-contained even though visual assets knew the selected variant.

3. Quest pose paths now apply `render_placements[*].rotation_deg`.
   - Segment, live, armor-stand, and motion pose paths compose runtime placement rotation with the base Quest pose.

4. Runtime renderability checks now validate local GLB surfaces.
   - Missing/corrupt local GLBs fail `can_render_runtime_suit` instead of being hidden by Quest fallback.
   - Remote URLs remain allowed because they cannot be validated locally.

5. Web/Quest variant identity now resolves selected variants before stale canonical `asset_ref`.
   - This prevents `selected_variant_key=helmet:sleek` from rendering `helmet.glb`.

## Remaining Risks

- Desktop browser confirmation passed, but headset-side hand/controller clearance still needs a physical Quest pass.
- Some current GLB bounding boxes still warn against target envelope:
  - `chest` z about `-12.7%`
  - `waist` x about `-10.1%`
  - `left_upperarm` and `right_upperarm` x about `-11.5%`
  - `left_shin` and `right_shin` x about `-12.0%`

Decision: Web/Quest code recall is working, placement data is self-contained, Quest consumes runtime rotation, and local GLB gate hardening is in place. Promotion to full "placement parity pass" still waits for physical Quest headset review and bbox warning cleanup.

## Physical Quest Checklist - External Exhibition PC

Use this when the final demo PC is not the current development machine. Treat every checked box as evidence; write down the exact PC name, network name, LAN IP, ports, URL, recall code, and pass/fail notes.

### 0. External PC Baseline

- [ ] Windows external exhibition PC is on AC power, sleep disabled, and the repo is present at `C:\dev\codex\gavai-henshin` or the operator has recorded the actual path.
- [ ] Python 3.10+ is available: `python --version`.
- [ ] Node.js/npm is available: `node --version` and `npm --version`.
- [ ] Project dependencies are installed on that PC:

```powershell
cd C:\dev\codex\gavai-henshin
npm ci
python -m pip install -e .
```

- [ ] Optional for USB path: `adb version` works from a new PowerShell window.
- [ ] Optional for same-Wi-Fi path: Quest and PC are on the same SSID, guest/client isolation is off, and the operator can open Windows Firewall prompts.

### 1. Choose Connection Mode

Use exactly one path first. Do not mix modes until the first path is understood.

Same Wi-Fi / LAN mode:

- Use when the Quest can reach the PC over the exhibition Wi-Fi.
- Pros: no USB cable during demo.
- Cons: needs correct LAN IP, firewall allow rules, and HTTPS/cert if microphone/WebXR policy requires a secure origin.

USB adb reverse mode:

- Use when Wi-Fi is locked down, isolated, unstable, or the LAN IP keeps changing.
- Pros: Quest Browser can open `http://localhost:5173/...`; bypasses LAN routing and most firewall problems.
- Cons: Quest must stay connected by USB or be re-reversed after reconnect.

### 2. Start PC Servers

Terminal 1, dashboard/API/static server:

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev
```

Required signal:

- [ ] Server is listening on `8010`.
- [ ] PC browser opens `http://localhost:8010/viewer/armor-forge/`.
- [ ] Windows Firewall prompt, if shown, is allowed for Private networks.

Terminal 2, Quest Vite runtime:

```powershell
cd C:\dev\codex\gavai-henshin
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Required signal:

- [ ] Server is listening on `5173`.
- [ ] If Vite moves to `5174` or another port, stop the process that owns `5173` or update every URL and adb reverse command to the actual port. Preferred exhibition default is still `5173`.
- [ ] Windows Firewall prompt, if shown, is allowed for Private networks.

Port check:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8010,5173 | Select-Object LocalAddress,LocalPort,OwningProcess
```

### 3A. Same Wi-Fi / LAN URL Setup

LAN IP discovery on the external PC:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
  Select-Object InterfaceAlias,IPAddress
```

Pick the IPv4 address for the Wi-Fi/Ethernet interface that shares the Quest network, then test from the PC:

```text
http://<PC_LAN_IP>:8010/api/runtime-info
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1
```

Headset Browser URL for LAN HTTP smoke:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

If Quest Browser blocks mic/WebXR or the experience needs a secure origin, use HTTPS/cert:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp <PC_LAN_IP>
```

Then install/trust `config\quest-lan-root-ca.cer` on the Quest device, restart Quest Browser, and launch:

```powershell
npm run dev:quest:lan
```

HTTPS Headset Browser URL:

```text
https://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

Required LAN signals:

- [ ] Quest and PC are on the same Wi-Fi or routable LAN.
- [ ] `http://<PC_LAN_IP>:5173/...` or `https://<PC_LAN_IP>:5173/...` loads the Quest page in the headset.
- [ ] Recall API requests succeed through Vite proxy; wrong `8010` setup usually shows recall/code/API errors, not a blank page.

### 3B. USB adb Reverse Setup

Connect the Quest by USB and authorize debugging inside the headset.

```powershell
adb devices
npm run dev:quest:adb
```

Expected reverse mapping:

```text
Quest localhost:5173 -> PC localhost:5173
Quest localhost:8010 -> PC localhost:8010
```

Headset Browser URL for USB mode:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

Required USB signals:

- [ ] `adb devices` shows one `device`, not `unauthorized` or `offline`.
- [ ] Quest Browser loads the page at `localhost:5173`.
- [ ] If the USB cable is replugged or the Quest sleeps, rerun `npm run dev:quest:adb`.

### 4. Smoke Checklist

Run this after either LAN or USB setup.

- [ ] PC Web Forge opens: `http://localhost:8010/viewer/armor-forge/`.
- [ ] Generate a fresh suit and record the four-character Quest recall code. Do not reuse an old code as evidence for the external PC.
- [ ] Quest Browser opens the chosen headset URL.
- [ ] Before entering a recall code, armor is not permanently shown by default.
- [ ] Enter the fresh recall code in Quest UI and confirm recall state shows `OK` for that code.
- [ ] Confirm debug output includes `RUNTIME DIAGNOSTIC`.
- [ ] Confirm diagnostic gate is `gate: OK`, placement count is nonzero, rotation count is nonzero, GLB count is expected, and fallback count is `0` unless an intentional fallback is being tested.
- [ ] Press the in-VR armor-stand/preview control only after recall; armor appears in preview and can be hidden again.
- [ ] Run voice/mock trigger once; transformation armor appears during active playback rather than as idle permanent armor.
- [ ] Start VR, check head/hand clearance physically: helmet does not block view, hands are not hidden by oversized armor, shoulders/shins/boots do not float or rotate backward.
- [ ] Record pass/fail notes for rotation, placement offset, scale, GLB gate, frame smoothness, mic permission, and recovery steps used.

### 5. Wrong Port / Wrong URL Recovery

If Quest shows 404:

- [ ] Check that the headset URL uses `5173` for the Quest runtime, not `8010`.
- [ ] Open `/viewer/quest-iw-demo/`, not `/viewer/armor-forge/`, in the headset.
- [ ] If Vite auto-selected `5174`, stop the old `5173` process or explicitly use the actual port in URL and adb reverse.

If the page loads but recall fails:

- [ ] Confirm dashboard/API is listening on `8010`.
- [ ] Open `http://localhost:8010/api/runtime-info` on the PC.
- [ ] In LAN mode, open `http://<PC_LAN_IP>:8010/api/runtime-info` on the PC and verify firewall allowed inbound access.
- [ ] In USB mode, rerun `npm run dev:quest:adb` so both `5173` and `8010` are reversed.
- [ ] Generate a new four-character code in Web Forge and retry; do not use stale evidence.

If the page is blank or assets fail:

- [ ] Hard refresh PC browser, then close/reopen the Quest Browser tab.
- [ ] Restart both servers in order: `npm run dev`, then `npm run dev:quest -- --host 0.0.0.0 --port 5173`.
- [ ] Confirm the Quest debug panel reports `RUNTIME DIAGNOSTIC` with GLB count and fallback count.
- [ ] If fallback count is not `0`, capture the console line `[Quest runtime diagnostic]` and the failed GLB path before changing assets.

If LAN mode is blocked:

- [ ] Switch to USB adb reverse and use `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1`.
- [ ] If USB mode works, record the LAN blocker as Wi-Fi isolation, firewall, certificate trust, or unknown network policy.
