# 装甲パーツ フィット監査 / モデラー修正依頼

## 現状の格納場所

- 入力: `viewer/assets/armor-parts/*/*.modeler.json`
- GLB: `viewer/assets/armor-parts/<module>/<module>.glb`
- 生成元: `src/henshin/modeler_blueprints.py` / `henshin.armor_fit_contract`

## Wave 1成果物照合（2026-04-30）

- あるもの: 18 module、各 `.glb`、各 `.modeler.json`、各 `source/<module>.blend`、各 `preview/<module>.mesh.json`、各 preview PNG 4枚、`_masters/review_master.blend`。
- ないもの: `viewer/assets/armor-parts/_masters/full_suit_*.png`、`docs/armor-part-fit-modeler-requests.before.md`。`docs/armor-build-wave1-results.md` も監査開始時点では未格納だったため、本監査で新規作成する。
- `*.blend1` は見つからない。バックアップファイル混入なし。
- intake validationは `pass`。fit handoff auditは `warn` で、bbox deltaに大きい軸が残る。モデラー返答の「bbox ±9%」はローカル実態としては未確認。

## 監査サマリ

- 判定: `warn`
- ロード済みパーツ: 18 / 18
- 総三角形数: 12052
- material_zones集計: accent=18, base_surface=18, emissive=3, trim=13

## Wave 1優先 / Webプレビュー検収観点

- 最新Web Forgeは `modeler_glb_available` で12/12ロード済み。ただし見た目は半透明プロキシが主役で、ヒーロースーツに見えない。
- 透明箱・円筒は検査用プロキシ。最終GLBでは胸/背中/腰/肩/足元の外形が人体へ装着されて見えることを優先する。
- Wave 1は胸、背中、腰、肩、上腕、前腕を主対象にしつつ、Webの第一印象を壊す足元の接地感も同時に確認する。
- 検収はWebプレビュー正面/側面/回転で行い、箱感、浮き、体からの剥離、左右差、透明ガイドの主張が残らないことを見る。

