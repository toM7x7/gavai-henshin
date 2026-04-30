# モデラー向け: 文脈と対応内容まとめ

Updated: 2026-04-30

## この資料の位置づけ

この資料は、外部モデラーさんへ現状の文脈、こちら側のWeb実装対応、次にお願いしたい制作・確認ポイントを渡すための入口です。
細かい寸法、bbox、module別の監査結果は `docs/armor-part-fit-modeler-requests.md` を正とします。

関連資料:

- `docs/modeler-wave1pp-practical-handoff.md`: Wave 1++後にモデラーさんへ渡す短い実務handoff
- `docs/modeler-armor-brief.md`: 格納場所、制作方針、Wave 1優先観点
- `docs/modeler-new-route-acceptance-spec.md`: 寸法、装着、背面厚み、テクスチャ統一、トッピングの定量受け入れ基準
- `docs/modeler-wave1-checklist.md`: Wave 1だけを短く確認するチェックリスト
- `docs/armor-part-fit-modeler-requests.md`: module別の寸法・監査・修正依頼
- `docs/armor-build-wave1-results.md`: モデラー返答とローカル受け入れ結果の照合
- `GET /v1/catalog/part-blueprints`: authoring target、anchor、設計寸法のAPI

## プロジェクト文脈

新規路線では、体験を次の流れで成立させます。

1. Webで来場者が武装生成パラメータを入力し、4桁コードを受け取る。
2. Webプレビューで、Tポーズの鎧立てを見るように「これから装着するヒーロースーツ」を確認する。
3. Quest側で4桁コードを入力し、生成済み武装を呼び出す。
4. Quest上で変身アニメーション、鏡/第三者視点、リプレイへつなげる。

今回の焦点は 2 のWebプレビューです。
ここが弱いと、Quest側に持ち込む前に「何を装着するのか」が来場者にも制作者にも伝わりません。

## ロアとして守ること

- 基礎スーツはVRM表面のボディスーツとして扱う。
- 外装パーツは人体の前に置いた箱ではなく、VRM表面に沿って装着される追加装甲として見せる。
- 明るめでかっこいい特撮ヒーロー方向。暗いSF倉庫や無機質な検査UIに寄せすぎない。
- 変身前の鎧立て、呼び出し、装着、Questでの確認が一本の体験としてつながること。
- テクスチャ生成はNanobanana前提。GLB側はUV0とmaterial zoneを読める状態にする。

## 最新ユーザー要望の反映（生成・モデリング共通）

基礎スーツを単色のインナーとして扱わず、特撮ヒーローらしい表面意匠を持つ「VRM表面テクスチャ」として設計します。
外装はその上に足される追加パーツで、胸・肩・腰・腕・脚の硬いシルエットを作ります。
Nanobananaには、基礎スーツと外装を別々の見た目にしないため、同一のモチーフ、色面、発光ライン、素材コントラストでまとめる統一意匠を生成させます。

プロンプト上の扱い:

- `base_suit_surface`: VRM表面に貼るボディスーツ柄。単色禁止。細かな布/ラバー/繊維/幾何ライン、胴体から四肢へ流れる特撮スーツ意匠を持たせる。
- `armor_overlay_parts`: GLBで追加される外装。基礎スーツの線、色、発光アクセントを受け、同じヒーローに見えるように接続する。
- `unified_design`: Nanobananaの生成単位。基礎スーツだけ、外装だけの単独生成ではなく、全身のヒーロースーツとして先に意匠を決める。

現時点では、基礎スーツを先に派手にしすぎると外装が埋もれます。
外装パーツの下で読ませる細密テクスチャ、外装の縁でつながるライン、発光/差し色の反復を優先してください。

## パーツ分岐・トッピング追加へ向けた最小仕様案

今後は「全パーツ固定」ではなく、基礎スーツの上に外装を分岐・追加できる構造へ寄せます。
まずは次の最小メタデータだけで十分です。

- `part_family`: `helmet`, `chest`, `shoulder`, `arm`, `waist`, `leg`, `boot` などの大分類。
- `variant_key`: 同じfamily内の分岐名。例: `sleek`, `heavy`, `winged`, `tech`, `organic`。
- `topping_slots`: 追加装飾を載せられる位置。例: `crest`, `visor_trim`, `shoulder_fin`, `chest_core`, `belt_buckle`, `shin_spike`。
- `base_motif_link`: そのパーツが基礎スーツ側から受けるべき柄。例: 胸Vライン、肩から腕へ流れるライン、腰ベルトへ入る差し色。
- `conflicts_with`: 同時に載せると破綻するトッピングや大型variant。

