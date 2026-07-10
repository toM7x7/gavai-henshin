# P1 Limb Variant Order Acceptance - 2026-05-04

Scope: make the missing P1 limb variants orderable, deliverable, and reviewable. This file is an acceptance basis for `upperarm`, `forearm`, `hand`, and `thigh` variants across left/right sides and the 3 required line systems.

Non-scope: this file does not edit GLB, Blender, viewer runtime, validator code, tests, or the existing order manifest. Runtime activation remains a separate change after delivery and fidelity pass.

## Source Of Truth

- Order manifest: `docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json`
- Latest audit: `docs/modeler-fit-and-triview-next-audit-2026-05-04.md`
- Fit baseline: `docs/modeler-new-route-acceptance-spec.md` and `docs/modeler-fit-micro-adjustments-2026-05-04.md`
- Fidelity ladder: `docs/modeler-fidelity-hold-tracking-2026-05-04.md`

Current state from the latest audit:

- 24 P1 line variants are still missing: 8 modules x 3 line systems.
- The 8 canonical P1 limb sidecars exist but are `metadata_hold`.
- `left_hand` and `right_hand` exceed canonical target depth: `z=140.0mm` actual vs `136.0mm` target.
- The order is not public runtime activation. Delivered assets start as reviewer-only until tri-view, fit, Web, Quest, and Replay gates pass.

## 次回発注レビュー補助: 不足24件

`blocked_asset_count=24` は、下記12カードを左右別の24アセットとしてまだ受け入れていない状態を指す。モデル納品時は左右を1組で見るが、受け入れ判定は `variant_key` 単位で行う。

| Line | Family | Left missing | Right missing | モデル納品時の主チェック |
|---|---|---|---|---|
| `line_rescue_knight` | upperarm | `left_upperarm:rescue_upperarm_stream` | `right_upperarm:rescue_upperarm_stream` | 肩から肘までの白/シアン流線、肩上げと肘曲げの逃げ |
| `line_rescue_knight` | forearm | `left_forearm:rescue_vambrace` | `right_forearm:rescue_vambrace` | 前腕に巻き付くvambrace形状、手首回転とコントローラー視認 |
| `line_rescue_knight` | hand | `left_hand:rescue_cuff_lock` | `right_hand:rescue_cuff_lock` | 掌/拳/カフの読み、手深さ `z<=0.136m` またはreviewer-only waiver |
| `line_rescue_knight` | thigh | `left_thigh:rescue_speed_plate` | `right_thigh:rescue_speed_plate` | 腰から脛へ流れる速度線、股関節/膝の逃げ |
| `line_royal_insect` | upperarm | `left_upperarm:guardian_upperarm_ridge` | `right_upperarm:guardian_upperarm_ridge` | 甲殻ridgeの横/3Q読み、肩/肘の可動域 |
| `line_royal_insect` | forearm | `left_forearm:guardian_forearm_shell` | `right_forearm:guardian_forearm_shell` | shell plate分割、手首回転と浮き防止 |
| `line_royal_insect` | hand | `left_hand:guardian_knuckle` | `right_hand:guardian_knuckle` | knuckle/palm emitter、握り姿勢とコントローラー干渉 |
| `line_royal_insect` | thigh | `left_thigh:guardian_outer_guard` | `right_thigh:guardian_outer_guard` | 外側guardの甲殻感、腰/膝をまたぐ固定バー化の回避 |
| `line_final_oath` | upperarm | `left_upperarm:oath_upperarm_guard` | `right_upperarm:oath_upperarm_guard` | 白/金/シアン密度、Royal Insectとの差分、肩/肘の逃げ |
| `line_final_oath` | forearm | `left_forearm:oath_gauntlet` | `right_forearm:oath_gauntlet` | ceremonial gauntlet、手首/コントローラー安全域 |
| `line_final_oath` | hand | `left_hand:oath_palm_core` | `right_hand:oath_palm_core` | palm coreの視認、手深さとジェスチャー読み |
| `line_final_oath` | thigh | `left_thigh:oath_gold_flow` | `right_thigh:oath_gold_flow` | 金/シアンの腰-脛フロー、歩行姿勢での干渉 |

