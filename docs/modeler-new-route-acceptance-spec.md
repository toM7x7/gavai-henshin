# モデラー向け新規路線 定量仕様と受け入れ基準

Updated: 2026-04-30

## 目的

この資料は、モデラーさんへ次回依頼するための定量仕様です。
対象は「Web ForgeでTポーズの鎧立てとして見たとき、基礎スーツの上に外装が装着されたヒーロースーツに見えること」です。

正本になる契約:

- visual layer: `base-suit-overlay.v1`
- body fit: `armor-body-fit.v1`
- modeler blueprint: `modeler-part-blueprint.v1`
- reference body: 170cm VRM preview space, unitは meter

非ゴール:

- 検査用の半透明箱、bbox、床グリッド、身長ガイドを最終形として作り込まない。
- 基礎スーツだけ、または外装だけを別々のデザインとして仕上げない。
- パーツ数不足を、意味のない細切れ分割で水増ししない。

## 受け入れゲート概要

| 項目 | 合格 | warn | fail |
|---|---|---|---|
| canonical module数 | 18/18 GLB + sidecar納品 | 12以上18未満で暫定reviewのみ | required core不足 |
| Web preview load | `previewGlbParts=18`, `previewFallbackParts=0` | fallbackが後続wave対象だけ | P0でfallbackあり |
| bbox | target比 各軸±10%以内 | ±10%超から±15%以内 | ±15%超 |
| 左右ペア | 寸法差3%以内 | 3%超、理由あり | 5%超または意図不明 |
| body intersection | 基準姿勢で交差なし | 軽微な疑いを画像で説明 | 明確に身体へ刺さる |
| material zones | `base_surface`必須、`accent`/`emissive`/`trim`を必要に応じて宣言 | 4 zoneは理由付き許容 | `base_surface`なし |
| UV0 | 非重複、2K texture前提で破綻なし | 仮UVだがNanobanana入力に使える | UV0なし、重なりが主面にある |
| 基礎スーツ | 単色でなく、首/胴/腕/脚へ連続する表面意匠 | 一部が弱い | 無地下着または未完成地肌に見える |
| 外装 | VRM表面上に装着された硬質パーツに見える | 一部に箱感/浮き | 検査用箱が主役 |
| トッピング準備 | P0に `variant_key`, `base_motif_link`, 2個以上の `topping_slots` | 呼び名だけ暫定 | metadataなし |

required coreは `helmet`, `chest`, `back` です。
モデラー発注としてのフル納品は18 canonical moduleを要求します。

## Target Envelope一覧

`authoring_target_m` は170cm基準の外形目標です。
まず各軸±10%以内を目標にし、±15%を超えたら再制作対象にします。

| module | category | target x/y/z m | clearance m | shell thickness m | triangle budget |
|---|---|---:|---:|---:|---:|
| helmet | head | 0.2856 / 0.3400 / 0.2584 | 0.018 | 0.035 | 1800 |
| chest | torso | 0.6392 / 0.4992 / 0.1632 | 0.024 | 0.045 | 1800 |
| back | dorsal | 0.5984 / 0.5148 / 0.1360 | 0.026 | 0.050 | 1600 |
| waist | waist | 0.4896 / 0.1716 / 0.1904 | 0.022 | 0.034 | 1200 |
| left_shoulder / right_shoulder | shoulder | 0.1904 / 0.1224 / 0.1632 | 0.028 | 0.038 | 900 |
| left_upperarm / right_upperarm | arm | 0.1088 / 0.2924 / 0.1088 | 0.018 | 0.028 | 1100 |
| left_forearm / right_forearm | arm | 0.1020 / 0.2788 / 0.1020 | 0.018 | 0.028 | 1100 |
| left_hand / right_hand | hand | 0.1156 / 0.0816 / 0.1360 | 0.014 | 0.020 | 700 |
| left_thigh / right_thigh | leg | 0.1360 / 0.3956 / 0.1292 | 0.020 | 0.030 | 1100 |
| left_shin / right_shin | leg | 0.1156 / 0.3956 / 0.1156 | 0.020 | 0.030 | 1100 |
| left_boot / right_boot | foot | 0.1224 / 0.0884 / 0.2856 | 0.018 | 0.032 | 900 |

