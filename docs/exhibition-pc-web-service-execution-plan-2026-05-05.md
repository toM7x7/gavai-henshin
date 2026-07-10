# Exhibition PC And Web Service Execution Plan - 2026-05-05

Purpose: restructure the carry-in PC, LAN sharing, Web service, GCP,
PlayCanvas, and GitHub push preparation into one PM-owned execution order.

This document is docs-only. It does not authorize code edits or file moves.
The parent-side work on `viewer/quest-iw-demo/quest-demo.js` and
`tests/test_quest_recall_render_contract.py` is treated as in flight and must
not be touched by this plan.

## Fixed User Conditions

Use these assumptions for the next execution pass:

- Exhibition PC is Windows. The working target path is
  `C:\henshin-demo\gavai-henshin`, and the operator commands are PowerShell.
- GPU is unknown. Do not assume discrete GPU, high FPS, WebGPU, or a
  heavyweight 3D/cloud preview path. The pass/fail gate is package validation,
  GLB load smoke, whole-suit audit, and Quest/browser visibility. If the canvas
  is black, unstable, or too slow, downgrade to BODY/static or the
  last-known-good package before trying optional lanes.
- Quest can be wired. USB ADB reverse is the primary Quest sharing route.
  Same-LAN sharing is a fallback only.
- Shared network exists but is unstable. Do not make LAN, hosted Web service,
  PlayCanvas, or GCP mandatory for visitor operation. The show-floor baseline
  must survive with local PC + USB Quest + BODY/static fallback.
- mocopi settings screen is available. Use it only after the local BODY/static
  route is working: set Motion Send destination to the PC IPv4 address and UDP
  port `12351`, then prove transport with `tools/probe_mocopi_udp.py`. Do not
  store raw motion payloads unless consent and retention are explicitly
  recorded.

## Current Implementation Read

From local docs/tools:

- Local Web/API/static server baseline is port `8010`.
- Quest Vite baseline is port `5173`.
- USB ADB reverse is the primary Quest sharing path.
- Same-LAN URL is fallback when USB is unavailable and the venue network allows
  device-to-device access.
- `tools/start_exhibition_local_stack.ps1` can start/reuse the local Web/API
  and Quest servers, run the local service deployment contract check, set ADB
  reverse unless skipped, and run exhibition smoke.
- `tools/validate_service_deployment_contract.py` explicitly separates
  `local` mode from `external` mode. Local mode allows localhost/private LAN;
  external mode rejects localhost, private LAN, and plaintext HTTP.
- `tools/export_gcp_phase0_service_contract.py` and
  `tools/validate_exhibition_service_gate.py` exist for the Web service/GCP
  lane, but they do not replace local exhibition pass.
- `tools/validate_playcanvas_snapshot.py` exists for PlayCanvas snapshot
  import validation. PlayCanvas is an adapter, not source of truth.
- `tools/audit_repo_readiness.py`,
  `tools/list_release_stage_candidates.py`,
  `tools/export_release_stage_manifest.py`, and
  `tools/validate_release_stage_manifest.py` exist for GitHub push readiness.
- Current mocopi state remains `DEMO-ONLY` at best until centerline,
  BODY/MOCOPI/fallback packs, and external-PC local pass are all proven.

## PM Decision

The work must proceed in this order:

```text
1. Stabilize local exhibition PC path
2. Rehearse Quest sharing: USB first, LAN fallback second
3. Record local-pass on a separate PC or clean equivalent
4. Freeze Web/Quest/Replay service contract
5. Rehearse Web service/GCP as optional anshin lane
6. Validate PlayCanvas only as snapshot adapter
7. Run GitHub push cleanup after the runtime evidence exists
```

GitHub cleanup is not the first task. It is the final packaging operation after
the exhibition route has a verified shape.

## After Development 2-4 Transition Gate

Interpret "after development 2-4" as: centerline work has been addressed or
explicitly labeled, BODY/MOCOPI/fallback evidence work has a current owner, and
the Web/Quest/Replay contract is stable enough to create one candidate package.
At that point, stop adding feature work and move through the hardware/service
path below.

1. Freeze one candidate package.