### モデル納品時に見る項目

- `GLB`, sidecar, source `.blend`, preview `.mesh.json` がmanifestの期待pathと一致する。
- sidecarに `line_id`, `source_concept_ids`, `design_intent`, `fidelity_notes`, `bbox_m`, `target_envelope_m`, `vrm_attachment` がある。
- `variant_key` は `<module>:<asset_key>` と完全一致し、右側の `mirror_of` は対応する左側 `variant_key` を指す。
- front/side/back/3q/closeupのreview packetが左右ペアで揃い、横/3Qだけでも3ラインを識別できる。
- family別の可動証跡がある: upperarmは肩/肘、forearmは肘/手首、handは握り/掌/コントローラー、thighは股関節/膝。
- bboxは原則 `+/-10%`、failは `+/-15%` 超過、左右差は各軸 `<=3%`、GLB/sidecar/preview差は `<=0.002m`。

### Reject条件

- manifestにない名前、path、`variant_key`、`line_id`、`source_concept_ids` で納品されている。
- 右側variantの `mirror_of` が欠落、または別ライン/別familyの左側を指している。
- `base`、topping、仮proxy、色替えだけのassetをP1 line variantとして提出している。
- sidecar必須field、tri-view packet、clearance proof、source `.blend`、preview `.mesh.json` のいずれかが欠落している。
- reference poseで身体交差、浮き、関節またぎの固定バー、コントローラー隠れ、手深さ超過の未waiverがある。
- `runtime_activation_allowed=true` 相当の設定や公開runtimeへの組み込みを、P1受け入れ完了前に含めている。

### Web/Quest Runtime Activation条件

- order manifest検証を `--require-delivered` で通し、`ordered variants=24`, `catalog gaps=0`, `delivery gaps=0` になる。
- P1 auditで `missing`, `metadata_hold`, `invalid` が0になり、line別不足も0になる。
- Web smokeで選択 `variant_key` がfallback count `0` で読み込まれ、Quest packageでも同じ `variant_key` をfallbackなしでrecallできる。
- Replay evidenceが `line_id`, `source_concept_ids`, `variant_key` をsidecar由来で追跡できる。
- `blocked_asset_count>0` または `package_gate_status=warn_now_block_p1` の間は展示package全体を進められてもP1 public activationは不可。`runtime_activation_allowed=false` は、別PR/別changeで明示的に切り替えるまで維持する。

### Validator JSON: `missing_matrix`

`tools/validate_modeler_variant_order_manifest.py --report-json` は `missing_matrix` を返す。これは24件を `line_id` / `limb_family` / `side` の3軸で機械的に読むための表で、発注レビューと次回納品確認の共通入力にする。

主なfield:

- `entries[]`: 24行。各行に `line_id`, `limb_family`, `side`, `module`, `variant_key`, `order_status`, `delivery_status`, `catalog_registration_status`, `runtime_activation_status`, `current_stop_stage`, `blocked_stages` を持つ。
- `by_line`: line別の集計。各lineに `upperarm` / `forearm` / `hand` / `thigh` と `left` / `right` のcompact行を持つ。
- `stage_counts`: `order`, `delivery`, `catalog_registration`, `runtime_activation`, `current_stop` の件数集計。
- `p1_blocked_asset_count`: P1受け入れ未完の件数。現状は24。
- `runtime_activation_blocked_count`: public runtime activationが未許可の件数。P1受け入れが完了しても、別のruntime activation changeまではblockedのまま。

`current_stop_stage` の読み方:

- `order`: manifestの発注行そのものが壊れている。名前、line、family、side、mirror、path契約を直す。
- `delivery`: manifestは正しいが、GLB/sidecar/source/previewの納品が揃っていない。
- `catalog_registration`: 納品物は揃ったが、`variant_catalog.json` 登録がまだ、または登録keyが一致しない。
- `runtime_activation`: P1受け入れは通せるが、Web/Quest runtimeで公開選択する段階ではない。`runtime_activation_allowed=false` を維持する。

### Modeler Order Packet Export

