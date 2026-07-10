# Exhibition PC Release Package Manifest - 2026-05-04

Purpose: define what must be copied to the external exhibition PC, and what the demo must not depend on.

Target external PC path:

```text
C:\henshin-demo\gavai-henshin
```

## Release Lanes

1. Local external-PC fallback: required for exhibition. Everything needed for Web -> Quest -> Replay must be in this package and runnable without cloud services.
2. Web service/GCP: later durable-service lane. Include docs/config notes if available, but do not make the package depend on a live Cloud Run/GCP service unless a separate service release is declared.
3. PlayCanvas adapter: optional preview/editor/QA lane. Include only as an exported runtime-package consumer, never as variant, placement, code, or Replay authority.
4. mocopi hardware enhancement: optional lane. Include only if hardware pairing, receiver path, latency, and fallback gates have a written `GO` or `DEMO-ONLY` decision.

Required local preflight:

- `local-pass` is prerequisite for visitor operation.
- `local-pass cannot be overridden` by GCP, PlayCanvas, or mocopi.
- Core demo must run without live GCP, internet, provider secrets, or mocopi.

Optional enhancement preflight:

- GCP/service exits as `service-pass/fail/not-included`. The service endpoint
  must pass the same forge, recall, replay, and no-local-path checks before it
  is treated as a service rehearsal.
- PlayCanvas exits as `playcanvas-pass/fail/not-included`. PlayCanvas must
  consume an exported runtime package snapshot and must not own variant,
  placement, code, or Replay truth. Before `playcanvas-pass`, run
  `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`.
- mocopi exits as `mocopi-GO/DEMO-ONLY/NO-GO/not-included`; fallback must be
  confirmed before any public mention of mocopi.

## Copy Required

### Stage Candidate Mapping

Before building a GitHub branch/tag or a clone-based package, generate the
read-only stage candidate report:

```powershell
python tools/list_release_stage_candidates.py --json > qa\release_stage_candidates_latest.json
```

The tool only reads `git status --porcelain=v1 -z --ignored`; it does not stage,
commit, remove, or clean files. Use the JSON categories as a checklist:

| Tool category | Package handling |
| --- | --- |
| `release-critical` | Must be reviewed for the release branch. Runtime code, config examples, schemas, smoke/validator tools, sample JSON, and tests live here. |
| `operator-docs` | Must be included when the doc is listed below or referenced by the runbook/checklist. Broad planning docs may stay out unless explicitly needed. |
| `armor-assets` | Must be included for a clone-based exhibition package. Missing catalog-referenced GLB/modeler/preview assets break Web Forge or Quest recall. |
| `generated-artifact` | Do not stage for a normal GitHub release. This includes ignored Playwright dumps, `tests/.tmp/**`, Vite build output, transient server logs, and local screenshots. |
| `ambiguous` | Manual review. Stage only when the release owner confirms it is package input or curated evidence. |

For a GitHub clone to be the package, every required item below must either be
tracked in Git or intentionally supplied by a separate copied artifact. Do not
count ignored or untracked generated evidence as part of the package.

### Repository Runtime

- `package.json`
- `package-lock.json` if present in the release package
- `pyproject.toml`
- `vite.quest.config.js`
- `tools/list_release_stage_candidates.py`
- `tools/run_henshin.py`
- `tools/exhibition_smoke_check.py`
- `tools/smoke_web_glb_load.py`
- `tools/validate_exhibition_release_package.py`
- `tools/validate_variant_catalog.py`
- `tools/start_quest_adb_reverse.ps1`
- `tools/start_quest_lan_https.ps1`
- `tools/new_quest_lan_cert.ps1`
- `.env.demo.example`
- `src/**`
- `viewer/armor-forge/**`
- `viewer/quest-iw-demo/**`
- `viewer/assets/armor-parts/**`
- `viewer/assets/vrm/**` if present in the release package
- `schemas/**`
- `config/**` except machine-local secrets
- `examples/suitspec.sample.json`
- `examples/modeler_delivery_manifest.sample.json`

### Demo Docs

