# Roadmap（実装ロードマップ）

最終更新: 2026-03-01

## 方針
- Loreは制約として使う（体験に露出しすぎない）
- Blueprintを実行単位へ分解して前進する
- 先に検証可能な最小ループを確保し、後で品質を積む

## フェーズ

### Phase 0: Repository Baseline（完了）
- [x] リポジトリ骨格
- [x] Schema / CLI / Test 基盤
- [x] Demo（happy/refused）で成果物保存

### Phase 1: Gate 0 実装固定（完了）
- [x] SuitSpec / Morphotype の初期契約
- [x] 状態遷移（B->C->D->蒸着->封印）の機械化
- [x] SuitID/ApprovalID運用ポリシー確定
- [x] Armory Viewer I/O 契約のドキュメント化

### Phase 2: 画像生成連携（進行中）
- [x] Gemini REST 連携モジュール（CLI呼び出し）
- [x] `generate-image` コマンド
- [x] `generate-parts`（部位別パーツ生成）コマンド
- [x] `generate-parts --texture-mode mesh_uv`（展開図寄りプロンプト）を追加
- [ ] APIキー投入で実画像生成のスモークテスト
- [x] 失敗時フォールバック（既存画像再利用）を自動化

### Phase 3: Track A 強化（次）
- [ ] SuitSpecテンプレート拡充（最低10パターン）
- [ ] モジュールキット設計（helmet/chest/shoulder/back）
- [ ] Blueprint投影モードの実検証（decal/projector/triplanar）
- [x] 右腕PoCの装着ロジックを独立モジュールとして取り込み
- [x] 全身当てはめビューア（検証用）を追加
- [x] スーツ別 生成/確認ダッシュボード（部位個別3Dカード）を追加

### Phase 4: Track B 強化（次）
- [ ] Unity XR プロジェクト最小接続（Quest Link）
- [ ] SuitPackage読込口の固定
- [ ] mocopi -> Morphotype推定の前処理導入
- [ ] MediaPipe/WebCam結果を body シミュレーション入力へ接続

### Phase 5: 運用品質（後半）
- [ ] CI拡張（lint/type/schema check）
- [ ] セッション成果物の監査ビューア
- [ ] 展示会運用手順の固定

## 直近2週間の優先
1. APIキー投入後に `generate-image` の実働確認
2. Track Aの最初のWear Buildを1回完走
3. SuitSpecテンプレート拡充（最低10パターン）

- [ ] Backlog: Blender�A�g�iOBJ/GLTF�G�N�X�|�[�g + UV��C�����[�N�t���[�j�͖{�،�Ɏ��{