`missing_matrix` をモデラー発注/納品チェックに渡すときは、次のCLIでpacket化する。

```powershell
python tools\export_p1_modeler_order_packet.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --out docs\modeler-deliveries\p1-limb-order-packet.json --format json
```

- JSON packetは `order_items`, `acceptance_checks`, `blocked_by_stage`, `runtime_activation_policy`, `modeler_message_outline` を持つ。
- `--format markdown` はレビュー表、`--format csv` はスプレッドシート取り込み用。`--report-json` は出力ファイル形式に関係なくJSONをstdoutへ出す。
- 既に `validate_modeler_variant_order_manifest.py --report-json` の結果を保存している場合は、そのJSON pathを `--manifest` に渡して同じpacketを作れる。

## Order Units

Use 12 paired order cards for production management. Each card delivers 2 assets: left and right. Final strict delivery still counts 24 assets.

| Order card | Line | Family | Left variant | Right variant | Primary acceptance risk |
|---|---|---|---|---|---|
| `P1-LIMB-RK-UPPERARM` | `line_rescue_knight` | upperarm | `left_upperarm:rescue_upperarm_stream` | `right_upperarm:rescue_upperarm_stream` | shoulder-to-elbow cyan/white flow without arm-lift block |
| `P1-LIMB-RK-FOREARM` | `line_rescue_knight` | forearm | `left_forearm:rescue_vambrace` | `right_forearm:rescue_vambrace` | worn vambrace/cuff, not floating wrist prop |
| `P1-LIMB-RK-HAND` | `line_rescue_knight` | hand | `left_hand:rescue_cuff_lock` | `right_hand:rescue_cuff_lock` | palm/knuckle readability and controller clearance |
| `P1-LIMB-RK-THIGH` | `line_rescue_knight` | thigh | `left_thigh:rescue_speed_plate` | `right_thigh:rescue_speed_plate` | waist-to-shin rescue speed line, no hip/knee block |
| `P1-LIMB-RI-UPPERARM` | `line_royal_insect` | upperarm | `left_upperarm:guardian_upperarm_ridge` | `right_upperarm:guardian_upperarm_ridge` | carapace ridge visible in side/3Q |
| `P1-LIMB-RI-FOREARM` | `line_royal_insect` | forearm | `left_forearm:guardian_forearm_shell` | `right_forearm:guardian_forearm_shell` | shell plate breaks plus wrist mobility |
| `P1-LIMB-RI-HAND` | `line_royal_insect` | hand | `left_hand:guardian_knuckle` | `right_hand:guardian_knuckle` | guardian knuckle and palm emitter remain readable |
| `P1-LIMB-RI-THIGH` | `line_royal_insect` | thigh | `left_thigh:guardian_outer_guard` | `right_thigh:guardian_outer_guard` | outer guard reads as heroic insect armor, not a flat stripe |
| `P1-LIMB-FO-UPPERARM` | `line_final_oath` | upperarm | `left_upperarm:oath_upperarm_guard` | `right_upperarm:oath_upperarm_guard` | gold/cyan density separated from royal insect |
| `P1-LIMB-FO-FOREARM` | `line_final_oath` | forearm | `left_forearm:oath_gauntlet` | `right_forearm:oath_gauntlet` | ceremonial gauntlet with controller-safe wrist |
| `P1-LIMB-FO-HAND` | `line_final_oath` | hand | `left_hand:oath_palm_core` | `right_hand:oath_palm_core` | palm core visible without exceeding hand depth |
| `P1-LIMB-FO-THIGH` | `line_final_oath` | thigh | `left_thigh:oath_gold_flow` | `right_thigh:oath_gold_flow` | final-form gold/cyan flow into shin without gait interference |

Line reads:

- `line_rescue_knight`: white/cyan rescue suit, slim and public-safety clear. Shape language should be clean panels, stream seams, and functional cuffs.
- `line_royal_insect`: green/white/gold guardian suit, compound/carapace language. Shape language should be shell plates, ridges, and guarded edges.
- `line_final_oath`: white/gold/cyan final form, denser and ceremonial. Shape language should be stronger trim, cyan cores, and continuous oath-flow panels.

