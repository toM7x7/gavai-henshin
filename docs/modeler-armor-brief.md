# モデラー向け装甲パーツ依頼メモ

Updated: 2026-04-29

## Intake validation note

- Final delivered GLBs live at `viewer/assets/armor-parts/<module>/<module>.glb`.
- Modeler sidecars live at `viewer/assets/armor-parts/<module>/<module>.modeler.json`.
- Blender source files live at `viewer/assets/armor-parts/<module>/source/<module>.blend`.
- Do not store Blender backup files such as `*.blend1` in the handoff tree.
- Optional shared review masters can live under `viewer/assets/armor-parts/_masters/`.
- Run `python tools/validate_armor_parts_intake.py` before treating a delivery as formally staged.

## モデラーさんへ渡す最小情報

- 依頼対象: Web Forgeの水色プロキシを置き換える外装GLBパーツです。
- 正本: `GET /v1/catalog/part-blueprints` の `authoring_target_m` と `vrm_attachment` です。
- 納品先: `viewer/assets/armor-parts/<module>/<module>.glb`
- 制作元: `viewer/assets/armor-parts/<module>/source/<module>.blend`
- テクスチャ: `viewer/assets/armor-parts/<module>/textures/`
- 補足: `viewer/assets/armor-parts/<module>/<module>.modeler.json`
- テクスチャ生成: Nano Bananaのみを使います。
- 進捗状態: draft readyです。発注前にシルエットレビューと干渉確認を通します。

## 目的

現在のWebプレビューは完成ヒーロースーツではなく、`VRM人体 + 基礎スーツ表面 + 仮装甲プロキシ` の接続試験です。
モデラーさんへ依頼する対象は、この仮プロキシを置き換える外装パーツです。

ロアは固定です。

```text
Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す
```

## 格納場所

- 人が読む簡易メモ: `docs/modeler-armor-brief.md`
- 詳細な機械可読設計図API: `GET /v1/catalog/part-blueprints`
- 設計図生成コード: `src/henshin/modeler_blueprints.py`
- 現行の仮パーツ: `viewer/assets/meshes/*.mesh.json`
- 外部制作GLBの受け入れ先: `viewer/assets/armor-parts/<module>/<module>.glb`
- 制作元ファイルの受け入れ先: `viewer/assets/armor-parts/<module>/source/<module>.blend`
- テクスチャ成果物の受け入れ先: `viewer/assets/armor-parts/<module>/textures/`
- GLBごとの補足sidecar: `viewer/assets/armor-parts/<module>/<module>.modeler.json`

## 制作ルール

- 納品形式は `glTF 2.0 GLB` を基本にします。
- Blenderなどの制作元ファイルも残してください。
- 単位はメートル相当です。Web Forgeの170cm基準VRMに合わせます。
- pivotはパーツ中心、transformは適用済みにしてください。
- UV0必須、Base ColorとEmissive Maskを貼れる状態にします。
- テクスチャ生成は Nano Banana のみを使います。
- 現行の水色箱/筒は発注寸法そのものではありません。設計図APIの `authoring_target_m` を優先してください。

## レイヤー分け

- 基礎スーツ: VRM表面に貼るボディスーツ。体に沿う模様、発光ライン、布/素材感を担当。
- 外装パーツ: ヘルメット、胸、背中、肩、腕甲、ベルト、すね、ブーツなどの硬い装甲。
- 手足全体を固い筒で覆いすぎると動きが壊れるため、関節付近は分割と逃げを優先します。

## 優先Wave

| Wave | 優先部位 | 目的 |
|---|---|---|
| Wave 1 | chest, back, waist, shoulders, upperarms, forearms | 胴体から腕のヒーローシルエットを成立させる |
| Wave 2 | thighs, shins, boots | 下半身と足元の接地感を整える |
| Wave 3 | helmet, hands | 顔、手先、展示映えを仕上げる |

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

- 正面、側面、背面、斜めの確認画像がある
- 左右ペアの寸法差が3%以内
- VRM人体にめり込まず、少し浮いた外装として見える
- UVが重なっていない
- `base_surface`, `accent`, `emissive`, `trim` の素材意図が分かる
- 明るめの特撮ヒーローとして、暗すぎず攻撃的すぎない

## 現時点の注意

胸・背中・腰の箱プロキシは、形状検討用の仮表示です。
最終的には人体に沿う胸板、背面ユニット、ベルトへ置き換えます。
テクスチャを先に詰めすぎると箱の形に引っ張られるため、Wave 1の形状品質を先に上げます。