```powershell
git status --short
python tools\validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json > qa\service-deployment-contract-local-candidate.json
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_candidate.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_candidate.json
```

2. Rehearse on the current development PC, but label it `dev-pass`, not
   `local-pass`.

```powershell
.\tools\start_exhibition_local_stack.ps1 -RequireAdbReverseSmoke -LaunchQuest
```

3. Move the exact same candidate to a separate Windows exhibition PC or clean
   equivalent. Use `C:\henshin-demo\gavai-henshin`; do not depend on
   `C:\dev\codex`, local browser caches, local QA logs, or untracked files
   unless the package was intentionally a dated working-tree snapshot.

4. Prove unknown-GPU viability on that PC before optional hardware. Required
   evidence is package validation, GLB smoke, whole-suit audit, and browser or
   Quest visibility. A weak GPU does not block a BODY/static demonstration if
   the fallback route is visible and stable.

5. Connect Quest by USB first. Require `adb devices -l` to show `device`, then
   require reverse mappings for `5173` and `8010`. The headset URL is
   `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>`.

6. Treat LAN as recovery for USB trouble or operator need. Because the shared
   network is assumed unstable, LAN success is useful evidence but not the
   public baseline. If LAN fails because of firewall, client isolation, or
   DHCP/IP churn, keep the route on USB and record LAN as `not-included` or
   `lan-fail`.

7. Use the mocopi settings screen only after BODY/static local evidence exists.
   On the Windows PC, find the PC IPv4 address, allow UDP `12351` if needed,
   set the mocopi app to Motion Send, and send to `<PC_IPV4>:12351`.

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
python tools\probe_mocopi_udp.py --port 12351 --seconds 20 --out qa\mocopi-udp-probe-external-pc.json --report-json
python tools\serve_mocopi_body_sim_latest.py --udp-port 12351 --http-port 8021
```

If the probe receives packets, that is only `mocopi transport received`. It is
not `mocopi-GO`. `MOCOPI 7f` plus unresolved `centerlineQa=fail/runtime_anchor`
keeps the lane `DEMO-ONLY` at best until BODY baseline, MOCOPI candidate,
fallback recovery, centerline, latency, calibration, consent, and retention all
pass.

8. Record external-PC `local-pass` only after a fresh Web-generated code opens
   on Quest and smoke reports `preflight_gate.operator_label=local-pass`.

9. Move to Web service only after external-PC `local-pass`. External mode must
   be HTTPS, must not use localhost/private LAN/plain HTTP, and must not become
   the required show-floor path while the network is considered unstable.

10. Run GitHub cleanup only after the local, optional service, PlayCanvas, and
    mocopi lane labels are written.

## Lane Split

| Lane | Role | Required for visitors | Promotion rule |
|---|---|---:|---|
| Local exhibition PC | Show-floor baseline on `8010` and `5173`. | Yes | Must reach `local-pass`. |
| USB Quest sharing | Primary headset path using ADB reverse. | Preferred | Must be rehearsed or formally rejected. |
| LAN Quest sharing | Fallback path using `http://<PC_LAN_IP>:5173/...` or HTTPS cert mode. | No | Use only after USB trouble or venue requirement. |
| Web service | Hosted/API rehearsal and future service path. | No | Only after local-pass. |
| GCP | Candidate infrastructure for durable service. | No | Cloud Run/SQL/GCS/Tasks/Secrets mapping only after contract freeze. |
| PlayCanvas | Preview/editor/QA adapter. | No | Snapshot consumer only; no write authority. |
| GitHub cleanup | Publishable branch and release staging. | Yes for clone path | After evidence and lane labels are known. |

## Phase 1: Local Exhibition PC Baseline

Goal: prove the demo can run without internet, GCP, provider secrets,
PlayCanvas, or mocopi.

Target path:

```text
C:\henshin-demo\gavai-henshin
```

Checklist:

- [ ] Choose exactly one source package: clean clone, dated zip, or explicit
  working-tree snapshot.
- [ ] Copy to `C:\henshin-demo\gavai-henshin`.
- [ ] Confirm this is a normal Windows user environment. Do not require admin
  rights except for firewall/certificate recovery steps.