- `docs/exhibition-pc-runbook-2026-05-04.md`
- `docs/exhibition-day-one-page-checklist-2026-05-04.md`
- `docs/exhibition-pc-release-package-manifest-2026-05-04.md`
- `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`
- `docs/web-service-phase0-task-breakdown-2026-05-02.md`
- `docs/quest-mocopi-exhibition-spike-2026-05-04.md`
- `docs/two-week-execution-schedule-2026-05-04.md`
- `docs/current-web-quest-check-guide.md`
- `docs/modeler-fit-micro-adjustments-2026-05-04.md`
- `docs/modeler-exhibition-readiness-risks-2026-05-04.md`
- `docs/modeler-triview-30variant-audit-table-2026-05-03.md`
- `docs/quest-deposition-visual-direction-2026-05-04.md`
- `docs/exhibition-ui-redesign-backlog-2026-05-04.md`
- `docs/p1-limb-variant-order-acceptance-2026-05-03.md`
- `docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json`
- Japanese UI copy checklist or waiver notes, if stored as a separate doc
- Existing 3D model quality check and strengthening notes for the frozen demo package
- Per-part fit/size/position tuning notes or waiver notes for the frozen demo package
- Tri-view-conscious cool-suit visual QA screenshots/notes for front, side, back, and 3q review

### Assets And Seeds

- `viewer/assets/armor-parts/variant_catalog.json`
- `viewer/assets/armor-parts/**/variants/**` referenced by the catalog
- `viewer/assets/armor-parts/**/toppings/**` referenced by the catalog
- All GLB files referenced by `viewer/assets/armor-parts/variant_catalog.json`
- All matching `.modeler.json` sidecars needed by the runtime package
- Preview metadata used by Web Forge and Quest smoke
- Any frozen sample suit, manifest, trial, or replay seed chosen for offline fallback
- The last-known-good asset package, stored separately from the active package

### Do Not Stage From Candidate Report

Keep these out of a normal GitHub release even if `--ignored` lists them:

- `.playwright-cli/**`
- `.playwright-mcp/**`
- `tests/.tmp/**`
- `output/playwright/**`
- `qa/logs/**`
- root temporary screenshots such as `armor-forge-japanese-ui-*.png`
- transient server logs, Vite build directories, browser snapshots, and local QA screenshots

`qa/*.json` reports are not automatically ignored. Treat them as curated
evidence: stage only a small named clean-clone/external-PC report when the
release owner asks for it.

Important: `.gitignore` does not affect files already tracked by Git. If
`tools/list_release_stage_candidates.py` reports tracked `generated-artifact`
items, leave them unstaged unless a separate reviewed cleanup decides to
`git rm --cached` them.

### Optional mocopi Hardware Lane

Copy or bring only when the mocopi gate is `GO` or `DEMO-ONLY`:

- mocopi sensors, straps, charging hardware, and any required receiver phone/device
- receiver software installer or setup notes used by the approved path
- pairing/calibration instructions
- documented fallback command or UI choice to return to `sim`/body replay
- short risk note with the gate result: `GO`, `DEMO-ONLY`, or `NO-GO`

### Runtime Dependencies To Install On The PC

- Python 3.11+ or the project-approved Python runtime
- Node.js/npm compatible with the release package
- Chrome or Edge
- Android Platform Tools or Meta Quest Developer Hub for `adb`
- Meta Quest Browser on the headset

Preferred fixed-code Quest QA launch:

```powershell
.\tools\start_quest_adb_reverse.ps1 -RecallCode 3601 -CacheBust -LaunchBrowser
```

This applies USB ADB reverse for `5173` and `8010`, appends a cache-busting query, and sends the URL to Quest Browser. Headset-visible WebXR state is still a physical QA check; the ADB intent only confirms that Android accepted the launch request.

## Generate Or Verify On The PC

Run after copying:

```powershell
cd C:\henshin-demo\gavai-henshin
npm install
python -m pip install -e ".[dev]"
python tools/validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json
python tools/validate_exhibition_release_package.py
python tools/exhibition_smoke_check.py --forge
```

Normal release handoff should pass the validator without special flags. In a git checkout this means every critical runtime, asset, schema, example, and operator-doc path is tracked by git, so a normal tracked release archive will not silently omit it.

For a hosted/GCP rehearsal, run the service deployment gate in `external` mode
with HTTPS Web/API/Quest URLs and `--check-http`. A green external service
report never replaces the external-PC `local-pass` requirement.

