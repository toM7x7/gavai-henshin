# Project Structure And Exhibition Roadmap - 2026-05-04

Purpose: organize the directory and module migration plan before moving to an
external exhibition PC and before publishing a GitHub-ready branch. This file is
planning-only. It does not authorize moving code yet.

Scope of this pass:

- Sources inspected: local `docs/`, `tools/`, and `tests/` only.
- Responsibility: new docs only.
- Do not revert or overwrite other agents' work.
- Do not move files until a release owner has a reviewed stage manifest, a
  clean-clone result, and an external-PC local baseline plan.

The working principle is:

```text
Web creates the suit.
Quest runs the transform trial.
Replay preserves the experience.
```

GCP, PlayCanvas, and mocopi are optional lanes around that spine. They cannot
override a missing local exhibition pass.

## Current Planning Inputs

Important local documents already define the release posture:

- `docs/exhibition-pc-release-package-manifest-2026-05-04.md`: what must be in
  the package and what must not be staged.
- `docs/exhibition-pc-transfer-readiness-2026-05-04.md`: external-PC transfer
  gates and local fallback evidence.
- `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`: service, GCP,
  PlayCanvas, and mocopi labels and gates.
- `docs/web-ui-service-gcp-playcanvas-direction-2026-05-03.md`: service shape,
  GCP mapping, and PlayCanvas adapter limits.
- `docs/web-service-phase0-task-breakdown-2026-05-02.md`: contract freeze and
  store/artifact boundary tasks.
- `docs/quest-mocopi-exhibition-spike-2026-05-04.md`: mocopi evidence packs,
  fallback, and hardware gate.
- `tools/list_release_stage_candidates.py`,
  `tools/export_release_stage_manifest.py`,
  `tools/validate_release_stage_manifest.py`: read-only GitHub staging helpers.
- `tools/validate_exhibition_release_package.py`,
  `tools/exhibition_smoke_check.py`,
  `tools/smoke_web_glb_load.py`,
  `tools/validate_service_deployment_contract.py`: local and service gates.
- `docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md`: current
  carry-in PC and mocopi stage table, including the latest `MOCOPI 7f` evidence
  and remaining `runtime_anchor` blocker.
- `docs/repo-cleanup-github-readiness-2026-05-05.md`: executable cleanup and
  GitHub readiness checklist for this updated sequence.
- `docs/exhibition-pc-web-service-execution-plan-2026-05-05.md`: PM-owned
  execution plan that separates local exhibition PC, USB/LAN Quest sharing,
  Web service/GCP, PlayCanvas, and GitHub push readiness.

Observed from `git status`: the worktree is heavily shared and dirty across
runtime code, assets, docs, tests, generated artifacts, and local QA output.
Therefore the first cleanup goal is classification, not physical moves.

## Current Status Update - 2026-05-05

Latest local docs record a real step forward, but not a public GO:

- Quest replay evidence exists at `qa\logs\quest-3601-20260505-035451`.
- Quest reached `browser_archive_replay_mirror_active`.
- Quest diagnostics showed `MOCOPI 7f`, `bodySimFrames=7`, and
  `replayMotionSource=mocopi`.
- Replay/body-sim refs are now portable under `/sessions/...`; this fixes the
  prior Windows absolute path fetch problem for mocopi-derived replay QA.
- Centerline QA still reports `fail/runtime_anchor`.
- The mocopi lane is therefore `mocopi-DEMO-ONLY` at best. Treat the current
  evidence as mocopi-derived replay/body-sim proof, not as live visitor-route
  mocopi or true body-following armor proof.

Updated next order:

1. Fix `centerlineQa=fail/runtime_anchor`.
2. Capture BODY baseline, MOCOPI candidate, and fallback recovery evidence
   packs with the fixed centerline behavior.
3. Stabilize the local exhibition PC package and Quest sharing path.
4. Prefer USB ADB reverse; rehearse LAN sharing only as a fallback or explicit
   venue requirement.
