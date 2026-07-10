# Modeler Wave 1++ Practical Handoff

Updated: 2026-04-30

この資料は、現在のWebプレビュー、モデル生成、モデラー納品の橋渡しです。詳細な思想は [modeler-wave1pp-analog-suit-addendum.md](modeler-wave1pp-analog-suit-addendum.md) を正本とし、このファイルでは実務上の確認項目と納品物を整理します。

## 現在の判断

18部位のGLB、metadata、Webプレビュー読み込みは成立しています。ただし、これだけではヒーロースーツとしては不十分です。現状の主な問題は、外装パーツが「体に沿って装着されている」よりも「周囲に置かれたパーツ」に見える点です。

今回、Web側と生成側では次を修正しました。

- 保存用SuitSpecは既存スキーマを守り、modeler sidecarはWeb preview recordへだけ展開。
- Web Forgeで `attachment_offset_target_m` を配置ベクトルとして誤用しないように分離。
- `vrm_attachment.offset_m` / `attachment_offset_m` を実配置に使い、部位ごとに装着深度を制限。
- ブーツは床接地を優先し、足から離れた床オブジェクトに見えにくくした。
- 胸、腰、背面、ブーツに部位別のsurface-worn clampを追加。
- 背面ユニットは実測bbox zを `0.110m` から `0.135m` へ回復。

## 検証状態

2026-04-30の確認結果:

- canonical armor module: 18/18
- Web preview smoke: `previewGlbParts=18`, `previewFallbackParts=0`
- armor intake: failなし、warnあり
- pytest: `72 passed`
- `back` bbox: target z `0.136m` / actual z `0.135m`

残warnは、胸、腰、上腕、すねが10% pass枠から少し外れているものです。15% fail枠は超えていません。次Waveでは、これを単純な数値合わせではなく、見た目の装着感改善として処理します。

## モデラーさんに依頼したいP0確認

P0部位:

- `helmet`
- `chest`
- `back`
- `waist`
- `left_shoulder`
- `right_shoulder`
- `left_shin`
- `right_shin`

各P0で確認したいこと:

- front / side / back / 3Qで、人体に沿う内側面と外側面が読める。
- 基礎スーツの線と外装の線が接続している。
- 可動部に意図した逃げがある。偶然の隙間はNG。
- `topping_slots` が親部位に自然に後乗せできる位置にある。
- `clearance_m` と `shell_thickness_target_m` が外装として成立する。

## 部位別の実務メモ

### Back

単なる背負い板ではなく、肩甲骨、脊柱、腰をつなぐdorsal shellです。側面から見たときに、背中に沿って厚みがあり、胸・腰と連続する必要があります。

今回の仮GLBでは、背面z厚みを仕様値まで戻しています。モデラー版では、中央spine ridge、左右scapula pad、lumbar clasp、side returnを面として整理してください。

### Waist

前面だけの桶ではなく、骨盤を一周するbelt loopです。前面buckle、左右side clip、背面claspが同じ高さ帯でつながり、脚の可動を潰さない形にしてください。

### Boots

足裏接地が最優先です。つま先、かかと、靴底、足首カフ、すね受けが見える必要があります。左右で高さや接地面がずれると、即座に玩具の置物に見えます。

### Chest / Shoulders

胸は胸郭ラップ、肩は三角筋キャップです。正面だけの板、肩に乗った球体、胸から背面へ線がつながらないものはNGです。

### Shins

すねはブーツと接続する下腿シェルです。膝と足首に可動逃げを残しつつ、ブーツ上端に自然に入るsocket構造にしてください。

## 納品時に欲しいもの

- 18部位GLB
- 各部位の `modeler.json` 相当メモ
- 全身 front / side / back / 3Q preview
- P0 close-up front / side / back / 3Q
- `base_motif_link` 図
- `topping_slots` 図
- 接触/クリアランス図
- ブーツ接地図
- Nanobanana texture board

## Web側で確認するポイント

Webプレビューでは次を見ます。

- 側面で背面、腰、靴が体から離れていないか。
- ぐりぐり回しても、装着物として破綻しないか。
- 基礎スーツの線と外装の線がバラバラに見えないか。
- Quest呼び出し時に、4桁コードで同じ装備が再現できるか。

## 関連資料

- [hero-suit-reference-analysis-2026-04-30.md](hero-suit-reference-analysis-2026-04-30.md)
- [assets/hero-suit-surface-fit-concept.svg](assets/hero-suit-surface-fit-concept.svg)
- [modeler-new-route-acceptance-spec.md](modeler-new-route-acceptance-spec.md)
- [nanobanana-texture-prompt-contract.md](nanobanana-texture-prompt-contract.md)
