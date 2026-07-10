# Repo Cleanup And GitHub Readiness - 2026-05-05

Purpose: make the next repository cleanup executable without breaking the
exhibition path or overwriting other agents' work.

Scope:

- This is a docs-only planning artifact.
- Do not revert existing changes.
- Do not move runtime files yet.
- Use local `docs/`, `tools/`, and `tests/` as the source of planning truth.

Current status:

- Quest MOCOPI evidence improved: `MOCOPI 7f`, `bodySimFrames=7`, and
  `replayMotionSource=mocopi` have been observed in current-PC Quest replay QA.
- The evidence folder named in docs is
  `qa\logs\quest-3601-20260505-035451`.
- The remaining blocker is centerline QA:
  `centerlineQa=fail/runtime_anchor`.
- Current preflight posture is `mocopi-DEMO-ONLY` at best. It is not
  `mocopi-GO`, not live public mocopi, and not proof that armor follows the
  body correctly.

Updated execution order:

```text
centerline fix
-> BODY/MOCOPI/fallback evidence packs
-> external PC local-pass
-> Web service anshin lane
-> GitHub cleanup and staging
```

## 0. Stop Conditions

Stop before GitHub cleanup if any of these is true:

- `centerlineQa` still reports `runtime_anchor`, `hard_sync_centerline`,
  `mixed`, or `fail` and no explicit operator-only waiver exists.
- BODY baseline pack is missing.
- MOCOPI candidate pack is missing or shows `MOCOPI 0f`.
- Fallback recovery pack is missing or cannot return to BODY/static within
  60 seconds.
- External-PC or clean-equivalent `local-pass` is missing.
- Release validator reports missing required runtime files.
- Git stage manifest still has unresolved `ambiguous` release blockers.

## 1. Centerline Fix Checklist

Goal: determine whether the current drift is runtime anchor/setup, not mocopi
transport.

Checklist:

- [ ] Start Web/API on `8010` from the target candidate package.
- [ ] Start Quest Vite on `5173`.
- [ ] Use USB ADB reverse first; require `adb devices -l` to show `device`.
- [ ] Generate a fresh Web Forge code. Do not use `3601` for final proof.
- [ ] Open Quest with `qa=centerline`, `debug=1`, and a timestamp query.
- [ ] Capture:

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code <FRESH_CODE> -QaCenterline -Screencap
```

- [ ] Confirm the new `operator-summary.txt` records:
  `telemetryCode=<FRESH_CODE>`, current URL, `xrSession` when relevant,
  `uxState`, `centerlineVerdict`, and `centerlineClassification`.
- [ ] If classification is `runtime_anchor`, fix recenter / anchor capture /
  runtime anchor readiness before changing GLBs or armor part offsets.
- [ ] If classification becomes `pass`, continue to evidence packs.
- [ ] If classification is still failing but the team proceeds, write an
  explicit operator-only waiver. Without that waiver, mocopi remains blocked at
  `DEMO-ONLY`.

Minimum pass:

```text
centerlineVerdict=pass
centerlineClassification=pass
```

or a named, time-limited waiver that says this is not public mocopi GO.

## 2. BODY / MOCOPI / Fallback Evidence Packs

Goal: prove the public fallback before any mocopi claim.

Use the same fresh code and same package where possible.

BODY baseline:

- [ ] mocopi off or ignored.
- [ ] Quest route works with BODY/static.
- [ ] Capture with `-QaCenterline`.
- [ ] Save the folder name.

MOCOPI candidate:

- [ ] Run imported mocopi replay/body-sim or physical sensor rehearsal in an
  operator-only lane.
- [ ] Quest diagnostic shows usable `MOCOPI <n>f` or `MOCOPI+LIVE`.
- [ ] Capture with `-QaCenterline -Screencap`.
- [ ] Save the folder name.

Fallback recovery:

- [ ] Disable or bypass mocopi.
- [ ] Return to BODY/static within 60 seconds.
- [ ] Do not change the public visitor URL to achieve recovery.
- [ ] Capture with `-QaCenterline`.
- [ ] Save the folder name.

Evaluate:

```powershell
python tools\evaluate_mocopi_evidence_pack.py --body-baseline qa\logs\quest-<body> --mocopi-candidate qa\logs\quest-<mocopi> --fallback-recovery qa\logs\quest-<fallback> --report-json > qa\mocopi-evidence-evaluation.json
python tools\export_mocopi_rehearsal_plan.py --evaluation-json qa\mocopi-evidence-evaluation.json --out qa\mocopi-rehearsal-plan-latest.json --report-json
python tools\package_mocopi_evidence.py --evaluation-json qa\mocopi-evidence-evaluation.json --rehearsal-plan qa\mocopi-rehearsal-plan-latest.json --evidence-dir qa\logs\quest-<mocopi> --out qa\mocopi-evidence-package-latest.json --report-json
```

Decision:

- `mocopi-GO`: only if local-pass, three packs, centerline, fallback,
  calibration, latency, left/right, consent, and retention all pass.
- `mocopi-DEMO-ONLY`: usable MOCOPI evidence exists, but one or more GO
  conditions are not proven.
- `mocopi-NO-GO`: BODY baseline, Quest telemetry, MOCOPI frames, or fallback
  recovery is missing or failing.

## 3. External PC local-pass Checklist

Goal: prove the carried-in PC can run the show without cloud, provider secrets,
PlayCanvas, or mocopi.

Fixed target path:

```text
C:\henshin-demo\gavai-henshin
```

Package and install:

```powershell
cd C:\henshin-demo\gavai-henshin
node --version
npm --version
python --version
adb version
npm ci
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
```

Validate package:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_external_pc.json --fail-on fail
```

