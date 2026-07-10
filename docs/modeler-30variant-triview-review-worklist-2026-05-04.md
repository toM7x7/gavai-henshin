# Modeler 30 Variant Triview Review Worklist - 2026-05-04

Scope: turn the existing 30 delivered three-line variants into an executable front/side/back/3Q review workflow.

Owner boundary: this document only. Do not edit GLB, Blender, assets, viewer code, tools, or tests as part of this worklist.

## Inputs And Current Decision

Source docs:

- `docs/modeler-triview-30variant-audit-table-2026-05-03.md`
- `docs/modeler-fidelity-hold-tracking-2026-05-04.md`
- `docs/modeler-fit-micro-adjustments-2026-05-04.md`
- `docs/modeler-fit-and-triview-next-audit-2026-05-04.md`

Current gate:

- The 30 variants are mechanically delivered in the modeler delivery worktree.
- The 30 variants remain `fidelity_hold`; they are not public runtime assets.
- Hold reasons are visual identity, tri-view completeness, missing top-level sidecar provenance, and missing closeup/overlay proof.
- P1 limb variants for `upperarm`, `forearm`, `hand`, and `thigh` are not part of this 30variant review because those 24 filesets are still missing.

## Machine-Readable Audit Packet

Use this when turning the current tri-view audit into modeler tickets or a fix handoff. It reads `docs/modeler-triview-30variant-audit-table-2026-05-03.md` and emits JSON without Blender, image rendering, or GLB inspection.

```powershell
python tools\export_modeler_triview_audit_packet.py --out qa\modeler-triview-audit-latest.json --report-json
```

The packet contains `review_status`, `fidelity_hold_items`, `per_part_findings`, `modeler_fix_message_outline`, `acceptance_recheck_steps`, and `runtime_release_impact`. Treat `fidelity_hold_items` as the 30 delivered-but-held fix list; keep `missing_p1` rows as separate P1 limb order work.

## Modeler Fix Request Export

Use this when sending the audit packet back to the modeler as a correction request plus acceptance recheck table.

```powershell
python tools\export_modeler_fix_request.py --out docs\modeler-fix-request-latest.md --report-json
```

The Markdown contains the fidelity hold list, per-part fix requests, modeler delivery blockers, acceptance recheck steps, and runtime release impact. If `qa\modeler-triview-audit-latest.json` already exists, pass it with `--packet qa\modeler-triview-audit-latest.json` to reuse the saved audit packet.

## Review Result Labels

Use one label per variant and one rollup label per part family.

| Label | Meaning | Allowed next step |
|---|---|---|
| `fidelity_hold` | File-valid but not runtime-ready. Evidence, metadata, fit, or visual identity is insufficient. | Rework or add evidence. |
| `review_candidate` | Rework/evidence packet is complete enough for human tri-view review. | Human review can start. |
| `staging_candidate` | Human accepts visual identity and fit smoke has no blocking defect. | Runtime staging check, still not public. |
| `fidelity_pass` | Route proof is complete for a named package/build. | Separate runtime activation change may map it into public selection. |

Promotion is strict:

- `fidelity_hold -> review_candidate`: sidecar provenance exists, front/side/back/3Q evidence exists, and micro-adjustment record is filled if any size/position/angle change was made.
- `review_candidate -> staging_candidate`: human reviewer accepts line identity in front/side/back/3Q, fit checks are non-blocking, and Web smoke has fallback count `0`.
- `staging_candidate -> fidelity_pass`: packaged Web proof, Quest/replay proof where relevant, no unresolved visitor-facing waiver, and runtime visibility explicitly approved.

## Global View Checks

Apply these checks to every variant before per-part specifics.

| View | What to inspect | Fail condition |
|---|---|---|
| `front` | First-read identity, broad color/shape blocks, silhouette against source concept, left/right balance for paired parts. | Reads as generic white armor, color-only distinction, or obvious left/right drift. |
| `side` | Body-relative depth, surface contact, joint clearance, no floating shell, no paper-thin side profile. | Floats off body, clips into body, blocks motion, or loses all line identity from side. |
| `back` | Continuity around the body, rear line identity, Replay/archive readability. | Back is blank, box-like, unrelated to front, or impossible to trace to the same line. |
| `3Q` | Visitor-like read: silhouette, depth, line separation, and material zones under mixed front/side view. | Only front view works; 3Q collapses into proxy geometry or another line. |

Line separation checks:

