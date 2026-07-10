# Modeler Fit And Triview Next Audit - 2026-05-04

Scope: current main-repo `viewer/assets/armor-parts/*` only. This audit is read-only for GLB, Blender, viewer code, and tests. Output artifacts are this doc and `tests/.tmp/modeler-fit-and-triview-next-audit-2026-05-04.json`.

Role focus: model / triview / parts-fit audit for P1 limbs: `upperarm`, `forearm`, `hand`, and `thigh`.

## Commands Run

```powershell
python tools\audit_modeler_part_delivery.py --part left_upperarm --part right_upperarm --part left_forearm --part right_forearm --part left_hand --part right_hand --part left_thigh --part right_thigh --format json --output tests\.tmp\modeler-fit-and-triview-next-audit-2026-05-04.json

python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json

python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json

python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered
```

## Headline

- `variant_catalog.json` is structurally valid: `status=pass`, `module_count=18`, no reasons, no warnings.
- P1 limb modules are not line-complete. Each of the 8 modules has only `:<base>` declared in the catalog.
- The P1 order manifest still has `ordered variants=24`, `catalog gaps=24`, and `delivery gaps=24`.
- Strict P1 delivery validation fails as expected until those 24 line variants are declared and delivered.
- Canonical P1 GLB/sidecar/source/preview companions exist, but all 8 canonical sidecars are `metadata_hold`.
- Both hand canonical sidecars exceed their target bbox on `z`: `140.0mm` actual vs `136.0mm` target. Treat this as a P1 fit follow-up before hand variants inherit the shape.

## P1 Coverage From Variant Catalog

| Module | Family | Mirror of | Catalog variants | Topping slots | 3-line declared |
|---|---|---|---:|---|---:|
| `left_upperarm` | upperarm | - | 1 (`left_upperarm:base`) | `bicep_band`, `outer_plate` | 0/3 |
| `right_upperarm` | upperarm | `left_upperarm` | 1 (`right_upperarm:base`) | `bicep_band`, `outer_plate` | 0/3 |
| `left_forearm` | forearm | - | 1 (`left_forearm:base`) | `forearm_cuff`, `wrist_module` | 0/3 |
| `right_forearm` | forearm | `left_forearm` | 1 (`right_forearm:base`) | `forearm_cuff`, `wrist_module` | 0/3 |
| `left_hand` | hand | - | 1 (`left_hand:base`) | `knuckle`, `palm_emitter` | 0/3 |
| `right_hand` | hand | `left_hand` | 1 (`right_hand:base`) | `knuckle`, `palm_emitter` | 0/3 |
| `left_thigh` | thigh | - | 1 (`left_thigh:base`) | `knee_socket_trim`, `outer_guard` | 0/3 |
| `right_thigh` | thigh | `left_thigh` | 1 (`right_thigh:base`) | `knee_socket_trim`, `outer_guard` | 0/3 |

Interpretation: catalog pass only proves the current catalog shape is valid. It does not prove the P1 line variants exist, because the line variants are still absent from the catalog.

## Sidecar And Preview Mesh Numeric Read

Units are meters unless noted. `Within target` is computed by `tools/audit_modeler_part_delivery.py` from sidecar bbox against sidecar target bbox.

| Module | Status | bbox x/y/z | target x/y/z | Within target | Sidecar tris | Preview verts/tris | Missing top-level sidecar metadata |
|---|---|---|---|---|---:|---:|---|
| `left_upperarm` | `metadata_hold` | `0.096304 / 0.283008 / 0.103745` | `0.108800 / 0.292400 / 0.108800` | yes | 604 | 1812 / 604 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `right_upperarm` | `metadata_hold` | `0.096304 / 0.283008 / 0.103745` | `0.108800 / 0.292400 / 0.108800` | yes | 604 | 1812 / 604 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `left_forearm` | `metadata_hold` | `0.094755 / 0.266040 / 0.099889` | `0.102000 / 0.278800 / 0.102000` | yes | 596 | 1788 / 596 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `right_forearm` | `metadata_hold` | `0.094755 / 0.266040 / 0.099889` | `0.102000 / 0.278800 / 0.102000` | yes | 596 | 1788 / 596 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `left_hand` | `metadata_hold` | `0.115000 / 0.078272 / 0.140037` | `0.115600 / 0.081600 / 0.136000` | no (`z +0.004037m`) | 296 | 888 / 296 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `right_hand` | `metadata_hold` | `0.115000 / 0.078272 / 0.140037` | `0.115600 / 0.081600 / 0.136000` | no (`z +0.004037m`) | 296 | 888 / 296 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `left_thigh` | `metadata_hold` | `0.129839 / 0.376908 / 0.122482` | `0.136000 / 0.395600 / 0.129200` | yes | 716 | 2148 / 716 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |
| `right_thigh` | `metadata_hold` | `0.129839 / 0.376908 / 0.122482` | `0.136000 / 0.395600 / 0.129200` | yes | 716 | 2148 / 716 | `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes` |

