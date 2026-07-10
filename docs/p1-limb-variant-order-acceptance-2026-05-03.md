# P1 Limb Variant Order Acceptance - 2026-05-03

Scope: `upperarm`, `forearm`, `hand`, and `thigh` on both left/right sides.

Current state:

- `variant_catalog.json` has only `base` for the eight P1 limb modules.
- The existing 30 delivered line variants are a technical file pass but remain `fidelity_hold`.
- This order does not activate runtime assets. Web/Quest adoption waits for delivery validation and fidelity review.

## Order Manifest

Primary manifest:

```bash
docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json
```

The manifest requests 24 variants:

- 8 target modules.
- 3 line systems per module: `line_rescue_knight`, `line_royal_insect`, `line_final_oath`.
- Right-side modules must declare `mirror_of` pointing to the same left-side asset key.

## Validation

Open-order validation:

```bash
python tools/validate_modeler_variant_order_manifest.py --manifest docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json
```

Strict delivery acceptance:

```bash
python tools/validate_modeler_variant_order_manifest.py --manifest docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered
```

Open-order mode should pass structurally and report catalog/file gaps as open work. Strict mode is the handoff gate: it fails until each ordered variant is declared in `variant_catalog.json` and has GLB, sidecar, source blend, and preview mesh at the manifest paths.

Current verification:

```text
open-order: PASS with WARN
ordered variants: 24
catalog gaps: 24
delivery gaps: 24

strict delivery: expected FAIL until delivery lands
```

Exhibition release JSON reading:

```text
p1_acceptance.package_gate_status = warn_now_block_p1
p1_acceptance.runtime_activation_allowed = false
p1_acceptance.blocked_asset_count = 24
```

This is acceptable for the current exhibition package only as a warning: the core Web -> Quest -> Replay demo may proceed if the release validator has no blocking `reasons` and the local preflight is `local-pass`. It also means P1 limb variants are not accepted, not selectable as final runtime variants, and not proof that any of the three line systems has landed.

Line-specific shortage is read from `p1_acceptance.line_system_reports`:

- `line_rescue_knight`: `package_gate_status=warn_now_block_p1` until its eight upperarm/forearm/hand/thigh assets are delivered and accepted.
- `line_royal_insect`: `package_gate_status=warn_now_block_p1` until its eight assets are delivered and accepted.
- `line_final_oath`: `package_gate_status=warn_now_block_p1` until its eight assets are delivered and accepted.

Regression test:

```bash
python -m pytest tests/test_validate_modeler_variant_order_manifest.py -q
# passed
```

## Acceptance Rules

Each delivered variant must keep the same module name, `variant_key`, path stem, and sidecar reference as the order manifest.

### P1 Acceptance Labels

Use the same package-gate vocabulary as the waist belt-loop validator:

- `warn_now_block_p1`: the order or delivery may exist, but P1 acceptance is not complete. This includes missing catalog entries, missing GLB/source/sidecar/preview files, missing sidecar review fields, sidecar/runtime activation claims, or any review evidence gap.
- `pass_p1`: the strict delivered gate has enough catalog, file, sidecar, and review metadata to accept that variant or line system for P1.

These labels are not runtime switches. `runtime_activation_allowed=false` remains true for this order even when a variant reaches `pass_p1`; Web/Quest activation must happen in a later catalog/runtime selection change. A validator report can therefore be:

- `p1_acceptance.package_gate_status=pass_p1`
- `p1_acceptance.acceptance_complete=true`
- `p1_acceptance.runtime_activation_allowed=false`
- `p1_acceptance.runtime_activation_label=runtime_activation_blocked_by_order_manifest`

The manifest validator emits the label at three levels:

- top-level `p1_acceptance`: overall order acceptance status.
- `line_system_reports[*].package_gate_status`: each of the three line systems, `line_rescue_knight`, `line_royal_insect`, and `line_final_oath`.
- `assets[*].p1_acceptance.package_gate_status`: each `upperarm`, `forearm`, `hand`, and `thigh` variant asset.

Required sidecar fields:

- `source_concept_ids`
- `line_id`
- `design_intent`
- `fidelity_notes`

Rejected sidecar/runtime fields:

- `runtime_activation_allowed=true`
- `activate_runtime=true`

Those fields mean "select this in runtime now", not "accept the delivered asset". P1 acceptance should fail with `warn_now_block_p1` if either appears in a sidecar or order record.

Required review evidence:

- front, side, back, 3q, and closeup review images in the delivery manifest or reviewer packet.
- Web check: armor reads as a worn suit part, not a floating prop or flat proxy.
- Quest check: transformation recall keeps controller/hand, elbow, hip, and knee clearance.
- Replay check: the selected line and part identity remain traceable from manifest metadata.

## Intake Gate Checklist

Use this checklist before moving any P1 limb variant from delivered to activation review. A missing item keeps the variant in `fidelity_hold`; it does not block the open-order manifest from existing.

- Size/position gate: `upperarm`, `forearm`, `hand`, and `thigh` variants stay inside the `authoring_target_m` envelope from `docs/modeler-new-route-acceptance-spec.md`; target is each axis within +/-10%, fail is any axis over +/-15%, and left/right pair delta is <=3%. Sidecars must keep the canonical module bone (`leftUpperArm`/`rightUpperArm`, `leftLowerArm`/`rightLowerArm`, `leftHand`/`rightHand`, `leftUpperLeg`/`rightUpperLeg`) and use offsets as fit metadata, not visual compensation.
- Position clearance gate: front/side/back/3q evidence shows no body intersection at the reference pose, no floating limb shells, and no blocked elbow, wrist/controller, hip, or knee articulation. Hand variants must preserve palm/knuckle readability and controller-safe clearance.
- Tri-view gate: each of the 24 ordered variants has front, side, back, 3q, and closeup review images linked from the delivery manifest or reviewer packet; the three line systems remain visibly distinct in the same module slot.
- Web rendering gate: Web Forge or the GLB smoke report loads the selected variant with fallback count 0, shows the correct `variant_key`, and reads as worn armor over the base suit rather than a proxy, flat stripe, or floating prop.
- Quest rendering gate: Quest recall loads the same selected `variant_key` through the runtime package, has no GLB fallback, and a headset/controller check confirms hand, elbow, hip, and knee clearance during transform/stand display.

## Runtime Rule

The order manifest is not a runtime catalog patch. After strict acceptance passes, update `variant_catalog.json` and runtime selection in a separate activation change.