## Naming And Fileset Contract

Each asset must preserve the manifest `module`, `asset_key`, and `variant_key`. Do not rename to make local organization easier.

Path pattern:

```text
viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.glb
viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.modeler.json
viewer/assets/armor-parts/<module>/variants/<asset_key>/source/<module>__<asset_key>.blend
viewer/assets/armor-parts/<module>/variants/<asset_key>/preview/<module>__<asset_key>.mesh.json
```

Naming rules:

- `asset_key` is a path-safe slug and never contains `:`, `/`, or `\`.
- `variant_key` is exactly `<module>:<asset_key>`.
- Right-side variants use the same `asset_key` as the left side.
- Right-side `mirror_of` is exactly the matching left-side `variant_key`.
- A `base` asset, topping, or renamed proxy does not satisfy a P1 line variant order.

## Per-Family Model Requirements

| Family | Modules | Target x/y/z m | Primary bones | Required runtime clearance | Family-specific acceptance |
|---|---|---|---|---|---|
| upperarm | `left_upperarm`, `right_upperarm` | `0.1088 / 0.2924 / 0.1088` | `leftUpperArm`, `rightUpperArm` | shoulder lift and elbow bend | Pair-widen from current `96.3mm` x toward `99.4mm` demo target; minimum pass is `97.9mm`. Line identity must bridge shoulder/forearm in side and 3Q. |
| forearm | `left_forearm`, `right_forearm` | `0.1020 / 0.2788 / 0.1020` | `leftLowerArm`, `rightLowerArm` | elbow bend, wrist rotation, controller sightline | Must read as a worn gauntlet/cuff wrapped around the arm, not loose wrist props or texture-only bands. |
| hand | `left_hand`, `right_hand` | `0.1156 / 0.0816 / 0.1360` | `leftHand`, `rightHand` | controller grip, palm view, gesture readability | Must resolve canonical hand `z` overflow or carry the waiver below. Palm/knuckle details must not obscure controller-safe hand read. |
| thigh | `left_thigh`, `right_thigh` | `0.1360 / 0.3956 / 0.1292` | `leftUpperLeg`, `rightUpperLeg` | hip flex, knee bend, walking stance | Must connect waist/belt motif into shin/knee while preserving side and 3Q line separation. |

Numeric fit rules:

- Target pass is each axis within `+/-10%` of the family target.
- Review-only tolerance is `+/-10%` to `+/-15%` with explicit note.
- Fail is any axis beyond `+/-15%`, unless a documented waiver keeps it out of public runtime.
- Left/right pair delta must be `<=3%` per axis.
- GLB, sidecar bbox, and preview mesh bbox must match within `0.002m`.
- `vrm_attachment` offsets must describe attachment, not hide poor geometry placement. Magnitude should stay within `0.04m` unless explicitly reviewed.

## Metadata Sidecar Requirements

Every delivered P1 variant sidecar must include enough information for Web, Quest, and Replay to identify the same part. Catalog fallback does not count.

Required top-level fields:

```json
{
  "contract_version": "modeler-part-variant-sidecar.v1",
  "asset_kind": "variant",
  "module": "left_upperarm",
  "variant_asset_key": "rescue_upperarm_stream",
  "variant_key": "left_upperarm:rescue_upperarm_stream",
  "line_id": "line_rescue_knight",
  "source_concept_ids": ["c02"],
  "design_intent": "Slim rescue upperarm shell that carries cyan suit flow from shoulder to elbow without blocking arm bend.",
  "fidelity_notes": "front/side/back/3Q differences, clearance decisions, and any intentional source deviation"
}
```

Additional required sidecar content:

- `bbox_m`, `target_envelope_m`, `triangle_count`, `material_zones`, and `vrm_attachment`.
- `vrm_attachment.primary_bone` must match the module family table above.
- `reference_pose_checks` should cover the relevant motion: `arms_raised`, `elbow_bend`, `wrist_controller`, `hip_flex`, `knee_bend`.
- If the right side differs from simple mirroring, `intentional_deviation_reason` must explain why.
- If external textures exist, `texture_files` lists them. Missing texture references fail intake.

Line metadata must match the manifest:

| Line | Required `source_concept_ids` | Required `line_id` |
|---|---|---|
| Rescue Knight | `["c02"]` | `line_rescue_knight` |
| Royal Insect | `["c01"]` | `line_royal_insect` |
| Final Oath | `["c15"]` | `line_final_oath` |

## Tri-View Review Packet

Each order card needs a paired review packet. A packet contains the left and right variants together so mirror quality is visible.

Required views:

- `front`: proves full-body first-read and line identity.
- `side`: proves depth, attachment, controller/hip/knee clearance, and no floating shell.
- `back`: proves the line continues around the limb and does not become blank from Replay angles.
- `3q`: proves silhouette and line identity under the most visitor-like view.
- `closeup`: proves local modeling quality, panel language, and palm/knuckle/cuff/guard detail.

Acceptance checks:

- The reviewer can identify the line from side and 3Q without relying only on front color.
- The shape reads as worn armor over the base suit, not an inspection bbox, flat texture stripe, or detached prop.
- Paired left/right geometry is symmetric enough for runtime use, with any intentional asymmetry documented.
- Rescue, royal insect, and final oath remain separable within the same family slot.
- Hand packets include side-depth and controller-grip proof.
- Upperarm/forearm packets include elbow and arm-lift proof.
- Thigh packets include hip/knee and waist-to-shin continuity proof.

Suggested packet paths in a delivery bundle:

```text
review/p1-limb/<order_card>/front.png
review/p1-limb/<order_card>/side.png
review/p1-limb/<order_card>/back.png
review/p1-limb/<order_card>/3q.png
review/p1-limb/<order_card>/closeup.png
review/p1-limb/<order_card>/notes.md
```

## Runtime Placement Gate

Runtime placement is evaluated after fileset delivery and before public activation.

Acceptance:

- Web Forge or GLB smoke loads the exact `variant_key` with fallback count `0`.
- Quest recall loads the same `variant_key` through the runtime package with no GLB fallback.
- Replay evidence can trace `line_id`, `source_concept_ids`, and `variant_key` from sidecar metadata.
- The selected part follows the correct limb bone and does not lag, float, clip, or jump under reference poses.
- Runtime placement nudges are allowed only as small attachment corrections. They cannot be used to make an oversized or mis-modeled asset appear acceptable.

Per-family placement notes:

- Upperarm: preserve shoulder lift and elbow clearance. Pair outward nudge is limited to `2mm` per side if shoulder clipping appears.
- Forearm: preserve wrist rotation and controller sightline; avoid bulky wrist modules that hide grip pose.
- Hand: no public pass while canonical or variant hand depth exceeds accepted target without waiver. Controller clearance is mandatory.
- Thigh: preserve hip and knee articulation; line plates must not bridge across joints as rigid bars.

## Acceptance Test Flow

Use these commands as the engineering acceptance sequence. A failed earlier gate blocks later promotion.

1. Manifest shape, open-order mode:

```powershell
python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json
```

Expected before delivery: pass with warnings for catalog and delivery gaps.

2. Strict delivery gate:

```powershell
python tools\validate_modeler_variant_order_manifest.py --manifest docs\modeler-deliveries\p1-limb-three-line-variants-2026-05-03.order-manifest.json --require-delivered
```

Acceptance: `ordered variants=24`, `catalog gaps=0`, `delivery gaps=0`, no sidecar metadata failures.

3. Variant catalog gate:

```powershell
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
```

Acceptance: catalog status is `pass`; right-side P1 variants mirror their matching left-side variants; recommended topping slots remain valid for the parent module.

4. P1 module audit:

```powershell
python tools\audit_modeler_part_delivery.py --part left_upperarm --part right_upperarm --part left_forearm --part right_forearm --part left_hand --part right_hand --part left_thigh --part right_thigh --format json --output tests\.tmp\modeler-fit-and-triview-next-audit-2026-05-04.json
```

Acceptance: no `missing`, no `metadata_hold`, no `invalid`. Any remaining `fidelity_hold` must be a human visual decision with packet links, not missing metadata.

5. Runtime smoke when moving from `staging_candidate` to `fidelity_pass`:

```powershell
python tools\smoke_web_glb_load.py --report-json
```

Acceptance: fallback parts remain `0`, bbox warnings are either `0` or covered by an approved reviewer-only waiver, and the tested runtime package identifies the same `line_id` and `variant_key`.

## Promotion States

| State | Meaning | Entry criteria | Exit criteria |
|---|---|---|---|
| `order_open` | Manifest requests the variant but files are absent. | Current state for all 24 assets. | Strict validator sees the fileset and catalog entry. |
| `delivered_candidate` | Files exist and sidecars are parseable. | GLB, sidecar, source blend, and preview mesh are present. | Strict delivery validator passes with sidecar metadata. |
| `review_candidate` | Delivery is mechanically valid and ready for human tri-view review. | No `missing`, no `metadata_hold`, no `invalid`; review packet complete. | Human reviewer accepts visual identity and fit proof. |
| `staging_candidate` | Human review accepted, but public runtime is not active. | Tri-view sign-off, bbox/mirror proof, Web smoke candidate. | Web/Quest/Replay route proof passes. |
| `fidelity_pass` | Safe to map into a named runtime package. | Packaged Web proof, Quest/replay proof, fallback `0`, no unresolved visitor-facing waiver. | Separate runtime activation PR/change. |

## Waiver Conditions

A waiver is not a shortcut to `fidelity_pass`. It is a controlled way to keep rehearsal or reviewer work moving while a known defect is visible.

Waiver may be considered only when all are true:

- The asset is file-valid and metadata-complete.
- The issue is bounded to a named metric or visual defect, such as hand `z` overflow, minor bbox warning, or a clearly documented line-read compromise.
- The defect has front, side, back, 3Q, and closeup proof.
- The risk is acceptable for reviewer-only or rehearsal use.
- The waiver names owner, reviewer, date, affected `variant_key`, reason, expiry/recheck condition, and runtime visibility.

Waiver cannot be used when:

- GLB, sidecar, source blend, or preview mesh is missing.
- `line_id`, `source_concept_ids`, `design_intent`, or `fidelity_notes` are absent.
- A right-side `mirror_of` value is wrong.
- Runtime fallback is non-zero.
- The asset clips hands/controllers, blocks elbow/hip/knee motion, or cannot be identified from side/3Q.

Hand-specific waiver:

- Preferred pass: `left_hand` and `right_hand` bbox `z <= 0.136000m`, GLB/sidecar/preview bbox delta `<=0.002m`, left/right delta `<=3%`.
- If waived, hand variants remain `review_candidate` or `fidelity_hold`. They cannot become `fidelity_pass` until controller clearance and public route risk are explicitly accepted by the reviewer.

Waiver record shape for a delivery packet:

```json
{
  "waiver_id": "P1-HAND-Z-2026-05-04",
  "variant_keys": ["left_hand:oath_palm_core", "right_hand:oath_palm_core"],
  "issue": "bbox z exceeds 0.136000m target",
  "measured_value_m": 0.140037,
  "risk": "controller-side depth may read bulky in Quest",
  "visibility": "reviewer_only",
  "reviewer": "TBD",
  "expires_when": "hand bbox corrected or Quest controller proof is accepted",
  "evidence": ["front", "side", "back", "3q", "closeup", "controller_clearance"]
}
```

## Final Acceptance Definition

The P1 limb shortage is accepted as resolved only when:

1. All 12 order cards are delivered as 24 manifest-matching assets.
2. Strict order validation passes with `catalog gaps=0` and `delivery gaps=0`.
3. P1 audit reports no `missing`, `metadata_hold`, or `invalid`.
4. Every order card has front, side, back, 3Q, closeup, and clearance notes.
5. Hand depth is fixed or explicitly waived as reviewer-only.
6. Web, Quest, and Replay route proof identify the same `line_id` and `variant_key`.
7. No P1 limb variant is exposed in public runtime before reaching `fidelity_pass`.