5. Prove external-PC `local-pass` with a fresh Web Forge code.
6. Rehearse Web service/GCP as a separate anshin lane.
7. Validate PlayCanvas only as a runtime-package snapshot adapter.
8. Only then perform GitHub cleanup/staging.

GitHub cleanup is deliberately last. A tidy repository that still has
`runtime_anchor` drift, missing BODY/fallback packs, or no external-PC
`local-pass` is tidy but not exhibition-ready.

For the PM execution checklist, use
`docs/exhibition-pc-web-service-execution-plan-2026-05-05.md` as the current
top-level order. This roadmap remains the structural rationale; the 2026-05-05
execution plan is the run sheet.

2026-05-05 execution assumptions are now fixed in that run sheet: Windows
exhibition PC, unknown GPU, Quest USB available, shared network treated as
unstable, and mocopi settings screen available. After development items 2-4,
the next move is not GitHub cleanup; it is candidate package freeze, current-PC
`dev-pass`, separate Windows-PC `local-pass`, optional mocopi UDP/settings
probe, then HTTPS Web service/GCP validation.

## Non-Negotiable Gates

1. `local-pass` is required for visitor operation.
2. `local-pass` must be proven on the external exhibition PC or a clean
   equivalent PC, not only on the development machine.
3. Core Web -> Quest -> Replay must run without live GCP, internet, provider
   secrets, PlayCanvas, or mocopi.
4. Web/API port `8010` and Quest Vite port `5173` are the documented baseline.
5. Final proof uses a fresh Web-generated 4-digit code. Code `3601` is
   historical evidence only.
6. Optional lane labels are recorded after local:
   `service-pass/fail/not-included`,
   `playcanvas-pass/fail/not-included`,
   `mocopi-GO/DEMO-ONLY/NO-GO/not-included`.
7. Optional successes do not override local failure.

## Short-Term Plan

Target window: 2026-05-05 to 2026-05-08.

### 1. Fix Centerline Before Treating mocopi As GO

`MOCOPI 7f` proves that mocopi-derived replay/body-sim frames can reach Quest.
It does not clear the placement gate while centerline remains
`fail/runtime_anchor`.

Immediate centerline checklist:

- Open the current fresh-code Quest URL with `qa=centerline`, `debug=1`, and a
  timestamp cache buster.
- Confirm `centerlineQa.present=true`.
- Confirm whether the classification is still `runtime_anchor`.
- If classification is `runtime_anchor`, fix recenter / anchor capture /
  runtime anchor readiness before tuning armor parts or GLB offsets.
- Re-run the same code path after the fix and capture a new Quest debug
  snapshot with `-QaCenterline -Screencap`.
- Do not promote mocopi above `DEMO-ONLY` until centerline no longer reports
  `runtime_anchor`, `hard_sync_centerline`, `mixed`, or `fail`.

Suggested commands:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline -Screencap
python tools\prepare_mocopi_rehearsal_preflight.py --code <FRESH_CODE> --report-json
```

Exit condition: a named evidence folder under `qa\logs\quest-<code>-<timestamp>`
shows the fixed centerline result, current Quest URL, authorized ADB path if
USB is selected, and the relevant `uxState`.

### 2. Capture BODY / MOCOPI / Fallback Evidence Packs

After the centerline issue is fixed or explicitly waived as non-public
operator-only risk, collect the three packs in this order:

1. BODY baseline: mocopi off or ignored; Quest route works with BODY/static.
2. MOCOPI candidate: Quest reports usable `MOCOPI <n>f` or `MOCOPI+LIVE`.
3. Fallback recovery: disable/bypass mocopi and return to BODY/static within
   60 seconds without changing the public visitor URL.

Commands:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline -Screencap
python tools\evaluate_mocopi_evidence_pack.py --body-baseline qa\logs\quest-<body> --mocopi-candidate qa\logs\quest-<mocopi> --fallback-recovery qa\logs\quest-<fallback> --report-json
python tools\export_mocopi_rehearsal_plan.py --evaluation-json qa\mocopi-evidence-evaluation.json --out qa\mocopi-rehearsal-plan-latest.json --report-json
```

