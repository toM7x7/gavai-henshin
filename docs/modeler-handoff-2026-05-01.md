# Modeler Handoff — Wave 2 Smoke (2026-05-01)

宛先: エンジニアリング側
担当モデラー: Claude (worktree: `claude/jovial-cohen-4bf60f`)
Blender: `Blender 5.1.1 (hash b70da489d7f4)` at `C:\Program Files\Blender Foundation\Blender 5.1\blender.exe`
リポジトリ: `C:\dev\codex\gavai-henshin\.claude\worktrees\jovial-cohen-4bf60f`

`docs/modeler-blender-wave2-operation-guide.md` の手順を全部走らせた結果と納品物のレポートです。

## 1. 実行したコマンド

事前 (Blender 不要):

```powershell
cd C:\dev\codex\gavai-henshin\.claude\worktrees\jovial-cohen-4bf60f
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
python tools\blender\run_variant_pipeline.py validate
python tools\blender\run_variant_pipeline.py dry-run --kind all
```

スモーク (Blender CLI):

```powershell
$BLENDER = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

# Step 1 — variant スモーク
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- `
    build-variant --module helmet --variant-key helmet:sleek

# Step 2 — topping スモーク
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- `
    build-topping --parent-module helmet --topping-slot crest --topping-key base

# Step 5 — P0 全バッチ (smoke 通過後)
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- `
    build-p0 --kind all --topping-key base
```

## 2. 最終 JSON 出力

### 2.1 helmet:sleek (variant)

```json
{
  "asset_kind": "variant",
  "ok": true,
  "paths": {
    "glb": "viewer/assets/armor-parts/helmet/variants/sleek/helmet__sleek.glb",
    "blend": "viewer/assets/armor-parts/helmet/variants/sleek/source/helmet__sleek.blend",
    "sidecar": "viewer/assets/armor-parts/helmet/variants/sleek/helmet__sleek.modeler.json",
    "preview_mesh": "viewer/assets/armor-parts/helmet/variants/sleek/preview/helmet__sleek.mesh.json"
  },
  "dims": { "x": 0.27989, "y": 0.25399, "z": 0.34960 },
  "triangles": 1100,
  "materials": ["armor_base_surface", "armor_emissive", "armor_accent", "armor_trim"],
  "warnings": [],
  "errors": [],
  "module": "helmet",
  "variant_key": "helmet:sleek",
  "variant_asset_key": "sleek"
}
```

ログ:
```
INFO Draco mesh compression is available, ...
10:56:57 | INFO: Starting glTF 2.0 export
10:56:57 | INFO: Extracting primitive: armor_helmet__sleek_v001
10:56:57 | INFO: Primitives created: 4
10:56:57 | INFO: Finished glTF 2.0 export in 0.05271s
情報: コピーを「helmet__sleek.blend」で保存しました
```

### 2.2 helmet / crest / base (topping)

```json
{
  "asset_kind": "topping",
  "ok": true,
  "paths": {
    "glb": "viewer/assets/armor-parts/helmet/toppings/crest/base/helmet__crest__base.glb",
    "blend": "viewer/assets/armor-parts/helmet/toppings/crest/base/source/helmet__crest__base.blend",
    "sidecar": "viewer/assets/armor-parts/helmet/toppings/crest/base/helmet__crest__base.modeler.json",
    "preview_mesh": "viewer/assets/armor-parts/helmet/toppings/crest/base/preview/helmet__crest__base.mesh.json"
  },
  "dims": { "x": 0.02480, "y": 0.09357, "z": 0.05580 },
  "triangles": 108,
  "materials": ["armor_trim"],
  "warnings": [],
  "errors": [],
  "parent_module": "helmet",
  "topping_slot": "crest",
  "topping_key": "base"
}
```

ログ:
```
警告: 統合するメッシュデータがありません   ← 単一panelの topping のため対象なし。無害。
INFO Draco mesh compression is available, ...
10:57:17 | INFO: Starting glTF 2.0 export
10:57:17 | INFO: Extracting primitive: armor_helmet__crest__base_v001
10:57:17 | INFO: Primitives created: 1
10:57:17 | INFO: Finished glTF 2.0 export in 0.05131s
情報: コピーを「helmet__crest__base.blend」で保存しました
```

## 3. 生成されたディレクトリ

### 3.1 variant: `viewer/assets/armor-parts/helmet/variants/sleek/`

```
helmet__sleek.glb            84564 bytes
helmet__sleek.modeler.json    1519 bytes
preview/helmet__sleek.mesh.json   571982 bytes
source/helmet__sleek.blend       116701 bytes
```

### 3.2 topping: `viewer/assets/armor-parts/helmet/toppings/crest/base/`

```
helmet__crest__base.glb            8836 bytes
helmet__crest__base.modeler.json   1509 bytes
preview/helmet__crest__base.mesh.json   56305 bytes
source/helmet__crest__base.blend       94515 bytes
```

### 3.3 P0 バッチ全体集計 (Step 5)

- variants: 54 GLB (`viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.glb`)
- toppings: 32 GLB (`viewer/assets/armor-parts/<parent>/toppings/<slot>/<key>/<parent>__<slot>__<key>.glb`)

`build-p0 --kind all --topping-key base` 実行時、stdout に各成果物の `"ok": true` が並びました（PowerShell 出力長制限のため抜粋）。

## 4. スクリーンショット

すべて `docs/_smoke_renders/` に出力。EEVEE / 1024×1024 / 50mm。

| 用途 | ファイル |
|---|---|
| helmet:sleek 正面 (装着・接近) | `docs/_smoke_renders/helmet_sleek_front.png` |
| helmet:sleek 側面 (装着・接近) | `docs/_smoke_renders/helmet_sleek_side.png` |
| chest + back 装着 (3Q) | `docs/_smoke_renders/chest_back_3q.png` |
| chest + back 装着 (側面) | `docs/_smoke_renders/chest_back_side.png` |
| chest + back 装着 (正面) | `docs/_smoke_renders/chest_back_front.png` |
| 全 P0 スーツ 正面 | `viewer/assets/armor-parts/_masters/full_suit_front.png` |
| 全 P0 スーツ 側面 | `viewer/assets/armor-parts/_masters/full_suit_side.png` |
| 全 P0 スーツ 背面 | `viewer/assets/armor-parts/_masters/full_suit_back.png` |
| 全 P0 スーツ 3Q | `viewer/assets/armor-parts/_masters/full_suit_3q.png` |

helmet 装着画像は手順書の「helmet variant front/side」要件、chest_back_* と full_suit_* は「chest + back on body」「full P0 suit front/side/back」要件にそれぞれ対応します。

## 5. 手で行った Blender 編集

**今回はゼロです。**

- メッシュをいじっていない (`build-variant` / `build-topping` / `build-p0` の手続き的出力のみ)
- マテリアル名や zone を書き換えていない
- 寸法、anchor、rotation を Blender 側で動かしていない
- `.blend` のシーン構成を上書きしていない (sandbox 経由の `read_factory_settings` が使えなかったので、master の `review_master.blend` を開いてレビュー描画だけ行った。生成 `.blend` には触っていない)

レンダリング用に `viewer/assets/armor-parts/_masters/review_master.blend` を一時的に開いて GLB をインポートしましたが、master 自体は保存していません。

## 6. 手順書 Step 6 — Post-Build Checks

```text
$ python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots
[PASS] viewer\assets\armor-parts\variant_catalog.json   18/18