Start servers:

```powershell
python tools\run_henshin.py serve-dashboard --port 8010 --root "$PWD"
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

Verify transport:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
adb devices -l
npm run dev:quest:adb
adb reverse --list
```

Show-floor smoke:

```powershell
python tools\exhibition_smoke_check.py --forge --require-adb-reverse > qa\exhibition_smoke_check_external_pc.json
```

Pass requires:

- [ ] `missing_count=0`.
- [ ] `pattern_gap_count=0`.
- [ ] No GLB failures.
- [ ] `previewFallbackParts=0`.
- [ ] `adb devices -l` shows `device`.
- [ ] `adb reverse --list` includes `tcp:5173` and `tcp:8010`.
- [ ] Fresh Web Forge code, not stale `3601`.
- [ ] Quest recalls that same fresh code.
- [ ] `runtime_contract=runtime-render-placement.v1`.
- [ ] `unsafe_public_ref_count=0`.
- [ ] `preflight_gate.operator_label=local-pass`.

If any item fails, record `local-fail` and use last-known-good BODY/static.

## 4. Web Service Anshin Lane

Entry condition: external-PC `local-pass` is already recorded.

Purpose: reduce future deployment anxiety. It does not replace the local
exhibition baseline.

Checklist:

- [ ] Hosted Web/API/Quest URLs are HTTPS and public.
- [ ] `.env.demo.example` does not contain real secrets.
- [ ] Public responses have no `C:\...`, `file://`, private LAN URL, raw
  provider payload, or `local_path`.
- [ ] Hosted forge can create a fresh code, or the service smoke explicitly
  uses `--service-forge`.
- [ ] Hosted recall returns the same runtime package shape as local.
- [ ] Replay/artifact refs are bundle-relative, `gs://`, or approved HTTPS.

Commands:

```powershell
python tools\validate_service_deployment_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json --check-http > qa\service-deployment-contract-external.json
python tools\export_gcp_phase0_service_contract.py --mode external --web-base-url https://<web-host> --api-base-url https://<api-host> --quest-base-url https://<quest-host> --env-file .env.demo.example --report-json > qa\gcp-phase0-service-contract-external.json
python tools\validate_exhibition_service_gate.py qa\gcp-phase0-service-contract-external.json qa\service-deployment-contract-external.json --exhibition-smoke-report qa\exhibition_smoke_check_external_pc.json --report-json > qa\exhibition-service-gate-external.json
```

Label:

- `service-pass`: external contract, reachability, forge/recall/replay, and
  no-local-path checks pass.
- `service-fail`: attempted but failed.
- `not-included`: not attempted for this exhibition path.

No service label can override `local-fail`.

## 5. GitHub Cleanup And Staging

Entry condition:

- centerline path is fixed or explicitly waived as operator-only.
- BODY/MOCOPI/fallback decision is written.
- external-PC `local-pass` exists.
- service lane is labeled.

Run read-only classification:

