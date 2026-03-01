# Priority Backlog (2026-03-01)

このバックログは、既存のRoadmap/Lore方針を維持したまま、直近の実装優先度を明確化するための補助計画です。

## 優先度A: 生成速度の短縮

- [ ] `generate-parts` の並列化（2〜4並列、レート制限に合わせて可変）
- [ ] 差分生成（前回生成との hash 比較で未変更パーツはスキップ）
- [ ] キャッシュ（`model_id + texture_mode + uv_refine + prompt_hash + mesh_hash`）
- [x] 計測基盤（全体時間/パーツ別時間）

完了条件:
- `parts.generation.summary.json` に `total_elapsed_sec` と `part_durations_sec` が出力される
- 将来的に p50/p95 の観測を追加可能な形になっている

## 優先度A: 非表示/視認不良対策（helmet/chest/body全景）

- [ ] 再現条件を固定化（データセット + 手順）
- [ ] 可視化診断オーバーレイ（visible判定, texture_path, mesh bounds）
- [ ] fallback画像の白背景除去ルール（アルファ化 or 明度マスク）
- [ ] カメラ/near/far/露光設定の自動補正

補足:
- 今回は「詰まらない」方針のため、緊急修正ではなく速度改善と同列で管理する

## 優先度A: モデリング品質向上（足・手）

- [ ] `viewer/assets/meshes/*boot*, *hand*` の形状見直し（シルエット優先）
- [ ] 足先/甲/踵、手背/掌のボリューム再配分
- [ ] UV展開の連続性（指示方向の破綻を減らす）
- [ ] Relief適用時の崩れ防止（法線・振幅の部位別上限）

完了条件:
- 足・手で現行比の視認品質改善（スクリーンショット比較）
- UV一致度指標の平均改善

## Lore準拠の継続条件

- [ ] 既存の `suit_id / morphotype_id / approval_id / oath` のルールは維持
- [ ] Industrial hero armor の世界観を崩す変更は禁止
- [ ] 「装着プロトコル体験」を壊すUI変更は禁止

## 次に着手する順序

1. 速度改善（並列化 + 差分生成）
2. 足・手メッシュ品質改善
3. 非表示/視認不良の再現固定と根治対応