For an intentional working-tree snapshot, use the explicit snapshot flag and save the JSON report beside the package:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json --allow-untracked-for-local-snapshot > qa\exhibition_release_package_snapshot_report.json
```

This mode keeps the git tracking check enabled and still reports `untracked_count` plus the full `untracked` path list. It only changes whether those untracked critical files are blocking. Use it when the bundle/export process copies the working tree contents, not when creating a git-only release archive.

For a zip/package without `.git`, run the same gate in package-existence mode:

```powershell
python tools/validate_exhibition_release_package.py --skip-git-tracking
```

The gate must list exact missing paths/patterns. Its `model_quality` section also emits existing 3D model quality, strengthening targets, and per-part size/position micro-adjustments for front/side/back review, so bbox or tri-view model risks are not hidden behind file completeness.

The `experience_gates` section is read-only:

- Japanese UI: warns if no Japanese copy is detected in public Web/Quest UI files.
- Model fit artifacts: verifies that the report itself contains per-part micro-adjustment artifacts.
- Tri-view/fidelity hold: warns if package docs do not preserve front/side/back/3Q and `fidelity_hold` language.
- P1 limb baseline: requires the P1 order/acceptance doc and manifest, then warns if key scope/line/runtime-activation terms are missing.

The `p1_acceptance` section is also read-only for this release:

- `package_gate_status=warn_now_block_p1` means the exhibition package may still be runnable, but P1 limb variant acceptance is not complete.
- `runtime_activation_allowed=false` must remain false even when the package is otherwise usable; P1 order acceptance is not a Web/Quest runtime activation.
- `blocked_asset_count` is the number of ordered P1 limb assets still not accepted. Current expected value is `24` until the three line systems land.
- `line_system_reports[*].package_gate_status` shows line-by-line shortage for `line_rescue_knight`, `line_royal_insect`, and `line_final_oath`.
- Exhibition `local-pass` and P1 `pass_p1` are separate labels. A package can be used for the core Web -> Quest -> Replay demo with P1 still `warn_now_block_p1`, but it must not claim those limb variants as accepted or active.

Start commands expected by the checklist:

```powershell
npm run dev
npm run dev:quest -- --port 5173
npm run dev:quest:adb
```

Quest port `5173` is fixed for headset URLs and USB ADB reverse. A port conflict should fail the server startup; do not silently move the public demo to `5174`.

## Do Not Depend On

- `C:\dev\codex\gavai-henshin` or any path on the development machine.
- Uncommitted files outside the release package.
- The developer's `.env`, shell history, Python virtual environment, npm cache, or global PATH quirks.
- A private dev-machine LAN IP such as a previous `192.168.x.x` value.
- A running server on the dev machine.
- Provider secrets being present, unless the demo mode explicitly requires online provider calls.
- External internet for the core Web -> Quest -> Replay loop.
- A live GCP/Cloud Run service for the core loop, unless a separate service release has passed smoke.
- A PlayCanvas preview for the core loop, unless a separate adapter proof has
  passed with `python tools/validate_playcanvas_snapshot.py <runtime-package.snapshot.json> --report-json`
  and the local Web -> Quest -> Replay path remains `local-pass`.
- mocopi hardware for the core loop. If mocopi fails, the demo must fall back to simulated/body replay.
- mocopi lane status being assumed without a physical sensor and headset rehearsal on the packaged PC.
- Online web-service rehearsal being treated as the baseline exhibition path.
- Browser cache, old recall codes, or previous Quest tabs.
- Assets under `.claude/worktrees/**` unless they have been copied into the release package and listed in the asset manifest.
- Fidelity-held modeler assets being treated as final accepted runtime assets.

## Package Acceptance

Before the package is handed to the venue operator:

1. `python tools/exhibition_smoke_check.py --forge` passes on the external PC or matching clean PC.
2. `npm run dev` starts Web/API on `8010`.
3. `npm run dev:quest -- --port 5173` starts Quest viewer on `5173`.
4. `npm run dev:quest:adb` can establish the USB fallback, or the reason it cannot is written down.
5. Web Forge creates a fresh 4-digit code.
6. Quest recalls that same code.
7. Replay proof is created or the offline fallback replay seed is verified.
8. Last-known-good package and active package are both labeled with date, commit/zip name, and operator note.
9. Japanese UI status is labeled `pass`, `fix`, or `waived`.
10. Quest deposition visual status is labeled `pass`, `fix`, or `waived`.
11. Existing 3D model quality/strengthening status is labeled `pass`, `strengthen`, `hold`, or `waived`.
12. Per-part 3D fit/size/position status is labeled `pass`, `fix`, or `waived`.
13. Tri-view-conscious cool-suit visual QA status is labeled `pass`, `fix`, or `waived`.
14. Web service/GCP status is labeled `not included`, `service-smoke-pass`, or `service-smoke-fail`.
15. PlayCanvas status is labeled `playcanvas-pass`, `playcanvas-fail`, or `not-included`; `playcanvas-pass` requires the snapshot validator report and cannot make PlayCanvas a truth owner.
16. mocopi status is labeled `GO`, `DEMO-ONLY`, `NO-GO`, or `not included`, with fallback confirmed.
17. If `--allow-untracked-for-local-snapshot` was used, `qa\exhibition_release_package_snapshot_report.json` is stored with the bundle and the operator confirms the listed untracked files are physically present in the copied package.
18. Optional GCP/PlayCanvas/mocopi results are recorded after the local result; none can override a missing `local-pass` for public operation.
