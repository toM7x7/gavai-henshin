# Body Fit Viewer 手順

更新日: 2026-03-03

## 1. 目的

`viewer/body-fit` は、全身プレビュー上で以下を確認するための画面です。

1. body-sim に対する各パーツの追従
2. 部位ごとの fit 調整（scale / offset）
3. VRM 骨格を重ねた配置確認（Attach: BodySim / Hybrid / VRM）
4. 接続ブリッジ（隙間可視化）の確認

## 1.1 コード構成

- `viewer/body-fit/viewer.js` は scene / VRM / fit editor / UI 操作のオーケストレーションです。
- `viewer/body-fit/body-fit-live.js` は WebCam / MediaPipe / pose quality 判定の live 入力専用モジュールです。
- 今後の追加改修で live 系を触る場合は、まず `body-fit-live.js` を確認してください。

## 2. 起動

```powershell
$env:PYTHONPATH="src"
python -m henshin serve-dashboard --port 8010 --root .
```

開くURL:

- `http://localhost:8010/viewer/body-fit/`

補足:

- `--port` は値を1つ取ります。正しくは `--port 8010` です。
- `--port8010` や改行で分断された `--port` はエラーになります。
- 更新後に表示が古い場合は `Ctrl + F5` で強制再読込してください。

## 3. 最短確認フロー

1. `Load` を押して `suitspec` と `sim` を読込
2. `Load VRM` を押して `viewer/assets/vrm/default.vrm` を読込
3. `Apply T-Pose` を押してVRMを基準姿勢にそろえる
4. `Auto Fit Armor` を押して鎧サイズをVRM体型へ自動補正する
   - この操作で `chest/腕` を中心に `vrm_anchor` の offset/rotation も自動キャリブレーションされます
5. `Attach` を押して `Hybrid` か `VRM` に切替
6. `VRM Bones: On` で骨表示
7. 必要に応じて `VRM Anchor Editor` で微調整（`Load Anchor` -> `Apply Anchor`）
8. `Save SuitSpec` で永続化

## 3.1 VRM単体の確認（推奨）

1. `Armor: Off` にして鎧表示を隠す
2. `Focus VRM` でカメラをVRMに合わせる
3. `VRM Idle: On` で待機モーション（軽い揺れ）を確認
4. 必要に応じて `VRM Idle Amount / Speed` を調整

## 4. 画面メモ（重要）

- `meta` に `vrm_bone_count > 0` が出ていれば、骨取得は成功です。
- `meta` に `vrm_live_rig_ready=true` が出ていれば、VRMライブ駆動の準備は完了です。
- `meta` の `vrm_live_driven` は、ライブ入力時にVRM骨が実際に駆動されているかの指標です。
- `meta` の `live_pose_model` は実際に使われているPoseモデル（`full`/`lite`）です。
- `meta` の `live_pose_quality` と `live_pose_reliable_joints` で、追跡品質の健全性を確認できます。
- `live_pose_quality=low` は「有効関節が不足」または「胴体4点(左右肩・左右腰)が欠けた」状態です。
- `live_pose_quality=missing` は「landmark未検出」です。
- `meta.live_pipeline_error` が空でない場合、WebCam開始失敗の原因文字列が入ります。
- `meta` の `vrm_missing_anchor_parts` が空なら、骨未解決部位はありません。
- `meta` の `vrm_resolved_anchors` で、部位 -> 実際に使われた骨名を確認できます。
- `meta` の `vrm_attach_mode` で現在モード（`body`/`hybrid`/`vrm`）を確認できます。
- `attachment_slot` が設定されている部位は、そのスロット基準で骨マッチします。
- `meta` の `three_revision` / `three_target` で three.js 実行系を確認できます。
- `Bridges` は部位間ギャップの可視化です。

## 5. 404/読込失敗の対処

1. URLが `http://localhost:8010/viewer/body-fit/` か確認
2. `suitspec` / `sim` / `vrm` の相対パスを確認
   - `examples/suitspec.sample.json`
   - `sessions/body-sim.json`
   - `viewer/assets/vrm/default.vrm`
3. `Load` → `Load VRM` の順で再実行

## 6. 既知の改善対象

1. `helmet/chest` の当たり精度をさらに上げる
2. `BodySim` と `VRM` の切替時に、部位ごとの初期オフセット最適化を追加
3. Live入力（WebCam / mocopi）の平滑化・遅延メトリクス表示を強化

## 7. Webcam追跡が不安定なとき

1. カメラから 1.5m - 2.5m 離れ、全身が画面内に収まる構図にする
2. 背景と服のコントラストを確保し、逆光を避ける
3. `meta` の `live_pose_reliable_joints` が 7 未満になっていないか確認する
4. `Live` ステータスが `low confidence` のときは、前フレーム保持になるため大きな追従更新は止まる
5. 初期姿勢は一度 `Apply T-Pose` -> `Auto Fit Armor` を行ってから `Start WebCam` を押す