Exit condition: the evaluator is not `mocopi-NO-GO`. If it remains
`mocopi-DEMO-ONLY`, keep mocopi operator-only and keep BODY/static as public
fallback.

### 3. Prove The Local Package Before Service Work

On the development machine or release candidate:

```powershell
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py -q
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_pretransfer.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_pretransfer.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_pretransfer.json --fail-on fail
```

Then prove the exact branch/tag/commit from a clean clone before calling it
GitHub-ready. A working-tree snapshot may be useful for emergency transfer, but
a normal GitHub release must pass without required untracked runtime files.

### 4. Move To External PC As A Fixed Path

Use:

```text
C:\henshin-demo\gavai-henshin
```

Install and run from that path:

```powershell
npm ci
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
python tools\validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
```

Start Web/API and Quest:

```powershell
python tools\run_henshin.py serve-dashboard --port 8010 --root "$PWD"
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

USB ADB route:

```powershell
adb devices -l
npm run dev:quest:adb
adb reverse --list
```

Local smoke:

```powershell
python tools\exhibition_smoke_check.py --forge --require-adb-reverse
```

Pass condition: fresh code, recall success, `runtime-render-placement.v1`, at
least 18 render placements, no selected-variant mismatch, no runtime surface
failure, `unsafe_public_ref_count=0`, and `preflight_gate.operator_label =
local-pass`.

### 5. Rehearse Web Service As An Optional Lane

Only after external-PC `local-pass`, run the service lane. This is an anshin
lane, not the show-floor baseline:

```powershell
python tools\validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http
python tools\export_gcp_phase0_service_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json
python tools\validate_exhibition_service_gate.py qa\gcp-phase0-service-contract-latest.json qa\service-deployment-contract-external.json --exhibition-smoke-report qa\exhibition_smoke_check_external_pc.json --report-json
```

Exit condition: `service-pass`, `service-fail`, or `not-included` is recorded
without changing the local visitor route.

### 6. Freeze Classification Before GitHub Cleanup

Run read-only classification after the gates above:

```powershell
python tools/list_release_stage_candidates.py --json > qa\release_stage_candidates_latest.json
python tools/export_release_stage_manifest.py --out qa\release-stage-manifest-latest.json --sample-limit 5
python tools/validate_release_stage_manifest.py --manifest qa\release-stage-manifest-latest.json --report-json
python tools/export_release_stage_review_markdown.py --out docs\release-stage-review-latest.md --report-json
```

Do not use the JSON as an automatic `git add` list. Use it as a review map:

- `release-critical`: runtime, config examples, schemas, smoke/validator tools,
  sample JSON, and tests.
- `operator-docs`: exhibition runbooks, transfer docs, checklists, service and
  mocopi plans.
- `armor-assets`: `viewer/assets/armor-parts/**`, catalog, variants, toppings,
  sidecars, previews, and GLBs referenced by the catalog.
- `qa-evidence`: only curated shareable manifests or explicitly promoted named
  reports.
- `local-qa-artifact`, `generated-artifact`, `local-workspace`,
  `user-feedback-media`: do not stage for a normal GitHub release.
- `reference-docs` and `reference-artifact`: stage only when promoted by name.
- `ambiguous`: blocks push review until classified or excluded.

### 7. Keep Move Units Larger Than Individual Files

Recommended movement/staging units:

| Unit | Paths | Why it moves together |
|---|---|---|
| Release hygiene | `.gitignore`, release classification docs | Makes later status readable without changing runtime behavior. |
| Runtime contract | `src/henshin/**`, `schemas/**`, runtime samples, contract tests | Forge, recall, runtime package, and replay identity must stay consistent. |
| Web/Quest viewer | `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`, `viewer/shared/**`, `vite.quest.config.js` | Web-generated code, Quest recall, and runtime placement are one user flow. |
| Exhibition tools | `tools/run_henshin.py`, `tools/exhibition_smoke_check.py`, `tools/validate_*`, `tools/export_*`, ADB/LAN scripts | Operators need the same gates that developers use. |
| Armor assets | `viewer/assets/armor-parts/**`, `variant_catalog.json`, `.modeler.json`, GLB previews/source | Missing one catalog-referenced asset breaks clone equivalence. |
| Operator docs | `docs/exhibition-*`, `docs/quest-*`, required Web service and mocopi docs | External PC operation needs written fallback and labels. |
| Curated QA evidence | `qa/shareable-qa-evidence-latest.json` and named promoted reports only | Raw screenshots, logs, ADB dumps, and local paths are not release inputs. |

Do not split `viewer/assets/armor-parts/**` by visual convenience. The safer
unit is catalog plus all referenced base, variant, topping, sidecar, and preview
assets. If size becomes a problem, create a separate asset package with a
manifest and validator output; do not silently omit paths from the GitHub clone.

## Medium-Term Plan

Target window: 2026-05-08 to 2026-05-17+.

### 1. Contract Freeze For Serviceization

Before GCP or PlayCanvas work, freeze the public `/v1` surface:

- `POST /v1/suits/forge`
- `GET /v1/quest/recall/{code}`
- `POST /v1/trials`
- `POST /v1/trials/{trial_id}/events`
- `GET /v1/trials/{trial_id}/replay`

Public responses must contain logical identities and portable artifact refs:
`suit_id`, `suit_version_id`, `recall_code`, `trial_id`, manifest id,
runtime package version, catalog version, selected variants, render placements,
texture/model gates, replay refs, and cache policy.

Public responses must not contain `C:\...`, `file://`, `/tmp/...`, machine LAN
URLs, `local_path`, provider secrets, raw provider payloads, raw mocopi sensor
IDs, or debug-only state.

### 2. Add Store And Artifact Boundaries

Keep the current local implementation as the source of truth while shaping the
future service boundary:

| Boundary | Local now | GCP later |
|---|---|---|
| Suit metadata | JSON/repository interface | Cloud SQL |
| Suit version/runtime package | local manifest snapshot | Cloud SQL row plus GCS artifact |
| Recall code | local code index | Cloud SQL `recall_code` table |
| GLB/texture/preview | `viewer/assets` and local artifacts | Cloud Storage |
| Trial/events | local session/event files | Cloud SQL rows or event archive |
| Replay | portable JSON bundle | Cloud SQL index plus GCS artifacts |
| Secrets | `.env` / `.env.demo.example` blanks | Secret Manager |
| Async jobs | synchronous/local for now | Cloud Tasks after idempotency exists |

### 3. GCP Staging Without Forking Truth

Minimum GCP shape:

- One Cloud Run service hosting the current API/UI boundary.
- One Cloud SQL database for metadata and lookup.
- One Cloud Storage bucket namespace for GLBs, manifests, previews, textures,
  motion, replay, voice/audio, and exports.
- One Cloud Tasks queue only after slow jobs have idempotency keys.
- Secret Manager and least-privilege service accounts.
- Structured logs with suit id, recall code, manifest id, runtime package
  version, trial id, job id, and mocopi session ref when applicable.

External service readiness:

```powershell
python tools\validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http
python tools\export_gcp_phase0_service_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json
python tools\validate_exhibition_service_gate.py qa\gcp-phase0-service-contract-latest.json qa\service-deployment-contract-external.json --exhibition-smoke-report qa\exhibition_smoke_check_external_pc.json --report-json --strict
```

Even when this passes, the exhibition baseline remains the local external-PC
loop unless a separate service release is declared.

### 4. PlayCanvas Adapter Only

PlayCanvas may be useful as preview, editor, visual QA, or replay viewer. It
must consume exported runtime package snapshots and must not own variant
selection, placement policy, recall lookup, catalog acceptance, replay
derivation, or mocopi provenance.

Gate:

```powershell
python tools\export_runtime_package_snapshot.py --api-base http://127.0.0.1:8010 --code <FRESH_CODE> --out qa\runtime-package-<CODE>.snapshot.json --report-json
python tools\validate_playcanvas_snapshot.py qa\runtime-package-<CODE>.snapshot.json --report-json
```

## Move-Prohibited And Defer List

Do not move, rename, or split these before the external-PC local baseline and
GitHub stage review pass:

- Canonical armor module names: `helmet`, `chest`, `back`, `waist`, and the
  left/right shoulder, upperarm, forearm, hand, thigh, shin, and boot parts.
- `/v1` forge and Quest recall payload shapes.
- `runtime-render-placement.v1` fields and Web/Quest placement parity.
- Fixed ports `8010` and `5173` without updating ADB reverse, URLs, runbooks,
  validators, and smoke scripts together.
- `viewer/assets/armor-parts/**` catalog structure unless the catalog validator
  and smoke gate are updated in the same reviewed unit.
- Replay artifact portability rules.
- `.env.demo.example` semantics around public/local variables and blank secrets.
- ADB/Quest setup scripts used by the runbook.

Defer these until after local-pass:

- Microservices, GKE, service mesh, Pub/Sub/Eventarc fanout, BigQuery analytics,
  CDN strategy, signed URL policy, and Firestore as canonical history.
- PlayCanvas as a platform rewrite.
- Cloud-only visitor path.
- True live mocopi body-following as the default visitor path.
- Broad historical artifact cleanup such as tracked `.playwright-*` or
  `tests/.tmp/**` removal. That needs a separate reviewed `git rm --cached`
  plan and must not be mixed into runtime release commits.
- Raw `qa/logs/**`, screenshots, ADB dumps, replay records, browser dumps, Vite
  build output, local server logs, local workspaces, and user feedback media.

## Quest/Web Shared Contract

The contract between Web, Quest, and Replay is the migration lock.

Web owns:

- Suit creation.
- `suit_id`, `suit_version_id`, generated 4-digit `recall_code`.
- Selected variants/toppings normalized to catalog keys.
- Preview and artifact pointers.

Quest owns:

- Reading by recall code.
- Rendering the runtime package snapshot.
- Recording transform UX state, physical Quest diagnostics, and visible trial
  evidence.
- Never mutating variant selection, placement policy, code lifecycle, or replay
  history.

Replay owns:

- Durable experience record with `suit_id`, `suit_version_id`, `recall_code`,
  `trial_id`, manifest/runtime package version, transform events, motion source,
  artifacts, consent, and retention status.
- Portable artifact refs: bundle-relative, `gs://`, or approved `https://`.

Shared response requirements:

- `runtime_package.render_placements` is authoritative.
- Mirrored placement records may exist in `asset_pipeline` and
  `visual_layers.armor_overlay`, but they must not disagree with the selected
  runtime package placements.
- Quest fields remain explicit:
  `quest_coordinate_space`, `quest_rig_offset_m`,
  `quest_surface_offset_clamped_m`.
- A stale or reused code is not final exhibition evidence.
- Fallback rendering can be diagnostic, but it must not be counted as a public
  pass when GLBs are missing or corrupt.

## mocopi Introduction Procedure

mocopi is hardware enhancement, not the baseline.

Order:

1. Decide `local-pass/fail` on the external PC with mocopi off or ignored.
2. If `local-pass`, capture BODY fallback baseline evidence.
3. Rehearse mocopi in an operator-only lane: imported JSON first, then physical
   sensors if the import path is stable.
4. Capture MOCOPI candidate evidence.
5. Disable/bypass mocopi and capture fallback recovery evidence.
6. Evaluate and label `mocopi-GO`, `mocopi-DEMO-ONLY`, `mocopi-NO-GO`, or
   `not-included`.
7. Promote nothing into the public route unless the result is `mocopi-GO`.

Evidence capture:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline -Screencap
```

Required packs:

- BODY fallback baseline: Quest route works without mocopi.
- MOCOPI candidate: Quest diagnostic shows usable `MOCOPI <n>f` or
  `MOCOPI+LIVE`, not `MOCOPI 0f`.
- Fallback recovery: BODY/static returns within 60 seconds without changing the
  public visitor URL.

Evaluate:

```powershell
python tools\evaluate_mocopi_evidence_pack.py --body-baseline qa\logs\quest-<code>-<body> --mocopi-candidate qa\logs\quest-<code>-<mocopi> --fallback-recovery qa\logs\quest-<code>-<fallback> --report-json
python tools\export_mocopi_rehearsal_plan.py --evaluation-json qa\mocopi-evidence-evaluation.json --out qa\mocopi-rehearsal-plan-latest.json --report-json
python tools\package_mocopi_evidence.py --evaluation-json qa\mocopi-evidence-evaluation.json --rehearsal-plan qa\mocopi-rehearsal-plan-latest.json --evidence-dir qa\logs\quest-<code>-<timestamp> --out qa\mocopi-evidence-package-latest.json --report-json
```

GO threshold:

- Six sensors stable for at least 60 seconds before calibration.
- No left/right swap after calibration.
- Median visible latency `<= 120 ms`.
- p95 visible latency `<= 250 ms`.
- Dropped/frozen motion `< 2%`.
- No freeze above `500 ms`.
- BODY/static fallback under 60 seconds.
- Consent and retention notes for raw motion and voice/audio.

If any of these are not proven, label as `DEMO-ONLY` or `NO-GO` and keep the
public route on BODY/static.

## GCP And Local Fallback Policy

Local fallback is the show-floor baseline:

- Web/API: `http://127.0.0.1:8010`
- Quest USB: `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>`
- Quest LAN fallback:
  `http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>`
- Local JSON/files remain valid until the service boundary is proven.
- Last-known-good package must be labeled and kept separately.

GCP is the durable service/archive lane:

- It may become `service-pass` only after HTTPS external-mode validation,
  forge/recall/replay smoke, no-local-path checks, and the exhibition service
  gate pass.
- It must preserve the same `/v1` payload semantics as the local route.
- It must not become a new canonical truth for variant selection, Quest
  placement, or Replay derivation without the local contract being updated and
  tested first.
- If GCP fails, record `service-fail` and continue local Web -> Quest -> Replay
  if local remains pass.

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Dirty worktree mixes unrelated work | Accidental staging or rollback | Use read-only stage manifests; stage by unit; never revert unrelated changes. |
| Required files remain untracked | GitHub clone misses runtime or assets | Clean-clone gate without snapshot flags before GitHub-ready label. |
| Generated evidence is staged | Privacy leak, repo bloat, unstable diffs | Stage only curated QA manifests; keep raw logs/screenshots local. |
| Armor assets split from catalog | Quest/Web loads fallback or missing GLB | Move catalog plus referenced assets as one unit; run GLB smoke. |
| Quest `adb unauthorized` | False API/browser diagnosis | Treat as setup gate; accept headset prompt before debugging app behavior. |
| Old code/browser cache used | Stale pass | Use fresh code and timestamped Quest URL; close old Quest tabs. |
| GCP chosen too early | Contract drift and show-floor fragility | Freeze `/v1` and local fallback first. |
| mocopi over-claimed | Visitor flow breaks or misleading claim | Require BODY baseline, MOCOPI candidate, fallback recovery, and conservative labels. |
| Port changes | Quest URL/ADB mismatch | Keep `8010`/`5173`; if changed, update scripts, env, runbooks, and smoke gates together. |

## Release Owner Checklist

Before moving directories or pushing GitHub cleanup:

- Stage manifest exists and has no unresolved `ambiguous` release blockers.
- `release-critical`, `operator-docs`, and `armor-assets` are reviewed as
  complete units.
- Raw QA, local workspaces, generated artifacts, and user feedback media are
  explicitly excluded.
- `git diff --cached --check` passes for the staged set.
- Clean clone runs `npm ci` and Python install.
- Package validator, GLB smoke, Quest whole-suit audit, and local forge smoke
  pass.
- External PC or clean equivalent records `local-pass`.
- Optional lanes are labeled after local and cannot override local.
- Rollback/last-known-good package exists and is named.

Until all items pass, directory cleanup should remain a docs-backed plan and
classification exercise, not a physical move.
