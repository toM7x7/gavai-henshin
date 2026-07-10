# Modeler Fit Micro-Adjustments - 2026-05-04

Purpose: provide a modeler-friendly intake packet for exhibition-facing size and placement fixes. This is not a GLB edit log; GLB/Blend files remain untouched here. The source of numeric truth is the current Web GLB smoke report, exported by:

```powershell
python tools/export_modeler_fit_adjustments.py --format markdown
python tools/export_modeler_fit_adjustments.py --format json
```

Current gate:

- `preview_glb_parts=18`
- `preview_fallback_parts=0`
- `bbox_warning_count=6`
- exporter contract: `modeler-fit-adjustments.v0.2`
- mirror pairs pass now, so left/right edits must stay paired unless explicitly approved

## Latest Release-Validator Warning Triage

最新ローカル validator の model warning は、展示 runtime の進行可否と modeler fidelity の停止条件を分けて扱う。

| 区分 | 対象 warning | 次回モデラー指示 |
|---|---|---|
| 展示 runtime で進める | `preview_glb_parts=18`, `preview_fallback_parts=0`; helmet/back/boot/hand/shin の UV/material-zone 系 warning; boot の offset-compensated clearance warning | 公開展示の smoke は継続可。ただし waiver には front/side/back/3Q と Quest 姿勢写真を添え、GLB 実寸 pass とは書かない。 |
| P1 / fidelity で止める | `waist body_wrap_loop_export_status=export_status_not_declared`; belt-loop clearance unresolved; 30variant waist | metadata-only の `body_wrap_loop` は装着筒 pass ではない。腰は GLB loop export、belt aperture sidecar、front/side/back/3Q 再確認まで fidelity hold。 |
| P1 / fidelity で止める | chest/back の `no_body_intersection_at_reference_pose` negative clearance | 展示 runtime は進められるが、胸/背中が人体外皮に沈む疑いは残る。`chest.z` 微調整と背中の body-hugging 証跡をセットで再確認。 |
| 微量調整寸法 | `bbox_warning_count=6`: `chest.z`, `waist.x`, `left/right_upperarm.x`, `left/right_shin.x` | 下表の demo target を初回修正量にする。左右ペアは同量で編集し、mirror delta <=3% を維持。 |

## Intake Data Shape

Use the JSON output as the handoff source when assigning work. Each `adjustments[]` row is intentionally small enough to paste into a modeler ticket.

```json
{
  "contract_version": "modeler-fit-adjustments.v0.2",
  "route_lore": "Webでスーツ成立、Questで変身試験、Replayで体験を残す",
  "adjustments": [
    {
      "module": "chest",
      "priority": "P0",
      "affected_fidelity_hold_variants": ["chest:rescue_wrap"],
      "size_tasks": [
        {
          "axis": "z",
          "actual_mm": 142.4,
          "pass_min_mm": 146.9,
          "recommended_demo_target_mm": 148.4,
          "target_mm": 163.2
        }
      ],
      "placement_nudges": [{"axis": "z", "max_mm": 2.0, "direction": "forward"}],
      "evidence_required": ["full_front", "side", "3q"],
      "route_gate": {"web": "...", "quest": "...", "replay": "..."},
      "acceptance": {"bbox_warning_count_target": 0, "sidecar_glb_bbox_match_max_m": 0.002}
    }
  ]
}
```

## Per-Part Numeric Tasks

| Priority | Part | Axis | Current -> target | Minimum pass | Demo target | Full target delta | Placement micro-adjust | Affected fidelity-hold variants |
|---|---|---:|---:|---:|---:|---:|---|---|
| P0 micro / runtime proceed | 胸部装甲 (`chest`) | 奥行き `z` | `142.4mm -> 163.2mm` | `146.9mm` | `148.4mm` (`+6.1mm`) | `+20.8mm` | Add depth front/back; if the chest reads sunken, runtime placement `z +2mm` max. Recheck body-intersection clearance with back unit. | `chest:rescue_wrap`, `chest:emerald_v_core`, `chest:oath_core_shell` |
| P1 fidelity hold / micro | ベルト (`waist`) | 横幅 `x` | `440.4mm -> 489.6mm` | `440.6mm` | `442.1mm` (`+1.8mm`) | `+49.2mm` | Widen symmetrically; keep center. Metadata-only `body_wrap_loop` is not enough: export a real GLB loop and prove belt aperture/clearance. | `waist:rescue_driver`, `waist:guardian_buckle`, `waist:oath_driver_ring` |
| P0 micro / future P1 limb rule | 左上腕 (`left_upperarm`) | 横幅 `x` | `96.3mm -> 108.8mm` | `97.9mm` | `99.4mm` (`+3.1mm`) | `+12.5mm` | Pair-widen with right upperarm; if shoulder clips, left `x +2mm` max outward. | No delivered 30variant scope; apply as base/P1 fit rule for future line variants. |
| P0 micro / future P1 limb rule | 右上腕 (`right_upperarm`) | 横幅 `x` | `96.3mm -> 108.8mm` | `97.9mm` | `99.4mm` (`+3.1mm`) | `+12.5mm` | Pair-widen with left upperarm; if shoulder clips, right `x -2mm` max outward. | No delivered 30variant scope; apply as base/P1 fit rule for future line variants. |
| P0 micro / runtime proceed | 左すね (`left_shin`) | 横幅 `x` | `101.7mm -> 115.6mm` | `104.0mm` | `105.5mm` (`+3.8mm`) | `+13.9mm` | Pair-widen with right shin; if shin/boot step appears, left `x +2mm` max outward. Recheck slight clearance warning and boot continuity. | `left_shin:rescue_stream`, `left_shin:guardian_ridge`, `left_shin:oath_glow_guard` |
| P0 micro / runtime proceed | 右すね (`right_shin`) | 横幅 `x` | `101.7mm -> 115.6mm` | `104.0mm` | `105.5mm` (`+3.8mm`) | `+13.9mm` | Pair-widen with left shin; if shin/boot step appears, right `x -2mm` max outward. Recheck slight clearance warning and boot continuity. | `right_shin:rescue_stream`, `right_shin:guardian_ridge`, `right_shin:oath_glow_guard` |

