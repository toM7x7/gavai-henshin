# Body Fit Viewer Webcam 確認手順

## 目的

Webカメラ入力から `BodyTrackingFrame` を生成し、VRM表面点群へ再投影できているかを実機で確認する。

## 起動

```powershell
python tools/run_henshin.py serve-dashboard --port 8010 --root .
```

確認用URL:

```text
http://127.0.0.1:8010/viewer/body-fit/?ui=detail&attach=vrm&fitOverlay=1&surfaceGraph=1&surfaceShell=1&surfaceMounts=1&webcamCheck=1
```

## 画面操作

1. ページを開き、VRM と SuitSpec が読み込まれるまで待つ。
2. `Webカメラ開始` を押す。
3. ブラウザのカメラ許可を許可する。
4. `Webcam確認` パネルを見る。
5. 正面に全身または上半身が入り、明るい状態で腕や体をゆっくり動かす。

## 合格目安

- `入力`: `ON / ... fps / ...` になっている。
- `姿勢`: `joints` が 7 以上、可能なら 12 以上になっている。
- `TrackingFrame`: `webcam / schema 1 / ...` になっている。
- `Surface追従`: `webcam / nodes ... / ... / reproject ON` になっている。
- Surface-first の点群、密着殻、装着点が動きに追従する。
- `meta` の `surface_first.live_reprojected` が `true` になっている。

## 見るべき違和感

- 点群だけ動いて、密着殻や装着点がVRM側に残る。
- `TrackingFrame` が出ているのに `Surface追従` が `vrm` のままになる。
- `joints` が少なく、腕・肩・腰の推定が頻繁に消える。
- テクスチャ由来の色が点群側へ乗らない、または部位分類が明らかにずれる。

## トラブルシュート

- カメラが起動しない場合は、ブラウザのサイト権限でカメラ許可を確認する。
- モデル読込で失敗する場合は、MediaPipe の CDN / モデルファイル取得がネットワークで遮断されていないか確認する。
- `joints` が低い場合は、照明を増やし、背景とのコントラストを上げ、カメラから少し離れる。
- `Surface追従` が `vrm` のままの場合は、`Webカメラ開始` 後に `Surface-first デモ > 再構築` を押す。

## 次の実装判断

実機確認で `TrackingFrame=webcam` と `reproject ON` が安定すれば、次は webcam 点群を fit shell の基準へ昇格する。安定しない場合は、先に骨格推定の平滑化、欠損補完、信頼度ゲートを強化する。
