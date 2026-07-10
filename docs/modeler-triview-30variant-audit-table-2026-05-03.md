# Modeler Triview 30 Variant Audit Table - 2026-05-03

Scope: `.claude/worktrees/jovial-cohen-4bf60f` の `first-three-lines-2026-05-02` 納品を、既存の三面図基準で1パーツずつ確認するための監査表。  
Runtime premise: ロアを守りつつ「Webでスーツ成立、Questで変身試験、Replayで体験を残す」。  
Decision: **technical/file pass, fidelity hold**。Web/Quest runtime への本採用は、三面図 fidelity pass まで保留。

## Source Docs Read

- `docs/modeler-triview-handoff-2026-05-02.md`
- `docs/modeler-first-three-lines-order-2026-05-02.md`
- `docs/modeler-three-lines-fidelity-review-2026-05-02.md`
- `docs/modeler-fidelity-gate-status-2026-05-02.md`
- `docs/modeler-part-delivery-audit-worktree-2026-05-03.md`
- `.claude/worktrees/jovial-cohen-4bf60f/docs/modeler-handoff-three-lines-2026-05-02.md`

## Mechanical Cross-check

Run location matters: the delivery manifest uses paths relative to the delivery worktree. Running the validator from the main repo cwd reports missing files; running from the delivery worktree passes.

```powershell
cd C:\dev\codex\gavai-henshin\.claude\worktrees\jovial-cohen-4bf60f
python tools\validate_modeler_delivery_manifest.py --manifest docs\modeler-deliveries\first-three-lines-2026-05-02.delivery-manifest.json
# status=pass, asset_count=30, reasons=[], warnings=[]

python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
# status=pass, module_count=18, reasons=[], warnings=[]
```

Additional read-only audit from the main repo:

```powershell
python tools\audit_modeler_part_delivery.py `
  --assets-root .claude\worktrees\jovial-cohen-4bf60f\viewer\assets\armor-parts `
  --catalog .claude\worktrees\jovial-cohen-4bf60f\viewer\assets\armor-parts\variant_catalog.json `
  --format json
