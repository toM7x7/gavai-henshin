# 装甲パーツ フィット監査・モデラー修正依頼

入力: `viewer/assets/armor-parts/*/*.modeler.json`

参照した契約:

- `henshin.modeler_blueprints`: 目標bboxとtriangle予算
- `henshin.armor_fit_contract`: body anchorと装着スロット順
- `viewer/assets/armor-parts/<module>/<module>.modeler.json`: 納品済みメトリクス

要約:

- 判定: `warn`
- 認識パーツ: 18 / 18
- 総三角形数: 12052
- material_zones集計: accent=18, base_surface=18, emissive=3, trim=13
- 見方: `修正依頼` 欄だけを順に潰せば、次の受け入れチェックに進めます。

| module | anchor | bbox 実測 -> 目標 m | 差分 | triangles | material_zones | 修正依頼 |
|---|---|---|---|---:|---|---|
| helmet | head | 0.2509/0.3096/0.1700 -> 0.2856/0.3400/0.2584 | x -12.1%, y -8.9%, z -34.2% | 540 | accent, base_surface, emissive, trim | `authoring_target_m` に近づくようbboxを調整してください: z -34.2% (0.1700 -> 0.2584m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| chest | upperChest | 0.6627/0.4573/0.0892 -> 0.6392/0.4992/0.1632 | x +3.7%, y -8.4%, z -45.4% | 1196 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: z -45.4% (0.0892 -> 0.1632m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| back | upperChest | 0.5431/0.4319/0.0683 -> 0.5984/0.5148/0.1360 | x -9.2%, y -16.1%, z -49.8% | 520 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: y -16.1% (0.4319 -> 0.5148m); z -49.8% (0.0683 -> 0.1360m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shoulder | leftShoulder | 0.1434/0.0971/0.0851 -> 0.1904/0.1224/0.1632 | x -24.7%, y -20.7%, z -47.8% | 452 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: x -24.7% (0.1434 -> 0.1904m); y -20.7% (0.0971 -> 0.1224m); z -47.8% (0.0851 -> 0.1632m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shoulder | rightShoulder | 0.1434/0.0971/0.0851 -> 0.1904/0.1224/0.1632 | x -24.7%, y -20.7%, z -47.8% | 452 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: x -24.7% (0.1434 -> 0.1904m); y -20.7% (0.0971 -> 0.1224m); z -47.8% (0.0851 -> 0.1632m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_upperarm | leftUpperArm | 0.1027/0.2536/0.0939 -> 0.1088/0.2924/0.1088 | x -5.6%, y -13.3%, z -13.7% | 664 | accent, base_surface | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_upperarm | rightUpperArm | 0.1027/0.2536/0.0939 -> 0.1088/0.2924/0.1088 | x -5.6%, y -13.3%, z -13.7% | 664 | accent, base_surface | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_forearm | leftLowerArm | 0.0877/0.2516/0.0978 -> 0.1020/0.2788/0.1020 | x -14.0%, y -9.7%, z -4.1% | 708 | accent, base_surface, trim | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_forearm | rightLowerArm | 0.0877/0.2516/0.0978 -> 0.1020/0.2788/0.1020 | x -14.0%, y -9.7%, z -4.1% | 708 | accent, base_surface, trim | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_hand | leftHand | 0.0832/0.0725/0.0913 -> 0.1156/0.0816/0.1360 | x -28.0%, y -11.1%, z -32.9% | 536 | accent, base_surface, trim, emissive | `authoring_target_m` に近づくようbboxを調整してください: x -28.0% (0.0832 -> 0.1156m); z -32.9% (0.0913 -> 0.1360m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_hand | rightHand | 0.0832/0.0725/0.0913 -> 0.1156/0.0816/0.1360 | x -28.0%, y -11.1%, z -32.9% | 536 | accent, base_surface, trim, emissive | `authoring_target_m` に近づくようbboxを調整してください: x -28.0% (0.0832 -> 0.1156m); z -32.9% (0.0913 -> 0.1360m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_thigh | leftUpperLeg | 0.1426/0.3685/0.1018 -> 0.1360/0.3956/0.1292 | x +4.9%, y -6.9%, z -21.2% | 664 | accent, base_surface | `authoring_target_m` に近づくようbboxを調整してください: z -21.2% (0.1018 -> 0.1292m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_thigh | rightUpperLeg | 0.1426/0.3685/0.1018 -> 0.1360/0.3956/0.1292 | x +4.9%, y -6.9%, z -21.2% | 664 | accent, base_surface | `authoring_target_m` に近づくようbboxを調整してください: z -21.2% (0.1018 -> 0.1292m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shin | leftLowerLeg | 0.1170/0.3783/0.0949 -> 0.1156/0.3956/0.1156 | x +1.2%, y -4.4%, z -17.9% | 644 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: z -17.9% (0.0949 -> 0.1156m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shin | rightLowerLeg | 0.1170/0.3783/0.0949 -> 0.1156/0.3956/0.1156 | x +1.2%, y -4.4%, z -17.9% | 644 | accent, base_surface, trim | `authoring_target_m` に近づくようbboxを調整してください: z -17.9% (0.0949 -> 0.1156m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_boot | leftFoot | 0.1151/0.0917/0.2628 -> 0.1224/0.0884/0.2856 | x -6.0%, y +3.8%, z -8.0% | 792 | accent, base_surface, trim | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_boot | rightFoot | 0.1151/0.0917/0.2628 -> 0.1224/0.0884/0.2856 | x -6.0%, y +3.8%, z -8.0% | 792 | accent, base_surface, trim | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| waist | hips | 0.4915/0.1476/0.1917 -> 0.4896/0.1716/0.1904 | x +0.4%, y -14.0%, z +0.7% | 876 | accent, base_surface | QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |

再生成コマンド:

```bash
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
```
