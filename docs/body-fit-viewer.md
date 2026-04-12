# Body Fit Viewer 手順

更新日: 2026-03-28

## 1. 目的

`viewer/body-fit` は、全身プレビュー上で以下を確認するための画面です。

1. body-sim に対する各パーツの追従
2. 部位ごとの fit 調整（scale / offset）
3. VRM 骨格を重ねた配置確認（Attach: BodySim / Hybrid / VRM）
4. Live 入力と VRM 駆動の切り分け確認
5. 接続ブリッジ（隙間可視化）の確認

## 1.1 コード構成

- `viewer/body-fit/viewer.js` は scene / VRM / fit editor / UI 操作のオーケストレーションです。
- `viewer/body-fit/body-fit-live.js` は WebCam / MediaPipe / pose quality 判定の live 入力専用モジュールです。
- live view や camera preset を触る場合は、まず `body-fit-live.js` と `viewer.js` の `Live View` 関連処理を確認してください。

## 2. 起動

推奨:

```powershell
npm run dev
```

代替:

```powershell
python tools/run_henshin.py serve-dashboard --port 8010 --root .
```

開く URL:

- `http://localhost:8010/viewer/body-fit/`

補足:

- 表示が古い場合は `Ctrl + F5` で強制再読込してください。
- 再開ハブは `docs/reentry-hub.md` を参照してください。

## 3. 最短確認フロー

1. `Load` を押して `SuitSpec` と `Body Sim` を読込
2. `Load VRM` を押して `viewer/assets/vrm/default.vrm` を読込
3. `Apply T-Pose` を押して VRM を基準姿勢にそろえる
4. `Auto Fit Armor` か `Auto Fit + Save` を押して鎧サイズを VRM 体型へ補正する
5. `Attach` を押して `Hybrid` か `VRM` に切替
6. `VRM Bones: On` で骨表示
7. 必要に応じて `VRM Anchor Editor` で微調整（`Load Anchor` -> `Apply Anchor`）
8. `Start WebCam` を押して live tracking を開始

補足:

- 原型メッシュの再制作判断は viewer 上の感覚ではなく `authoring-audit` を使って決める
- 詳細は `docs/vrm-first-authoring-plan.md` を参照

## 3.1 再開時の推奨順

1. `Load`
2. `Load VRM`
3. `Apply T-Pose`
4. `Auto Fit + Save`
5. `Attach: Hybrid`
6. `Start WebCam`

この順序で、装着補正と live tracking を混ぜずに切り分けられます。

VRM-first のメッシュ再構築を進めるときは、ここに次を差し込みます。

```powershell
python tools/run_henshin.py authoring-audit --root .
```

この監査結果で `rebuild / tune / keep` を見てから mesh 作業へ入ってください。

## 4. UI Surface

### 4.1 Camera Preset

- `Cam Front`
- `Cam Side`
- `Cam Back`
- `Cam POV`
- `Cam Top`
- `Focus Fit`

### 4.2 Live View

`Live View` セレクタは次の 3 モードです。

- `auto`
  - `Cam Front` では mirror
  - `Cam Back` / `Cam POV` では world
- `mirror`
  - 常に鏡デモ表示
- `world`
  - 常に順転表示

確認基準:

1. `Cam Front` + `Live View auto` で video が mirror
2. `Cam Back` / `Cam POV` + `Live View auto` で video が world
3. `Live View world` は `Cam Front` でも world
4. `Live View mirror` は `Cam Back` / `Cam POV` でも mirror

## 5. 画面メモ（重要）

- `meta.vrm_bone_count > 0` なら骨取得は成功
- `meta.vrm_live_rig_ready=true` なら VRM live 駆動準備は完了
- `meta.vrm_live_driven` は live 入力時に VRM 骨が実際に駆動されているかの指標
- `meta.live_pose_model` は実際に使われている pose model（`full` / `lite`）
- `meta.live_pose_quality` と `meta.live_pose_reliable_joints` で追跡品質を確認
- `meta.live_view_mode` / `meta.live_view_effective` / `meta.live_view_mirrored` で左右反転の実効状態を確認
- `meta.camera_preset` で現在の視点プリセットを確認
- `meta.live_pipeline_error` が空でない場合、WebCam 開始失敗の原因文字列が入る
- `meta.vrm_missing_anchor_parts` が空なら、骨未解決部位はない
- `meta.vrm_resolved_anchors` で、部位 -> 実際に使われた骨名を確認できる
- `meta.vrm_attach_mode` で現在モード（`body` / `hybrid` / `vrm`）を確認できる

## 6. Webcam 追跡が不安定なとき

1. カメラから 1.5m - 2.5m 離れ、上半身または全身が画面内に収まる構図にする
2. 背景と服のコントラストを確保し、逆光を避ける
3. `meta.live_pose_reliable_joints` が 7 未満になっていないか確認する
4. `live_pose_quality=low` のときは前フレーム保持になり、大きな追従更新は止まる
5. まず `Apply T-Pose` -> `Auto Fit + Save` を済ませてから `Start WebCam` を押す

## 7. 既知の改善対象

1. `upperarm / forearm` の骨ロール由来の向き違和感の切り分け
2. `BodySim` と `VRM` の切替時に、部位ごとの初期オフセット最適化をさらに強化
3. live 入力（WebCam / mocopi）の平滑化・遅延メトリクス表示を強化
4. mocopi 統合前に `low confidence` 時の fallback を再確認