```powershell
python tools/list_release_stage_candidates.py --json > qa\release_stage_candidates_latest.json
python tools/list_release_stage_candidates.py --summary-json > qa\release_stage_candidates_summary_latest.json
python tools/export_release_stage_manifest.py --out qa\release-stage-manifest-latest.json --sample-limit 5
python tools/validate_release_stage_manifest.py --manifest qa\release-stage-manifest-latest.json --package-report qa\exhibition_release_package_external_pc.json --report-json > qa\release-stage-validation-latest.json
python tools/export_release_stage_review_markdown.py --out docs\release-stage-review-latest.md --report-json
```

Stage candidates:

- [ ] `release-critical`: runtime/API/viewer/tools/schemas/examples/tests
  required by the package.
- [ ] `operator-docs`: exhibition runbooks, transfer docs, service/mocopi docs,
  and this roadmap/checklist if release owner promotes them.
- [ ] `armor-assets`: catalog plus all referenced GLB, sidecar, variant,
  topping, preview, and source assets required for clone equivalence.

Manual review only:

- [ ] `qa-evidence`: stage only curated shareable manifests or named
  release-owner reports.
- [ ] `reference-docs`: stage only if they are part of the handoff.
- [ ] `reference-artifact`: stage only named visual/reference assets.
- [ ] `ambiguous`: classify or exclude before push.

Do not stage for normal GitHub release:

- [ ] `.playwright-cli/**`
- [ ] `.playwright-mcp/**`
- [ ] `tests/.tmp/**`
- [ ] `output/playwright/**`
- [ ] `qa/logs/**`
- [ ] raw screenshots, ADB dumps, server logs, Vite build outputs
- [ ] `.env`
- [ ] local workspaces such as `.claude/**` and `blender/**`
- [ ] user feedback media unless explicitly promoted

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

GitHub-ready means:

- [ ] Required runtime files are tracked or intentionally packaged separately.
- [ ] Clean clone can run `npm ci` and Python install.
- [ ] Release package validator passes without hiding required untracked files.
- [ ] GLB smoke passes.
- [ ] External-PC local-pass evidence exists.
- [ ] Raw/local QA evidence is not accidentally staged.
- [ ] Optional lane labels are recorded and cannot override local.

## 6. Recommended Commit Order

Use small reviewed commits:

1. `docs-roadmap`: updated roadmap and cleanup checklist.
2. `release-hygiene`: `.gitignore` and stage classification helpers, if
   changed by the release owner.
3. `runtime-contract`: `/v1`, runtime package, replay, validators, tests.
4. `web-quest-runtime`: Web Forge, Quest viewer, shared runtime JS, Vite config.
5. `mocopi-evidence-tools`: mocopi preflight/evaluation/package tools and
   related tests, if changed.
6. `armor-assets`: catalog and referenced armor assets.
7. `operator-docs`: runbooks and final external-PC handoff docs.
8. `curated-qa-evidence`: only shareable manifests or named release reports.

Do not mix raw QA cleanup, tracked artifact removal, asset moves, and runtime
contract changes in one commit. That makes rollback and review needlessly hard.

## 7. Final Go / No-Go Summary

Public visitor path can proceed only when:

- [ ] `local-pass` exists on the external PC or clean equivalent.
- [ ] BODY/static fallback works.
- [ ] Quest uses a fresh code.
- [ ] Replay/artifacts are portable.
- [ ] GitHub package or release snapshot includes every required runtime input.

mocopi can be shown only as:

- `mocopi-GO`: full gate pass.
- `mocopi-DEMO-ONLY`: operator-led only; public route stays BODY/static.
- `mocopi-NO-GO`: do not use mocopi.
- `not-included`: no mocopi lane in this package.

Web service can be shown only as:

- `service-pass`: hosted endpoint passed its checks.
- `service-fail`: recorded failure, visitors remain local.
- `not-included`: no hosted lane in this package.

GitHub cleanup starts after those labels are known, not before.

## 8. Current Read-Only Audit Snapshot

Command used:

```powershell
python tools\audit_repo_readiness.py --report-json --sample-limit 8
```

Current result:

| Field | Count |
|---|---:|
| total dirty / ignored paths inspected | 26884 |
| blocked do-not-stage paths | 26200 |
| tracked blocked paths | 1 |
| ignored paths | 26141 |
| stage-candidate | 596 |
| manual-review | 88 |
| do-not-stage | 26200 |

Category split:

