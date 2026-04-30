# 装甲パーツ フィット監査 / モデラー修正依頼

## 現状の格納場所

- 入力: `viewer/assets/armor-parts/*/*.modeler.json`
- GLB: `viewer/assets/armor-parts/<module>/<module>.glb`
- 生成元: `src/henshin/modeler_blueprints.py` / `henshin.armor_fit_contract`

## 監査サマリ

- 判定: `warn`
- ロード済みパーツ: 18 / 18
- 総三角形数: 6484
- material_zones集計: accent=18, base_surface=18, emissive=10, trim=10

## Wave 1優先 / Webプレビュー検収観点

- 最新Web Forgeは `modeler_glb_available` で18/18ロード済み。ただし見た目はまだ検収用プロキシや白い仮素材の影響が残る。
- 透明箱・円筒は検査用プロキシ。最終GLBでは胸/背中/腰/肩/足元の外形が人体へ装着されて見えることを優先する。
- Wave 1は胸、背中、腰、肩、上腕、前腕を主対象にしつつ、Webの第一印象を壊す足元の接地感も同時に確認する。
- 検収はWebプレビュー正面/側面/回転で行い、箱感、浮き、体からの剥離、左右差、透明ガイドの主張が残らないことを見る。
- 定量gateの正本は `docs/modeler-new-route-acceptance-spec.md`。bboxは各軸±10%以内を合格目標、±15%超をfail、左右ペア差は3%以内とする。
- `back` は `target z=0.1360m`、合格目標 `0.122m-0.150m`。側面/3Qで薄い板に見えた場合は、bbox範囲内でも未達として戻す。
- P0 moduleは `variant_key`, `base_motif_link`, 2個以上の `topping_slots` を確認メモまたはsidecar相当のメタデータに残す。

