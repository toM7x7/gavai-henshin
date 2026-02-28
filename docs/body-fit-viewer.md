# Body Fit Viewer (Exhibition Setup)

展示会で初見の人にも分かりやすく見せるための、最短起動手順と画面説明です。

## 1. 事前データ生成（未生成なら）

```powershell
$env:PYTHONPATH="src"
python -m henshin simulate-body --input examples/body_sequence.sample.json --output sessions/body-sim.json
```

## 2. ビューアー起動

```powershell
$env:PYTHONPATH="src"
python -m henshin serve-viewer --port 8000
```

ブラウザで次を開く:

- `http://localhost:8000/viewer/body-fit/`

補足:

- `r --port 8000` は PowerShell の履歴コマンド解釈になり失敗します。
- 必ず `python -m henshin serve-viewer --port 8000` を使ってください。
- ビューアーは `three.js` をローカル同梱しているため、外部CDN接続なしで動作します。
- 更新後に表示が古い場合は `Ctrl + F5` で強制再読込してください。

## 3. 画面で何が見えているか

右側（3D表示）:

- 色付きブロック: 各装備パーツの仮形状（実寸イメージ確認用）
- 白い輪郭線: パーツ境界を見やすくする補助線
- 床とグリッド: 体勢・高さの把握用

左側（操作パネル）:

- `Load`: SuitSpec と Body Sim を読み込み
- `Play/Pause`: フレーム再生/停止
- `Prev/Next`: 1フレーム移動
- `Textures: On/Off`: 生成画像テクスチャ表示切替
- `Theme: Bright/Dark`: 明暗テーマ切替（展示時は Bright 推奨）
- `Cam Front/Side/Top`: 定点カメラ
- `Auto Fit`: 全身が画面に収まるよう再センタリング

## 4. 404対処（`Failed to load JSON ... (404)`）

1. URLが `http://localhost:8000/viewer/body-fit/` になっているか確認  
2. `examples/suitspec.sample.json` と `sessions/body-sim.json` が存在するか確認  
3. 左パネルのパス入力は、次のような相対パスで指定
   - `examples/suitspec.sample.json`
   - `sessions/body-sim.json`

## 5. 展示会向けおすすめ設定

1. `Theme: Bright`
2. `Textures: Off`（輪郭と構成優先で見せる）
3. `Auto Fit`
4. `Cam Front` で開始、説明時に `Cam Side` / `Cam Top` 切替