- [ ] Run `node --version`, `npm --version`, `python --version`, and
  `adb version`.
- [ ] Install with `npm ci` for clone/release packages. Use `npm install` only
  for emergency local snapshots and record that choice.
- [ ] Install Python package with `python -m pip install -e ".[dev]"`.
- [ ] Record GPU as `unknown`, `integrated`, or `discrete` only if visible from
  Windows UI or `Get-CimInstance Win32_VideoController`. Do not change the
  operator route based on that label until smoke evidence exists.
- [ ] Run package validation and GLB smoke:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_external_pc.json --fail-on fail
```

Pass criteria:

- `missing_count=0`.
- `pattern_gap_count=0`.
- No GLB smoke failures.
- `previewFallbackParts=0`.
- Whole-suit audit does not fail.

If this phase fails, stop optional lanes and use last-known-good BODY/static.
If it passes but the browser or Quest view is visually unstable on the unknown
GPU, label the package `local-degraded` and keep the public route on the
lightest BODY/static presentation until a better PC is available.

## Phase 2: Local Stack And Quest Sharing

Goal: make PC and Quest agree on the same fresh code.

Primary command:

```powershell
.\tools\start_exhibition_local_stack.ps1 -RequireAdbReverseSmoke -LaunchQuest
```

Use explicit recall code only for rehearsal/debug:

```powershell
.\tools\start_exhibition_local_stack.ps1 -RecallCode <CODE> -RequireAdbReverseSmoke -LaunchQuest
```

Manual fallback commands:

```powershell
$env:PYTHONPATH = "$PWD\src"
python tools\run_henshin.py serve-dashboard --port 8010 --root "$PWD"
npm run dev:quest -- --host 0.0.0.0 --port 5173
adb devices -l
npm run dev:quest:adb
adb reverse --list
python tools\exhibition_smoke_check.py --forge --require-adb-reverse > qa\exhibition_smoke_check_external_pc.json
```

USB pass:

- [ ] Web/API listens on `8010`.
- [ ] Quest Vite listens on `5173`.
- [ ] `adb devices -l` shows `device`, not `unauthorized`.
- [ ] `adb reverse --list` includes `tcp:5173 tcp:5173` and
  `tcp:8010 tcp:8010`.
- [ ] Quest opens
  `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>`.
- [ ] `preflight_gate.operator_label=local-pass`.

LAN fallback:

Use only when USB cannot be restored or the operator explicitly needs LAN.
Because the shared network is assumed unstable, do not spend visitor time
debugging LAN until the USB route has either passed or been explicitly rejected.

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

Quest LAN URL:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>
```

LAN pass:

- [ ] PC and Quest are on the same reachable network.
- [ ] Windows Firewall allows Node/Vite and Python.
- [ ] Venue Wi-Fi does not block client-to-client traffic.
- [ ] Quest can load Quest Vite and the API can still recall the fresh code.
- [ ] If WebXR/mic policy requires HTTPS, use the LAN cert scripts and record
  the trust setup:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp <PC_LAN_IP>
