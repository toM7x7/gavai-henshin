# Exhibition External PC + mocopi Stage Plan - 2026-05-05

Purpose: make the carry-in path executable for the current operator situation:
Windows PC, unknown GPU, Quest USB available, shared network available, and
mocopi hardware available but not used yet.

Decision spine:

```text
Local external PC first.
Quest over USB first.
Web service is the anshin lane.
mocopi starts operator-only and promotes to GO only with evidence.
BODY/static fallback is mandatory at every step.
```

## Lane Definitions

| Lane | Label | Role | Can block visitors? |
|---|---|---|---|
| External PC local | `local-pass/fail` | Required show-floor baseline on the carried-in Windows PC. | Yes. `local-fail` blocks public operation. |
| Local fallback | BODY/static | Required recovery route without internet, cloud, provider secrets, or mocopi. | Yes. Missing fallback blocks mocopi promotion. |
| Web service anshin lane | `service-pass/fail/not-included` | Hosted/service rehearsal for future confidence. It is allowed to be comforting, not required. | No, unless explicitly promoted in a separate service release. |
| PlayCanvas adapter | `playcanvas-pass/fail/not-included` | Preview/QA consumer of exported runtime packages. | No. |
| mocopi | `mocopi-GO/DEMO-ONLY/NO-GO/not-included` | Hardware enhancement after local-pass. | Only `mocopi-GO` can enter the visitor route. |

## External PC Carry-In Stage Table

| Stage | Owner | Action | Pass | Fallback / stop |
|---|---|---|---|---|
| 0. Freeze package | Release owner | Choose one dated zip, git checkout, or working-tree snapshot. Copy it to `C:\henshin-demo\gavai-henshin`. Carry QA JSONs with it. | The external PC has one fixed repo path and no dependency on `C:\dev\codex`. | Use last-known-good package. Do not repair from the dev PC during visitor time. |
| 1. Install runtime | External PC operator | Run `node --version`, `npm --version`, `python --version`, `adb version`, then `npm install` and `python -m pip install -e ".[dev]"`. | Node, Python, and adb are available on the exhibition PC. | Stop optional lanes until runtime is fixed. |
| 2. Validate package | Release owner / asset QA | Run release validator and GLB smoke from the external PC. | `missing_count=0`, `pattern_gap_count=0`, no GLB failures, `previewFallbackParts=0`. | `local-fail`; use last-known-good BODY/static package. |
| 3. Start local servers | Web / Quest owner | Web/API/static on `8010`; Quest Vite on `5173`; confirm with `Get-NetTCPConnection`. | Both fixed ports listen on the external PC. | Do not change ports casually. If changed, update adb reverse, Quest URL, docs, and smoke commands together. |
| 4. Prove Quest transport | Quest owner | Prefer USB-C data cable, accept USB debugging, require `adb devices -l` = `device`, then reverse `tcp:5173` and `tcp:8010`. | Quest opens `http://localhost:5173/...` and recalls the fresh code. | Same-LAN is fallback only after PC/Quest reachability is verified. Venue shared network is not the primary path. |
| 5. Record local-pass | Exhibition lead | Generate a fresh Web Forge code, open the matching Quest URL, and run `python tools/exhibition_smoke_check.py --forge --require-adb-reverse` when USB is selected. | `preflight_gate.operator_label=local-pass` with the fresh code. | If not local-pass, public operation stays on last-known-good BODY/static only. |
| 6. Optional lanes | Service / adapter / hardware owners | Record service, PlayCanvas, and mocopi labels after local-pass. | Optional labels are written without changing the local fallback route. | Any optional fail remains non-blocking for visitors unless local fallback is broken. |

## Commands For The Required Local Lane

```powershell
cd C:\henshin-demo\gavai-henshin
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools/smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
```

Terminal A:

```powershell
cd C:\henshin-demo\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"
```

Terminal B:

```powershell
cd C:\henshin-demo\gavai-henshin
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Quest USB:

```powershell
adb devices -l
npm run dev:quest:adb
adb reverse --list
```

Expected reverse entries:

```text
tcp:5173 tcp:5173
tcp:8010 tcp:8010
```

Show-floor smoke:

```powershell
python tools/exhibition_smoke_check.py --forge --require-adb-reverse
```

## Quest + mocopi Connection Stage Table

| Stage | Owner | Action | Pass | Fallback / label |
|---|---|---|---|---|
| Q-1. Preflight report | mocopi prep owner | Run `python tools/prepare_mocopi_rehearsal_preflight.py --code <CODE> --report-json`. | Static reception points, local ports, adb authorization/reverse, and Quest debug API are reported in one file. | If the label is `mocopi-NO-GO`, fix blockers before pairing sensors. |
| Q0a. UDP reachability | mocopi prep owner | Run `python tools/probe_mocopi_udp.py --port 12351 --seconds 20 --out qa\mocopi-udp-probe-latest.json`; send mocopi Motion data to the PC IPv4 address. | `udp-received` proves phone-to-PC transport. | If no packets arrive, fix LAN/firewall/IP/port before Quest integration. This is not yet a live Quest mocopi claim. |
| Q0c. body-sim/latest adapter | mocopi prep owner | Run `python tools/serve_mocopi_body_sim_latest.py --udp-port 12351 --http-port 8021`; send JSON fixture or parsed mocopi-like UDP. | `GET http://127.0.0.1:8021/body-sim/latest` returns derived `motion_source=mocopi` body-sim JSON. | Unknown/binary packets are rejected until a real parser is implemented. This is still rehearsal infrastructure, not `mocopi-GO`. |
| Q0b. Quest baseline | Quest owner | Use USB ADB reverse first. Require `adb devices -l` = `device`; require reverse for `5173` and `8010`. | Quest recalls the fresh Web Forge code. | If `unauthorized`, recover USB before mocopi. Same-LAN only if USB cannot be restored. |
| Q1. BODY/static evidence | Quest owner | Keep mocopi off/ignored. Run visitor route. Capture `capture_quest_debug_snapshot.ps1 -Code <CODE> -QaCenterline`. | BODY/static works and centerline QA does not fail baseline. | If this fails, mocopi is `mocopi-NO-GO`. |
| Q2. Sensor prep | mocopi operator | Charge, label, pair, and strap six sensors: head, hip, left/right wrist, left/right ankle. Confirm 60 seconds connected. | Pairing is stable before calibration. | If a sensor disconnects twice, stay `DEMO-ONLY` or `NO-GO`. |
| Q3. Calibration | mocopi operator | Calibrate facing the Quest/exhibition-PC origin. Run slow arm raise and weight shift checks. | Left/right mapping stays correct. | Recalibrate once; if still swapped, `mocopi-NO-GO`. |
| Q4. Candidate capture | mocopi + Quest owner | Run imported mocopi or physical sensor rehearsal in an operator-only lane. Capture with `-QaCenterline -Screencap`. | Quest shows `MOCOPI <n>f` or `MOCOPI+LIVE`, not `MOCOPI 0f`. | If not MOCOPI, do not claim mocopi; continue BODY/static. |
| Q5. Recovery capture | Quest owner | Disable/bypass mocopi and return to BODY/static without changing the visitor URL. | Recovery pack proves BODY/static within 60 seconds. | If recovery exceeds 60 seconds, `mocopi-NO-GO`. |
| Q6. Label | Exhibition lead | Write `mocopi-GO`, `DEMO-ONLY`, `NO-GO`, or `not-included`. | Public wording matches the label. | When uncertain, downgrade to `DEMO-ONLY` and keep BODY/static public. |

## 2026-05-05 Current-PC Status

Current-PC Quest replay lane is now good enough for mocopi-derived evidence:

- `qa\logs\quest-3601-20260505-035451` captured Quest debug and screencap.
- Quest debug shows `browser_archive_replay_mirror_active`.
- Quest debug shows `MOCOPI 7f`, `bodySimFrames=7`, and
  `replayMotionSource=mocopi`.
- Replay/body-sim paths are now portable under `/sessions/...`; this is required
  for the external-PC lane and for any later hosted Web service.

Not yet GO:

- The latest centerline result is still `fail/runtime_anchor`.
- Real-time mocopi streaming into Quest bones is not proven; this evidence is a
  mocopi-derived replay/body-sim lane.
- BODY fallback and recovery packs still need to be captured on the target
  exhibition PC.

## mocopi GO Conditions

All conditions below are required to raise mocopi from `DEMO-ONLY` to `GO`:

- External-PC `local-pass` with a fresh Web Forge code.
- BODY fallback baseline pack exists and passes.
- Physical mocopi pairing and calibration are documented.
- Six sensors stay connected for at least 60 seconds before calibration.
- Quest diagnostic shows usable `MOCOPI` frames or `MOCOPI+LIVE`.
- Median visible latency is `<= 120 ms`; p95 is `<= 250 ms`.
- Frozen/dropped motion is `< 2%`; no freeze exceeds `500 ms`.
- Slow arm raise and weight shift do not swap left/right.
- Centerline QA does not report `runtime_anchor`, `hard_sync_centerline`, `mixed`, or `fail`.
- Consent and retention notes exist for raw mocopi motion.
- BODY/static fallback recovery is proven within 60 seconds.

If any condition is missing, the result is `mocopi-DEMO-ONLY` at best. If
Quest telemetry, USB authorization, fallback recovery, or BODY baseline fails,
the result is `mocopi-NO-GO`.

## Preflight Report Tool

Before touching sensors, create the current-PC readiness report:

```powershell
python tools/prepare_mocopi_rehearsal_preflight.py --code <CODE> --report-json
```

Default output:

```text
qa/mocopi-rehearsal-preflight-latest.json
```

Use `--skip-runtime` only for documentation/static contract review. For actual
PC + Quest rehearsal, do not skip runtime checks; the report should inspect:

- required mocopi tools/docs/viewer diagnostic tokens
- `python`, `node`, `npm`, and `adb` availability
- local ports `8010` and `5173`
- `adb devices -l`
- `adb reverse --list`
- `http://127.0.0.1:8010/api/quest-debug/latest`

Interpretation:

- `mocopi-NO-GO`: do not pair sensors yet; fix listed blockers first.
- `mocopi-DEMO-ONLY`: you may run an operator-only mocopi rehearsal and collect
  BODY/MOCOPI/fallback packs, but do not make mocopi the visitor default.
- `mocopi-GO`: only possible after the evaluation JSON also proves the three
  evidence packs and manual GO gates.

## Web Service Anshin Lane

The service lane is useful because it reduces future deployment anxiety, but it
does not replace the carried-in PC for this exhibition.

Entry condition:

- External-PC `local-pass` is already recorded.

Pass condition:

- Hosted/service endpoint passes forge, recall, replay/artifact, and
  no-local-path checks with HTTPS public URLs.

Failure behavior:

- Record `service-fail` or `not-included`.
- Keep visitors on the local PC fallback.
- Do not move secrets or provider dependencies into the required show-floor
  baseline.
