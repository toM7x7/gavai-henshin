# Web Hero Armor Stand One-Page Spec

Updated: 2026-04-30

## 目的

Web生成の第一画面は、単なる3Dパーツ表示ではなく「Questで呼び出して装着する前のヒーロースーツ鎧立て」として成立させる。
来場者が4桁コードを受け取る前に、Tポーズの身体へ基礎スーツ、外装シェル、トッピング候補が一体化していることを理解できる状態をゴールにする。

## 体験フロー

1. 入力
   Web Forgeで `守る対象`, `気質`, `身長`, `palette`, `brief`, `selected parts` を受け取る。
   入力は見た目の飾り文ではなく、スーツのモチーフ、色面、外装の方向性、Quest呼び出し時の印象を決める設計データとして扱う。

2. 基礎スーツ
   `base_suit_surface` をVRM表面に貼る完成ボディスーツとして生成する。
   単色インナーは禁止。首、胸、腕、腰、脚、ブーツへ続くラバー/繊維感、細密パネル、発光導線、色面を持たせる。

3. 外装シェル
   `armor_overlay_parts` を基礎スーツ上に装着された硬質装甲として載せる。
   胸、背面、腰、肩、すね、ブーツは身体の前に置いた箱ではなく、VRM表面を包む外装シェルに見せる。
   各外装は `base_motif_link` で基礎スーツの線、色、発光を受ける。

4. トッピング
   toppingは親moduleが成立した後に追加する。
   `crest`, `visor_trim`, `chest_core`, `rib_trim`, `spine_ridge`, `belt_buckle`, `shoulder_fin`, `shin_spike`, `ankle_cuff_trim` などを候補にする。
   toppingは親のlocal slotへ載せ、身体anchorを直接奪わない。

5. Quest呼び出し
   Webは `recall_code` を発行し、Questは `GET /v1/quest/recall/{recallCode}` で同じSuitManifestとasset pointersを読む。
   Quest側では生成し直さず、Webで見た鎧立てと同じ基礎スーツ、外装、emissive maskを呼び出して変身演出へ入る。

## 成立条件

- Web正面で「ヒーロースーツを着たTポーズ」に見える。
- 側面で胸、背面、腰が身体を挟み込む外装に見える。
- 足元が床に接地し、すねとブーツの継ぎ目が読める。
- 基礎スーツが単色下着や未完成地肌に見えない。
- 外装シェルが検査用bbox、透明箱、灰色proxyに見えない。
- `previewGlbParts` が選択parts数と一致し、`previewFallbackParts=0`。
- Quest recallでWeb previewと同じbase/overlay texture pointersを取得できる。

## 現状ギャップ

- Wave 1++で18/18 GLB、fallback 0、bbox failなしまでは到達済み。
- 残るwarnは数値failではなく、ヒーロースーツとしての第一印象の検収枠。
- 背面は寸法内でも薄板に見えると未達。
- 腰と肩は、浮いた輪/肩上の小物に戻ると外装シェル感が崩れる。
- すねとブーツは、接地と継ぎ目が弱いとWeb鎧立ての説得力を失う。
- Nanobanana本番前なので、基礎スーツと外装がまだ別物に見えるリスクがある。
- toppingは名前とslot設計を先に固定しないと、後でUI、prompt、Quest manifestがずれる。

## Wave 2優先順位

1. P0 metadata gate
   `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_shin`, `right_shin` に `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `vrm_attachment`, `texture_zone_notes` を入れる。

2. 背面/腰/肩の外装シェル化
   `back` を肩甲骨から腰へ流れる背面装甲にし、`waist` を骨盤へ巻き付くベルト、肩を胸/背中へ差し込むアーマーとしてWeb QAする。

3. 脚/ブーツの接地
   `left_shin`, `right_shin`, `left_boot`, `right_boot` を優先し、床接地、左右底面差、すね-ブーツのカフ接続を詰める。

4. Nanobanana統一テクスチャ
   `unified_design` から `base_suit_surface` と `armor_overlay_parts` を同時に設計する。
   negative promptには dark, gritty, horror, muddy, single-color underwear, random sci-fi panel noise, gray proxy, transparent guide box を入れる。

5. topping library最小版
   親module合格後、helmet/chest/back/waist/shoulder/shinのslotだけを小さく始める。
   toppingは見た目の盛りではなく、基礎スーツと外装motifを反復する追加装飾として扱う。

## 関連正本

- `docs/base-suit-overlay-contract.md`
- `docs/nanobanana-texture-prompt-contract.md`
- `docs/modeler-wave1pp-practical-handoff.md`
- `docs/modeler-new-route-acceptance-spec.md`