.\tools\start_quest_lan_https.ps1 -ApiTarget http://127.0.0.1:8010
```

If USB and LAN both fail, the exhibition route is `local-fail`.
If USB passes and LAN fails, the exhibition route can still be `local-pass`
with `lan-fail` or `lan-not-included`.

## Phase 3: Evidence And Optional mocopi Status

Goal: keep the mocopi state honest while Web/Quest/Replay stabilizes.

Current rule:

- `MOCOPI 7f` is useful evidence.
- `centerlineQa=fail/runtime_anchor` keeps mocopi at `DEMO-ONLY` at best.
- BODY/static fallback remains the public baseline.

Checklist:

- [ ] Fix or explicitly waive the current centerline issue.
- [ ] Capture BODY baseline evidence.
- [ ] Before sensor pairing, configure mocopi Motion Send from the settings
  screen to the Windows PC IPv4 address and UDP port `12351`.
- [ ] Capture mocopi UDP reachability without retaining raw motion:

```powershell
python tools\probe_mocopi_udp.py --port 12351 --seconds 20 --out qa\mocopi-udp-probe-external-pc.json --report-json
```

- [ ] Capture MOCOPI candidate evidence only after UDP reachability and
  BODY/static baseline are recorded.
- [ ] Capture fallback recovery evidence.
- [ ] Evaluate:

```powershell
python tools\evaluate_mocopi_evidence_pack.py --body-baseline qa\logs\quest-<body> --mocopi-candidate qa\logs\quest-<mocopi> --fallback-recovery qa\logs\quest-<fallback> --report-json > qa\mocopi-evidence-evaluation.json
python tools\export_mocopi_rehearsal_plan.py --evaluation-json qa\mocopi-evidence-evaluation.json --out qa\mocopi-rehearsal-plan-latest.json --report-json
```

Exit label:

- `mocopi-GO`: all gates pass, including centerline, fallback, latency,
  calibration, left/right, consent, and retention.
- `mocopi-DEMO-ONLY`: operator-led only; public visitors stay BODY/static.
- `mocopi-NO-GO`: do not use mocopi.
- `not-included`: no mocopi lane for this package.

## Phase 4: Web Service Contract Freeze

Goal: separate serviceization from the show-floor local baseline.

Freeze these contracts before GCP or PlayCanvas decisions:

- `POST /v1/suits/forge`
- `GET /v1/quest/recall/{code}`
- `POST /v1/trials`
- `POST /v1/trials/{trial_id}/events`
- `GET /v1/trials/{trial_id}/replay`
- runtime package with selected variants, render placements, texture/model
  gates, artifact refs, catalog version, and runtime package version.

Contract rules:

- Public responses must not contain `C:\...`, `file://`, private LAN URLs,
  raw provider payloads, raw motion identifiers, or `local_path`.
- The 4-digit code is a short-lived lookup handle, not durable identity.
- Quest reads by code and does not mutate selection, placement, or replay.
- Replay stores portable refs: bundle-relative, `gs://`, or approved HTTPS.
- Debug surfaces may exist, but visitor payloads remain portable and minimal.

Local contract validation:

```powershell
python tools\validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json > qa\service-deployment-contract-local-latest.json
```

This phase can proceed in parallel with docs/review, but it must not block
local-pass.

## Phase 5: Web Service / GCP Anshin Lane

Entry condition: local exhibition PC has `local-pass`.

Goal: prove hosted service shape without making it the required show path.

Checklist:

- [ ] Candidate Web/API/Quest URLs are HTTPS.
- [ ] External URLs are not localhost, private LAN, `.local`, or HTTP.
- [ ] `.env.demo.example` contains placeholders or blank secrets only.
- [ ] CORS and `QUEST_API_TARGET` align.
- [ ] Hosted forge/recall routes return the same public contract shape.
- [ ] Hosted replay/artifact refs remain portable.

Commands:

```powershell
python tools\validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http > qa\service-deployment-contract-external.json
python tools\export_gcp_phase0_service_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json > qa\gcp-phase0-service-contract-external.json
python tools\validate_exhibition_service_gate.py qa\gcp-phase0-service-contract-external.json qa\service-deployment-contract-external.json --exhibition-smoke-report qa\exhibition_smoke_check_external_pc.json --report-json > qa\exhibition-service-gate-external.json
```

GCP split:

- Cloud Run: current API/UI boundary.
- Cloud SQL: suits, versions, recall codes, trials, events, replay indexes,
  consent, retention, generation jobs.
- Cloud Storage: GLBs, manifests, runtime snapshots, previews, textures,
  replay scripts, motion, voice/audio, exports.
- Cloud Tasks: async generation/validation only after idempotency exists.
- Secret Manager: provider keys and deployment secrets.

Explicit deferrals:

- No GKE or service mesh.
- No durable Firestore as the main suit/replay store.
- No cloud-only show path before local-pass.
- No provider secrets in the required local show path.

## Phase 6: PlayCanvas Adapter Decision

Entry condition: service contract is stable enough that exported snapshots are
boring.

Allowed:

- preview/editor/QA adapter
- replay viewer for exported runtime packages
- visual QA harness for accepted GLBs

Forbidden:

- variant selection authority
- placement policy authority
- recall-code lifecycle
- replay derivation
- mocopi provenance or consent/retention ownership
- write-back mutation endpoint without a separately reviewed service contract