座標は glTF Y-up、x=lateral、y=vertical または proximal-distal、z=outward です。
GLB export前にtransformをapplyし、originはパーツ中心に置いてください。

## 装着位置整合

sidecarの `vrm_attachment.primary_bone` は次を基準にします。

| module | primary_bone | offset目標 |
|---|---|---|
| helmet | `head` | magnitude 0.08m以内 |
| chest | `upperChest` | zは前方、magnitude 0.08m以内 |
| back | `upperChest` | zは後方、magnitude 0.08m以内、`rotation_deg.y=180` |
| waist | `hips` | magnitude 0.06m以内 |
| left_shoulder / right_shoulder | `leftShoulder` / `rightShoulder` | magnitude 0.04m以内 |
| left_upperarm / right_upperarm | `leftUpperArm` / `rightUpperArm` | magnitude 0.04m以内 |
| left_forearm / right_forearm | `leftLowerArm` / `rightLowerArm` | magnitude 0.04m以内 |
| left_shin / right_shin | `leftLowerLeg` / `rightLowerLeg` | magnitude 0.04m以内 |
| left_boot / right_boot | `leftFoot` / `rightFoot` | magnitude 0.06m以内 |

smoke testのhard toleranceは0.30mですが、モデラー納品の品質目標は上表を使います。
offsetは「見た目を後から無理やり合わせる補正」ではなく、パーツ中心と骨anchorの関係を説明する値として扱います。

装着位置の画像検収:

- 正面で胸/腰/足元が左右に流れない。
- 側面で胸、背中、腰が人体を挟む外装に見える。
- 回転時に肩、腰、すね、ブーツが身体から剥がれて見えない。
- 靴底はfloor planeに接し、左右の底面高さ差は0.015m以内に見える。

## 背面が薄い問題の修正基準

`back` は板ではなく、肩甲骨から腰へ流れる背面装甲です。
数値目標:

- bbox target: `x=0.5984m`, `y=0.5148m`, `z=0.1360m`
- z合格目標: 0.122mから0.150m
- z warn範囲: 0.116mから0.156m
- shell thickness target: 0.050m
- clearance target: 0.026m
- upperChest anchorからの後方offset magnitude: 0.08m以内

形状条件:

- 側面/3Qで、背面中央が薄いタイルではなく、背骨ラインと肩甲骨面を持つ。
- 左右端に0.030m以上の見える返し、リップ、または段差を持ち、胸装甲と側面でつながる。
- `back` 単体で薄い場合でも、`chest` と `waist` を合わせた全身側面で胴体を挟み込む厚みが読める。
- 背面中央の意匠は基礎スーツの spine line または rear power bus と `base_motif_link` で接続する。

## パーツ数不足の解消基準

canonical互換面は18 moduleのまま固定します。

フル納品:

- 18/18 moduleに `<module>.glb`
- 18/18 moduleに `<module>.modeler.json`
- 18/18 moduleに `source/<module>.blend`
- 18/18 moduleに `preview/<module>.mesh.json`
- 18/18 moduleに front/back/side/3q preview、可能ならcloseup 4視点

最低限の見た目成立:

- Web previewで `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder` がGLBとして見える。
- 下半身はWave 2でも、`left_shin`, `right_shin`, `left_boot`, `right_boot` の接地と継ぎ目が第一印象を壊さない。
- 追加toppingは18 canonical module不足の代替にしない。まず親moduleが単体で合格し、その上に追加する。

## 基礎スーツと外装テクスチャ統一

`base_suit_surface` は無地のインナーではありません。
VRM表面に貼る完成スーツ表面として、次を持たせます。

- rubber/fabric grain
- body-following panel seams
- fine geometric linework
- subtle color blocking
- glow guides visible through armor gaps

`armor_overlay_parts` は上記の意匠を受ける硬質外装です。
各P0 moduleは確認メモまたはsidecar相当のメタデータで、最低1つの `base_motif_link` を宣言してください。

受け入れ基準:

- 基礎スーツと外装が同じprimary color、accent color、emissive colorの文法で読める。
- 外装の縁、段差、トリムが基礎スーツのラインを受ける。
- 外装の隙間から見えるVRM表面が未完成の地肌、灰色proxy、単色下着に見えない。
- `base_surface`, `accent`, `emissive`, `trim` のmaterial zone意図がNanobananaの2K texture jobへ渡せる。
- 左右ペアは同じtexel density、同じpalette、同じmotif接続にする。

## VariantとTopping設計

今後のパーツ増殖は、canonical moduleの置き換えと追加装飾を分けます。

- variant: canonical moduleを同じslot上で置き換える。例: `shoulder:sleek` から `shoulder:winged`。
- topping: canonical moduleに載せる小型add-on。例: `shoulder_fin`, `chest_core`。

variantの条件:

- 親moduleの `authoring_target_m` から±15%を超えない。
- 同じ `primary_bone`, `attachment_slot`, coordinate frameを使う。
- `variant_key`, `part_family`, `base_motif_link` を必須にする。

toppingの条件:

- `parent_module`, `topping_slot`, `slot_transform`, `max_bbox_m`, `conflicts_with` を持つ。
- 親moduleがtoppingなしで合格する。
- toppingはbody anchorを直接奪わず、親moduleのlocal slotへ載る。
- 左右pairのtoppingはmirror可能にする。

P0で予約するslot:

| parent | required slots | max_bbox_m目安 |
|---|---|---|
| helmet | `crest`, `visor_trim` | crest 0.08/0.12/0.06, trimはhelmet外形内 |
| chest | `chest_core`, `rib_trim` | core 0.14/0.12/0.035 |
| back | `spine_ridge`, `rear_core` | ridge 0.12/0.20/0.040 |
| waist | `belt_buckle`, `side_clip` | buckle 0.16/0.08/0.035 |
| shoulder | `shoulder_fin`, `edge_trim` | fin 0.10/0.12/0.040 |
| shin | `shin_spike`, `ankle_cuff_trim` | spike 0.06/0.12/0.040 |

`conflicts_with` は、大型variant同士、視界を塞ぐcrest、腕可動を潰すshoulder_fin、足首可動を潰すankle cuffで必ず宣言してください。

## 納品エビデンス

納品時にほしいもの:

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
  preview/<module>_front.png
  preview/<module>_back.png
  preview/<module>_side.png
  preview/<module>_3q.png
  preview/<module>_closeup_front.png
  preview/<module>_closeup_back.png
  preview/<module>_closeup_side.png
  preview/<module>_closeup_3q.png
  textures/
