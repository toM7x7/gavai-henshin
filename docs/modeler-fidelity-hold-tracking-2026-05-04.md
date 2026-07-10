# Modeler Fidelity Hold Tracking - 2026-05-04

Purpose: compact exhibition-facing tracker for the 30 three-line tri-view variants currently marked `fidelity_hold`. This does not replace the full audit table; it names the highest-risk variants, manual micro-adjustments, and evidence needed before any held asset moves toward runtime pass.

Route baseline: `Web: Suit Forge -> Quest: Henshin Trial -> Replay: Archive`. A modeler pass is not only "files load"; the suit must read as the same lore identity through Web inspection, Quest transformation, and Replay evidence.

## Source Links

- `docs/modeler-triview-30variant-audit-table-2026-05-03.md`: source of the 30-variant per-part hold table.
- `docs/modeler-exhibition-readiness-risks-2026-05-04.md`: exhibition package risks and waiver protocol.
- `docs/modeler-fit-micro-adjustments-2026-05-04.md`: active bbox and placement micro-adjustment list.
- `docs/modeler-fidelity-gate-status-2026-05-02.md`: original `technical pass / fidelity hold` decision.
- `docs/modeler-triview-handoff-2026-05-02.md`: source tri-view interpretation rules and sidecar expectations.
- `docs/new-route-design-coherence-audit.md`: lore route and visual coherence baseline.

## Current Gate

- File/mechanical status: the delivered 30 P0 variants are file-valid in the delivery worktree.
- Runtime status: keep all 30 disabled for the public exhibition selector until a new fidelity packet exists.
- Main blocker: the three lines are not yet visually distinct enough in full-body front/side/back/3Q, and per-asset provenance is incomplete.
- Exhibition posture: canonical/base public demo can proceed separately if smoke and package gates pass; held variants stay reviewer-only.
- Fit handoff contract: `tools/export_modeler_fit_adjustments.py --format json` emits `modeler-fit-adjustments.v0.2` rows for numeric bbox fixes that overlap this hold list.
- Waist loop posture: `body_wrap_loop` metadata is not a modeler pass. `waist` remains on fidelity hold until a GLB loop export exists and front/side/back/3Q evidence proves a closed pelvis-worn tube; this hold is separate from any exhibition runtime smoke pass.

## Route Quality Gates

Experience lore: **Webでスーツ成立、Questで変身試験、Replayで体験を残す**.

| Route stage | Model quality gate | What must not fail |
|---|---|---|
| Web / Suit Forge | Full-body first-read, line identity, no GLB fallback, no public selector exposure for held variants. | Visitor sees a generic white armor or accidentally selects a `fidelity_hold` line variant. |
| Quest / Henshin Trial | Body-relative placement, motion clearance, grounding, mirror-pair symmetry. | Chest/waist/arms/legs float, clip, or break the transformation read at headset distance. |
| Replay / Archive | Side/back/3Q evidence, sidecar provenance, stable 4-digit recall identity. | Recorded proof cannot tell which source line was used, or back/side views contradict the Web read. |

## Modeler Intake Row Format

Use this row shape when creating modeler tickets from the 30 held variants. Numeric rows should copy values from `docs/modeler-fit-micro-adjustments-2026-05-04.md`; non-numeric fidelity rows should still name size/position intent and proof.

```json
{
  "adjustment_id": "FID-P0-CHEST-Z",
  "priority": "P0",
  "scope": "chest core depth and identity",
  "variant_keys": ["chest:rescue_wrap", "chest:emerald_v_core", "chest:oath_core_shell"],
  "size_tasks": [{"axis": "z", "actual_mm": 142.4, "pass_min_mm": 146.9, "demo_target_mm": 148.4}],
  "placement_nudges": [{"axis": "z", "max_mm": 2.0, "direction": "forward", "when": "only if visually sunken"}],
  "proof_required": ["front", "side", "back", "3q", "closeup"],
  "route_gate": ["web", "quest", "replay"],
  "runtime_visibility": "reviewer_only_until_fidelity_pass"
}
```

## Exhibition-Direct Adjustment Rows