Commands:

```powershell
python tools\export_runtime_package_snapshot.py --api-base http://127.0.0.1:8010 --code <FRESH_CODE> --out qa\runtime-package-<CODE>.snapshot.json --report-json
python tools\validate_playcanvas_snapshot.py qa\runtime-package-<CODE>.snapshot.json --report-json
```

Exit label:

- `playcanvas-pass`: snapshot consumer passes and has no write authority.
- `playcanvas-fail`: attempted and failed.
- `not-included`: no PlayCanvas lane for this package.

## Phase 7: GitHub Push Readiness

Entry condition:

- local-pass exists
- USB or LAN Quest route is recorded
- service lane is labeled
- PlayCanvas lane is labeled or not included
- mocopi lane is labeled
- raw QA policy is known

Run read-only audit first:

```powershell
python tools\audit_repo_readiness.py --report-json > qa\repo-readiness-audit-latest.json
python tools\list_release_stage_candidates.py --json > qa\release_stage_candidates_latest.json
python tools\export_release_stage_manifest.py --out qa\release-stage-manifest-latest.json --sample-limit 5
python tools\validate_release_stage_manifest.py --manifest qa\release-stage-manifest-latest.json --package-report qa\exhibition_release_package_external_pc.json --report-json > qa\release-stage-validation-latest.json
python tools\export_release_stage_review_markdown.py --out docs\release-stage-review-latest.md --report-json
```

Stage groups:

- `stage-candidate`: `release-critical`, `operator-docs`, `armor-assets`.
- `manual-review`: curated QA manifests, reference docs/artifacts, ambiguous
  paths.
- `do-not-stage`: local QA artifacts, raw logs, user media, local workspaces,
  generated artifacts, dependency caches, `.env`.

Commit order:

1. Docs roadmap / operator docs.
2. Runtime contract and tests.
3. Web/Quest viewer and shared runtime.
4. Exhibition tools.
5. Armor assets and catalog.
6. Curated QA manifests only if release owner approves.
7. Artifact cleanup only as a separate reviewed decision.

Before commit:

```powershell
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

Before push:

```powershell
git status --short --branch
git log --oneline --decorate -n 12
```

Do not push if:

- required runtime files are still untracked for a GitHub clone path
- `ambiguous` paths remain unresolved
- raw `qa/logs/**`, screenshots, ADB dumps, server logs, or browser dumps are
  staged
- `.env` or real secrets are staged
- local-pass is missing
- service/PlayCanvas/mocopi labels are implied but not written

## PM Status Board

Use this board for the next handoff.

| Item | Status | Evidence |
|---|---|---|
| User conditions | fixed | Windows, GPU unknown, Quest USB available, network unstable, mocopi settings available |
| Local exhibition PC package | pending | `qa\exhibition_release_package_external_pc.json` |
| GPU viability | unknown | `Get-CimInstance Win32_VideoController`, GLB smoke, visual check |
| Web/API `8010` | pending | `tools/start_exhibition_local_stack.ps1` report dir |
| Quest Vite `5173` | pending | `tools/start_exhibition_local_stack.ps1` report dir |
| USB ADB reverse | pending | `adb-reverse.txt`, smoke `--require-adb-reverse` |
| LAN fallback | optional / unstable | IP, firewall, Quest URL, HTTPS cert note if used |
| local-pass | pending | `qa\exhibition_smoke_check_external_pc.json` |
| centerline | in progress | latest `centerlineQa` summary |
| mocopi settings | available / pending | Motion Send to `<PC_IPV4>:12351`, `qa\mocopi-udp-probe-external-pc.json` |
| mocopi | DEMO-ONLY at best | `MOCOPI 7f`; `centerlineQa=fail/runtime_anchor`; missing GO gates |
| Web service | not included until local-pass | external contract/gate JSON |
| GCP | planning only | phase0 contract export |
| PlayCanvas | adapter only | runtime package snapshot validation |
| GitHub readiness | after local-pass | repo readiness audit and stage manifest |

The PM rule is simple: if a lane is not evidenced, label it `not-included` or
`fail`. Do not let an interesting partial success silently become a show-floor
promise.