| Category | Count | Default handling |
|---|---:|---|
| `release-critical` | 141 | stage-candidate after code review |
| `operator-docs` | 33 | stage-candidate in docs commit |
| `armor-assets` | 422 | stage-candidate in asset commit |
| `qa-evidence` | 1 | manual-review only |
| `local-qa-artifact` | 16 | do-not-stage unless promoted through shareable manifest |
| `reference-docs` | 48 | manual-review |
| `reference-artifact` | 35 | manual-review |
| `user-feedback-media` | 41 | do-not-stage |
| `local-workspace` | 2 | do-not-stage |
| `generated-artifact` | 26142 | do-not-stage |
| `ambiguous` | 3 | manual-review before push |

Current blockers:

- `blocked-paths-present`: 26200 paths match do-not-stage rules.
- `tracked-blocked-paths-present`: 1 tracked blocked path exists and can still
  be staged accidentally. Current sample is
  `tests/.tmp/quest-api-live.err.log`; leave it unstaged unless a separate
  reviewed artifact cleanup is opened.

## 9. Directory Decisions From The Audit

### `qa/`

Current count: 75 paths.

| Handling | Count | Meaning |
|---|---:|---|
| do-not-stage | 73 | raw/local/privacy-unvalidated QA evidence |
| manual-review | 2 | curated manifest candidates |

Do not stage raw QA outputs:

- `qa/*.json` such as `qa/exhibition_release_package_latest.json`,
  `qa/exhibition_smoke_check_3601_adb_latest.json`,
  `qa/gcp-phase0-service-contract-latest.json`,
  `qa/model-quality-acceptance-latest.json`, and
  `qa/release-stage-validation-latest.json`.
- `qa/replay/*.json`, raw replay summaries, replay records, runtime package
  snapshots, and local package reports.
- `qa/logs/**`, ADB dumps, Quest debug snapshots, operator summaries,
  screenshots, and local smoke media.

Manual-review candidates:

- `qa/shareable-qa-evidence-latest.json`
- `qa/release-stage-manifest-latest.json`

Rule: stage QA only when the shareable evidence validator recommends the exact
path and the release owner approves it. Never run broad `git add qa/`.

### `sessions/`

Current count: 3915 paths.

All are do-not-stage. They are generated session/provider artifacts such as
`sessions/**/artifacts/parts/*.generated.*` and `*.generation.json`.

Rule: keep `sessions/**` local or archive outside the normal GitHub release.
Do not move or delete during this cleanup pass.

### `examples/*.jpg`

Current count: 14 paths.

All are do-not-stage as `user-feedback-media`. They are ad-hoc user/reference
images, not release inputs. Keep them local unless a named image is explicitly
promoted into a curated reference artifact.

Sample blocked pattern:

```text
examples/*.jpg
```

Rule: never stage all examples media with a broad pathspec. Runtime examples
that are stage candidates are the reviewed JSON fixtures, not the loose media.

### Generated GLB / Blend / Armor Assets

Current `viewer/assets/armor-parts/**` count: 422 paths.

All current armor asset paths are stage-candidates, not blocked. This includes
catalog-referenced GLB, sidecar JSON, preview metadata, source `.blend`, and
variant/topping assets under `viewer/assets/armor-parts/**`.

Blend split:

| Path class | Count | Handling |
|---|---:|---|
| `viewer/assets/armor-parts/**/source/*.blend` and related armor asset blends | 104 | stage-candidate with armor-assets |
| `blender/review_master.blend` | 1 | do-not-stage local workspace |

Rule: generated or delivered armor assets can be staged only as an asset commit
after catalog validation and GLB smoke. Local workspace blends under
`blender/**` stay out.

Required checks before staging armor assets:

```powershell
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
python tools\smoke_web_glb_load.py --repo-root . --report-json
```

### `docs/`

Current count: 94 paths.

| Handling | Count | Meaning |
|---|---:|---|
| stage-candidate | 33 | operator docs and exhibition handoff docs |
| manual-review | 61 | reference docs and reference artifacts |

Stage-candidate docs include `docs/exhibition-*`, `docs/quest-*`, selected
operator checklists, and handoff docs required by the external-PC runbook.

Manual-review docs include broad planning/modeler/reference notes such as
`docs/base-suit-overlay-contract.md`, `docs/modeler-wave1pp-practical-handoff.md`,
`docs/armor-build-wave2-results.md`, and visual references under
`docs/_smoke_renders/**` or `docs/assets/**`.

