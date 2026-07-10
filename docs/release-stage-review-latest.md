# Release Stage Review

- Read-only review output. This file does not stage, commit, or push.
- Manifest contract: `release-stage-manifest.v5`
- Validation contract: `release-stage-manifest-validation.v6`
- Validation status: `fail`
- Validation ok: `false`
- Blockers: `package-report-untracked-required-files`
- Warnings: `manifest-stage-candidates-exceed-package-tracked-candidates`

## stage_summary

Use this section as the mechanical split before manual `git add`.

### Staging candidates
- Count: `583`
- Categories: `release-critical, operator-docs, armor-assets`

### Manual review
- Count: `81`
- Categories: `qa-evidence, reference-docs, reference-artifact, ambiguous`

### Exclude from normal staging
- Count: `25961`
- Categories: `local-qa-artifact, user-feedback-media, local-workspace, generated-artifact`

## release-critical

- Manifest count: `132`
- Stage policy: `stage-candidate`
- Recommended action: review and stage in the runtime/release-critical commit
- Required untracked package candidates: `9`
- Package validator groups: `examples=1, replay=2, runtime=6`

Review sample paths:
- `.env.demo.example`
- `examples/modeler_delivery_manifest.sample.json`
- `examples/replay-record.sample.json`
- `schemas/replay-record.v0.2.schema.json`
- `src/henshin/variant_selection.py`
- `tools/exhibition_smoke_check.py`
- `tools/validate_exhibition_release_package.py`
- `tools/validate_modeler_variant_order_manifest.py`
- `tools/validate_variant_catalog.py`

## operator-docs

- Manifest count: `29`
- Stage policy: `stage-candidate`
- Recommended action: stage required runbook, checklist, and handoff docs after runtime/assets
- Required untracked package candidates: `14`
- Package validator groups: `operator_docs=14`

Review sample paths:
- `docs/current-web-quest-check-guide.md`
- `docs/exhibition-day-one-page-checklist-2026-05-04.md`
- `docs/exhibition-pc-release-package-manifest-2026-05-04.md`
- `docs/exhibition-pc-runbook-2026-05-04.md`
- `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`
- `docs/exhibition-ui-redesign-backlog-2026-05-04.md`
- `docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json`
- `docs/modeler-exhibition-readiness-risks-2026-05-04.md`
- `docs/modeler-triview-30variant-audit-table-2026-05-03.md`
- `docs/p1-limb-variant-order-acceptance-2026-05-03.md`
- `docs/quest-deposition-visual-direction-2026-05-04.md`
- `docs/quest-mocopi-exhibition-spike-2026-05-04.md`
- `docs/replay-record-contract.md`
- `docs/web-service-phase0-task-breakdown-2026-05-02.md`

## armor-assets

- Manifest count: `422`
- Stage policy: `stage-candidate`
- Recommended action: stage catalog-referenced armor assets in a dedicated asset commit
- Required untracked package candidates: `259`
- Package validator groups: `armor=1, armor_catalog_ref=90, armor_toppings=96, armor_variants=162`