$ python tools\blender\run_variant_pipeline.py validate
ok=True  variants=38  slots=55  errors=0  warnings=55  (slot_transform inferred の情報のみ)

$ python tools\validate_armor_parts_intake.py
INTAKE: status=warn  reasons=0  warnings=6
   → 既知の Wave 2.1 形状リファインメント警告 (chest z, waist x,
     left/right_upperarm x, left/right_shin x). 手順書の許容範囲。

$ python tools\smoke_web_glb_load.py
previewGlbParts=18  previewFallbackParts=0

$ python -m pytest tests\test_armor_part_variant_catalog.py `
                  tests\test_validate_variant_catalog.py `
                  tests\test_variant_topping_intake.py -q
15 passed in 0.11s
```

## 7. ランタイム契約 — 維持確認

手順書の "Runtime Contract To Preserve" 項目を一通り確認。

- canonical 18 module 名: 変更なし
- variant sidecar に必須キー: `contract_version=modeler-part-variant-sidecar.v1`, `asset_kind=variant`, `module`, `variant_key`, `base_motif_link`, `bbox_m`, `triangle_count`, `material_zones`, `coordinate_frame` 揃い済 (sidecar JSON 添付参照)
- topping sidecar に必須キー: `contract_version=modeler-topping-sidecar.v1`, `asset_kind=topping`, `parent_module`, `topping_slot`, `topping_key`, `slot_transform`, `max_bbox_m`, `conflicts_with`, `bbox_m`, `triangle_count`, `material_zones`, `coordinate_frame` 揃い済
- canonical part sidecar の `vrm_attachment`, `attachment_offset_target_m`, `qa_self_report`, `topping_slots`, `texture_zone_notes`, `conflicts_with`: 維持 (canonical 18 を `tools/blender/_run_canonical_build.py` 経由で再ビルドし反映済)

## 8. 次のお願い

エンジニアリング側で Web Forge の variant 選択 UI を立ち上げる際は、次を入口にしてください:

- `armor_glb_asset_ref(module, repo_root)` (`src/henshin/forge.py`)
  → `viewer/assets/armor-parts/<module>/variants/<asset_key>/<module>__<asset_key>.glb` への分岐を足せる
- `tools/smoke_web_glb_load.py`
  → `selected_variant_key` 列を追加する余地あり
- variant_key 命名は `<module>:<asset_key>` (例: `helmet:sleek`). フォルダ slug は `<asset_key>` のみ (Windows path に `:` を入れない)

何か追加スモーク (例: `chest:bold`, `back:rear_core`, `waist/belt_buckle/base` 等) が必要なら同じコマンド形でお知らせください。すぐ走ります。

— モデラーより
