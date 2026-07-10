# Modeler 30variant Fix Request

Contract: `modeler-fix-request.v1`

30 delivered variants passed file checks but remain fidelity_hold. Please treat this as a visual/metadata/evidence rework request, not a new runtime activation request.

## Status

- Decision: `technical_file_pass_fidelity_hold`
- Fidelity hold items: `30`
- Separate P1 missing rows: `24`
- Public runtime activation: `False`

## Modeler Delivery Blockers

| Code | Severity | Count | Required resolution |
|---|---|---:|---|
| `fidelity-hold-visual-identity` | `blocker` | 30 | Strengthen line identity in front, side, back, and 3Q before promotion. |
| `sidecar-provenance-incomplete` | `blocker` | 30 | Add source_concept_ids, line_id, design_intent, and fidelity_notes to each held sidecar. |
| `review-evidence-incomplete` | `blocker` | 30 | Attach front/side/back/3Q, source_overlay_front.png, helmet/torso closeups, and boot_closeup_side.png where applicable. |
| `runtime-release-blocked` | `blocker` | 30 | Keep reviewer-only visibility until fidelity_pass and route proof are complete. |
| `p1-limb-order-separate` | `warn` | 24 | Do not claim line-complete limbs from this 30variant fix request. |
| `do-not-claim-1` | `guardrail` | 0 | Keep this as a review note in the modeler handoff. |
| `do-not-claim-2` | `guardrail` | 0 | Keep this as a review note in the modeler handoff. |
| `do-not-claim-3` | `guardrail` | 0 | Keep this as a review note in the modeler handoff. |

## Per-Part Fix Requests

### helmet

- Priority: `P0`
- Variants: `helmet:oath_crown_visor`, `helmet:rescue_sleek`, `helmet:compound_guardian`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `helmet:oath_crown_visor` | Separate from c01 with crown geometry and denser gold/cyan trim; add side-view proof. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `helmet_closeup_front`, `helmet_closeup_side` |
| `line_rescue_knight` | `helmet:rescue_sleek` | Strengthen blue visor and rescue-face silhouette; add `fidelity_notes` with front/side/back deltas. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `helmet_closeup_front`, `helmet_closeup_side` |
| `line_royal_insect` | `helmet:compound_guardian` | Make compound visor and crest read in grayscale; avoid tiny texture-only eye detail. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `helmet_closeup_front`, `helmet_closeup_side` |

### chest

- Priority: `P0`
- Variants: `chest:oath_core_shell`, `chest:rescue_wrap`, `chest:emerald_v_core`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `chest:oath_core_shell` | More final-form density without growing into arm/abdomen interference. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_rescue_knight` | `chest:rescue_wrap` | Increase core contrast and rib wrap; show source overlay front. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_royal_insect` | `chest:emerald_v_core` | Make V chest the main read from distance; connect to waist and back panels. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |

### back

- Priority: `P0`
- Variants: `back:oath_spine_rear_core`, `back:compact_spine`, `back:wing_shell_close`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `back:oath_spine_rear_core` | Back must visibly exceed c01 in completion/density. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_rescue_knight` | `back:compact_spine` | Add blue spine identity visible in full back and side. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_royal_insect` | `back:wing_shell_close` | Increase shell/wing silhouette while staying body-hugging. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |

### left_shin

- Priority: `P0`
- Variants: `left_shin:oath_glow_guard`, `left_shin:rescue_stream`, `left_shin:guardian_ridge`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `left_shin:oath_glow_guard` | Tie waist/thigh/shin/boot into one flow after P1 thigh arrives. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_rescue_knight` | `left_shin:rescue_stream` | Strengthen color blocking and boot connection; include boot side closeup. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_royal_insect` | `left_shin:guardian_ridge` | Make ridge readable at Quest distance, not only as line texture. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |

### right_shin

- Priority: `P0`
- Variants: `right_shin:oath_glow_guard`, `right_shin:rescue_stream`, `right_shin:guardian_ridge`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `right_shin:oath_glow_guard` | Compare left/right trim continuity into boots. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_rescue_knight` | `right_shin:rescue_stream` | Compare left/right height, glow placement, and side angle. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_royal_insect` | `right_shin:guardian_ridge` | Compare left/right silhouette and material-zone read. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |

### left_boot