| module | anchor | bbox actual -> target m | delta | triangles | material_zones | 見た目優先度/Wave 1 | モデラーさんに出す直しポイント |
|---|---|---|---|---:|---|---|---|
| helmet | head | 0.2509/0.3096/0.1700 -> 0.2856/0.3400/0.2584 | x -12.1%, y -8.9%, z -34.2% | 540 | accent, base_surface, emissive, trim | P1 / Wave 1 review | `authoring_target_m` に近づくよう bbox を調整してください: z -34.2% (0.1700 -> 0.2584m).<br>見た目優先度/Wave 1 `P1 / Wave 1 review`: Webプレビューでは頭部の透明ガイドも目立つため、バイザー/額/後頭部の外形が仮でも読めること。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| chest | upperChest | 0.6627/0.4573/0.0892 -> 0.6392/0.4992/0.1632 | x +3.7%, y -8.4%, z -45.4% | 1196 | accent, base_surface, trim | P0 / Wave 1 | `authoring_target_m` に近づくよう bbox を調整してください: z -45.4% (0.0892 -> 0.1632m).<br>見た目優先度/Wave 1 `P0 / Wave 1`: 透明な胴体箱ではなく、胸郭を包む曲面胸装甲にする。腹側の箱エッジを消し、胸-背中-腰を分割線としてつなぐ。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| back | upperChest | 0.5431/0.4319/0.0683 -> 0.5984/0.5148/0.1360 | x -9.2%, y -16.1%, z -49.8% | 520 | accent, base_surface, trim | P0 / Wave 1 | `authoring_target_m` に近づくよう bbox を調整してください: y -16.1% (0.4319 -> 0.5148m); z -49.8% (0.0683 -> 0.1360m).<br>見た目優先度/Wave 1 `P0 / Wave 1`: 背面ユニットは板箱ではなく、肩甲骨から腰へ流れる背中装甲にする。側面から見ても胴体を挟み込む厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shoulder | leftShoulder | 0.1434/0.0971/0.0851 -> 0.1904/0.1224/0.1632 | x -24.7%, y -20.7%, z -47.8% | 452 | accent, base_surface, trim | P0 / Wave 1 | `authoring_target_m` に近づくよう bbox を調整してください: x -24.7% (0.1434 -> 0.1904m); y -20.7% (0.0971 -> 0.1224m); z -47.8% (0.0851 -> 0.1632m).<br>見た目優先度/Wave 1 `P0 / Wave 1`: 肩球に小物が乗った見え方を避け、三角筋を覆う肩アーマーにする。胸/背中側へ薄く差し込むリップを作る。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shoulder | rightShoulder | 0.1434/0.0971/0.0851 -> 0.1904/0.1224/0.1632 | x -24.7%, y -20.7%, z -47.8% | 452 | accent, base_surface, trim | P0 / Wave 1 | `authoring_target_m` に近づくよう bbox を調整してください: x -24.7% (0.1434 -> 0.1904m); y -20.7% (0.0971 -> 0.1224m); z -47.8% (0.0851 -> 0.1632m).<br>見た目優先度/Wave 1 `P0 / Wave 1`: 肩球に小物が乗った見え方を避け、三角筋を覆う肩アーマーにする。胸/背中側へ薄く差し込むリップを作る。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_upperarm | leftUpperArm | 0.1027/0.2536/0.0939 -> 0.1088/0.2924/0.1088 | x -5.6%, y -13.3%, z -13.7% | 664 | accent, base_surface | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 上腕は棒状プロキシではなく、腕に沿う分割外装にする。肩と前腕の間は内側スーツが見える程度の隙間に抑える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_upperarm | rightUpperArm | 0.1027/0.2536/0.0939 -> 0.1088/0.2924/0.1088 | x -5.6%, y -13.3%, z -13.7% | 664 | accent, base_surface | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 上腕は棒状プロキシではなく、腕に沿う分割外装にする。肩と前腕の間は内側スーツが見える程度の隙間に抑える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_forearm | leftLowerArm | 0.0877/0.2516/0.0978 -> 0.1020/0.2788/0.1020 | x -14.0%, y -9.7%, z -4.1% | 708 | accent, base_surface, trim | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 前腕は手首側へ細くなる装着パーツにする。透明な円筒ガイドの印象を残さず、上腕との接続を読む形にする。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_forearm | rightLowerArm | 0.0877/0.2516/0.0978 -> 0.1020/0.2788/0.1020 | x -14.0%, y -9.7%, z -4.1% | 708 | accent, base_surface, trim | P1 / Wave 1 | 見た目優先度/Wave 1 `P1 / Wave 1`: 前腕は手首側へ細くなる装着パーツにする。透明な円筒ガイドの印象を残さず、上腕との接続を読む形にする。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_hand | leftHand | 0.0832/0.0725/0.0913 -> 0.1156/0.0816/0.1360 | x -28.0%, y -11.1%, z -32.9% | 536 | accent, base_surface, trim, emissive | P2 / later wave | `authoring_target_m` に近づくよう bbox を調整してください: x -28.0% (0.0832 -> 0.1156m); z -32.9% (0.0913 -> 0.1360m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_hand | rightHand | 0.0832/0.0725/0.0913 -> 0.1156/0.0816/0.1360 | x -28.0%, y -11.1%, z -32.9% | 536 | accent, base_surface, trim, emissive | P2 / later wave | `authoring_target_m` に近づくよう bbox を調整してください: x -28.0% (0.0832 -> 0.1156m); z -32.9% (0.0913 -> 0.1360m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_thigh | leftUpperLeg | 0.1426/0.3685/0.1018 -> 0.1360/0.3956/0.1292 | x +4.9%, y -6.9%, z -21.2% | 664 | accent, base_surface | P2 / later wave | `authoring_target_m` に近づくよう bbox を調整してください: z -21.2% (0.1018 -> 0.1292m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_thigh | rightUpperLeg | 0.1426/0.3685/0.1018 -> 0.1360/0.3956/0.1292 | x +4.9%, y -6.9%, z -21.2% | 664 | accent, base_surface | P2 / later wave | `authoring_target_m` に近づくよう bbox を調整してください: z -21.2% (0.1018 -> 0.1292m).<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_shin | leftLowerLeg | 0.1170/0.3783/0.0949 -> 0.1156/0.3956/0.1156 | x +1.2%, y -4.4%, z -17.9% | 644 | accent, base_surface, trim | P1 visual blocker / Wave 1 review | `authoring_target_m` に近づくよう bbox を調整してください: z -17.9% (0.0949 -> 0.1156m).<br>見た目優先度/Wave 1 `P1 visual blocker / Wave 1 review`: 足元の浮きを隠すため、ブーツと接続する下端形状を先に合わせる。脚の透明プロキシが主役に見えない厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_shin | rightLowerLeg | 0.1170/0.3783/0.0949 -> 0.1156/0.3956/0.1156 | x +1.2%, y -4.4%, z -17.9% | 644 | accent, base_surface, trim | P1 visual blocker / Wave 1 review | `authoring_target_m` に近づくよう bbox を調整してください: z -17.9% (0.0949 -> 0.1156m).<br>見た目優先度/Wave 1 `P1 visual blocker / Wave 1 review`: 足元の浮きを隠すため、ブーツと接続する下端形状を先に合わせる。脚の透明プロキシが主役に見えない厚みを持たせる。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| left_boot | leftFoot | 0.1151/0.0917/0.2628 -> 0.1224/0.0884/0.2856 | x -6.0%, y +3.8%, z -8.0% | 792 | accent, base_surface, trim | P0 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P0 visual blocker / Wave 1 review`: Webのヒーロー表示では足元の接地感が重要。Wave 2制作対象でも靴底を床面に揃え、すね装甲との継ぎ目をカフで受ける。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| right_boot | rightFoot | 0.1151/0.0917/0.2628 -> 0.1224/0.0884/0.2856 | x -6.0%, y +3.8%, z -8.0% | 792 | accent, base_surface, trim | P0 visual blocker / Wave 1 review | 見た目優先度/Wave 1 `P0 visual blocker / Wave 1 review`: Webのヒーロー表示では足元の接地感が重要。Wave 2制作対象でも靴底を床面に揃え、すね装甲との継ぎ目をカフで受ける。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |
| waist | hips | 0.4915/0.1476/0.1917 -> 0.4896/0.1716/0.1904 | x +0.4%, y -14.0%, z +0.7% | 876 | accent, base_surface | P0 / Wave 1 | 見た目優先度/Wave 1 `P0 / Wave 1`: 腰に浮いた輪ではなく、骨盤へ巻き付くベルトにする。胸装甲と脚の間の隙間を隠し、前後左右の高さを揃える。<br>QA warnは修正するか、問題なしと判断できる確認画像/根拠を添えてください: bbox_within_target_envelope, non_overlapping_uv0, no_body_intersection_at_reference_pose. |

## 確認コマンド

```bash
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
python tools/validate_armor_parts_intake.py
```