| module | anchor | bbox actual -> target m | delta | triangles | material_zones | 見た目優先度/Wave 1 | モデラーさんに出す直しポイント |
|---|---|---|---|---:|---|---|---|
| helmet | head | 0.2742/0.3496/0.2429 -> 0.2856/0.3400/0.2584 | x -4.0%, y +2.8%, z -6.0% | 392 | accent, base_surface, emissive, trim | P1 / Wave 1 review | 見た目優先度/Wave 1 `P1 / Wave 1 review`: Webプレビューでは頭部の透明ガイドも目立つため、バイザー/額/後頭部の外形が仮でも読めること。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| chest | upperChest | 0.5890/0.4600/0.1607 -> 0.6392/0.4992/0.1632 | x -7.9%, y -7.9%, z -1.5% | 352 | accent, base_surface, emissive | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 透明な胴体箱ではなく、胸郭を包む曲面胸装甲にする。腹側の箱エッジを消し、胸-背中-腰を分割線としてつなぐ。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| back | upperChest | 0.5452/0.5150/0.1440 -> 0.5984/0.5148/0.1360 | x -8.9%, y +0.0%, z +5.8% | 396 | accent, base_surface, trim, emissive | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 背面ユニットは板箱ではなく、肩甲骨から腰へ流れる背中装甲にする。側面から見ても胴体を挟み込む厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shoulder | leftShoulder | 0.1772/0.1180/0.1682 -> 0.1904/0.1224/0.1632 | x -6.9%, y -3.6%, z +3.1% | 204 | accent, base_surface | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 肩球に小物が乗った見え方を避け、三角筋を覆う肩アーマーにする。胸/背中側へ薄く差し込むリップを作る。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shoulder | rightShoulder | 0.1772/0.1180/0.1682 -> 0.1904/0.1224/0.1632 | x -6.9%, y -3.6%, z +3.1% | 204 | accent, base_surface | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 肩球に小物が乗った見え方を避け、三角筋を覆う肩アーマーにする。胸/背中側へ薄く差し込むリップを作る。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_upperarm | leftUpperArm | 0.1000/0.2830/0.1100 -> 0.1088/0.2924/0.1088 | x -8.1%, y -3.2%, z +1.1% | 332 | accent, base_surface | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 上腕は棒状プロキシではなく、腕に沿う分割外装にする。肩と前腕の間は内側スーツが見える程度の隙間に抑える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_upperarm | rightUpperArm | 0.1000/0.2830/0.1100 -> 0.1088/0.2924/0.1088 | x -8.1%, y -3.2%, z +1.1% | 332 | accent, base_surface | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 上腕は棒状プロキシではなく、腕に沿う分割外装にする。肩と前腕の間は内側スーツが見える程度の隙間に抑える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_forearm | leftLowerArm | 0.1000/0.2570/0.1020 -> 0.1020/0.2788/0.1020 | x -2.0%, y -7.8%, z -0.0% | 332 | accent, base_surface, trim | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 前腕は手首側へ細くなる装着パーツにする。透明な円筒ガイドの印象を残さず、上腕との接続を読む形にする。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_forearm | rightLowerArm | 0.1000/0.2570/0.1020 -> 0.1020/0.2788/0.1020 | x -2.0%, y -7.8%, z -0.0% | 332 | accent, base_surface, trim | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 前腕は手首側へ細くなる装着パーツにする。透明な円筒ガイドの印象を残さず、上腕との接続を読む形にする。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_hand | leftHand | 0.1150/0.0783/0.1400 -> 0.1156/0.0816/0.1360 | x -0.5%, y -4.1%, z +3.0% | 296 | accent, base_surface, emissive, trim | P2 / later wave | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_hand | rightHand | 0.1150/0.0783/0.1400 -> 0.1156/0.0816/0.1360 | x -0.5%, y -4.1%, z +3.0% | 296 | accent, base_surface, emissive, trim | P2 / later wave | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_thigh | leftUpperLeg | 0.1323/0.3769/0.1237 -> 0.1360/0.3956/0.1292 | x -2.8%, y -4.7%, z -4.3% | 348 | accent, base_surface | P2 / later wave | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_thigh | rightUpperLeg | 0.1323/0.3769/0.1237 -> 0.1360/0.3956/0.1292 | x -2.8%, y -4.7%, z -4.3% | 348 | accent, base_surface | P2 / later wave | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shin | leftLowerLeg | 0.1078/0.3967/0.1139 -> 0.1156/0.3956/0.1156 | x -6.7%, y +0.3%, z -1.5% | 396 | accent, base_surface, emissive, trim | P1 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P1 visual blocker / Wave 1 review`: 足元の浮きを隠すため、ブーツと接続する下端形状を先に合わせる。脚の透明プロキシが主役に見えない厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shin | rightLowerLeg | 0.1078/0.3967/0.1139 -> 0.1156/0.3956/0.1156 | x -6.7%, y +0.3%, z -1.5% | 396 | accent, base_surface, emissive, trim | P1 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P1 visual blocker / Wave 1 review`: 足元の浮きを隠すため、ブーツと接続する下端形状を先に合わせる。脚の透明プロキシが主役に見えない厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_boot | leftFoot | 0.1150/0.0890/0.2900 -> 0.1224/0.0884/0.2856 | x -6.0%, y +0.7%, z +1.5% | 532 | accent, base_surface, emissive, trim | P0 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P0 visual blocker / Wave 1 review`: Webのヒーロー表示では足元の接地感が重要。Wave 2制作対象でも靴底を床面に揃え、すね装甲との継ぎ目をカフで受ける。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_boot | rightFoot | 0.1150/0.0890/0.2900 -> 0.1224/0.0884/0.2856 | x -6.0%, y +0.7%, z +1.5% | 532 | accent, base_surface, emissive, trim | P0 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P0 visual blocker / Wave 1 review`: Webのヒーロー表示では足元の接地感が重要。Wave 2制作対象でも靴底を床面に揃え、すね装甲との継ぎ目をカフで受ける。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| waist | hips | 0.4500/0.1655/0.1929 -> 0.4896/0.1716/0.1904 | x -8.1%, y -3.5%, z +1.3% | 464 | accent, base_surface, emissive | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 腰に浮いた輪ではなく、骨盤へ巻き付くベルトにする。胸装甲と脚の間の隙間を隠し、前後左右の高さを揃える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |

## 確認コマンド

```bash
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
python tools/validate_armor_parts_intake.py
```
