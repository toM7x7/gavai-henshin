# Wave 1 モデラー発注チェックリスト

Updated: 2026-04-30

## Wave 1+受け入れ監査メモ（2026-04-30）

- ローカル実態: 18 moduleすべてに `.glb`, `.modeler.json`, `source/<module>.blend`, `preview/<module>.mesh.json`, preview PNG 4枚がある。
- `*.blend1` は `viewer/assets/armor-parts` 配下に見つからなかった。
- `_masters` には `review_master.blend` と `full_suit_front/side/back/3q/overlay.png` が格納済み。
- closeup PNGは18 module x 4視点で格納済み。
- `python tools/validate_armor_parts_intake.py` は `pass`。
- `python tools/audit_armor_part_fit_handoff.py --format json` は `warn` のまま。ただしこれは視覚優先度ガイダンスを残すためで、bbox実測は最大絶対値8.9% / 平均3.7%。
- `docs/armor-build-wave1-results.md` と `docs/armor-part-fit-modeler-requests.before.md` は格納済み。

## 格納場所

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
  textures/
```

詳細な寸法・監査結果は `docs/armor-part-fit-modeler-requests.md` を参照してください。
定量gateの正本は `docs/modeler-new-route-acceptance-spec.md` です。

## 対象パーツ

- P0: `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`
- P1: `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`
- Web見た目ブロッカー確認: `left_boot`, `right_boot`, `left_shin`, `right_shin`

## 生成意匠チェック

- 基礎スーツは `base_suit_surface` としてVRM表面に貼る。単色・無地ではなく、特撮ボディスーツらしい繊維感、ラバー感、細密ライン、差し色を持つ。
- 外装は `armor_overlay_parts` として基礎スーツ上に追加する。人体の前に置いた箱ではなく、VRM表面に沿って装着される硬質パーツにする。
- Nanobananaには `unified_design` として、基礎スーツと外装を同一モチーフで生成させる。基礎スーツだけ、外装だけの別デザイン生成にしない。
- 基礎スーツのラインが胸装甲、肩、前腕、腰ベルト、すね/ブーツへ自然につながる。
- 外装の隙間から見える基礎スーツが「未完成の地肌」ではなく、完成したヒーロースーツの下地に見える。

## 分岐・トッピング準備

Wave 1では大きな実装追加は不要ですが、後でパーツ分岐とトッピング追加に進めるよう、確認メモかsidecarに次の呼び名を残せるとよいです。

- `part_family`: 例 `chest`, `shoulder`, `waist`, `forearm`, `shin`, `boot`。
- `variant_key`: 例 `sleek`, `heavy`, `tech`, `organic`, `heroic`。
- `base_motif_link`: 基礎スーツ側のどの線/柄とつながるか。
- `topping_slots`: 例 `crest`, `visor_trim`, `chest_core`, `shoulder_fin`, `belt_buckle`, `shin_spike`。
- `conflicts_with`: 同時に載せると破綻する大型パーツや装飾。

最低限P0では、`helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder` に `variant_key`, `base_motif_link`, 2個以上の `topping_slots` を意識してください。

## Wave 1定量gate

- bboxは `authoring_target_m` に対して各軸±10%以内を合格目標、±15%超をfailにする。
- 左右ペアの寸法差は3%以内にする。
- P0の `vrm_attachment.offset_m` は `helmet/chest/back` 0.08m以内、`waist` 0.06m以内、`shoulder` 0.04m以内を目標にする。
- `back` は `target z=0.1360m`、合格目標 `0.122m-0.150m`。側面/3Qで薄い板に見える場合はbboxが合っていても未達にする。
- `chest`, `back`, `waist` は側面確認で胴体を挟み込む外装に見えること。隙間や段差が第一印象を壊す場合は未達にする。
- `left_boot` / `right_boot` はWave 2対象でも靴底の左右高さ差を0.015m以内に見せる。
- material zoneは `base_surface` 必須。`accent`, `emissive`, `trim` は必要に応じて宣言し、4 zoneの場合は理由を添える。

## P0観点

- 胸・背中・腰が、透明な箱ではなく人体を包む外装に見える。
- 肩が球体に乗った小物ではなく、胸/背中へ差し込まれた肩アーマーに見える。
- 腰ベルトが骨盤に巻き付き、胸装甲と脚の間の隙間を自然に受けている。

## P1観点

- 上腕と前腕が棒状プロキシではなく、腕に沿う分割装甲に見える。
- 肩-上腕-前腕の間に大きな浮きや不自然な隙間がない。
- 透明ガイドやbboxより、装甲の輪郭が先に目に入る。

## Webプレビュー検収

正面、側面、回転で確認します。

- ヒーロースーツを着ている第一印象になっている。
- 半透明プロキシが主役に見えない。
- 肩、腰、足元が浮いて見えない。
- 左右ペアのサイズ差が意図しない差に見えない。
- 足元はWave 2対象でも、靴底の接地感だけ先に確認する。
- パーツ間の隙間、箱感、パーツ位置、基礎スーツと外装のテクスチャ不一致が残っている場合は、未達として隠さずメモする。

## 次回Webプレビュー合格基準

- 基礎スーツが単色ではなく、VRM表面テクスチャとして首、胴、腕、脚へ連続して見える。
- 外装パーツが基礎スーツ上の追加装甲として読め、後から `variant_key` や `topping_slots` で増やせる余白がある。
- 胸、肩、腰、すね/ブーツで、隙間・箱感・位置ずれが第一印象を壊していない。
- 基礎スーツの線、色、発光アクセントが外装の縁やトリムへつながり、別々の素材を重ねただけに見えない。
- 正面、側面、回転の3確認で `previewFallbackParts=0`、かつ半透明プロキシやbboxより完成スーツの輪郭が先に目に入る。

## 納品チェック

- 各対象moduleに `<module>.glb` と `<module>.modeler.json` がある。
- `modeler.json` に `bbox_m`, `triangle_count`, `material_zones`, `vrm_attachment.primary_bone` が入っている。
- `base_surface` のmaterial zoneがある。
- 正面/側面/回転のWebプレビュー確認画像、または同等の確認メモを添える。

## 確認コマンド

```bash
python tools/validate_armor_parts_intake.py
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
```