Wave 1では実装を増やすより、生成プロンプトとsidecar上の呼び名を揃えることを優先します。
「基礎スーツの柄」と「外装/トッピングの柄」が同じヒーロー文法で接続できれば、後から分岐数を増やせます。

## 現在こちらで確認できていること

- `viewer/assets/armor-parts` には18 moduleが存在する。
- 各moduleに `.glb`, `.modeler.json`, `source/<module>.blend`, `preview/<module>.mesh.json`, preview PNG 4枚、closeup PNG 4枚がある。
- `python tools/validate_armor_parts_intake.py` は `pass`。
- `*.blend1` の混入は見つかっていない。
- Web Forge smokeでは18/18パーツをGLBとして解決し、fallback 0を確認できる。
- `viewer/assets/armor-parts/_masters/full_suit_*.png` が格納済み。
- `docs/armor-part-fit-modeler-requests.before.md` が格納済み。

補足:

- `python tools/audit_armor_part_fit_handoff.py --format json` は `warn` のまま。ただしこれは視覚優先度ガイダンスを残す設計で、bbox自体は全moduleで許容内。
- bboxは18 module x 3 axisで最大絶対値8.9%、平均3.7%。
- VRM実体をBlender 5.1へ取り込む工程はglTF importer側の問題で保留。現時点のfull suit renderは強化プロキシによる検収画像。
- 未達はまだ残る。主な論点は、パーツ間の隙間、箱感、肩/腰/足元の位置、基礎スーツと外装のテクスチャ不一致である。

## Web側で今回対応したこと

Web Forge側では、モデラーさんの納品GLBを見やすくするために表示責務を分離しました。

- 納品GLB本体を主表示にする。
- VRM表面ボディスーツ、外装パーツ、表面/発光ライン、寸法ガイドをレイヤーとして区別する。
- 半透明プロキシ、bbox、検査用ハッチングが主役に見えないように弱める。
- 生成結果パネルがプレビューに被ったり、ウィンドウリサイズで不自然に伸びたりする問題を修正する。
- Web smokeで `previewGlbParts=18`, `previewFallbackParts=0` を確認する。

つまり、今後Webプレビューで見える問題は、なるべく「表示UIのせい」ではなく「モデル/sidecar/寸法の検収論点」として切り分けられる状態に寄せています。

## モデラーさんへお願いしたいこと

最優先は、正面の第一印象で「ヒーロースーツを着ている」と見えることです。
寸法の完全一致より先に、人体への装着感、シルエット、接地、浮きのなさを見ます。

次回からの数値判断は `docs/modeler-new-route-acceptance-spec.md` を基準にします。
bboxは各軸±10%以内を合格目標、±15%超をfailにし、左右ペア差は3%以内にしてください。
特に `back` は `target z=0.1360m`、合格目標 `0.122m-0.150m` とし、側面/3Qで薄い板に見えたら数値が範囲内でも未達とします。
P0 moduleは `variant_key`, `base_motif_link`, 2個以上の `topping_slots` を確認メモまたはsidecar相当のメタデータへ残してください。

P0:

- `chest`: 透明な胴体箱ではなく、胸郭を包む曲面胸装甲にする。
- `back`: 板箱ではなく、肩甲骨から腰へ流れる背面装甲にする。
- `waist`: 浮いた輪ではなく、骨盤へ巻き付くベルトにする。
- `left_shoulder` / `right_shoulder`: 肩球に乗る小物ではなく、三角筋を覆い、胸/背中へ薄く差し込む肩アーマーにする。
- `left_boot` / `right_boot`: Wave 2対象でも、Web第一印象を壊さないよう靴底の接地感を確認する。

P1:

- `left_upperarm` / `right_upperarm`: 棒状プロキシではなく、腕に沿う分割外装にする。
- `left_forearm` / `right_forearm`: 円筒ガイドではなく、手首側へ細くなる前腕装甲にする。
- `left_shin` / `right_shin`: ブーツとの接続が読める下端形状にする。
- `helmet`: バイザー、額、後頭部の外形が仮でも読める状態にする。

## 納品時にほしいもの

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
  textures/
