# Execution Plan (2026-03-01)

## 目的

- 体に沿う装着品質を上げる
- 生成待ち時間を短縮する
- Live入力（WebCam / mocopi）へ段階的に接続する

## 現在地（完了）

1. `body-fit` に VRM 読込・骨表示・Attach切替を実装
2. three-vrm 読込経路を安定化（importmap + runtime更新）
3. VRMローダ責務を `vrm-loader.js` に分離（保守性改善）

## 進行状況（本ターン）

1. `helmet/chest` 対策として、部位別の骨フォールバック解決を追加
2. `meta` / 凡例に `missing anchor` 情報を追加して診断性を向上
3. `body-fit` / `suit-dashboard` 手順書を現行コマンドに更新
4. `body-fit` に `VRM Anchor Editor` を追加（全身プレビューで直接調整可能）
5. `attachment_slot` ベースの部位整合処理と Attach 3モード（BodySim/Hybrid/VRM）を追加
6. `body-fit` に VRM単体確認導線（Armor Off / Focus VRM / Idle motion）を追加

## フェーズA: 装着品質の安定化（最優先）

### A-1. 部位ごとの初期anchor最適化

- 対象: `helmet/chest/back/waist/thigh/boot/hand`
- 作業:
  1. `vrm_anchor` の基準値を部位別に見直し
  2. BodySim / VRM 切替時の差分を縮小
  3. `helmet/chest` の見切れ再発を抑制
- 完了条件:
  - `body-fit` で全対象部位が可視
  - `Attach: VRM` / `Attach: Hybrid` 時に大きな飛び・回転破綻がない

### A-2. フィッティング操作性の改善

- 作業:
  1. Fit編集の適用速度を改善（即時反映の安定化）
  2. 推奨値（Suggest）のロジックを部位別に調整
- 完了条件:
  - 操作後 1 秒以内に視覚反映
  - `fit_score` の平均改善

## フェーズB: 生成速度短縮

### B-1. 生成ジョブ最適化

- 作業:
  1. `generate-parts` の並列化
  2. 差分生成（未変更部位スキップ）
  3. キャッシュキーの厳密化
- 完了条件:
  - 現状比で p50 時間を短縮
  - summary にパーツ別時間とキャッシュヒット率を出力

### B-2. UI 側の待ち時間体験改善

- 作業:
  1. 進捗表示の粒度を上げる（部位単位）
  2. 実行中のキャンセル/再試行導線
- 完了条件:
  - 「待ちっぱなし」状態を解消

## フェーズC: トラッキング統合

### C-1. WebCam 安定化

- 作業:
  1. 平滑化係数と遅延表示
  2. 入力品質（検出欠落）時のフォールバック

### C-2. mocopi アダプタ

- 作業:
  1. mocopi出力を body-sim 互換へ正規化
  2. 入力ソース切替（sim / webcam / mocopi）
- 完了条件:
  - 1画面で入力源切替しつつ再生可能

## フェーズD: モデル品質（中期）

- 作業:
  1. 足・手メッシュ形状の精度改善
  2. UV連続性改善
  3. 将来の Blender ラウンドトリップ導入準備
- 完了条件:
  - 足・手の違和感低減
  - UV破綻の再発抑制

## 直近の実行順（この後）

1. フェーズA-1: `helmet/chest` anchor再調整
2. フェーズA-2: Fit Suggest の部位別補正
3. フェーズB-1: 並列化 + 差分生成
4. フェーズC-1: Live 安定化