- `line_rescue_knight`: blue/cyan rescue identity must read as clean, slim, functional armor.
- `line_royal_insect`: green/white/gold guardian identity must read through compound/carapace/ridge forms, not only tint.
- `line_final_oath`: pearl/gold/cyan final form must be denser and more ceremonial than royal insect without breaking fit.

## Exhibition Priority Order

Use this order until exhibition package risk is closed:

1. Helmet: visitor first-read and face identity.
2. Chest: hero core and full-body suit identity.
3. Back: Replay/archive proof and non-blank rear read.
4. Boots: grounding, floor read, and Quest stance.
5. Shins: lower-body continuity into boots.
6. Waist: torso-to-leg bridge.
7. Shoulders: line silhouette without arm-lift interference.
8. P1 limb shortages: separate order flow, not a blocker for reviewing the existing 30.

## Per-Part Review Worklist

### Helmet

Variants: `helmet:rescue_sleek`, `helmet:compound_guardian`, `helmet:oath_crown_visor`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Visor/face direction, line-specific faceplate, grayscale silhouette. Rescue needs a blue visor block; royal insect needs compound-eye/crest read; final oath needs crown/ceremonial visor. |
| `side` | Helmet depth, crest/visor projection, no flat mask read, no neck/shoulder collision. |
| `back` | Rear helmet cap or trim continues the line; not a blank white shell. |
| `3Q` | Face identity remains readable when not straight-on; c01/c02/c15 do not collapse into the same helmet. |

Staging condition: reviewer can identify all 3 lines in grayscale front and 3Q, and side view shows real geometry rather than texture-only marks.

Likely micro-adjustments: visor scale, crest height, faceplate angle, side trim depth.

### Chest

Variants: `chest:rescue_wrap`, `chest:emerald_v_core`, `chest:oath_core_shell`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Core shape dominates first-read. Rescue needs cyan/blue rescue core; royal insect needs emerald V; final oath needs larger cyan core plus gold density. |
| `side` | Chest depth and rib wrap; avoid flat plate and sunken core. Apply `chest.z` micro-adjustment record when changed. |
| `back` | Chest choices connect into back/shoulder line; no abrupt visual cutoff at side seam. |
| `3Q` | Core, ribs, and collar still read as armor wrapped around torso. |

Staging condition: side/3Q proof shows volume and wrap, Web first-read does not return to generic white torso, and bbox/sidecar match remains `<=0.002m`.

Likely micro-adjustments: core depth, rib width, collar angle, side seam placement.

### Back

Variants: `back:compact_spine`, `back:wing_shell_close`, `back:oath_spine_rear_core`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Back volume must not protrude visibly as a backpack block from front/3Q outline. |
| `side` | Body-hugging rear depth, shoulder-blade relationship, no floating slab. |
| `back` | Main review view: rescue compact spine, royal insect dorsal shell, final oath rear core/spine. |
| `3Q` | Rear identity visible while still tied to chest/waist/shoulders. |

Staging condition: back view has line-specific geometry and side view proves it is attached, not a rectangular pack.

Likely micro-adjustments: rear depth, spine height, shell width, shoulder-blade angle.

### Waist

Variants: `waist:rescue_driver`, `waist:guardian_buckle`, `waist:oath_driver_ring`

Priority: P1 for exhibition, but review before shoulders if torso-to-leg flow is visually broken.

| View | Review focus |
|---|---|
| `front` | Belt/driver identity, buckle shape, line connection from chest to legs. |
| `side` | Pelvis wrap and float check; runtime `y -1mm` max only if the belt visibly floats. |
| `back` | Belt continues around pelvis; no blank rear band. |
| `3Q` | Waist reads as a bridge, not a separate ring hovering between torso and legs. |

Staging condition: no floating ring read, hip clearance is preserved, and any remaining `waist.x` warning has proof or waiver.

Likely micro-adjustments: x width, y placement, buckle depth, side clip angle.

### Left Shoulder

Variants: `left_shoulder:sleek_rescue_cap`, `left_shoulder:wing_cap`, `left_shoulder:oath_guard_fin`

Priority: P1.

| View | Review focus |
|---|---|
| `front` | Shoulder cap silhouette and line identity without oversized width. |
| `side` | Arm-lift clearance and cap depth. |
| `back` | Shoulder-to-back flow, especially final oath trim and royal insect wing/carapace hint. |
| `3Q` | Cap reads as paired armor and does not hide chest/helmet identity. |

