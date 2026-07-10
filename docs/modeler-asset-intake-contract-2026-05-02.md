# Web/Quest モデラー納品 GLB 入稿契約

Date: 2026-05-02  
Scope: モデラーから受け取った GLB を、既存の Web Forge / Quest 体験へ壊さず入れるための最小契約。

## 基本方針

この契約は「受け取ったモデルを安全に確認する」ためのものです。三面図からの発想や造形判断はモデラー側に残します。一方で、Web/Questに入れる瞬間だけは、既存 runtime の名前、パス、sidecar、GLB形式を厳密に合わせます。

重要な分離:

- 三面図/企画段階: `proposed_variant_key` / `proposed_topping_key` で自由に提案してよい。
- 入稿段階: 既存 `variant_catalog.json` に存在する `variant_key` / `topping_slot` / `choice_key` へマッピング済みのものだけ受領する。
- 検証段階: manifest は受領票であり、runtime を直接 activate しない。

## 許可する module

`helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`, `left_hand`, `right_hand`, `left_thigh`, `right_thigh`, `left_shin`, `right_shin`, `left_boot`, `right_boot`

## 入稿ディレクトリ

Canonical module:

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>.mesh.json
```

Variant:

```text
viewer/assets/armor-parts/<module>/variants/<variant_asset_key>/
  <module>__<variant_asset_key>.glb
  <module>__<variant_asset_key>.modeler.json
  source/<module>__<variant_asset_key>.blend
  preview/<module>__<variant_asset_key>.mesh.json
```

Topping:

```text
viewer/assets/armor-parts/<module>/toppings/<topping_slot>/<choice_key>/
  <module>__<topping_slot>__<choice_key>.glb
  <module>__<topping_slot>__<choice_key>.modeler.json
  source/<module>__<topping_slot>__<choice_key>.blend
  preview/<module>__<topping_slot>__<choice_key>.mesh.json
```

## 必須ファイル

- `.glb`: glTF 2.0 binary。外部依存なしを原則にする。
- `.modeler.json`: GLBと同名の UTF-8 JSON。
- `source/*.blend`: 再書き出し可能な Blender source。`.blend1` はコミット禁止。

人間レビューでは `front`, `side`, `back`, `3q` の画像も必須扱いにします。ただし機械的な入稿ゲートでは、まず GLB / sidecar / source を優先します。

## Sidecar 最小項目

Canonical sidecar:

```json
{
  "contract_version": "modeler-part-sidecar.v1",
  "module": "helmet",
  "bbox_m": {"x": 0.28, "y": 0.35, "z": 0.25},
  "triangle_count": 1000,
  "material_zones": ["base_surface", "accent", "emissive", "trim"],
  "texture_provider_profile": "nano_banana",
  "vrm_attachment": {
    "primary_bone": "head",
    "offset_m": [0.0, 0.02, 0.04],
    "rotation_deg": [0.0, 0.0, 0.0]
  }
}
```

Variant sidecar:

```json
{
  "contract_version": "modeler-part-variant-sidecar.v1",
  "asset_kind": "variant",
  "module": "helmet",
  "variant_key": "helmet:sleek",
  "variant_asset_key": "sleek",
  "source_concept_ids": ["c01"],
  "modeler_notes": "三面図の複眼感を、面分割とvisor trimで再解釈した。",
  "bbox_m": {"x": 0.28, "y": 0.35, "z": 0.25},
  "triangle_count": 1100,
  "material_zones": ["base_surface", "accent", "emissive", "trim"]
}
```

任意だが推奨:

- `interpretation_notes`
- `intentional_deviation_reason`
- `texture_files`
- `reference_pose_checks`
- `review_images`

## 受領 manifest

納品バッチごとに manifest を作ります。サンプル:

`examples/modeler_delivery_manifest.sample.json`

検証:

```bash
python tools/validate_modeler_delivery_manifest.py --manifest examples/modeler_delivery_manifest.sample.json
```

この manifest validator が見ること:

- `contract_version == modeler-delivery-manifest.v1`
- `asset_kind` が `canonical | variant | topping | base_suit_texture | reference`
- path が repo-relative で repository 外へ出ないこと
- `activate_runtime` が `true` ではないこと
- canonical は既存18 moduleのみ
- variant は `variant_key == <module>:<variant_asset_key>`
- topping は `<module>/toppings/<topping_slot>/<choice_key>/...` と一致
- GLB header が glTF 2.0 binary として読めること
- sidecar の `module` / `variant_key` が manifest と矛盾しないこと
- 三面図 `source_concept_ids` と review image の参照が追えること

## 既存選定を壊さないルール

- `variant_catalog.json` の既存順序を変えない。
- `module:base` は canonical GLB に解決する。variants配下へ移さない。
- 新規 variant / topping は、受領直後に catalog へ直書きしない。まず提案、承認、検証の順に進める。
- 左右ペアは原則セットで納品する。
- Webで fallback 表示に落ちたものを成功扱いにしない。
- Questで小さく見える、浮く、骨とズレる場合は runtime scale だけで吸収せず、GLB寸法と sidecar を揃える。

## 既存検証コマンド

構造確認:

```bash
python tools/validate_armor_parts_intake.py --root viewer/assets/armor-parts
```

variant/topping catalog:

```bash
python tools/validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

Web GLB smoke:

```bash
python tools/smoke_web_glb_load.py
```

期待値:

- `previewFallbackParts=0`
- GLB / sidecar / catalog の module と key が一致
- bbox, mirror pair, attachment offset が fail しない

## 失敗時の戻し方

- GLBだけ失敗: 対象 `.glb` のみ直前版へ戻す。
- sidecarだけ失敗: 対象 `.modeler.json` のみ戻す。
- variant/topping表示失敗: 対象 `variants/<asset_key>/` または `toppings/<slot>/<choice_key>/` のみ戻す。
- catalog編集で失敗: catalog を戻し、納品物自体は staging として残す。

戻した後は必ず以下を再実行します。

```bash
python tools/validate_modeler_delivery_manifest.py --manifest <manifest.json>
python tools/validate_armor_parts_intake.py --root viewer/assets/armor-parts
python tools/smoke_web_glb_load.py
```