| Adjustment id | Priority | Scope | Variant keys | Size/position action | Route gate hit |
|---|---|---|---|---|---|
| `FID-P0-HELMET-SIL` | P0 | Helmet first-read | `helmet:rescue_sleek`, `helmet:compound_guardian`, `helmet:oath_crown_visor` | Increase readable visor/compound-eye/crown geometry and silhouette contrast; texture-only lines are not enough. | Web first-read, Replay source identity. |
| `FID-P0-CHEST-Z` | P0 | Chest depth/core | `chest:rescue_wrap`, `chest:emerald_v_core`, `chest:oath_core_shell` | Use `chest.z`: current `142.4mm`, pass min `146.9mm`, demo target `148.4mm`, full target `163.2mm`; runtime `z +2mm` max only if visually sunken. | Web hero core, Quest torso clearance, Replay side/3Q proof. |
| `FID-P0-BACK-HUG` | P0 | Rear identity | `back:compact_spine`, `back:wing_shell_close`, `back:oath_spine_rear_core` | Add visible spine/shell/rear-core volume that stays body-hugging and tied to chest/waist; avoid backpack-block depth. | Web back toggle/read, Replay archive proof. |
| `FID-P0-BOOT-GROUND` | P0 | Foot grounding | `left/right_boot:rescue_toe_guard`, `left/right_boot:guardian_split_toe`, `left/right_boot:oath_hero_sole` | Tune toe cap, heel, sole contact, ankle cuff, and left/right sole height; require `boot_closeup_side.png`. | Quest stance, Web floor read, Replay lower-body evidence. |
| `FID-P0-SHIN-X` | P0 | Shin-to-boot width | `left/right_shin:rescue_stream`, `left/right_shin:guardian_ridge`, `left/right_shin:oath_glow_guard` | Use shin `x`: current `101.7mm`, pass min `104.0mm`, demo target `105.5mm`, full target `115.6mm`; outward nudge max `2mm` per side only if boot step appears. | Web lower-body strength, Quest leg motion, Replay stance proof. |
| `FID-P1-WAIST-X` | P1 | Waist continuity | `waist:rescue_driver`, `waist:guardian_buckle`, `waist:oath_driver_ring` | Use `waist.x`: current `440.4mm`, pass min `440.6mm`, demo target `442.1mm`, full target `489.6mm`; runtime `y -1mm` max only if floating. Also export the actual GLB `body_wrap_loop`; metadata-only loop does not pass as a wearable tube. | Web torso-leg bridge, Quest hip clearance, front/side/back/3Q loop proof. |
| `FID-P1-SHOULDER-PAIR` | P1 | Shoulder silhouette | `left/right_shoulder:*` across 3 lines | Make shoulder caps line-specific without broadening into arm-lift interference; preserve paired symmetry. | Web line identity, Quest shoulder clearance. |
| `FID-P1-LIMB-FUTURE` | P1 | Missing line limbs | 24 missing upperarm/forearm/hand/thigh filesets | Do not claim complete limbs. For future upperarms, inherit base numeric width rule: current `96.3mm`, pass min `97.9mm`, demo target `99.4mm`, paired outward nudge max `2mm` if needed. | Quest controller/body motion, Replay pose proof. |

## Highest-Risk Parts And Variants

| Priority | Scope | Variants affected | Why it is high risk | Manual micro-adjustment needed |
|---|---|---|---|---|
| P0 | Helmet identity | `helmet:rescue_sleek`, `helmet:compound_guardian`, `helmet:oath_crown_visor` | Visitor first read depends on face silhouette; c01/c02/c15 separation is weak. | Enlarge broad visor/crest geometry, not only texture lines. Rescue needs a blue visor block; royal insect needs compound-eye and short crest readable in grayscale; final oath needs crown geometry and denser gold/cyan trim. |
| P0 | Chest core | `chest:rescue_wrap`, `chest:emerald_v_core`, `chest:oath_core_shell` | Chest anchors the hero-suit identity and currently risks generic white armor read. | Increase core/V silhouette contrast and side thickness. Respect `chest.z` micro target from `modeler-fit-micro-adjustments`: current `142.4mm`, target `163.2mm`, minimum pass `146.9mm`. |
| P0 | Back read | `back:compact_spine`, `back:wing_shell_close`, `back:oath_spine_rear_core` | Lore route requires Replay/Archive back proof; back cannot be a blank or box-like afterthought. | Add line-specific spine/rear-core/shell shape visible in back and side. Keep it body-hugging, tied to chest/waist, and not a backpack block. |
| P0 | Boots and grounding | `left/right_boot:rescue_toe_guard`, `left/right_boot:guardian_split_toe`, `left/right_boot:oath_hero_sole` | Quest stance and exhibition floor read fail fast if feet float or toe/sole language is vague. | Add side `boot_closeup_side.png`; tune toe cap, heel, sole contact, ankle cuff, and left/right sole height. Use broad colored panels, not tiny trim only. |
| P0 | Shin-to-boot continuity | `left/right_shin:rescue_stream`, `left/right_shin:guardian_ridge`, `left/right_shin:oath_glow_guard` | Lower body currently has bbox width warnings and weak boot connection risk. | Pair-widen shins toward `115.6mm`; minimum pass `104.0mm`. Preserve mirror delta <=3% and show front plus boot-side closeup. |
| P1 | Missing limbs | upperarm, forearm, hand, thigh across all 3 lines | 24 filesets are still absent, so line-complete arms/hands/thighs cannot be claimed. | Keep as ordered P1 work. For exhibition, do not script these as complete. For later pass, use paired left/right geometry with controller, elbow, hip, knee clearance proof. |
| P1 | Waist continuity | `waist:rescue_driver`, `waist:guardian_buckle`, `waist:oath_driver_ring` | Belt connects torso to legs; narrow or generic waist breaks full-body tri-view flow. Metadata-only `body_wrap_loop` can also create false confidence. | Widen or edge-density tune toward `waist.x` minimum pass `440.6mm`; export GLB loop and attach front/side/back/3Q proof before any fidelity pass. |