Staging condition: arm-lift risk is explicitly checked and the shoulder remains line-specific without broadening into motion interference.

Likely micro-adjustments: cap angle, outer width, fin height, rear trim depth.

### Right Shoulder

Variants: `right_shoulder:sleek_rescue_cap`, `right_shoulder:wing_cap`, `right_shoulder:oath_guard_fin`

Priority: P1.

| View | Review focus |
|---|---|
| `front` | Mirror balance against left shoulder; no visible quality drift. |
| `side` | Arm-lift clearance and cap depth matching the left-side intent. |
| `back` | Shoulder-to-back flow mirrors left without losing line detail. |
| `3Q` | Right-side trim remains visible in visitor-like view. |

Staging condition: mirror-pair delta is `<=3%` unless a documented asymmetry is accepted, and arm-lift clearance is preserved.

Likely micro-adjustments: mirrored angle, cap height, outer offset, trim alignment.

### Left Shin

Variants: `left_shin:rescue_stream`, `left_shin:guardian_ridge`, `left_shin:oath_glow_guard`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Shin stream/ridge/guard is broad enough to read at Quest distance. |
| `side` | Depth and knee/ankle escape; no paper-thin stripe. |
| `back` | Calf-side continuity and no blank rear lower leg. |
| `3Q` | Line identity connects from knee area toward boot. |

Staging condition: shin-to-boot continuity is visible, x width is at or above minimum pass when adjusted, and mirror-pair review with right shin remains balanced.

Likely micro-adjustments: x width toward pass minimum, outer ridge depth, ankle transition, knee trim angle.

### Right Shin

Variants: `right_shin:rescue_stream`, `right_shin:guardian_ridge`, `right_shin:oath_glow_guard`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Mirror of left shin streams/ridges/guards, equal height and scale. |
| `side` | Right-side depth and ankle/knee clearance. |
| `back` | Calf-side continuity mirrors left. |
| `3Q` | Trim continues into right boot and does not disappear. |

Staging condition: mirror-pair delta `<=3%`, shin-to-boot continuity visible, and no Quest stance risk is introduced.

Likely micro-adjustments: paired x width, height alignment, side ridge angle, ankle placement.

### Left Boot

Variants: `left_boot:rescue_toe_guard`, `left_boot:guardian_split_toe`, `left_boot:oath_hero_sole`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Toe cap, ankle cuff, and line identity are readable without overcomplicating the foot. |
| `side` | Ground contact, heel, sole height, toe projection. `boot_closeup_side.png` is required before staging. |
| `back` | Heel and rear ankle read; no blank boot rear. |
| `3Q` | Boot looks grounded and connected to shin, not detached footwear. |

Staging condition: sole/toe/heel are grounded in side view, boot-side closeup exists, and no foot float is visible.

Likely micro-adjustments: toe cap depth, heel height, sole y placement, ankle cuff angle.

### Right Boot

Variants: `right_boot:rescue_toe_guard`, `right_boot:guardian_split_toe`, `right_boot:oath_hero_sole`

Priority: P0.

| View | Review focus |
|---|---|
| `front` | Mirror balance with left boot and equal line identity. |
| `side` | Ground contact, heel, sole height, toe projection. `boot_closeup_side.png` is required before staging. |
| `back` | Heel and rear ankle read mirrors left. |
| `3Q` | Boot-to-shin connection remains visible. |

Staging condition: left/right sole height and toe/heel mass match, no foot float, and Quest stance note is attached for promotion.

Likely micro-adjustments: paired sole height, toe cap depth, heel placement, ankle cuff alignment.

## Per-Variant Review Rows

Use this compact row while reviewing the 30 variants. Copy one row per variant into the review packet or issue tracker.

