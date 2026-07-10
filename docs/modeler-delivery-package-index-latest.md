# Modeler Delivery Package Index

- Contract: `modeler-delivery-package-index.v1`
- Rendering/Blender required: `False`
- P1 blocked assets: `24`
- 30variant fidelity_hold items: `30`
- Public runtime allowed: `False`

## Pre-GitHub Reading Order

| Step | Path | Read for | Must confirm |
|---:|---|---|---|
| 1 | `docs/modeler-delivery-package-index-latest.md` | Top-level package scope, blocked state, QA commands, and local artifacts that must not be shared. | P1 order and 30variant fidelity fixes are separate workstreams.<br>runtime_release_note keeps public Web/Quest activation false. |
| 2 | `docs/p1-limb-variant-order-acceptance-2026-05-04.md` | P1 upperarm/forearm/hand/thigh order units, fileset contract, reject conditions, and runtime activation policy. | There are 24 missing P1 assets: 3 lines x 4 limb families x left/right.<br>runtime_activation_allowed=false is intentional until a separate runtime change. |
| 3 | `docs/modeler-deliveries/p1-limb-order-packet-latest.json` | Machine-readable modeler checklist generated from missing_matrix. | order_items has 24 rows.<br>blocked_by_stage.delivery has 24 rows before modeler delivery. |
| 4 | `docs/modeler-30variant-triview-review-worklist-2026-05-04.md` | 30 delivered variants that are file-valid but still need tri-view fidelity rework. | fidelity_hold means not public runtime-ready.<br>missing_p1 rows are not part of the 30variant fix pass. |
| 5 | `docs/modeler-fix-request-latest.md` | Modeler-facing 30variant fix request and acceptance recheck table. | per_part_fix_requests is the 30variant correction queue.<br>modeler_delivery_blockers are listed before share. |
| 6 | `docs/modeler-handoff-summary-latest.md` | Single handoff summary after P1 packet and 30variant fix request are generated. | P1 shortage=24 and fidelity_hold=30 are both visible.<br>handoff validator passes in strict mode before GitHub submission. |

## Documents To Share

| Path | Purpose | Generated |
|---|---|---:|
| `docs/modeler-delivery-package-index-latest.md` | Top-level index for the modeler handoff package. | `True` |
| `docs/modeler-handoff-summary-latest.md` | Integrated P1 order and 30variant fidelity handoff summary. | `True` |
| `docs/modeler-fix-request-latest.md` | 30variant fidelity_hold fix request and acceptance recheck table. | `True` |
| `docs/p1-limb-variant-order-acceptance-2026-05-04.md` | P1 limb order, delivery, catalog registration, and runtime activation contract. | `False` |
| `docs/modeler-30variant-triview-review-worklist-2026-05-04.md` | Human review worklist for tri-view fidelity fixes. | `False` |
| `docs/modeler-triview-30variant-audit-table-2026-05-03.md` | Source audit table behind the tri-view audit packet. | `False` |
| `docs/modeler-delivery-coordinate-review-2026-05-03.md` | Coordinator note explaining file pass, fidelity_hold, and release-gate separation. | `False` |

## Generated Packets

| Artifact | Path | Command | Current summary |
|---|---|---|---|
| `p1_order_packet` | `docs/modeler-deliveries/p1-limb-order-packet-latest.json` | `python tools\export_p1_modeler_order_packet.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --out docs\modeler-deliveries\p1-limb-order-packet-latest.json --format json --report-json` | order_item_count=24, blocked_asset_count=24, acceptance_label=warn_now_block_p1 |
| `triview_audit_packet` | `qa/modeler-triview-audit-latest.json` | `python tools\export_modeler_triview_audit_packet.py --audit-doc docs\modeler-triview-30variant-audit-table-2026-05-03.md --worklist-doc docs\modeler-30variant-triview-review-worklist-2026-05-04.md --out qa\modeler-triview-audit-latest.json --report-json` | fidelity_hold_count=30, runtime_public_activation_allowed=False |
| `modeler_fix_request` | `docs/modeler-fix-request-latest.md` | `python tools\export_modeler_fix_request.py --audit-doc docs\modeler-triview-30variant-audit-table-2026-05-03.md --worklist-doc docs\modeler-30variant-triview-review-worklist-2026-05-04.md --out docs\modeler-fix-request-latest.md --report-json` | fidelity_hold_count=30, per_part_fix_request_count=10 |
| `modeler_handoff_summary` | `docs/modeler-handoff-summary-latest.md` | `python tools\export_modeler_handoff_summary.py --p1-manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --audit-doc docs\modeler-triview-30variant-audit-table-2026-05-03.md --worklist-doc docs\modeler-30variant-triview-review-worklist-2026-05-04.md --out docs\modeler-handoff-summary-latest.md --report-json` | p1_blocked_asset_count=24, fidelity_hold_count=30, must_pass_validator_before_share=True |
| `modeler_delivery_package_index` | `docs/modeler-delivery-package-index-latest.md` | `python tools\export_modeler_delivery_package_index.py --p1-manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --audit-doc docs\modeler-triview-30variant-audit-table-2026-05-03.md --worklist-doc docs\modeler-30variant-triview-review-worklist-2026-05-04.md --out docs\modeler-delivery-package-index-latest.md --report-json` | documents_to_share_count=7, validators_to_run_count=3 |