- Priority: `P0`
- Variants: `left_boot:oath_hero_sole`, `left_boot:rescue_toe_guard`, `left_boot:guardian_split_toe`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `left_boot:oath_hero_sole` | Increase final-form identity while keeping practical boot mass. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_rescue_knight` | `left_boot:rescue_toe_guard` | Add `boot_closeup_side.png`; verify sole does not float. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_royal_insect` | `left_boot:guardian_split_toe` | Make guardian toe/ankle motif distinct from c02 and c15. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |

### right_boot

- Priority: `P0`
- Variants: `right_boot:oath_hero_sole`, `right_boot:rescue_toe_guard`, `right_boot:guardian_split_toe`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `right_boot:oath_hero_sole` | Compare left/right gold/cyan trim and sole shape. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_rescue_knight` | `right_boot:rescue_toe_guard` | Compare grounded sole and toe cap with left. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |
| `line_royal_insect` | `right_boot:guardian_split_toe` | Compare left/right toe split and ankle line. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `boot_closeup_side` |

### waist

- Priority: `P1`
- Variants: `waist:oath_driver_ring`, `waist:rescue_driver`, `waist:guardian_buckle`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `waist:oath_driver_ring` | Add visible gold/cyan continuity to legs; keep hip motion clear. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_rescue_knight` | `waist:rescue_driver` | Connect blue/white chest line into belt and thigh start. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |
| `line_royal_insect` | `waist:guardian_buckle` | Make buckle read as line-specific, not generic belt trim. | `front`, `side`, `back`, `3q`, `source_overlay_front`, `torso_closeup_front`, `torso_closeup_back` |

### left_shoulder

- Priority: `P1`
- Variants: `left_shoulder:oath_guard_fin`, `left_shoulder:sleek_rescue_cap`, `left_shoulder:wing_cap`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `left_shoulder:oath_guard_fin` | More final-form trim density while preserving arm lift. | `front`, `side`, `back`, `3q`, `source_overlay_front` |
| `line_rescue_knight` | `left_shoulder:sleek_rescue_cap` | Read as compact rescue armor in front/side/back. | `front`, `side`, `back`, `3q`, `source_overlay_front` |
| `line_royal_insect` | `left_shoulder:wing_cap` | Increase silhouette distinction from c02 without widening too much. | `front`, `side`, `back`, `3q`, `source_overlay_front` |

### right_shoulder

- Priority: `P1`
- Variants: `right_shoulder:oath_guard_fin`, `right_shoulder:sleek_rescue_cap`, `right_shoulder:wing_cap`
- Runtime visibility: `reviewer_only_until_fidelity_pass`

| Line | Variant | Requested fix | Evidence |
|---|---|---|---|
| `line_final_oath` | `right_shoulder:oath_guard_fin` | Check right-side trim does not vanish in Quest view. | `front`, `side`, `back`, `3q`, `source_overlay_front` |
| `line_rescue_knight` | `right_shoulder:sleek_rescue_cap` | Mirror review with left in side/back views. | `front`, `side`, `back`, `3q`, `source_overlay_front` |
| `line_royal_insect` | `right_shoulder:wing_cap` | Confirm both shoulders are symmetric enough but not pasted-looking. | `front`, `side`, `back`, `3q`, `source_overlay_front` |

## Acceptance Recheck Steps

| Step | Gate | Command | Pass condition |
|---:|---|---|---|
| 1 | `delivery_manifest` | `python tools\validate_modeler_delivery_manifest.py --manifest docs\modeler-deliveries\first-three-lines-2026-05-02.delivery-manifest.json` | status=pass, asset_count=30, reasons=[] |
| 2 | `variant_catalog` | `python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots` | catalog validates without warnings or missing variant keys |
| 3 | `sidecar_provenance` | `inspect delivered *.modeler.json sidecars` | each held variant has top-level source_concept_ids, line_id, design_intent, fidelity_notes |
| 4 | `tri_view_evidence` | `review front/side/back/3q and required closeups per line` | evidence includes front, side, back, 3q, source_overlay_front, closeup, boot_closeup_side where applicable |
| 5 | `runtime_route_proof` | `run Web smoke, then capture Quest/Replay notes for promoted candidates` | fallback count is 0 and no fidelity_hold item is public runtime selectable |

## Runtime Release Impact

- Public runtime allowed: `False`
- Runtime block label: `runtime_release_blocked_by_fidelity_hold`
- Held variant count: `30`
- Missing P1 count: `24`

- Canonical/base exhibition runtime may proceed independently if package smoke passes.
- The 30 delivered line variants stay reviewer-only until fidelity_pass.
- A line-complete claim is blocked until the separate 24-item P1 limb order is accepted.
- Quest and Replay proof are required before any public runtime selector mapping.
