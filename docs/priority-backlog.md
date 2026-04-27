# Priority Backlog (2026-03-01)

このバックログは、既存のRoadmap/Lore方針を維持したまま、直近の実装優先度を明確化するための補助計画です。

## 優先度A: 生成速度の短縮

- [x] `generate-parts` の並列化（2〜4並列、レート制限に合わせて可変）
- [ ] 差分生成（前回生成との hash 比較で未変更パーツはスキップ）
- [x] キャッシュ（`model_id + texture_mode + uv_refine + prompt_hash + mesh_hash`）
- [x] 計測基盤（全体時間/パーツ別時間）
- [x] キャッシュキー安定化（`update_suitspec` の runtime metadata 書き戻しで cache miss しない）
- [x] `max_parallel=0` 入力の防御
- [x] summary順序安定化（並列完了順ではなく requested order で出力）

完了条件:
- `parts.generation.summary.json` に `total_elapsed_sec` と `part_metrics` が出力される
- 将来的に p50/p95 の観測を追加可能な形になっている

2026-04-27 status:
- 波ごとの `ThreadPoolExecutor` 並列実行と per-part cache は実装済み。
- `generation.last_*` / `part_prompts` などの運用メタ情報は cache key から除外済み。
- summary の `generated` / `errors` / `part_metrics` / cache/fallback lists は requested order に正規化済み。
- 未変更パーツを既存 session output のまま明示 skip する「差分生成」は未実装。次の速度改善候補。

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

## 実行レーン（2026-03-01 更新）

`mocopi` 連携は有効だが、優先度は「土台の体品質」を先に置く。

### レーンA: 静的品質（先行）

- [ ] UI文字化け・表示崩れの完全解消（UTF-8統一、凡例文言の監査）
- [ ] 体メッシュ v2（胸・肩・腰・太腿の形状見直し）
- [ ] UV連続性の改善（切れ目方向を設計し、展開図との一致率を向上）
- [ ] パーツ間ブリッジ（接続部）実装と調整UI（厚み・ON/OFF）
- [ ] 接続部KPI測定（gap/penetration の閾値管理）

### レーンB: 動的品質（並行）

- [x] WebCam Pose PoC（MediaPipe → body-fit 反映）
- [ ] Liveトラッキング安定化（平滑化係数・遅延可視化）
- [ ] mocopiアダプタ（mocopi → body-sim互換正規化）
- [ ] 入力ソース切替（sim / webcam / mocopi）と保存可能な検証ログ

## 優先度B: Live入力連携（WebCam / mocopi）

- [ ] `simulate-body` の入力拡張: フレームJSONだけでなくライブ入力ストリームを受ける抽象化レイヤを追加
- [ ] WebCam連携PoC: MediaPipe Poseを `body-sim` 互換フレームへ変換して `body-fit` に流し込む
- [ ] mocopi連携PoC: mocopi出力を同じ `body-sim` 互換に正規化して再利用
- [ ] レイテンシ計測（目標: 150ms未満）と平滑化パラメータのUI化
- [ ] プライバシー/安全ガード（ローカル処理優先、録画オプトイン）

## 保留メモ: VRM骨格ベース案（再開用）

目的:
- 体型差・関節追従の土台を「VRM骨格」に寄せ、アーマー装着品質を上げる

候補タスク:
- [ ] `viewer/body-fit` にVRM読込モード（`three-vrm`）を追加
- [ ] ベース体を単色表示（のっぺらぼう）に固定し、アーマー重畳を確認
- [ ] 主要パーツ（helmet/chest/waist/thigh/hand/foot）の骨追従アタッチを実装
- [ ] 現行メッシュ方式との比較表示（A/B）を用意
- [ ] 入力統合（sim/webcam/mocopi）をVRM骨格へ同一インターフェースで接続
- [ ] VRMモデル利用時のライセンス/利用条件チェック手順を文書化

優先順位:
- 直近は「速度改善・非表示対策・手足形状改善」を優先し、VRMは保留レーンとして並走管理

## VRM実装メモ（2026-03-01 調査反映）

- [x] `three-vrm` 連携のimport経路を `importmap + three/addons` 基準へ統一
- [x] `GLTFLoader + VRMLoaderPlugin` の登録を明示し、失敗時は CDN / unpkg の順でフォールバック
- [x] `VRMUtils.rotateVRM0(vrm)` を読込時に適用（VRM0の向き補正）
- [x] `vrm.update(delta)` をレンダーループに追加（VRMランタイム更新）
- [ ] VRM読込成否を E2E で検証（`body-fit` 画面で `vrm_bone_count > 0` を確認）

注意:
- 旧ローカル `three.module.js` は `REVISION 164` で、現行 `three-vrm` 系と整合しないため利用を避ける
