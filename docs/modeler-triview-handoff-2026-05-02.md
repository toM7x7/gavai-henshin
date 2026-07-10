# モデラー向け三面図ハンドオフ仕様

Date: 2026-05-02  
Scope: 生成済み三面図15案を、コスプレ造形に近い発想で3Dスーツ/鎧へ起こすための資料。  
Image set: `docs/assets/hero-suit-triview-2026-05-02/`

## 目的

三面図は、完成品を1ピクセル単位でなぞる設計図ではありません。モデラーが「着られる特撮スーツ」として解釈し、人体に沿う基礎スーツ、硬質外装、差し替えバリエーション、小物トッピングへ分解するための視覚資料です。

ただし、Web/Questで動かすための runtime 契約は固定します。既存の18 canonical module、既存 `variant_catalog.json`、既存の base variant 解決は壊さないでください。新しい形状案はまず `proposed_variant_key` / `proposed_topping_key` として提案し、Web/Quest入稿時に既存キーへマッピング承認されたものだけを受け取ります。

## 参照画像

| Sheet | Concept | File |
|---|---|---|
| 01 | c01-c03 | `docs/assets/hero-suit-triview-2026-05-02/sheet-01-concepts-01-03.png` |
| 02 | c04-c06 | `docs/assets/hero-suit-triview-2026-05-02/sheet-02-concepts-04-06.png` |
| 03 | c07-c09 | `docs/assets/hero-suit-triview-2026-05-02/sheet-03-concepts-07-09.png` |
| 04 | c10-c12 | `docs/assets/hero-suit-triview-2026-05-02/sheet-04-concepts-10-12.png` |
| 05 | c13-c15 | `docs/assets/hero-suit-triview-2026-05-02/sheet-05-concepts-13-15.png` |

Machine-readable catalog: `docs/assets/hero-suit-triview-2026-05-02/concept-catalog.json`

## 造形の読み方

特撮ヒーローとして大事にする順番:

1. 遠目のシルエット: 頭、胸、腰、すね、足先が瞬時に読めること。
2. 人体への装着感: 浮いた板ではなく、身体表面に沿って乗っていること。
3. スーツと外装の一体感: 基礎スーツの線が外装、ベルト、背面、脚へつながること。
4. 有機曲線と機械角の両立: なめらかな面に、細い溝、段差、ベベル、発光スリットを入れること。
5. Quest視認性: 近距離でも破綻せず、白飛び、極端な透明、細すぎる線を避けること。

## レイヤー分解

### 1. Base Suit Surface

VRM/body surface に追従するボディスーツです。単色の下着ではなく、完成したヒーロースーツの第1層として扱います。

含めるもの:

- 体表に沿う色面分割
- 布/ラバー/薄い装甲の質感
- 胸から脚へ流れるライン
- 関節に残る可動逃げの細線
- Nanobanana で再生成しやすい意匠メモ

含めないもの:

- rigid なヘルメットシェル
- 胸甲、背面ユニット、肩装甲、前腕装甲、すね装甲、ブーツ外装
- crest、fin、spike、core などの着脱小物

### 2. Canonical Armor Modules

Web/Quest runtime の基本パーツです。名前は固定です。

`helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`, `left_hand`, `right_hand`, `left_thigh`, `right_thigh`, `left_shin`, `right_shin`, `left_boot`, `right_boot`

人体に対する考え方:

- 胸と背面は別物に見せず、脇下または肩甲骨方向でつながる構造にする。
- 腰は腹部に刺さらず、骨盤を巻くベルト/ドライバーとして成立させる。
- 肩は三角筋を包み、上腕の動きを殺さない。
- 前腕、すね、ブーツは左右セットで寸法と意匠を揃える。
- 手、足、膝、肘の可動部には硬質パーツを詰めすぎない。

### 3. Variant

同じ canonical module slot に載る差し替え形状です。創作段階では名前を自由に提案して構いませんが、入稿時は既存 catalog key へマッピングします。

提案時の記録:

