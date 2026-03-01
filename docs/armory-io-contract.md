# Armory Viewer I/O Contract（v0.1）

最終更新: 2026-03-01  
対象: `viewer/body-fit` と `henshin` CLI の連携固定

## 1. 目的

Armory Viewer（現行は Browser 実装）で、`SuitSpec` と `Body Simulation` を読み込んで
「1着を表示し、フレーム追従で再生する」ための入出力契約を固定する。

## 2. 入力アーティファクト

1. `SuitSpec` JSON（例: `examples/suitspec.sample.json`）
2. `Body Simulation` JSON（例: `sessions/body-sim.json`）

生成コマンド:

```powershell
$env:PYTHONPATH="src"
python -m henshin simulate-body --input examples/body_sequence.sample.json --output sessions/body-sim.json
```

既存画像を優先利用してパーツ生成する場合:

```powershell
$env:PYTHONPATH="src"
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --fallback-dir sessions/S-20260228-JBJK/artifacts/parts --prefer-fallback
```

ビューア起動:

```powershell
$env:PYTHONPATH="src"
python -m henshin serve-viewer --port 8000
```

URL:

- `http://localhost:8000/viewer/body-fit/`
- `http://localhost:8000/viewer/body-fit/?suitspec=examples/suitspec.sample.json&sim=sessions/body-sim.json`

## 3. SuitSpec契約（Viewer読込で使う項目）

必須:

1. `modules`（オブジェクト）
2. 各モジュールの `enabled`（bool）
3. 各モジュールの `asset_ref`（文字列, 現行Viewerでは参照のみ）

任意:

1. `modules.<name>.texture_path`
2. `suit_id`, `approval_id`, `palette`, `blueprint`, `emblem`（メタ情報として保持可能）

挙動:

1. `enabled=false` のモジュールは描画しない。
2. `texture_path` があれば `Textures: On` で読み込む。
3. 未知モジュール名は `box` 形状 + `chest_core` 基準でフォールバック描画する。

## 4. Body Simulation契約（`simulate-body` 出力）

トップレベル:

1. `equipped`（bool）
2. `equip_frame`（int）
3. `trigger_joint`（string）
4. `segments`（string配列）
5. `frames`（配列）

`frames[i]`:

1. `index`（int）
2. `dt_sec`（number）
3. `equipped`（bool）
4. `hold_sec`（number）
5. `segments`（オブジェクト）

`frames[i].segments[segment_name]`:

1. `position_x`, `position_y`, `position_z`
2. `rotation_z`
3. `scale_x`, `scale_y`, `scale_z`

単位:

1. 座標は Viewer ワールド空間（`simulate-body` 出力値をそのまま使用）。
2. 回転はラジアン（Z軸回り）。
3. フレーム再生間隔は `dt_sec` を基準にする。

## 5. セグメント->モジュール参照マップ（現行）

1. `helmet/chest/back/waist` -> `chest_core`
2. `left_shoulder/left_upperarm` -> `left_upperarm`
3. `right_shoulder/right_upperarm` -> `right_upperarm`
4. `left_forearm/left_hand` -> `left_forearm`
5. `right_forearm/right_hand` -> `right_forearm`
6. `left_thigh/left_shin/left_boot` -> `left_thigh` or `left_shin`
7. `right_thigh/right_shin/right_boot` -> `right_thigh` or `right_shin`

参照元セグメントが当該フレームに存在しない場合は、そのモジュールを非表示にする。

## 6. パス解決契約

1. `\` は `/` に正規化する。
2. 相対パスはリポジトリルート基準で `/` を付与して解決する。
3. `http://` / `https://` はそのまま利用する。

## 7. エラー契約

1. JSON取得失敗時は `Load failed: Failed to load JSON: ... (HTTP_STATUS)` を表示する。
2. 404時はパス誤りとして扱い、`examples/...` と `sessions/...` の見直しを促す。
3. `frames` が空の場合はエラー終了せず、警告表示で読み込み完了とする。

## 8. 次の拡張ポイント

1. Unity Armory Viewer へ同一契約を移植し、`SuitPackage` ローダー契約へ昇格。
2. `Morphotype` 入力（身長・スケール）を Viewer の体型パラメータへ接続。
3. `Body Simulation` の JSON Schema 化（検証をCLI側で強制）。