Fit note: `docs/modeler-fit-micro-adjustments-2026-05-04.md` already marks upperarm `x` as a base/P1 fit rule: current `96.3mm`, pass minimum `97.9mm`, demo target `99.4mm`, full target `108.8mm`. Keep that rule paired left/right when authoring future upperarm line variants.

## Missing P1 Variant Filesets

The open order requests 24 line variants. None are currently declared in `variant_catalog.json`, and none have the required GLB / `.modeler.json` / source `.blend` / preview `.mesh.json` files.

| Line | Upperarm | Forearm | Hand | Thigh |
|---|---|---|---|---|
| `line_rescue_knight` | `left_upperarm:rescue_upperarm_stream`, `right_upperarm:rescue_upperarm_stream` | `left_forearm:rescue_vambrace`, `right_forearm:rescue_vambrace` | `left_hand:rescue_cuff_lock`, `right_hand:rescue_cuff_lock` | `left_thigh:rescue_speed_plate`, `right_thigh:rescue_speed_plate` |
| `line_royal_insect` | `left_upperarm:guardian_upperarm_ridge`, `right_upperarm:guardian_upperarm_ridge` | `left_forearm:guardian_forearm_shell`, `right_forearm:guardian_forearm_shell` | `left_hand:guardian_knuckle`, `right_hand:guardian_knuckle` | `left_thigh:guardian_outer_guard`, `right_thigh:guardian_outer_guard` |
| `line_final_oath` | `left_upperarm:oath_upperarm_guard`, `right_upperarm:oath_upperarm_guard` | `left_forearm:oath_gauntlet`, `right_forearm:oath_gauntlet` | `left_hand:oath_palm_core`, `right_hand:oath_palm_core` | `left_thigh:oath_gold_flow`, `right_thigh:oath_gold_flow` |

Expected filesystem shape per missing asset follows this pattern:

```text
viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.glb
viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.modeler.json
viewer/assets/armor-parts/<module>/variants/<asset_key>/source/<module>__<asset_key>.blend
viewer/assets/armor-parts/<module>/variants/<asset_key>/preview/<module>__<asset_key>.mesh.json
```

## Triview Fidelity Hold Items To Carry Forward

These are not just file gaps. They are the visual acceptance risks that should stay attached to the P1 limb order.

