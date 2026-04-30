# Modeler Wave 1++ Practical Handoff

Updated: 2026-04-30

この資料は、Wave 1++ の取り込み後にモデラーさんへ渡す短い実務ハンドオフです。詳細な数値仕様は `docs/modeler-new-route-acceptance-spec.md`、テクスチャ契約は `docs/nanobanana-texture-prompt-contract.md` を正本にします。

## 現状

Wave 1++ はローカルrepoへ取り込み済みです。

- canonical armor module: 18/18
- Web preview smoke: `previewGlbParts=18`, `previewFallbackParts=0`
- intake: pass
- bbox: failなし
- mirror pair: pass
- P0 metadata: 8 moduleで確認対象

残っている `warn` は、数値不合格ではなく「Webでヒーロースーツとして見えるか」を閉じるための視覚レビュー枠です。特に背面、すね、ブーツ、テクスチャ統一が次の山です。

## P0 Metadata

P0 metadata対象は次の8 moduleです。

- `helmet`
- `chest`
- `back`
- `waist`
- `left_shoulder`
- `right_shoulder`
- `left_shin`
- `right_shin`

各P0 moduleは、少なくとも次の情報をsidecar相当メモまたは納品メモで持たせてください。

| key | 目的 |
|---|---|
| `module` | canonical module名を固定する |
| `part_family` | UI/prompt上の大分類 |
| `variant_key` | 同じfamily内の置き換えvariant名 |
| `base_motif_link` | 基礎スーツ側のどの線、色面、発光ラインへ接続するか |
| `topping_slots` | 後乗せ装飾の取り付けslot |
| `conflicts_with` | 同時選択で干渉するvariant/topping |
| `vrm_attachment` | 骨anchor、offset、rotation |
| `texture_zone_notes` | Nanobananaへ渡すmaterial zone意図 |

最小JSONイメージ:

```json
{
  "module": "chest",
  "part_family": "chest",
  "variant_key": "chest:base",
  "base_motif_link": {"name": "chest_v_stripe", "surface_zone": "emissive"},
  "topping_slots": [
    {
      "topping_slot": "chest_core",
      "slot_transform": {"anchor": [0.0, 0.04, 0.07], "rotation_deg": [0, 0, 0]},
      "max_bbox_m": {"x": 0.14, "y": 0.12, "z": 0.035},
      "conflicts_with": ["rib_trim"],
      "parent_module": "chest"
    }
  ],
  "vrm_attachment": {
    "primary_bone": "upperChest",
    "offset_m": [0.0, 0.012, 0.064],
    "rotation_deg": [0, 0, 0]
  },
  "texture_zone_notes": {
    "base_surface": "main hard armor paint",
    "accent": "edge color continued from base suit",
    "emissive": "V-line glow continuation",
    "trim": "rib and bevel separators"
  }
}
```

## 次に依頼したい順番

1. 背面ユニット
   `back` を薄板ではなく、肩甲骨から腰へ流れる背中装甲として読ませる。側面/3Qで胸と腰をつなぐ厚みが見えること。

2. すね
   `left_shin` / `right_shin` を脚プロキシの筒ではなく、ブーツへ自然につながる下腿装甲にする。下端はブーツカフで受けられる形にする。

3. ブーツ
   `left_boot` / `right_boot` は床面への接地感を優先する。つま先、かかと、足首カフが読め、左右の床面差が目立たないこと。

4. topping library
   親moduleがtoppingなしで成立してから増やす。優先slotは `crest`, `visor_trim`, `chest_core`, `rib_trim`, `spine_ridge`, `rear_core`, `belt_buckle`, `side_clip`, `shoulder_fin`, `edge_trim`, `shin_spike`, `ankle_cuff_trim`。

## Nanobanana方針

テクスチャ生成はNanobananaオンリーで進めます。

- `base_suit_surface` は単色下地ではなく、VRM表面へ貼る完成ボディスーツとして扱う。
- `armor_overlay_parts` は基礎スーツから独立した飾りにしない。外装の縁、段差、差し色、発光線は `base_motif_link` で基礎スーツの意匠につなげる。
- 明るい特撮ヒーロー感を優先する。暗いSF倉庫、灰色proxy、透明bbox、泥っぽい低コントラストはnegativeとして避ける。
- UV0とmaterial zonesは、Nanobanana入力とWeb preview確認に使える状態で残す。

## 納品時に確認したいもの

- P0 metadataを含むsidecar相当メモ
- front / side / back / 3Q preview
- closeup preview
- `base_motif_link` がどの基礎スーツ線へ接続するか分かるメモ
- `topping_slots` の位置が分かるメモまたはannotation

最終判断は「Webで鎧立てとして成立し、Questで4桁コード呼び出ししたときに装着対象として読めるか」で行います。