```

全身確認:

```text
viewer/assets/armor-parts/_masters/review_master.blend
viewer/assets/armor-parts/_masters/full_suit_front.png
viewer/assets/armor-parts/_masters/full_suit_side.png
viewer/assets/armor-parts/_masters/full_suit_back.png
viewer/assets/armor-parts/_masters/full_suit_3q.png
viewer/assets/armor-parts/_masters/full_suit_overlay.png
```

こちら側の確認コマンド:

```bash
python tools/validate_armor_parts_intake.py
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
python tools/smoke_web_glb_load.py
```

最終判断は、数値gateとWeb previewの第一印象の両方で行います。
数値がpassでも、背面が薄い、装着位置が浮く、基礎スーツと外装が別物に見える場合は未達として戻します。

## Wave 1++後のwarn 8件の意味

Wave 1++時点の `warn` は、GLB納品やbboxの失敗ではありません。
18/18 GLB、fallback 0、bbox許容内を前提に、次Waveへ残す検収論点を8つの作業単位として扱います。

| warn | 意味 | 次の解消条件 |
|---|---|---|
| 1. `offset_m` 品質gate | sidecar offsetは小さくなったが、Web/Quest実装が最終配置根拠として使う前に、骨anchorとの意味を固定する必要がある。 | moduleごとに `primary_bone`, `offset_m`, `rotation_deg`, local forward/upを確認し、見た目補正ではなく装着関係の値として説明できる。 |
| 2. metadata gate | P0の `variant_key`, `part_family`, `base_motif_link`, `topping_slots`, `conflicts_with` がまだ生成/分岐の契約として閉じていない。 | P0 moduleがsidecar相当メモで上記metadataを持ち、Web QAとNanobanana promptで同じ名前を参照できる。 |
| 3. chest silhouette | 胸は寸法内だが、第一印象で箱や検査用ボリュームに戻るリスクが残る。 | 正面/側面/3Qで胸郭を包む曲面外装に見え、腹側の箱エッジが主役にならない。 |
| 4. back dorsal wrap | `back` のz寸法は範囲内だが、薄い板に見えたら未達。 | 肩甲骨から腰へ流れる背面装甲として、胸/腰と側面で胴体を挟む厚みが読める。 |
| 5. waist and pelvis contact | 腰のbboxは改善済みだが、浮いた輪に見えるとWebの鎧立て感を壊す。 | ベルトが骨盤へ巻き付き、前後左右の高さが破綻せず、胸装甲と脚の隙間を受ける。 |
| 6. shoulder integration | 左右肩は寸法・ミラーとしては成立しているが、肩球上の小物に見えるリスクが残る。 | 三角筋を覆い、胸/背中側へ薄いリップで差し込まれた肩アーマーに見える。 |
| 7. shin/boot grounding | すねとブーツはWave 2寄りでも、足元の接地不良は第一印象を壊す。 | 靴底がfloor planeへ接し、すね-ブーツ接続がカフ/段差で読め、左右底面差が0.015m以内に見える。 |
| 8. Nanobanana texture unity | 素材はまだplaceholderで、基礎スーツと外装が別物に見える危険が残る。 | Nanobananaで `unified_design` を先に決め、基礎スーツと外装が同じ色面・発光線・素材コントラストでつながる。 |

この8件は「passまであと8つの数値不合格」ではなく、「次Waveで閉じるべき検収観点」です。
特に 1 と 2 を先に閉じないと、Web QAとテクスチャ生成が別々の言葉で進み、後から分岐・toppingを増やすときに破綻します。

## 次Waveの実装順

ロア上の順序は、Webで鎧立てを確定し、Questで呼び出し、変身体験へ持ち込む流れです。
そのため次Waveは次の順で進めます。

1. `offset_m` / metadata gate完了: sidecarの装着値とP0 metadataを正本化する。ここで `base_motif_link` と `topping_slots` も名前を固定する。
2. Web QA反映: Web Forgeの正面/側面/回転で、offset、浮き、箱感、接地、fallback 0、layer表示を確認する。
3. Nanobanana基礎スーツ/外装統一: `unified_design` を先に生成し、`base_suit_surface` と `armor_overlay_parts` へ分配する。単色基礎スーツは禁止する。
4. topping library拡張: P0の親moduleが単体で合格した後、`crest`, `visor_trim`, `chest_core`, `shoulder_fin`, `belt_buckle`, `shin_spike` などを追加する。

## Nanobananaオンリーのテクスチャプロンプト方針

最終テクスチャ生成はNanobananaオンリーを前提にします。
fallback asset、単色塗り、検査用proxy色、外装だけの別モチーフは最終成果として扱いません。
入力パラメータ、出力asset pointers、Quest recall連携まで含む詳細契約は `docs/nanobanana-texture-prompt-contract.md` を正本にします。

プロンプトは必ず次の順で書きます。

1. `unified_design`: 明るい特撮ヒーローとして、全身の色面、発光ライン、素材コントラスト、モチーフ反復を先に定義する。
2. `base_suit_surface`: VRM表面に貼る完成ボディスーツ。単色禁止。ラバー/繊維質、細密パネル、関節部の連続柄、外装隙間から見える発光導線を含める。
3. `armor_overlay_parts`: GLB外装。基礎スーツのラインを受ける縁、段差、トリム、発光アクセントを持たせる。胸/肩/腰/すね/ブーツが同じヒーロー文法に見えること。
4. `negative`: plain single color undersuit, unrelated armor pieces, dark warehouse sci-fi, gray proxy material, inspection bbox, transparent guide box, muddy low contrast を避ける。

明るさの基準は「展示会のWebプレビューで、来場者がこれを装着したいと思える特撮ヒーロー感」です。
暗く重いSF兵器ではなく、白/シルバー/鮮やかな主色、読みやすい差し色、細い発光線で、Web上でも形が読める方向へ寄せます。
