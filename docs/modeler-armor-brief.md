# モデラー向け装甲パーツ制作メモ

Updated: 2026-04-30

## まず見る場所

- 依頼メモ: `docs/modeler-armor-brief.md`
- 詳細な設計図API: `GET /v1/catalog/part-blueprints`
- 設計図生成コード: `src/henshin/modeler_blueprints.py`
- 受け入れチェック: `python tools/validate_armor_parts_intake.py`

## 格納場所

モデルは次の形で格納します。

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
  textures/
```

例: ヘルメットは `viewer/assets/armor-parts/helmet/helmet.glb` に置きます。

`*.blend1` などのBlenderバックアップファイルは格納しません。共有レビュー用のマスターは `viewer/assets/armor-parts/_masters/` に置けます。

## 体験上の前提

ロアの導線は固定です。

```text
Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す
```

Web Forgeでは、VRM人体の表面を「基礎スーツ」として扱い、その上に分割した硬質装甲パーツを載せます。青い透明ボックスは最終デザインではなく、位置・大きさ・分割の確認用プロキシです。

## 制作ルール

- ランタイム形式は `glTF 2.0 GLB` を基本にします。
- 単位はメートル相当です。Web Forgeの170cm基準VRMに合わせます。
- transformは適用済みにし、見えないDCCオフセットを残さないでください。
- pivotはパーツ中心を基準にし、Quest/Web側で骨や装着スロットに載せ替えやすくします。
- UV0は必須です。Base ColorとEmissive Maskを貼れる状態にします。
- テクスチャ生成はNanobananaのみを使います。
- `base_surface`, `accent`, `emissive`, `trim` の材料スロットが分かる構成にします。
- パーツはVRM体表にめり込ませず、少し浮いた硬質装甲として見えるようにします。

## 優先Wave

| Wave | 優先パーツ | 目的 |
|---|---|---|
| Wave 1 | chest, back, waist, shoulder, upperarm, forearm | 胴体から腕のヒーローシルエットを成立させる |
| Wave 2 | thigh, shin, boot | 下半身と接地感を整える |
| Wave 3 | helmet, hand | 顔まわり、手元、展示映えを詰める |

## パーツ一覧

| module | 日本語 | 種別 | 左右 | 目安寸法 x/y/z m |
|---|---|---|---|---|
| helmet | ヘルメット | head | center | 0.286 / 0.340 / 0.258 |
| chest | 胸部装甲 | torso | center | 0.639 / 0.499 / 0.163 |
| back | 背面ユニット | dorsal | center | 0.598 / 0.515 / 0.136 |
| waist | ベルト | waist | center | 0.490 / 0.172 / 0.190 |
| left_shoulder | 左肩 | shoulder | left | 0.190 / 0.122 / 0.163 |
| right_shoulder | 右肩 | shoulder | right | 0.190 / 0.122 / 0.163 |
| left_upperarm | 左上腕 | arm | left | 0.109 / 0.292 / 0.109 |
| right_upperarm | 右上腕 | arm | right | 0.109 / 0.292 / 0.109 |
| left_forearm | 左腕甲 | arm | left | 0.102 / 0.279 / 0.102 |
| right_forearm | 右腕甲 | arm | right | 0.102 / 0.279 / 0.102 |
| left_hand | 左手甲 | hand | left | 0.116 / 0.082 / 0.136 |
| right_hand | 右手甲 | hand | right | 0.116 / 0.082 / 0.136 |
| left_thigh | 左太腿 | leg | left | 0.136 / 0.396 / 0.129 |
| right_thigh | 右太腿 | leg | right | 0.136 / 0.396 / 0.129 |
| left_shin | 左すね | leg | left | 0.116 / 0.396 / 0.116 |
| right_shin | 右すね | leg | right | 0.116 / 0.396 / 0.116 |
| left_boot | 左ブーツ | foot | left | 0.122 / 0.088 / 0.286 |
| right_boot | 右ブーツ | foot | right | 0.122 / 0.088 / 0.286 |

## 納品チェック

1. 正面、側面、背面、斜めの確認画像がある。
2. 左右ペアの寸法差が3%以内に収まっている。
3. VRM人体にめり込まず、少し浮いた外装として見える。
4. UV0が重なっていない。
5. `base_surface`, `accent`, `emissive`, `trim` の材料意図が分かる。
6. 明るめの特撮ヒーローとして読みやすく、暗すぎたり武器的すぎたりしない。

## 現時点の注意

現在のWebプレビューは、最終モデルの完成見本ではありません。人体表面の基礎スーツ、GLB外装パーツ、Nanobanana表面生成を接続するための開発プレビューです。

胸・背中・腰の箱状プロキシは最終形ではなく、Wave 1で人体に沿う板・背面ユニット・ベルトへ置き換える対象です。テクスチャを詰める前に、まず形状のフィット品質を上げます。