```json
{
  "proposal_id": "concept-c01-helmet-compound-eye",
  "source_concept_ids": ["c01"],
  "asset_kind": "variant",
  "module": "helmet",
  "proposed_variant_key": "helmet:compound_eye",
  "display_name": "Compound Eye Guardian Helmet",
  "base_motif_link": {"name": "head_crest_line", "surface_zone": "emissive"},
  "modeler_notes": "複眼の粒はテクスチャで密度を出し、GLB形状は大面と段差を優先する。"
}
```

入稿時は `variants/<variant_asset_key>/` を使います。`variant_key` の `:` はディレクトリ名に使いません。

```text
viewer/assets/armor-parts/<module>/variants/<variant_asset_key>/
  <module>__<variant_asset_key>.glb
  <module>__<variant_asset_key>.modeler.json
  source/<module>__<variant_asset_key>.blend
```

### 4. Topping

親 module に載る小型追加パーツです。crest、visor_trim、chest_core、rib_trim、spine_ridge、belt_buckle、shoulder_fin、shin_spike などを想定します。

提案時は `proposed_topping_key` を使い、入稿時は既存 `topping_slot` と `choice_key` へ合わせます。造形名や作家判断は `display_name` と `modeler_notes` に逃がしてください。

```text
viewer/assets/armor-parts/<module>/toppings/<topping_slot>/<choice_key>/
  <module>__<topping_slot>__<choice_key>.glb
  <module>__<topping_slot>__<choice_key>.modeler.json
  source/<module>__<topping_slot>__<choice_key>.blend
```

## Sidecar の使い分け

Canonical module:

- `contract_version`: `modeler-part-sidecar.v1`

Variant:

- `contract_version`: `modeler-part-variant-sidecar.v1`
- `asset_kind`: `variant`
- `variant_key`: `<module>:<variant_asset_key>`
- `variant_asset_key`: path-safe slug

任意だが強く推奨する記録:

- `source_concept_ids`: 参照した三面図ID
- `modeler_notes`: 造形判断
- `interpretation_notes`: 三面図から変えた理由
- `intentional_deviation_reason`: runtime都合であえて変えた理由
- `texture_files`: GLB外部 texture がある場合の一覧
- `reference_pose_checks`: `neutral`, `arms_raised`, `elbow_bend`, `knee_bend`, `head_turn`, `crouch_light`

## マテリアル/テクスチャ

- テクスチャ生成方針は `nano_banana` 前提です。
- GLBは原則 texture embedded とします。
- 外部 texture が必要な場合は `textures/` に置き、sidecar の `texture_files` に `baseColor`, `emissive`, `normal`, `roughnessMetallic` の有無を記録してください。
- emissive は「発光ラインの位置」を示す用途に留め、全身を白飛びさせないでください。

## モデラー裁量として歓迎すること

- 三面図より装着感が良くなる形状修正
- 人体可動を守るための分割線変更
- 造形密度を上げる小段差、リブ、薄い重なり
- 背面、側面、足元など画像生成が弱い箇所の実制作目線の補完
- コスプレ制作としての分割、接続、軽量化の提案

## 固定すること

- 18 canonical module の名前
- `variant_catalog.json` の既存順序
- `module:base` は canonical GLB に解決すること
- 左右ペアはセットで納品し、片側だけ品質差を出さないこと
- Web/Quest入稿前に `tools/validate_modeler_delivery_manifest.py` を通すこと
- 検証 manifest から runtime へ直接 activate しないこと

## 受領後の流れ

1. モデラーが三面図から `proposal_id` 単位で候補を提示する。
2. Engineering が既存 `variant_key` / `topping_slot` / `choice_key` へマッピングする。
3. モデラーが GLB, sidecar, source blend, review PNG を納品する。
4. `examples/modeler_delivery_manifest.sample.json` を参考に納品 manifest を作る。
5. `python tools/validate_modeler_delivery_manifest.py --manifest <manifest.json>` を通す。
6. 既存 intake / Web smoke / Quest smoke を通してから runtime 表示に入れる。