## Validators To Run

| Name | Command | Blocks | Expected now |
|---|---|---|---|
| P1 limb order manifest acceptance | `python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered --report-json` | P1 model delivery acceptance | fail_or_warn_until_modeler_delivery; do not treat runtime_activation_allowed=false as acceptance failure. |
| Modeler handoff share gate | `python tools\validate_modeler_handoff_summary.py --handoff docs\modeler-handoff-summary-latest.md --strict --report-json` | handoff sharing | pass before external modeler share |
| Variant catalog routing guard | `python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json` | public runtime activation | pass before public runtime activation of accepted variants |

## GitHub Submission Preflight

| Gate | Command | Required before GitHub | Expected current result | Failure action |
|---|---|---:|---|---|
| `generate_package_index` | `python tools\export_modeler_delivery_package_index.py --p1-manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --out docs\modeler-delivery-package-index-latest.md --report-json` | `True` | index JSON includes pre_github_reading_order, validators_to_run, blocked_items, and runtime_release_note. | Regenerate the index or fix the exporter before using the package as a PR/issue reference. |
| `generate_p1_order_packet` | `python tools\export_p1_modeler_order_packet.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --out docs\modeler-deliveries\p1-limb-order-packet-latest.json --format json --report-json` | `True` | order_items=24, blocked_by_stage.delivery=24, acceptance_label=warn_now_block_p1. | Do not summarize P1 shortage by hand; fix the manifest/report path until packet generation is deterministic. |
| `generate_triview_fix_request` | `python tools\export_modeler_fix_request.py --out docs\modeler-fix-request-latest.md --report-json` | `True` | fidelity_hold_items=30 and runtime_release_impact.public_runtime_allowed=false. | Keep the 30variant repair conversation out of GitHub until the audit packet is reproducible. |
| `handoff_share_validator` | `python tools\validate_modeler_handoff_summary.py --handoff docs\modeler-handoff-summary-latest.md --strict --report-json` | `True` | status=pass after handoff Markdown is generated. | Regenerate or tighten the handoff summary; missing P1/fidelity/runtime wording must block sharing. |
| `p1_strict_delivery_acceptance` | `python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered --report-json` | `False` | not pass until modeler delivery fills the 24 P1 filesets. | Use the failure as the modeler order backlog; do not treat it as a release-package failure yet. |

## Blocked Items

- P1 blocked assets: `24`
- P1 current stop counts: `{'order': 0, 'delivery': 24, 'catalog_registration': 0, 'runtime_activation': 0}`
- 30variant fidelity_hold items: `30`
- Separate missing P1 rows in audit: `24`

## Runtime Release Note

- Public runtime allowed: `False`
- Canonical/base runtime release can proceed: `True`
- Model delivery blocked: `True`
- Reviewer-only allowed: `True`
- Block label: `blocked_by_p1_order_and_triview_fidelity_hold`
- Distinction: Canonical/base exhibition runtime may proceed if package gates pass; P1 limb delivery and 30variant fidelity acceptance remain blocked, and public Web/Quest activation stays false until a separate approval.

## Do Not Share Local Artifacts

| Path | Reason |
|---|---|
| `.claude/worktrees/**` | Local review worktree and scratch state; share only the summarized docs/packets. |
| `tests/.tmp/**` | Local pytest/audit scratch output; regenerate if engineering needs evidence. |
| `.pytest_cache/** and __pycache__/**` | Local execution cache. |
| `qa/local-* and unreferenced screenshots/renders` | Local QA captures are not authoritative unless listed in documents_to_share. |
| `terminal logs or validator stdout copied outside generated packets` | Use --report-json outputs and Markdown packets instead of ad-hoc logs. |
