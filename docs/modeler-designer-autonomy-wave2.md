# Modeler / Designer Autonomy Wave 2

Updated: 2026-04-30

このメモは、Webプレビューが「装着は良くなったが、まだのっぺり見える」という指摘に対するWave 2の設計判断です。目的は、モデラー/デザイナーが自主的に複数案を出せる余白を作りつつ、Web ForgeとQuest recallで同じスーツとして破綻しない固定契約を明確にすることです。

## 1. ロア / 体験目的

Web Forgeは、ユーザーが自分のヒーロースーツを確定する鎧立てです。Questはその同じSuitSpec/manifestを呼び出し、身体へ装着される変身体験として見せます。

そのため、Webで見えるものは単なる3D部品一覧ではなく、「これを自分が着る」と信じられる特撮ヒーロースーツである必要があります。顔、胸、背中、腰、肩、すね、ブーツは、遠目でも同じヒーロー文法に見え、近づくと細部の理由が読める状態を目標にします。

## 2. なぜ細分パーツが必要か

18 canonical moduleだけでは、装着面の成立は確認できても、顔の印象、胸の主役感、腰の変身デバイス感、背面の厚み、ブーツの接地説得力が足りず、Webでは「のっぺり」見えます。

ただし、細分パーツは数の水増しではありません。親moduleの上に載る意味のあるdetail/toppingとして扱います。

- 顔: visor、face plate、crest、耳/後頭部ディテールでキャラクター性を出す。
- 胸: sternum core、rib trim、clavicle shelfで正面の主役を作る。
- 背中: spine ridge、rear core、scapula padで薄板感を消す。
- 腰: belt buckle、side clip、rear claspで「装着された変身ベルト」にする。
- 手足: knuckle、cuff、shin socket、toe/heel/soleで末端の玩具感と接地感を作る。

## 3. モデラーが自由に提案してよい範囲

固定契約を守る限り、各P0部位につき3案程度のvariantを自主提案してよいです。ラフメッシュ、GLB試作、スケッチ、設計メモのどれでも構いません。

- `variant_key`: `heroic`, `sleek`, `heavy`, `tech`, `organic`, `winged` などから派生した部位別案。
- `topping_slots`: `crest`, `visor_trim`, `chest_core`, `rib_trim`, `spine_ridge`, `belt_buckle`, `shoulder_fin`, `shin_spike`, `toe_fin` などの形状案。
- `base_motif_link`: ベーススーツの線、色面、発光導線を外装の縁や段差へどう接続するか。
- 表情付け: 顔の明るさ、守護者感、変身デバイス感、速度感、重量感。
- 意図的な非対称: 片側だけの追加装甲や記章は可。ただし理由、寸法差、`conflicts_with` を明記する。

提案してはいけないもの:

- 親moduleなしでは成立しないtopping。
- body anchorを直接奪うtopping。
- Quest側の再生成、隠し補正、スケール補正を前提にした造形。
- 無意味な細切れ分割、検査用bbox、灰色proxy、単色インナーを最終意匠にする案。

## 4. 固定すべき寸法 / 接続契約

固定するもの:

- canonical module名は18個のまま維持する。
- `variant` は同じcanonical slotの置き換え。`topping` は親moduleのlocal slotに載る追加装飾。
- 既存の `attachment_slot`, `primary_bone`, coordinate frame, meter単位, glTF Y-upを変えない。
- target bboxは原則±10%以内、±15%超はfail領域として扱う。
- 左右ペアは原則3%以内。意図的な非対称は理由と寸法差をmetadataへ書く。
- P0は `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_shin`, `right_shin`, `left_boot`, `right_boot` を優先する。
- P0 metadataは `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `vrm_attachment`, `texture_zone_notes` を揃える。
- material zone名は `base_surface`, `accent`, `emissive`, `trim` を維持する。

toppingは必ず `parent_module`, `topping_slot`, `slot_transform`, `max_bbox_m`, `conflicts_with` を持ちます。親moduleはtoppingなしでもWebで成立していることを前提にします。

## 5. まず依頼するバリエーション候補

| 部位 | 依頼する3案 |
|---|---|
| `helmet` | `heroic_clean_mask`: 明るいvisorと短いcrest / `compound_eye_signal`: 複眼・額シール・耳ポート / `crest_commander`: 高めcrestと顎ガード |
| `chest` | `heroic_v_core`: 中央V core / `rib_wrap_plate`: 左右rib trim強調 / `ceremonial_sternum`: 細い発光線と象徴core |
| `back` | `spine_bus_shell`: spine ridge中心 / `scapula_wrap`: 肩甲骨padとlat return / `compact_rear_core`: 小型rear coreで薄板回避 |
| `waist` | `driver_buckle_low`: 低い変身buckle / `side_clip_runner`: 可動を邪魔しないside clip / `rear_clasp_belt`: 背面claspでbackと接続 |
| `shoulder` | `sleek_cap`: 三角筋を覆う薄いcap / `winged_fin`: 小型finで胸背面へ接続 / `heavy_guard`: bbox内の重量感 |
| `shin/boot` | `runner_shin`: shin-to-bootの流線 / `ankle_driver`: ankle cuffと側面小panel / `grounded_toe`: toe/heel/soleを接地重視 |
| `hands` | `knuckle_glow`: 手甲と発光点 / `cuff_lock`: forearmへつながるcuff / `soft_plate`: 指はベーススーツ、手甲だけ硬質 |

最初の納品では、全案を完成GLBにしなくてよいです。各部位の方向性、slot、bbox感、Web/Questでの見え方が判断できる粒度を優先します。

## 6. Web / Questへの反映手順

1. モデラーはP0部位ごとに3案程度のvariant名、意図、slot、conflict、bbox目安を提出する。
2. 採用候補だけGLB/sidecarへ進める。sidecarには `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with` を入れる。
3. Web Forgeは既存のpreview metadataで `previewVariantKeyCount`, `previewToppingSlotCount`, `previewToppingSlots`, `previewVariantKeys` を確認する。
4. Web QAでは、fallback 0、装着gap、背面厚み、腰浮き、足元接地に加え、顔/胸/背中/腰/肩/脛/ブーツのdetail密度を確認する。
5. Nanobananaでは `unified_design` を先に決め、`base_suit_surface` と `armor_overlay_parts` を同じモチーフで生成する。単色インナー、無関係な装飾、灰色proxy、暗い倉庫SFは避ける。
6. QuestはWebで確定したSuitManifestとasset pointersを呼び出すだけにする。Quest側で別デザイン生成やスケール補正に頼らない。

Wave 2の判断基準は、細部を増やした結果として「装着されたヒーロースーツ」に見えるかです。パーツ数が増えても、親moduleの装着感、ベーススーツとのモチーフ接続、Quest recallの同一性が壊れるなら採用しません。