# part_count=18, asset_count=116
# status_counts={"metadata_hold":72,"fidelity_hold":30,"missing":14}
```

Interpretation:

- The 30 newly delivered line variants are file-valid: GLB, `.modeler.json`, source `.blend`, and preview mesh exist and parse.
- Those same 30 are `fidelity_hold`: catalog has `line_id` and `design_intent`, but per-asset sidecar top level still lacks `source_concept_ids`, `line_id`, `design_intent`, and especially `fidelity_notes`.
- Existing human review also holds fidelity because the 3 lines still read too similarly against the source triviews.
- P1 modules `upperarm`, `forearm`, `hand`, `thigh` have no line variants. Catalog still has only `<module>:base`; line variant count is 0 for left/right of all four families.
- Review render folder contains 30 PNGs: full front/side/back/3q plus helmet and torso closeups per line. Required `source_overlay_front.png` and `boot_closeup_side.png` are still not present.
- Waist loop note: current `body_wrap_loop` evidence is metadata/contract only. It does not pass as a tri-view wearable tube until a regenerated GLB loop is exported and front/side/back/3Q proof shows a closed belt around the pelvis.

## Current Delivery Coverage

| Module family | Module ids | 3-line variant coverage | Current gate |
|---|---|---:|---|
| helmet | `helmet` | 3/3 | file pass / fidelity hold |
| chest | `chest` | 3/3 | file pass / fidelity hold |
| back | `back` | 3/3 | file pass / fidelity hold |
| waist | `waist` | 3/3 | file pass / fidelity hold |
| shoulder | `left_shoulder`, `right_shoulder` | 6/6 | file pass / fidelity hold |
| shin | `left_shin`, `right_shin` | 6/6 | file pass / fidelity hold |
| boot | `left_boot`, `right_boot` | 6/6 | file pass / fidelity hold |
| upperarm | `left_upperarm`, `right_upperarm` | 0/6 | missing P1 line variants |
| forearm | `left_forearm`, `right_forearm` | 0/6 | missing P1 line variants |
| hand | `left_hand`, `right_hand` | 0/6 | missing P1 line variants |
| thigh | `left_thigh`, `right_thigh` | 0/6 | missing P1 line variants |

## Triview Audit Standard

Use this order for every part. The point is not pixel tracing; the part must still read as the source hero suit when seen in Web/Quest.

1. Silhouette: distinguishable in grayscale, especially head, chest, back, shin, and boots.
2. Body fit: follows VRM/body surface without floating, clipping, or blocking expected motion.
3. Base suit continuity: color panels and glow/trim lines connect across torso, arms, waist, legs, and boots.
4. Front/side/back readability: side and back must carry line-specific information, not only the front.
5. Quest readability: opaque shape, bevel, step, and broad color zones carry the read; tiny lines and glow alone do not.
6. Metadata: per-asset sidecar must carry `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`.

## Line-wide Hold Reasons

| Line | Source | Must read from triview | Current hold reason |
|---|---|---|---|
| `line_rescue_knight` | `c02 Rescue Knight Sleek` | white/blue rescue suit, blue visor, cyan chest core, compact back, grounded boots | reads too much like generic white procedural armor; blue base suit and rescue identity are weak |
| `line_royal_insect` | `c01 Royal Insect Guardian` | green/white/gold, compound-eye visor, short crest/antenna, emerald V chest, close-to-body shell | c02/c15 differentiation is weak; insect guardian symbols are not strong enough in full-body reads |
| `line_final_oath` | `c15 Final Oath Form` | pearl/gold/cyan final form, crown visor, large cyan core, dense gold trim, glow flow to legs/boots | too close to c01 and not yet dense or complete enough for final-form identity |

## Per-part Audit Table

Legend: `file pass` means manifest/catalog/files are present. `Hold` means do not promote to Web/Quest runtime. `Missing` means no 3-line variant was delivered for that module.

### helmet

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `helmet:rescue_sleek` | file pass | blue visor, forehead stripe, face direction readable in front/3q/side | Hold | Strengthen blue visor and rescue-face silhouette; add `fidelity_notes` with front/side/back deltas. |
| `line_royal_insect` | `helmet:compound_guardian` | file pass | compound-eye or compound-eye-like visor, short crest/antenna, green/gold identity | Hold | Make compound visor and crest read in grayscale; avoid tiny texture-only eye detail. |
| `line_final_oath` | `helmet:oath_crown_visor` | file pass | crown visor/crest, pearl/gold/cyan final-form faceplate | Hold | Separate from c01 with crown geometry and denser gold/cyan trim; add side-view proof. |

### chest

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `chest:rescue_wrap` | file pass | cyan triangular/core and blue/white base suit split, not a white block | Hold | Increase core contrast and rib wrap; show source overlay front. |
| `line_royal_insect` | `chest:emerald_v_core` | file pass | emerald V core, green/white/gold heroic insect read | Hold | Make V chest the main read from distance; connect to waist and back panels. |
| `line_final_oath` | `chest:oath_core_shell` | file pass | large cyan core, gold collar/rib density, final form completeness | Hold | More final-form density without growing into arm/abdomen interference. |

### back

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `back:compact_spine` | file pass | compact blue spine/back unit, no backpack-box read | Hold | Add blue spine identity visible in full back and side. |
| `line_royal_insect` | `back:wing_shell_close` | file pass | close-to-body dorsal shell, insect shell nuance, not large wings | Hold | Increase shell/wing silhouette while staying body-hugging. |
| `line_final_oath` | `back:oath_spine_rear_core` | file pass | gold/cyan rear core and spine, shoulder-to-back flow | Hold | Back must visibly exceed c01 in completion/density. |

### waist

Additional hold: `waist` must not be promoted from metadata-only `body_wrap_loop`. Runtime smoke may remain usable, but modeler fidelity stays held until GLB loop export plus front/side/back/3Q recheck proves the belt is an actual wearable cylinder, not only a named contract.

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `waist:rescue_driver` | file pass | pelvis-wrapping rescue driver, does not stab abdomen | Hold | Connect blue/white chest line into belt and thigh start. |
| `line_royal_insect` | `waist:guardian_buckle` | file pass | guardian buckle connected to emerald V motif | Hold | Make buckle read as line-specific, not generic belt trim. |
| `line_final_oath` | `waist:oath_driver_ring` | file pass | belt ring/side clip, gold/cyan flow toward thighs | Hold | Add visible gold/cyan continuity to legs; keep hip motion clear. |

### left_shoulder

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `left_shoulder:sleek_rescue_cap` | file pass | small sharp rescue cap, upper-arm motion preserved | Hold | Read as compact rescue armor in front/side/back. |
| `line_royal_insect` | `left_shoulder:wing_cap` | file pass | wing/edge hint, body-hugging, not monster wing | Hold | Increase silhouette distinction from c02 without widening too much. |
| `line_final_oath` | `left_shoulder:oath_guard_fin` | file pass | small oath fin, gold/cyan trim, shoulder-to-back flow | Hold | More final-form trim density while preserving arm lift. |

### right_shoulder

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `right_shoulder:sleek_rescue_cap` | file pass | mirror of left; dimensions and angle match | Hold | Mirror review with left in side/back views. |
| `line_royal_insect` | `right_shoulder:wing_cap` | file pass | mirror of left; wing cap reads as pair | Hold | Confirm both shoulders are symmetric enough but not pasted-looking. |
| `line_final_oath` | `right_shoulder:oath_guard_fin` | file pass | mirror of left; final trim readable | Hold | Check right-side trim does not vanish in Quest view. |

### left_upperarm

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | blue/white upper-arm seam continues from shoulder to forearm | Missing P1 | Order `left_upperarm:rescue_*` variant; protect elbow range. |
| `line_royal_insect` | - | Missing | green/white/gold bicep band or outer plate tied to shoulder shell | Missing P1 | Order `left_upperarm:guardian_*` variant; keep insect read heroic. |
| `line_final_oath` | - | Missing | gold/cyan line from shoulder into forearm, higher density than c01 | Missing P1 | Order `left_upperarm:oath_*` variant; add metadata and review images. |

### right_upperarm

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | mirror of left rescue upper-arm seam | Missing P1 | Order paired right-side variant with mirrored dimensions. |
| `line_royal_insect` | - | Missing | mirror of left guardian bicep/outer plate | Missing P1 | Order paired right-side variant; avoid left/right quality drift. |
| `line_final_oath` | - | Missing | mirror of left oath trim flow | Missing P1 | Order paired right-side variant with line-specific trim. |

### left_forearm

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | compact rescue gauntlet/wrist cuff, controller sightline preserved | Missing P1 | Order `left_forearm:rescue_*`; do not bulk up wrist. |
| `line_royal_insect` | - | Missing | insect-like forearm ridge/cuff, green/gold accent | Missing P1 | Order `left_forearm:guardian_*`; use broad shape, not tiny texture only. |
| `line_final_oath` | - | Missing | gold/cyan oath guard, arm flow from shoulder/chest | Missing P1 | Order `left_forearm:oath_*`; confirm Quest controller clearance. |

### right_forearm

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | mirror of left rescue gauntlet | Missing P1 | Order paired right-side forearm variant. |
| `line_royal_insect` | - | Missing | mirror of left guardian ridge/cuff | Missing P1 | Order paired right-side forearm variant. |
| `line_final_oath` | - | Missing | mirror of left oath guard | Missing P1 | Order paired right-side forearm variant. |

### left_hand

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | rescue glove, knuckle/wrist accent, not oversized for Quest hands | Missing P1 | Order `left_hand:rescue_*`; prioritize controller-safe silhouette. |
| `line_royal_insect` | - | Missing | green/gold knuckle or palm accent, insect nuance without claws | Missing P1 | Order `left_hand:guardian_*`; avoid monster/claw read. |
| `line_final_oath` | - | Missing | final-form glow/trim on small surface, palm/knuckle readable | Missing P1 | Order `left_hand:oath_*`; keep tiny detail as broad panels. |

### right_hand

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | mirror of left rescue glove | Missing P1 | Order paired right-hand variant. |
| `line_royal_insect` | - | Missing | mirror of left guardian hand accent | Missing P1 | Order paired right-hand variant. |
| `line_final_oath` | - | Missing | mirror of left oath hand trim | Missing P1 | Order paired right-hand variant. |

### left_thigh

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | blue thigh/base-suit contrast, waist-to-shin continuity | Missing P1 | Order `left_thigh:rescue_*`; check hip and knee clearance. |
| `line_royal_insect` | - | Missing | green/white vertical armor line, outer guard not too bulky | Missing P1 | Order `left_thigh:guardian_*`; connect to guardian shin/boot. |
| `line_final_oath` | - | Missing | gold/cyan flow from waist to shin, final-form density | Missing P1 | Order `left_thigh:oath_*`; visible in side view. |

### right_thigh

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | - | Missing | mirror of left rescue thigh contrast | Missing P1 | Order paired right-thigh variant. |
| `line_royal_insect` | - | Missing | mirror of left guardian thigh guard | Missing P1 | Order paired right-thigh variant. |
| `line_final_oath` | - | Missing | mirror of left oath thigh flow | Missing P1 | Order paired right-thigh variant. |

### left_shin

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `left_shin:rescue_stream` | file pass | blue/white shin stream, knee and ankle escape | Hold | Strengthen color blocking and boot connection; include boot side closeup. |
| `line_royal_insect` | `left_shin:guardian_ridge` | file pass | thin guardian ridge, green/white/gold continuity | Hold | Make ridge readable at Quest distance, not only as line texture. |
| `line_final_oath` | `left_shin:oath_glow_guard` | file pass | gold/cyan shin shell and glow flow | Hold | Tie waist/thigh/shin/boot into one flow after P1 thigh arrives. |

### right_shin

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `right_shin:rescue_stream` | file pass | mirror of left rescue stream | Hold | Compare left/right height, glow placement, and side angle. |
| `line_royal_insect` | `right_shin:guardian_ridge` | file pass | mirror of left guardian ridge | Hold | Compare left/right silhouette and material-zone read. |
| `line_final_oath` | `right_shin:oath_glow_guard` | file pass | mirror of left oath guard | Hold | Compare left/right trim continuity into boots. |

### left_boot

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `left_boot:rescue_toe_guard` | file pass | grounded toe cap, heel guard, ankle cuff, blue/white split | Hold | Add `boot_closeup_side.png`; verify sole does not float. |
| `line_royal_insect` | `left_boot:guardian_split_toe` | file pass | split toe symbol without losing grounded boot read | Hold | Make guardian toe/ankle motif distinct from c02 and c15. |
| `line_final_oath` | `left_boot:oath_hero_sole` | file pass | oath sole/toe/heel, gold/cyan completion at foot | Hold | Increase final-form identity while keeping practical boot mass. |

### right_boot

| Line | Delivered key | File gate | Triview check | Auditor status | Reorder memo |
|---|---|---|---|---|---|
| `line_rescue_knight` | `right_boot:rescue_toe_guard` | file pass | mirror of left rescue boot | Hold | Compare grounded sole and toe cap with left. |
| `line_royal_insect` | `right_boot:guardian_split_toe` | file pass | mirror of left guardian boot | Hold | Compare left/right toe split and ankle line. |
| `line_final_oath` | `right_boot:oath_hero_sole` | file pass | mirror of left oath boot | Hold | Compare left/right gold/cyan trim and sole shape. |

## Defect List

1. The 30 delivered P0 variants are not runtime-ready because the source triview identity is not yet strong enough. The hold is visual and lore-facing, not only technical.
2. `source_overlay_front.png` is missing for all 3 lines. This is required for the next fidelity review.
3. `boot_closeup_side.png` is missing for all 3 lines. Boots are a stated review focus because grounding and sole/toe/ankle reads are weak points.
4. Per-asset sidecar top level lacks `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`. Catalog fallback helps tooling, but asset-level provenance is still incomplete.
5. P1 line variants are absent for `left/right_upperarm`, `left/right_forearm`, `left/right_hand`, and `left/right_thigh`: 8 module ids x 3 lines = 24 missing variant filesets.
6. Manifest validation is cwd-sensitive. Repro instructions should run inside `.claude/worktrees/jovial-cohen-4bf60f` or the manifest paths should be normalized before cross-worktree validation.
7. Waist `body_wrap_loop` is a separate modeler fidelity hold: metadata alone is not a tri-view pass; require GLB loop export and front/side/back/3Q confirmation even if exhibition runtime smoke is otherwise acceptable.

## Reorder Memo

Send back as one combined request:

1. Keep the existing 30 P0 variant keys, but revise them for triview fidelity. Do not promote or remap into Web/Quest runtime yet.
2. Add required review imagery per line: `source_overlay_front.png`, `boot_closeup_side.png`, and keep full front/side/back/3q plus helmet/torso closeups.
3. Add sidecar top-level provenance and review notes: `source_concept_ids`, `line_id`, `design_intent`, `fidelity_notes`.
4. Add P1 variants for upperarm, forearm, hand, and thigh, left/right, across all 3 lines: 24 filesets total.
5. Prioritize visual differentiation in this order: helmet, chest, back, boots, shins, waist, shoulders, then P1 arms/hands/thighs. This keeps the Web first read strong while preparing Quest hand/controller and leg-motion checks.