| Field | Value |
|---|---|
| `variant_key` | `<module>:<asset_key>` |
| `line_id` | `line_rescue_knight` / `line_royal_insect` / `line_final_oath` |
| `source_concept_ids` | `["c02"]` / `["c01"]` / `["c15"]` |
| `front_status` | `pass` / `hold` plus one-line reason |
| `side_status` | `pass` / `hold` plus one-line reason |
| `back_status` | `pass` / `hold` plus one-line reason |
| `3q_status` | `pass` / `hold` plus one-line reason |
| `metadata_status` | `pass` only if top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes` are present |
| `fit_status` | bbox/mirror/placement result or `not_checked` |
| `next_state` | `fidelity_hold`, `review_candidate`, `staging_candidate`, or `fidelity_pass` |

## Micro-Adjustment Record

Use this JSON shape for every size, position, or angle change, even when the change is tiny. The goal is to avoid invisible "looks better" edits that cannot be replayed.

```json
{
  "adjustment_id": "TRI30-BOOT-L-RESCUE-001",
  "date": "2026-05-04",
  "variant_keys": ["left_boot:rescue_toe_guard"],
  "priority": "P0",
  "reason": "side view sole appears to float above floor",
  "change_type": "position",
  "axis": "y",
  "before": {"value_mm": 0.0, "source": "review side render"},
  "after": {"delta_mm": -1.0, "limit_mm": 2.0},
  "paired_change_required": true,
  "paired_variant_keys": ["right_boot:rescue_toe_guard"],
  "views_rechecked": ["front", "side", "back", "3q"],
  "fit_checks": {
    "fallback_parts": 0,
    "bbox_warning_count": "unchanged_or_lower",
    "sidecar_glb_bbox_match_max_m": 0.002,
    "mirror_pair_delta_max_percent": 3
  },
  "reviewer_note": "Side closeup confirms grounded sole; no ankle clipping."
}
```

Allowed tiny adjustment categories:

- `position`: x/y/z attachment or mesh placement corrections. Use only to fix float, clip, or side-depth read.
- `size`: scale or local geometry widening/deepening. Must preserve bbox tolerance and mirror pair balance.
- `angle`: rotation, cap angle, toe/heel pitch, fin/ridge angle. Must be rechecked in side and 3Q.
- `silhouette`: geometry edits that improve broad read. Must include grayscale or distance-read note for helmet/chest/back/boot.

Adjustment limits:

- Runtime placement nudges should stay within `2mm` unless explicitly reviewed.
- GLB/sidecar bbox match remains `<=0.002m`.
- Mirror-pair delta remains `<=3%`.
- A visual improvement that introduces fallback, clipping, or metadata loss is rejected.

## P1 Limb Shortage Cut Line

Do not mix the missing P1 limb delivery gap into this 30variant review.

In scope for this worklist:

- Existing 30 delivered variants for helmet, chest, back, waist, left/right shoulder, left/right shin, and left/right boot.
- Their sidecar provenance, fidelity notes, view evidence, micro-adjustments, and promotion state.

Out of scope for this worklist:

- `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`, `left_hand`, `right_hand`, `left_thigh`, `right_thigh` line variants.
- The 24 missing P1 filesets and their strict order acceptance.

Boundary rule:

- A delivered 30variant can move to `staging_candidate` without waiting for P1 limb delivery if its own part, route proof, and adjacent continuity are acceptable.
- A full-body "line complete" claim cannot be made until the P1 limb order passes its own delivery and review gates.
- Shins/boots may reference the missing thighs as a known continuity gap, but they should still be reviewed for their own grounding and lower-leg identity.

## Daily Review Sequence

1. P0 visual identity block: helmet, chest, back.
2. P0 grounding block: left boot, right boot, left shin, right shin.
3. P1 bridge block: waist.
4. P1 shoulder block: left shoulder, right shoulder.
5. Metadata sweep: verify top-level sidecar provenance and `fidelity_notes` for every variant reviewed that day.
6. Promotion sweep: update each reviewed variant label and list blockers for the next modeler handoff.

Stop condition for a day:

- Do not continue broad review if helmet/chest/back still collapse into the same line identity. Those are the highest exhibition risk and should consume review time first.

## Required Evidence Before Staging

For each promoted variant:

- front, side, back, and 3Q render links.
- sidecar provenance proof.
- `fidelity_notes` summarizing source concept interpretation and remaining deviations.
- micro-adjustment record if geometry/placement changed.
- reviewer sign-off naming line identity, fit, and route risk.

For each promoted line packet:

- `source_overlay_front.png`.
- helmet closeup.
- torso closeup.
- `boot_closeup_side.png`.
- Web smoke output showing fallback count `0`.
- Quest/replay note when the promoted change affects hands, feet, head, torso, recall identity, grounding, or motion clearance.

## Final Done Definition

This review worklist is complete when:

1. All 30 variants have front/side/back/3Q statuses.
2. Every hold has a concrete modeler action or evidence request.
3. Every staging candidate has sidecar provenance, view evidence, fit proof, and reviewer sign-off.
4. No `fidelity_hold` variant is marked public runtime-ready.
5. P1 limb shortages remain tracked in the separate P1 order acceptance flow, not hidden inside this 30variant review.