| Scope | Fidelity hold item | Required proof |
|---|---|---|
| Upperarm | Continue shoulder-to-forearm line identity without blocking arm lift. Rescue needs blue/white seam continuity; royal insect needs heroic bicep/outer plate language; final oath needs denser gold/cyan flow than royal insect. | Paired left/right front, side, back, 3Q, closeup, elbow/shoulder clearance note. |
| Forearm | Must read as worn gauntlet/cuff, not floating wrist props or flat stripes. Controller sightline and wrist motion are the main Quest risks. | Paired front/side/back/3Q, closeup, controller clearance note. |
| Hand | Preserve palm/knuckle readability and controller-safe clearance. Resolve or explicitly justify canonical hand `z` target overflow before deriving line variants. | Hand closeup, side depth proof, controller clearance, bbox target check. |
| Thigh | Connect waist/belt motif into knee/shin without hip or knee interference. Line separation must remain visible in side and 3Q, not only front color. | Paired front/side/back/3Q, hip/knee clearance note, waist-to-shin continuity proof. |
| Metadata | Every delivered P1 sidecar needs top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`; catalog fallback is not enough for Replay traceability. | Sidecar diff or manifest audit showing the fields on all 24 assets. |
| Full route | Web first-read, Quest body-relative fit, and Replay proof must all identify the same line and part. | Web GLB smoke report, Quest/replay note when relevant, no fallback parts. |

## Next Actions To Acceptance

These gates are intentionally narrower than "make the limbs better". A P1 limb task is accepted only when the named audit signal turns green and the proof packet can be reviewed without opening Blender.

| Blocker | Next action | Acceptance criteria | Evidence to attach |
|---|---|---|---|
| 24 P1 line variants are missing | Deliver and catalog every ordered `upperarm`, `forearm`, `hand`, and `thigh` variant for all 3 lines and both sides. | `python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered` returns pass with `ordered variants=24`, `catalog gaps=0`, and `delivery gaps=0`. All 24 catalog entries use the manifest `variant_key`, correct `line_id`, correct `recommended_topping_slots`, and right-side `mirror_of` points to the matching left-side variant. | Strict validator output, catalog diff, and a manifest/path checklist showing GLB, `.modeler.json`, `source/*.blend`, and `preview/*.mesh.json` for every ordered asset. |
| P1 sidecars are `metadata_hold` | Add top-level provenance and intent fields to canonical P1 sidecars and require the same fields on all new P1 variant sidecars. | Re-running `python tools\audit_modeler_part_delivery.py --part left_upperarm --part right_upperarm --part left_forearm --part right_forearm --part left_hand --part right_hand --part left_thigh --part right_thigh --format json --output tests\.tmp\modeler-fit-and-triview-next-audit-2026-05-04.json` reports no `metadata_hold` for the 8 canonical P1 assets. Each delivered P1 variant sidecar also has non-empty top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`; catalog fallback does not count. | Updated audit JSON/summary plus sidecar diff snippets for one left/right pair per family. |
| Canonical hands exceed target bbox depth | Fix hand geometry/metadata before deriving line hand variants, or file a deliberate waiver that keeps those variants reviewer-only. | Preferred pass: `left_hand` and `right_hand` sidecar bbox `z <= 0.136000m`, GLB/sidecar/preview bbox delta `<= 0.002m`, and left/right bbox delta `<= 3%` per axis. Waiver pass: reviewer, date, reason, risk, and controller-clearance proof are documented; any waived hand variant remains `review_candidate` or `fidelity_hold`, not `fidelity_pass`. | Audit row showing hand bbox result, side-depth closeup, controller-clearance note, and waiver text only if the numeric overflow is intentionally accepted. |
| Tri-view `fidelity_hold` is still unresolved | Produce a human review packet per P1 left/right pair and line, then promote only assets that pass visual identity plus fit checks. | Every P1 variant pair has front, side, back, 3Q, and closeup evidence. The reviewer can identify `line_rescue_knight`, `line_royal_insect`, or `line_final_oath` from side and 3Q views, not only front color. Evidence shows no floating shell, no body intersection, and no blocked elbow, wrist/controller, hip, or knee motion. A `fidelity_hold` can move only to `review_candidate` after evidence is complete, to `staging_candidate` after human tri-view sign-off plus smoke/bbox pass, and to `fidelity_pass` only after Web/Quest/Replay route proof has no fallback parts. | Review packet links, per-pair sign-off notes, Web GLB smoke report, Quest/replay note when hands or motion-critical limbs are involved. |

## Detailed Gate Checklist

1. **Delivery gap gate:** all 24 ordered line variants exist at the expected manifest paths; no base-only substitute or renamed asset is counted as delivered.
2. **Catalog gate:** `variant_catalog.json` contains exactly the ordered P1 `variant_key` values for the 24 assets, with line metadata and mirror relationships matching the order manifest.
3. **Fileset gate:** each delivered asset has a valid GLB header, valid modeler sidecar JSON, source `.blend`, and preview mesh JSON; any missing companion keeps that asset in delivery gap.
4. **Metadata gate:** canonical P1 sidecars and all 24 variant sidecars have non-empty top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`; otherwise the status remains `metadata_hold`.
5. **Fit gate:** P1 bbox checks pass for upperarm, forearm, hand, and thigh. Upperarm variants inherit the current fit note: `x` should move beyond the `97.9mm` minimum and toward the `99.4mm` demo target while staying paired left/right. Hands must either meet `z <= 136.0mm` or carry the explicit waiver described above.
6. **Tri-view gate:** front, side, back, 3Q, and closeup images are present for every pair; line identity is visible in silhouette/panel language, not only in small texture color.
7. **Clearance gate:** upperarm/forearm evidence names elbow and arm-lift clearance; hand evidence names palm/knuckle/controller clearance; thigh evidence names hip/knee clearance and waist-to-shin continuity.
8. **Route gate:** Web first-read, Quest body-relative fit, and Replay traceability all point to the same `line_id` and `variant_key`, with fallback count 0.
9. **Runtime guardrail:** keep existing 30 delivered non-P1 line variants and any P1 `fidelity_hold` assets out of public runtime until their promotion packet reaches `fidelity_pass`.