## Fidelity-Hold Size/Position Rows

These rows come from the 30 held tri-view variants. They are less numeric than bbox warnings, but they are still position/size tasks because they affect exhibition first-read, grounding, and body-relative placement.

| Priority | Scope | Variant keys | Size/position action | Proof required |
|---|---|---|---|---|
| P0 | Helmet identity | `helmet:rescue_sleek`, `helmet:compound_guardian`, `helmet:oath_crown_visor` | Enlarge or clarify visor/crest/compound-eye geometry enough to read in grayscale; do not solve only with tiny texture lines. | Helmet closeup, front/side/back/3Q, grayscale read. |
| P0 | Chest core | `chest:rescue_wrap`, `chest:emerald_v_core`, `chest:oath_core_shell` | Apply numeric `chest.z` depth task and broaden core/V silhouette without colliding with waist or arms. | Torso closeup, side/3Q depth proof, back interference note. |
| P0 | Back read | `back:compact_spine`, `back:wing_shell_close`, `back:oath_spine_rear_core` | Add rear spine/shell/core volume that stays body-hugging; avoid backpack-block silhouette. | Full back and side proof connected to chest/waist. |
| P0 | Boots and grounding | `left/right_boot:rescue_toe_guard`, `left/right_boot:guardian_split_toe`, `left/right_boot:oath_hero_sole` | Tune toe cap, heel, sole contact, ankle cuff, and left/right sole height; no floating foot read. | `boot_closeup_side.png`, full front/side, Quest stance note if promoted. |
| P0 | Shin-to-boot continuity | `left/right_shin:rescue_stream`, `left/right_shin:guardian_ridge`, `left/right_shin:oath_glow_guard` | Apply numeric shin `x` widening as paired edits and preserve boot connection. | Paired front, side, boot-side closeup, mirror delta <=3%. |
| P1 | Waist continuity | `waist:rescue_driver`, `waist:guardian_buckle`, `waist:oath_driver_ring` | Apply minimal `waist.x` pass correction, then export a real GLB `body_wrap_loop`; metadata-only loop does not pass as a closed wearable tube. | Front/side/back/3Q belt proof, Quest stance check, sidecar belt aperture, no waiver-only pass. |
| P1 | Shoulders | `left/right_shoulder:*` across 3 lines | Do not widen blindly; make silhouette line-specific while protecting arm lift. | Front/side/back paired shoulder proof. |
| P1 | Missing upperarm/forearm/hand/thigh variants | 24 future P1 filesets | Use the upperarm numeric fit rule as a baseline for future line variants; do not claim line-complete limbs now. | Pair geometry, controller/elbow/hip/knee clearance proof. |

## Route Gate Notes

The experience lore is: Webでスーツ成立、Questで変身試験、Replayで体験を残す. Model quality gates hit that route as follows:

- Web gate: silhouette, broad color/shape blocks, and full-body first-read decide whether the suit "成立" before the visitor enters Quest.
- Quest gate: body-relative placement, clearance, grounding, and pair symmetry decide whether the transformation trial feels attached to the player.
- Replay gate: side/back/3Q evidence and sidecar provenance decide whether the recorded experience proves the same suit identity later.

## Acceptance

- Re-run `python tools/smoke_web_glb_load.py --report-json` from the packaged root.
- Preferred public-demo pass: `bbox_warning_count=0`.
- If a warning remains, attach a waiver under `qa/waivers/` with front/side/back/3Q proof from the packaged external-PC build.
- `preview_fallback_parts == 0` must remain true.
- GLB/sidecar bbox match must remain <= `0.002m`.
- Mirror-pair max delta must remain <=3% for paired edits.
- Web and Quest must both call the same 4-digit code and show no major part size/position mismatch.
- Do not promote the 30 `fidelity_hold` variants into public runtime only because they are file-valid.
- Runtime load pass and modeler fidelity pass are separate: waist loop export and 30variant tri-view proof remain P1 holds even if exhibition runtime continues.
