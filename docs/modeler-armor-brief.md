# モデラー向け装甲パーツ制作メモ

Updated: 2026-04-30

## 現状の格納場所

装甲パーツは次の形で格納します。

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
  textures/
```

例: ヘルメットは `viewer/assets/armor-parts/helmet/helmet.glb` に置きます。
Blenderのバックアップファイル（`*.blend1` など）は格納しません。

## 次回受け入れ時の必須確認

- 18 moduleすべてに `<module>.glb`, `<module>.modeler.json`, `source/<module>.blend`, `preview/<module>.mesh.json`, preview PNG（front/back/side/3q）があること。
- `viewer/assets/armor-parts` 配下に `*.blend1` がないこと。
- `_masters/review_master.blend` に加え、全身確認画像 `viewer/assets/armor-parts/_masters/full_suit_*.png` が納品されていること。
- `docs/armor-build-wave1-results.md` にモデラー側の完了報告、受け入れ結果、差分、実行コマンド結果を残すこと。
- 既存依頼を上書き更新する場合は、前版スナップショット `docs/armor-part-fit-modeler-requests.before.md` を添えること。
- bboxが「±9%以内」と報告された場合は、sidecarの `bbox_m` と fit audit のdeltaで再確認すること。Wave 1+では `validate_armor_parts_intake.py` はpass、bboxは最大絶対値8.9% / 平均3.7%。fit auditは視覚優先度ガイダンスを残すため `warn` のまま。

## いま見えている問題

最新のWeb Forge smokeでは18/18パーツがGLBとしてロード済みです。
Wave 1+で半透明プロキシの主張は弱まりましたが、引き続き「ヒーロースーツを着ている」第一印象を検収軸にします。

特に直したい見え方:

- 透明箱: 胸・腰まわりの検査用ボックスが最終形に見える。
- 胴体箱: 胸装甲が人体の胸郭を包まず、四角い箱として読める。
- 肩: 肩パーツが肩球の上に乗っている小物に見え、胸/背中へ差し込まれていない。
- 腰: ベルトが骨盤に巻き付かず、浮いた輪に見える。
- 足元: 靴底の接地とすね-ブーツ接続が弱く、装着感が崩れる。
- 全体: パーツがVRM表面に沿う外装ではなく、人体の前に重ねた透明ガイドに見える。
- テクスチャ不一致: 基礎スーツが単色または無地に見え、外装パーツだけが別デザインとして浮く。

## 定量仕様の正本

次回発注から、具体的な合格値は `docs/modeler-new-route-acceptance-spec.md` を正本にします。
このbriefは意図と優先順位、acceptance specは寸法・装着・テクスチャ・トッピングの判定表です。

主要gate:

- canonical moduleは18/18納品。required coreは `helmet`, `chest`, `back`。
- Web previewは `previewGlbParts=18`, `previewFallbackParts=0` を目標にする。
- bboxは `authoring_target_m` 各軸±10%以内を合格目標、±15%超をfailにする。
- 左右ペアの寸法差は3%以内にする。
- `vrm_attachment.offset_m` は品質目標として torso/helmet/back 0.08m以内、waist/boot 0.06m以内、shoulder/limb 0.04m以内にする。
- `back` は `target z=0.1360m`、合格目標 `0.122m-0.150m`。薄い板ではなく、側面で胴体を挟み込む返しを持たせる。
- `base_suit_surface` と `armor_overlay_parts` は同じprimary/accent/emissive文法と `base_motif_link` でつなぐ。
- P0 moduleは `variant_key`, `base_motif_link`, 2個以上の `topping_slots` を確認メモまたはsidecar相当のメタデータに残す。

## 基礎スーツ・外装・Nanobananaの役割

今回の生成仕様では、基礎スーツと外装を次のように分けます。

- 基礎スーツ = `base_suit_surface`: VRM表面に貼るボディスーツテクスチャ。単色の下着ではなく、特撮らしいラバー/繊維/細密ライン/発光筋/幾何パネルを持つ。
- 外装 = `armor_overlay_parts`: VRM表面の上に追加されるGLBパーツ。胸板、背面、肩、前腕、腰、すね、ブーツなど、硬いシルエットと影を作る。
- Nanobanana = `unified_design`生成: 基礎スーツと外装を同じヒーロー意匠としてまとめる。基礎スーツだけを先に無地生成したり、外装だけを別モチーフで生成したりしない。

生成プロンプトでは、先に全身の意匠ルールを決めてから、基礎スーツと外装へ分配します。
例: 「胸のV字発光ラインが基礎スーツから胸装甲のエッジへ入り、肩から前腕へ同じ差し色が走り、腰ベルトのバックルでモチーフが反復する」。

基礎スーツ側に入れるもの:

- 全身をつなぐ低〜中周波のパネルライン。
- 外装の隙間から見える布/ラバー/繊維テクスチャ。
- 関節部、脇、肘、膝、首周りの連続柄。
- 発光ラインの下地、または外装の発光へつながる導線。

外装側に入れるもの:

- 胸、肩、腰、腕、脚のシルエットを決める硬質パーツ。
- 基礎スーツの線を受ける縁取り、段差、トリム。
- トッピングを載せる余白。額飾り、胸コア、肩フィン、ベルトバックル、すね飾りなど。

## パーツ分岐・トッピング追加の最小仕様案

将来の分岐に備え、各パーツは「置き換えvariant」と「追加topping」を分けて考えます。
Wave 1では実装追加より、命名とプロンプト設計を揃えることを優先します。

```json
{
  "part_family": "shoulder",
  "variant_key": "sleek",
  "base_motif_link": "arm_stream_line",
  "topping_slots": ["shoulder_fin", "edge_trim"],
  "conflicts_with": ["heavy_shoulder_spike"]
}
```

- `part_family`: 大分類。UIや生成プロンプトで選択肢を束ねる。
- `variant_key`: 同じfamily内の見た目分岐。例: `sleek`, `heavy`, `heroic`, `tech`, `organic`。
- `base_motif_link`: 基礎スーツ側のどの柄/ラインと接続するか。
- `topping_slots`: 後乗せ装飾の置き場。
- `conflicts_with`: 同時選択で干渉するvariant/topping。

最低限、P0の `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder` からこの考え方を当てます。
左右ペアは同じ `variant_key` と `base_motif_link` を持たせ、左右差は意図した非対称デザインのときだけ明記してください。

## Wave 1優先

Wave 1は「Webプレビュー正面でヒーロースーツとして成立するか」を最優先にします。
テクスチャや発光ラインより先に、シルエット、接地、人体への装着感を直してください。
表面テクスチャ生成はNanobanana前提です。GLB側はUV0と `base_surface`, `accent`, `emissive`, `trim` の意図が読める状態にしてください。
ただし最新方針では、最終見えの基礎スーツを単色にしません。形状修正と並行して、外装の隙間から見えるVRM表面テクスチャが特撮スーツとして成立する前提でUV/zoneを残してください。

| 優先 | module | 直しポイント |
|---|---|---|
| P0 | chest | 透明な胴体箱をやめ、胸郭を包む曲面胸装甲にする。腹側の箱エッジを消す。 |
| P0 | back | 板箱ではなく、肩甲骨から腰へ流れる背面装甲にする。胸装甲と側面でつながる厚みを持たせる。 |
| P0 | waist | 腰に浮いた輪ではなく、骨盤へ巻き付くベルトにする。胸装甲と脚の間の隙間を隠す。 |
| P0 | left_shoulder / right_shoulder | 肩球に乗る小物ではなく、三角筋を覆う肩アーマーにする。胸/背中側へ薄く差し込むリップを作る。 |
| P1 | left_upperarm / right_upperarm | 棒状プロキシではなく、腕に沿う分割外装にする。肩と前腕の隙間を小さく保つ。 |
| P1 | left_forearm / right_forearm | 円筒ガイドに見せず、手首側へ細くなる前腕装甲にする。 |
| P0 visual blocker | left_boot / right_boot | Wave 2制作対象でも、Webの第一印象を壊すため足元の接地感は先に確認する。靴底を床面に揃える。 |
| P1 visual blocker | left_shin / right_shin | ブーツとの継ぎ目を受ける下端形状にし、脚の透明プロキシを主役にしない。 |

## Webプレビューで検収する観点

正面、側面、回転で次を確認します。

- 胸/背中/腰が一体の外装として人体を包んでいる。
- 肩が胸・背中側へ接続され、浮いて見えない。
- 腰ベルトが骨盤に巻き付いていて、前後左右の高さが破綻しない。
- 足元が床に接地し、すね装甲とブーツの継ぎ目が読める。
- 半透明プロキシやbboxが見た目の主役になっていない。
- 左右ペアの寸法差が意図しない差に見えない。

## 格納後の確認コマンド

```bash
python tools/validate_armor_parts_intake.py
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
```

修正依頼の詳細は `docs/armor-part-fit-modeler-requests.md` を更新してモデラーさんに渡します。
Wave 1だけを短く依頼する場合は `docs/modeler-wave1-checklist.md` を使います。
必要な設計図データは `GET /v1/catalog/part-blueprints` でも確認できます。
