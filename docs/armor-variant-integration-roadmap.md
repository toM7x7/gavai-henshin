# Armor Variant Integration Roadmap

Updated: 2026-04-30

このロードマップは、Web/Quest新規路線で「デザイナー/モデラーが複数パーツを自由に作る」運用を、既存のSuitSpec/SuitManifest、Web preview、Nanobanana texture、Quest recallへ接続するための短い実装方針です。

参照元はローカルdocsのみです。主な前提は `docs/base-suit-overlay-contract.md`, `docs/armor-part-variant-taxonomy.md`, `docs/nanobanana-texture-prompt-contract.md`, `docs/web-hero-armor-stand-one-page-spec.md`, `docs/modeler-designer-autonomy-wave2.md`, `docs/modeler-order-sheet-wave2.md`, `docs/modeler-creative-variant-brief-wave2.md` に合わせます。

## 1. 現状

- compatibility surfaceは18個のcanonical moduleで固定されている。`helmet`, `chest`, `back`, `waist`, 左右shoulder/upperarm/forearm/hand/thigh/shin/bootは名前を変えない。
- Web Forgeは `base_suit_surface` と `armor_overlay_parts` の2層で見せる方針になっている。VRMだけの表示は生成スーツとしてvalidにしない。
- Wave 1++は18/18 GLB、fallback 0、bbox failなしの機械的baselineに到達しているが、胸/背中/腰/肩/脚/ブーツの「特撮ヒーロースーツとしての読み」はWave 2の検収対象。
- variant/toppingはまだruntimeの主契約ではなく、modeler sidecar、taxonomy、preview metadataで先に受け止める段階。
- `viewer/assets/armor-parts/variant_catalog.json` は将来の静的taxonomyとして想定され、現在runtimeを直接変えるものではない。

## 2. Wave2で増やす asset/variant/topping の関係

Wave 2では、親moduleを増やすのではなく、18 canonical moduleを親として保ったまま枝を増やします。

| 種別 | 意味 | 接続先 |
| --- | --- | --- |
| asset | canonical moduleのGLB本体。例: `chest`, `back`, `left_boot`。 | `asset_ref`, `attachment_slot`, `vrm_anchor`, material zones |
| variant | 親moduleを同じslot上で差し替える案。例: `chest:v_core`, `back:spine_ridge`。 | `variant_key`, `part_family`, same attachment slot |
| topping | 親moduleのlocal slotへ載る任意追加装飾。例: `crest`, `chest_core`, `belt_buckle`, `shin_spike`。 | `parent_module`, `topping_slot`, `slot_transform`, `max_bbox_m` |

固定ルール:

- variantはcanonical moduleの置換であり、新しいbody anchorを作らない。
- toppingは親moduleが単体合格した後に載せる。親moduleの代替にしない。
- `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `texture_zone_notes` をP0 metadataとして扱う。
- P0はまず `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_shin`, `right_shin`, `left_boot`, `right_boot` を優先する。
- asset pathは将来、`viewer/assets/armor-parts/<module>/variants/<variant_key>/` と `viewer/assets/armor-parts/<parent_module>/toppings/<topping_slot>/<topping_key>/` のように分けるが、SuitManifest上の親IDはcanonical moduleのまま維持する。

## 3. Webプレビューの表示/QA

Web previewは「どの親moduleが出ているか」だけでなく、「どのvariant/topping候補が選ばれているか」をQAできる表示にする。

表示するもの:

- selected canonical parts count and `previewGlbParts`.
- `previewFallbackParts=0`。
- selected `variant_key` per module。
- selected `topping_slot` and topping count per parent。
- `base_motif_link` and material zone notes for P0 parts。
- `conflicts_with` warnings when a selected variant/topping combination is invalid。
- `final_texture_ready`, `model_quality_ready`, `quest_recall_ready` のready flags。

QA観点:

- Web正面で「ヒーロースーツを着たTポーズ」に見える。
- 側面/背面で胸、背中、腰が胴体を挟み込む外装シェルに見える。
- 肩、前腕、脛が小物ではなく身体を覆うshellに見える。
- ブーツは床に接地し、shin-to-bootのカフ/継ぎ目が読める。
- toppingをOFFにしても親moduleが成立する。
- base suitとoverlayの線、色面、emissiveが `base_motif_link` でつながる。

## 4. Nanobananaテクスチャとの関係

Nanobananaは孤立した部品塗りではなく、`unified_design` を先に作り、そこから `base_suit_surface` と `armor_overlay_parts` へ分配する。

接続する入力:

- Web入力: `protect_target`, `temperament`, `height_cm`, `palette`, `brief`, `selected_parts`。
- Modeler metadata: `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `texture_zone_notes`。
- Variant/topping selection: prompt上では装飾量とモチーフ反復の指定として扱う。

出力として必要なもの:

- `base_suit_texture`
- selected overlay partsのtexture pointers
- emissive mask
- material zone map
- manifest linkage
- Quest recall asset pointers

fallback/cache/proxy textureはpreview/recovery用であり、最終Nanobanana生成結果として扱わない。Nanobanana完了前は `final_texture_ready=false` のまま、Webはprovisional previewとして明示する。

## 5. Quest呼び出しへの影響

Questは生成や補正をしない。`GET /v1/quest/recall/{recallCode}` でWeb側が保存したSuitManifestとasset pointersを読み、同じスーツをユーザー中心の変身体験へ読み込む。

必要なmanifest情報:

- `visual_layers.contract_version = base-suit-overlay.v1`
- `base_suit_surface` のVRM/body-surface asset and texture pointers
- `armor_overlay_parts` のselected canonical modules
- moduleごとの selected `variant_key`
- selected toppings and local slot data
- overlay texture pointers and emissive masks
- `conflicts_with` 解決済みであることを示すQA result

Quest側の扱い:

- variant未指定ならcanonical defaultを読む。
- topping未指定なら親moduleだけで変身演出する。
- manifestが未準備なら「manifest not ready」として止める。
- Nanobananaが後から完了した場合、recall responseは最新のtexture pointersを反映する。
- Quest側でスケール補正や別デザイン生成に頼らない。

## 6. 直近3ステップ

1. Metadata intakeを固める。
   P0 moduleの `.modeler.json` またはsidecar相当メモに `part_family`, `variant_key`, `base_motif_link`, `topping_slots`, `conflicts_with`, `texture_zone_notes`, `vrm_attachment` を揃える。`variant_catalog.json` はslot名、max bbox、material zone、例示variantの静的参照元として扱う。

2. Web preview QAへvariant/toppingを出す。
   Web preview metadataに selected variant count、selected topping slot count、conflict warnings、ready flagsを表示し、front/side/back/3QのQAで胸/背中/腰/肩/脛/ブーツの読みを確認する。toppingのON/OFFで親moduleが成立することも確認する。

3. NanobananaとQuest recallへlinkageを渡す。
   `unified_design` promptへmodeler metadataを入れ、生成後のtexture pointers、emissive masks、material zone mapsをSuitSpec/SuitManifestへ書き戻す。Quest recallは同じmanifestからbase suit、overlay variants、selected toppingsを読み、Quest側では再生成しない。