Rule: stage operator docs by name. Do not stage all `docs/**`; reference docs
and visual artifacts need explicit release-owner promotion.

### Ambiguous Paths

Current ambiguous count: 3.

Samples:

- `.tmp-dashboard.err`
- `.tmp-quest.err`
- `.tmp-quest.out`

Rule: these are not stage candidates. Treat as manual-review blockers until
classified or explicitly left unstaged.

## 10. Safe Staging Shape

Recommended stage groups:

1. `release-critical`: runtime/API/tools/tests/schemas/sample JSON. Exclude
   parent-side Quest JS/test work unless that owner explicitly hands it over.
2. `operator-docs`: named exhibition and cleanup docs.
3. `armor-assets`: `viewer/assets/armor-parts/**` after catalog and GLB smoke.
4. `manual-review`: only individually approved shareable QA manifests,
   reference docs, or reference artifacts.

Mechanical exclude set for the next staging pass:

```text
qa/logs/**
qa/*.json
qa/replay/*.json
sessions/**
tests/.tmp/**
.playwright-cli/**
.playwright-mcp/**
dist/**
build/**
output/**
examples/*.jpg
examples/*.png
examples/*.mp4
.claude/**
blender/**
.env
```

Exception: `qa/shareable-qa-evidence-latest.json`,
`qa/release-stage-manifest-latest.json`, and `qa/mocopi-evidence-package*.json`
are still manual-review only; they are not automatic stage inputs.

## 11. Post-2-4 Integration Review: mocopi / VRM / parity

Scope reviewed from local code only: Quest recall/runtime contract tests,
mocopi motion-source tests, Python/JS body-surface parity tests, the VRM
base-suit spike doc, and the current dirty worktree. Parent-side runtime files
remain outside this docs-only update.

### 11.1 Brittle mocopi Contract Points

- `tests/test_quest_mocopi_motion_source.py` is intentionally token-heavy. It
  locks Quest JS names and flow such as `DEFAULT_MOCOPI`,
  `REPLAY_MOTION_SOURCE_MOCOPI`, `normalizeReplayMotionSource`,
  `replayMotionSourceFromRecord`, `makeReplayMotionDiagnostic`,
  `autoplayReplay`, `qaReplay`, `archiveMotionFrames`, `bodySimFrames`, and
  `replayMotionSource`.
- The mocopi claim must be provenance-backed. A replay must not present mocopi
  as working unless the diagnostic carries non-zero mocopi-derived frames such
  as `MOCOPI 1f`; BODY/static fallback must remain available.
- Fixture schema changes are high-risk because the test expects
  `examples/quest-mocopi-motion-source.fixture.json` to carry both
  `simulated_body` and `mocopi_body` cases, six sensor labels, calibration pose,
  latency thresholds, fallback order, and privacy language.
- Runtime loading order is fragile: replay motion frames are expected to load
  before body-sim fallback evaluation. A refactor that changes the order can
  silently break diagnostics even if visual replay still appears to work.

Required checks before staging mocopi changes:

```powershell
python -m pytest tests/test_quest_mocopi_motion_source.py -q
python -m pytest tests/test_evaluate_mocopi_evidence_pack.py tests/test_package_mocopi_evidence.py tests/test_validate_qa_evidence_privacy.py -q
```

Also run Quest device or ADB smoke when hardware is available, confirming
diagnostic text, fallback, and no raw identifying motion data leakage.

### 11.2 VRM / Base-Suit Obstruction Risk

- `docs/quest-vrm-base-suit-spike-2026-05-05.md` currently documents a safe
  stop: do not wire raw VRM loading into Quest first-person until a VRM-aware
  adapter and proven head/neck mask exist.
- `tests/test_quest_recall_render_contract.py` statically protects this
  boundary by checking base-suit self-view behavior, mirror/stand behavior, and
  the absence of raw VRM loader integration tokens in Quest JS.
- First-person is the failure mode to treat as blocker. Helmet, VRM head, neck,
  torso, and shoulder-line geometry can occlude the Quest camera if a future
  VRM path bypasses the current procedural base-suit visibility rules.
- Future VRM enablement should add explicit debug snapshot evidence, at minimum
  `baseSuit.source = "vrm"` and `baseSuit.firstPersonHeadNeckVisible = false`,
  before any runtime path is enabled.

Required checks before staging VRM/base-suit changes:

```powershell
python -m pytest tests/test_quest_recall_render_contract.py -q
node --check viewer/quest-iw-demo/quest-demo.js
```

Also run Quest self-view/mirror smoke for head/neck obstruction and armor-stand
visibility.

### 11.3 Python/JS Body-Surface Parity Risk

- `BODY_SURFACE_FIT_POLICIES` is duplicated in
  `src/henshin/armor_fit_contract.py` and `viewer/shared/armor-canon.js`. The
  new parity test compares policy keys, clamp values, contact targets, and
  clamp behavior across Python and JS.
- The Z-axis sign split is intentional and easy to break: VRM baseline offsets
  and Quest runtime offsets use different front/back conventions. Editing only
  one side can pass local visual intuition while failing placement parity.
- `tests/test_body_surface_policy_parity.py` depends on Node ESM import of
  `viewer/shared/armor-canon.js`; clean-machine CI needs Node available in
  addition to Python pytest.

Required checks before staging parity changes:

```powershell
python -m pytest tests/test_body_surface_policy_parity.py -q
python -m pytest tests/test_armor_part_specs.py tests/test_validate_armor_part.py -q
node --check viewer/shared/armor-canon.js
```

### 11.4 Quest Render Placement / Runtime Parity Risk

- `tests/test_quest_recall_render_contract.py` fixes many static Quest tokens
  around `runtime-render-placement.v1`, `render_placements`,
  `quest_rig_offset_m`, selected variant parity, GLB scale, and placement
  offset application.
- Live mirror pose application is a specific regression trap. Scene mirror
  meshes must continue using mirror-specific pose code such as
  `applyLiveMirrorSuitPose`, not rig-local self-view pose paths.
- Base-suit alignment and body-shell pose constants are tested by proximity and
  token order. Small constant changes can be valid, but they should be treated
  as visual/runtime changes, not text-only refactors.

Required checks before staging Quest placement changes:

```powershell
python -m pytest tests/test_quest_recall_render_contract.py tests/test_body_surface_policy_parity.py -q
npx vite build --config vite.quest.config.js --outDir tests/.tmp/quest-vite-build-review --emptyOutDir
```

Also run ADB smoke on Quest for recall load, base-suit self-view, mirror,
mocopi/body fallback, and GLB placement.

### 11.5 Dirty Worktree / Staging Risk

- Current parent-side modified files include `viewer/quest-iw-demo/quest-demo.js`
  and `tests/test_quest_recall_render_contract.py`. Do not stage or rewrite
  them from repo-cleanup work without owner approval.
- Current untracked review/contract files include
  `tests/test_quest_mocopi_motion_source.py`,
  `tests/test_body_surface_policy_parity.py`,
  `docs/quest-vrm-base-suit-spike-2026-05-05.md`, this readiness doc, the audit
  tool, and its tests. Stage them by topic, not as one broad `git add .`.
- Suggested stage groups:
  - `quest-runtime-parent`: `viewer/quest-iw-demo/quest-demo.js` and
    `tests/test_quest_recall_render_contract.py`, only with parent
    implementation owner approval.
  - `mocopi-contract`: mocopi fixture, mocopi docs/tools, and
    `tests/test_quest_mocopi_motion_source.py`.
  - `surface-parity-contract`: Python/JS surface policy files plus
    `tests/test_body_surface_policy_parity.py`.
  - `vrm-spike-docs`: `docs/quest-vrm-base-suit-spike-2026-05-05.md`.
  - `repo-readiness-audit`: `tools/audit_repo_readiness.py`,
    `tests/test_audit_repo_readiness.py`, and this doc.
- Continue blocking raw or generated output from upload: `qa/`, `sessions/`,
  `.playwright*`, `tests/.tmp*`, `examples/*.jpg`, ad-hoc `.tmp-*`, local logs,
  generated GLB/Blend review outputs, and evidence archives unless they are
  deliberately curated fixtures.

### 11.6 Review Blockers

- A mocopi user-facing claim appears without diagnostic evidence and BODY/static
  fallback.
- A VRM path renders in Quest first-person without a proven head/neck mask and
  debug snapshot contract.
- Python and JS body-surface policies change on only one side.
- `runtime-render-placement.v1` or Quest GLB placement tokens change without
  recall/runtime package tests and Quest smoke.
- Raw QA/session/tmp/generated media is staged for GitHub upload.