Review sample paths:
- `viewer/assets/armor-parts/back/toppings/rear_core/base/back__rear_core__base.glb`
- `viewer/assets/armor-parts/back/toppings/rear_core/base/back__rear_core__base.modeler.json`
- `viewer/assets/armor-parts/back/toppings/rear_core/base/preview/back__rear_core__base.mesh.json`
- `viewer/assets/armor-parts/back/toppings/rear_core/compact_core/back__rear_core__compact_core.glb`
- `viewer/assets/armor-parts/back/toppings/rear_core/compact_core/back__rear_core__compact_core.modeler.json`
- `viewer/assets/armor-parts/back/toppings/rear_core/compact_core/preview/back__rear_core__compact_core.mesh.json`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/base/back__spine_ridge__base.glb`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/base/back__spine_ridge__base.modeler.json`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/base/preview/back__spine_ridge__base.mesh.json`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/compact_ridge/back__spine_ridge__compact_ridge.glb`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/compact_ridge/back__spine_ridge__compact_ridge.modeler.json`
- `viewer/assets/armor-parts/back/toppings/spine_ridge/compact_ridge/preview/back__spine_ridge__compact_ridge.mesh.json`
- `viewer/assets/armor-parts/back/variants/base/back__base.glb`
- `viewer/assets/armor-parts/back/variants/base/back__base.modeler.json`
- `viewer/assets/armor-parts/back/variants/base/preview/back__base.mesh.json`
- `viewer/assets/armor-parts/back/variants/bold/back__bold.glb`
- `viewer/assets/armor-parts/back/variants/bold/back__bold.modeler.json`
- `viewer/assets/armor-parts/back/variants/bold/preview/back__bold.mesh.json`
- `viewer/assets/armor-parts/back/variants/rear_core/back__rear_core.glb`
- `viewer/assets/armor-parts/back/variants/rear_core/back__rear_core.modeler.json`

## qa-evidence

- Manifest count: `1`
- Stage policy: `manual-evidence-review`
- Recommended action: stage only shareable QA evidence manifests recommended by the privacy/shareable validator
- Stage only shareable QA manifests or paths explicitly recommended by `qa/shareable-qa-evidence-latest.json`.

Review sample paths:
- `qa/shareable-qa-evidence-latest.json`

## local-only

These groups are not normal release staging inputs. Promote individual files only by explicit release-owner decision.

### local-qa-artifact
- Manifest count: `14`
- Manual required-untracked count: `0`
- Stage policy: `do-not-stage`
- Recommended action: do not stage raw or privacy-unvalidated QA evidence; promote through the shareable QA manifest if needed
- `qa/armor-forge-exhibition-mode-browser-check.json`
- `qa/exhibition-service-gate-latest.json`
- `qa/exhibition_release_package_latest.json`
- `qa/exhibition_smoke_check_3601_adb_latest.json`
- `qa/gcp-phase0-service-contract-latest.json`

### reference-docs
- Manifest count: `45`
- Manual required-untracked count: `0`
- Stage policy: `manual-doc-review`
- Recommended action: stage only docs promoted by the release owner; not required for clone runtime
- `docs/base-suit-overlay-contract.md`
- `docs/modeler-wave1pp-practical-handoff.md`
- `docs/armor-build-wave2-results.md`
- `docs/armor-part-variant-taxonomy.md`
- `docs/armor-variant-integration-roadmap.md`

### reference-artifact
- Manifest count: `35`
- Manual required-untracked count: `0`
- Stage policy: `manual-reference-review`
- Recommended action: stage only curated reference artifacts; keep screenshots/bundles out by default
- `docs/_smoke_renders/chest_back_3q.png`
- `docs/_smoke_renders/chest_back_front.png`
- `docs/_smoke_renders/chest_back_side.png`
- `docs/_smoke_renders/helmet_sleek_front.png`
- `docs/_smoke_renders/helmet_sleek_side.png`

### user-feedback-media
- Manifest count: `41`
- Manual required-untracked count: `0`
- Stage policy: `do-not-stage`
- Recommended action: do not stage user photos/screenshots by default
- `examples/1f7b1732-5e7e-45f6-bc9c-7f7f3bebfd3a.jpg`
- `examples/226a844c-3daa-4710-8b2b-73abfeb40d99.jpg`
- `examples/268647b4-8ca6-4ae4-9d22-98f996cee47d.jpg`
- `examples/2936d74a-a906-40e1-b608-b77da69d5789.jpg`
- `examples/3b7df9e5-be98-442e-a8fe-d543cccc1a5b.jpg`

### local-workspace
- Manifest count: `2`
- Manual required-untracked count: `0`
- Stage policy: `do-not-stage`
- Recommended action: do not stage local agent/modeling workspace files
- `.claude/worktrees/jovial-cohen-4bf60f/`
- `blender/review_master.blend`

## do-not-stage

- generated-artifact count: `25904`
- generated-artifact policy: `do-not-stage`
- generated-artifact action: do not stage for the normal GitHub release

Keep these out of normal release staging:
- `.playwright-cli/**`
- `.playwright-mcp/**`
- `tests/.tmp/**`
- `output/playwright/**`
- `qa/logs/**`
- `qa/*.json except qa/shareable-qa-evidence-latest.json and shareable manifest recommended paths`
- `qa/replay/*.json`
- `qa/replay/*.replay-record.json`
- `qa/*runtime-package*.snapshot.json`
- `qa/*replay-record*.demo.json`
- `qa/exhibition_release_package_latest.json`
- `qa/model-quality-acceptance-latest.json`
- `qa/release-stage-validation-latest.json`
- `qa/replay/*.summary.json`
- `examples/*.jpg`
- `examples/*.png`
- `examples/henshin_docs*_bundle*/**`
- `docs/_smoke_renders/**`
- `.claude/**`
- `blender/**`
- `transient server logs`
- `local QA screenshots`

Generated sample paths:
- `tests/.tmp/quest-api-live.err.log`
- `.env`
- `.playwright-cli/console-2026-04-28T11-51-49-689Z.log`
- `.playwright-cli/console-2026-05-03T11-58-48-988Z.log`
- `.playwright-cli/console-2026-05-03T12-18-43-188Z.log`
- `.playwright-cli/page-2026-04-28T11-51-50-792Z.yml`
- `.playwright-cli/page-2026-04-28T11-52-26-884Z.yml`
- `.playwright-cli/page-2026-04-28T11-52-57-734Z.yml`

## final_commands

Run these read-only/review commands before any manual staging:

```powershell
python tools\list_release_stage_candidates.py --summary-json --sample-limit 20
python tools\export_release_stage_manifest.py --out qa\release-stage-manifest-latest.json --sample-limit 20
python tools\validate_release_stage_manifest.py --manifest qa\release-stage-manifest-latest.json --package-report qa\exhibition_release_package_latest.json --report-json
python tools\export_release_stage_review_markdown.py --out docs\release-stage-review-latest.md --report-json
git status --short
git diff --check -- tools docs tests
git diff --cached --stat
git diff --cached --name-status
```