```

追加でほしい全身確認:

```text
viewer/assets/armor-parts/_masters/review_master.blend
viewer/assets/armor-parts/_masters/full_suit_front.png
viewer/assets/armor-parts/_masters/full_suit_side.png
viewer/assets/armor-parts/_masters/full_suit_back.png
viewer/assets/armor-parts/_masters/full_suit_3q.png
viewer/assets/armor-parts/_masters/full_suit_overlay.png
```

`*.blend1` は格納しないでください。

## GLB / sidecarの最低条件

- `modeler.json` に `bbox_m`, `triangle_count`, `material_zones`, `vrm_attachment.primary_bone` がある。
- `material_zones` には最低限 `base_surface` がある。
- 可能であれば `accent`, `emissive`, `trim` を分ける。
- Nanobananaで表面生成するため、UV0が破綻していない。
- 左右ペアは同じ設計思想・同等寸法にする。
- 検査用ボックス、寸法ガイド、仮プロキシが最終GLBの主形状に残らない。

## こちらでの受け入れ手順

納品後、こちらで次を実行します。

```bash
python tools/validate_armor_parts_intake.py
python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
```

その後、Web Forgeで次を見ます。

- 正面でヒーロースーツに見える。
- 側面で胸/背中/腰が人体を包んでいる。
- 肩、腰、足元が浮いていない。
- 半透明プロキシや寸法ガイドが主役に見えない。
- `previewGlbParts` が選択パーツ数と一致し、`previewFallbackParts=0` である。

## 現時点の結論

Web側は、納品GLBを主役にして検収しやすい表示へ寄せました。
Wave 1+で、モデラーさん側の改善結果はローカルrepoへ取り込み済みです。

次のボトルネックはNanobanana本番テクスチャ工程と、Blender 5.1のVRM取り込み問題の解消です。形状については、今後の確認でWebプレビューの第一印象とQuest呼び出し表示を見ながら、P0部位から順に追加調整します。

## Wave 1++後の次Wave方針

Wave 1++の返答は「数値検収が閉じたので完了」ではなく、「次に閉じるべきwarnが明確になった」と読む。
残るwarn 8件は、以下の8作業へ分解して扱う。

| warn | 解釈 | 担当する次Wave |
|---|---|---|
| offset | `offset_m` は見た目を後から合わせるつまみではなく、骨anchorと外装中心の契約値。 | offset/metadata gate |
| metadata | P0のvariant/topping呼称が未固定だと、Web、Nanobanana、Questで同じ部位を別名で扱う。 | offset/metadata gate |
| chest | 胸は寸法内でも箱に見えたらロア負け。 | Web QA |
| back | 背面は薄板に見えたら、側面の装着感が死ぬ。 | Web QA |
| waist | 腰が浮くと、Tポーズ鎧立てではなく検査用パーツ展示に見える。 | Web QA |
| shoulder pair | 肩が小物に見えると、胸/背中/腕の連続性が切れる。 | Web QA |
| shin/boot grounding | 足元の浮きは第一印象を最速で壊す。 | Web QA |
| texture unity | 単色基礎スーツと別モチーフ外装は、変身前の完成ヒーロースーツに見えない。 | Nanobanana texture |

実装順は次の通り。

1. `offset_m` / metadata gateを完了する。
   P0の `primary_bone`, `offset_m`, `rotation_deg`, `variant_key`, `part_family`, `base_motif_link`, `topping_slots`, `conflicts_with` を正本化する。
2. Web QAへ反映する。
   正面、側面、回転で、箱感、浮き、接地、fallback 0、基礎スーツ/外装レイヤーの見え方を確認する。
3. Nanobanana基礎スーツ/外装統一へ進む。
   `unified_design` を先に決め、`base_suit_surface` と `armor_overlay_parts` を同じ特撮ヒーロー文法へ分配する。
4. topping libraryを拡張する。
   親moduleがtoppingなしで合格してから、`crest`, `visor_trim`, `chest_core`, `shoulder_fin`, `belt_buckle`, `shin_spike` を増やす。

この順序はロアと実装の両方で重要。
Webで鎧立てとして成立してからQuestへ呼び出すため、テクスチャやtoppingは「装着される外装」が成立した後に積む。
ここを逆転すると、派手な絵で一瞬テンションは上がるが、Questで呼んだ瞬間に浮きや箱感が戻ってきて、体験の芯が折れる。

## Nanobananaオンリー方針

次のテクスチャ計画はNanobananaオンリーとし、最終成果にfallback assetや単色proxyを混ぜない。
Web上の暫定表示としてのfallbackは許容しても、`final_texture_ready` の根拠にはしない。

プロンプト制約:

- `base_suit_surface` を単色にしない。黒/灰/白の無地下着は禁止。
- `armor_overlay_parts` を基礎スーツから独立した飾りにしない。外装の縁、段差、発光、差し色は基礎スーツのラインを受ける。
- 明るい特撮ヒーロー感を優先する。来場者がWebプレビューで「これを装着する」と理解できる色面、輪郭、発光線にする。
- 暗いSF倉庫、灰色検査proxy、透明bbox、泥っぽい低コントラストはnegativeとして明示する。

この方針で、Web Forgeは「検査用モデル表示」から「変身前に呼び出されたヒーロースーツ確認」へ寄せる。
