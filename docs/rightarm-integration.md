# Right-Arm PoC 参照統合メモ

更新日: 2026-02-28
参照元: `examples/henshin-rightarm-poc`

## 1. 抽出した要点

PoCから有効だった実装要素:
- 右腕3点ランドマーク（肩/肘/手首）中心で最小追従を成立
- ドック（リング）侵入 + ホールド時間で装着トリガー
- 装着後は肘->手首ベクトルでガントレットTransformを更新
- 生成画像はテクスチャとして適用し、PoC段階は擬似ディスプレイスで十分

## 2. 現行リポジトリへの取り込み

実装済み:
- `src/henshin/rightarm.py`
  - `norm_to_world`: 正規化座標 -> ワールド座標変換
  - `DockCharger`: 装着チャージ判定
  - `ArmFollower`: 前腕追従Transform計算
  - `run_rightarm_sequence`: フレーム列シミュレーション
- `henshin simulate-rightarm` CLI
- `examples/rightarm_sequence.sample.json` サンプル入力
- `src/henshin/bodyfit.py`
  - 右腕に限定しない全身セグメント追従へ汎化
- `henshin simulate-body` CLI
- `examples/body_sequence.sample.json` サンプル入力

## 3. 実行例

```powershell
$env:PYTHONPATH="src"
python -m henshin simulate-rightarm --input examples/rightarm_sequence.sample.json --output sessions/rightarm-sim.json
python -m henshin simulate-body --input examples/body_sequence.sample.json --output sessions/body-sim.json
```

出力:
- `equip_frame`: 何フレーム目で装着成立したか
- 各フレームの `transform/segments`: Armory/XR連携に流せる値

## 4. 次に接続する先

1. Armory Viewer:
   - `transform` を読み込んで右腕モジュールの追従確認に使う
2. WebCam実機:
   - MediaPipe結果を同じフレームJSON形式に変換して `run_rightarm_sequence` へ接続
3. 生成画像:
   - `generate-image` の出力を右腕モジュールテクスチャへ適用