## Line-Specific Hold Focus

| Line | Must read from tri-view | Highest-risk fixes |
|---|---|---|
| `line_rescue_knight` | White/blue rescue suit, blue visor, cyan chest core, compact back, grounded boots. | Strengthen blue/cyan blocks on helmet, chest, back spine, shin stream, and boot toe/ankle so it no longer reads as generic white procedural armor. |
| `line_royal_insect` | Green/white/gold guardian suit, compound visor, short crest/antenna, emerald V chest, close-body shell. | Make insect language heroic and readable at Quest distance: compound-eye silhouette, emerald V, dorsal shell, guardian boot/ankle symbols. |
| `line_final_oath` | Pearl/gold/cyan final form, crown visor, large cyan core, dense gold trim, glow continuity into legs/boots. | Separate from royal insect by adding final-form density and crown/core dominance without growing into arm, waist, hip, or boot motion interference. |

## Evidence Needed To Move Toward Pass

Treat this as a promotion packet for each line, with per-asset notes for every promoted variant.

| Evidence | Required content | Why it matters |
|---|---|---|
| Sidecar provenance | Top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes` on each variant sidecar. | Replay/debug must know which source tri-view the asset claims to embody; catalog fallback is not enough. |
| Full tri-view renders | Per line: full front, side, back, and 3Q renders from the delivered assets. | Prevents front-only fixes that fail in Quest or Replay. |
| Source overlay | Per line: `source_overlay_front.png` comparing source front to delivered front. | Gives a reviewer a concrete silhouette/color-block delta, without requiring Blender. |
| Closeups | Per line: helmet closeup, torso closeup, and `boot_closeup_side.png`. | Focuses the highest-risk first-read and grounding areas. |
| Grayscale read | Helmet/chest/back/boot distinction remains visible without color. | Ensures identity is carried by shape and broad zones, not tiny emissive texture. |
| Fit proof | Updated `smoke_web_glb_load.py --report-json`, bbox deltas, mirror-pair result, and GLB/sidecar bbox match <= `0.002m`. | Prevents visual rework from regressing body fit or authoring metadata. |
| Waist loop proof | Validator JSON shows GLB loop exported, not metadata-only, plus front/side/back/3Q renders proving the belt is a closed pelvis tube. | Keeps runtime pass separate from modeler fidelity pass; Web/Quest should not present a contract-only loop as wearable geometry. |
| Route proof | Screenshots from packaged Web build plus Quest/replay note when the change affects hands, feet, head, torso, or recall. | Confirms the lore route: Suit Forge inspection, Henshin Trial body-relative read, Replay Archive evidence. |

## Promotion Ladder

Use these labels in review notes; do not rename held assets to pass prematurely.

| Stage | Meaning | Minimum evidence |
|---|---|---|
| `fidelity_hold` | File-valid but not runtime-ready. | Current state for all 30 variants. |
| `review_candidate` | Manual rework landed and evidence packet is complete enough for human tri-view review. | Sidecar provenance, full tri-view renders, overlay, closeups, and stated deltas. |
| `staging_candidate` | Human tri-view review accepts the visual identity and fit smoke has no failures. | Review sign-off, smoke JSON, bbox/mirror proof, no public selector exposure yet. |
| `fidelity_pass` | Safe to map into runtime selection for a named package/build. | Packaged Web proof, Quest/replay proof when relevant, no waiver hiding a known visitor-facing defect. |

## Exhibition Guardrails

- Public package must not expose `fidelity_hold` variants as accepted runtime choices.
- Any reviewer-only visibility must be marked as reviewer/operator-only, not `pass`.
- A waiver may support a demo rehearsal, but it does not convert `fidelity_hold` into `fidelity_pass`.
- Do not claim line-complete arms, hands, or thighs until the 24 missing P1 filesets have their own delivery and evidence.
- When in doubt, prioritize in this order: helmet, chest, back, boots, shins, waist, shoulders, then P1 limbs. This matches first visual read and exhibition failure risk.
