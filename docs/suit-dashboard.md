# Suit Dashboard 手順

更新日: 2026-03-01

## 1. 目的

`viewer/suit-dashboard` は次を1画面で行うためのUIです。

1. スーツ（SuitSpec）選択
2. 部位別パーツ画像の生成実行（CLI API経由）
3. 各部位を個別3Dで立体確認
4. Body Fit Viewer へ遷移して全身確認

## 2. 起動

```powershell
$env:PYTHONPATH="src"
python -m henshin serve-dashboard --port 8010 --root .
```

開くURL:

- `http://localhost:8010/viewer/suit-dashboard/`

## 3. 基本フロー

1. `SuitSpec` を選び `読込`
2. `生成モード` を選ぶ
   - `mesh_uv`: 展開図寄り（メッシュ貼り込み向け）
   - `concept`: 単体イメージ寄り
3. `Fallback Dir` を指定（既存画像活用時）
4. 対象パーツを選択して `生成実行`
5. 右側カードで各部位を個別3D確認
6. 必要に応じて `Body Fit` 側で全身調整（既定で Attach=Hybrid）
7. VRM配置パネルで `attachment_slot` と `vrm_anchor` を保存して整合性を固定

## 4. 推奨設定（既存画像活用）

1. `Fallback Dir`: `sessions/S-20260228-JBJK/artifacts/parts`
2. `既存画像優先`: ON
3. `SuitSpecへ反映`: ON
4. `生成モード`: `mesh_uv`

## 5. UV/3D確認の見方

1. パーツカードの `3D` タブで形状確認
2. `UV` タブで展開図との整合を確認
3. coverage 指標（UV被覆率など）を見て再生成判断

## 6. 補足

1. ダッシュボード生成は内部で `python -m henshin generate-parts` を呼び出します。
2. APIキー未設定でも `fallback-dir` があれば生成を継続できます。
3. 本実装は「部位別確認最適化」が目的で、最終メッシュ（GLB/FBX）統合は次フェーズです。

## 7. 2026-03-01 反映済み

- 白背景ベースの見た目に統一
- パーツカードに 3D / UV タブを追加
- UV指標（被覆率など）を表示
- 全身タブにボディ前景プレビューを追加
- `prefer fallback` 初期値を OFF に変更
- `uv_refine` 二段階生成（コンセプト参照付きUV再構築）を追加
- プロンプト確認UI（SuitSpec/実行時）を追加
- DoubleSide とライティング調整で視認性を改善
