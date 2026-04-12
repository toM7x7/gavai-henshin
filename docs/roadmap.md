# Roadmap（実装ロードマップ）

最終更新: 2026-03-28

## 方針

- Lore は制約として使い、体験面では出しすぎない
- Blueprint を実行単位へ分解し、検証可能な最小ループを先に回す
- `SuitSpec` / `Morphotype` を本線契約として固定し、XR は上位レーンとして切り分ける
- 8thWall は今後も継続評価対象とし、関連機能では毎回判断を記録する

## フェーズ

### Phase 0: Repository Baseline（完了）

- [x] リポジトリ骨格
- [x] Schema / CLI / Test 基盤
- [x] Demo（happy/refused）で成果物保存

### Phase 1: Gate 0 実装固定（完了）

- [x] `SuitSpec` / `Morphotype` の初期契約
- [x] 状態遷移（B -> C -> D -> 蒸着 -> 封印）の機械化
- [x] `SuitID` / `ApprovalID` 運用ポリシー確定
- [x] Armory Viewer I/O 契約の文書化

### Phase 2: 画像生成連携（概ね完了）

- [x] Gemini REST 連携モジュール（CLI 呼び出し）
- [x] `generate-image`
- [x] `generate-parts`
- [x] `generate-parts --texture-mode mesh_uv`
- [x] 失敗時フォールバック（既存画像再利用）の自動化
- [ ] API キー投入後の実画像生成スモークテスト

### Phase 3: Track A 強化（本線）

- [x] 右腕 PoC 装着ロジックの取り込み
- [x] `viewer/body-fit` の全身 fit viewer
- [x] `viewer/suit-dashboard` の部位別 3D カード
- [x] shared armor canon 抽出
- [x] VRM 基準の auto-fit v1 導入
- [x] VRM-first authoring audit（再制作 / 補正 / 維持の切り分け）
- [ ] `body-fit / live tracking` の再安定化
- [ ] `upperarm / forearm` の arm orientation / bone roll 切り分け
- [ ] `mocopi` 統合前の live fallback 仕上げ
- [ ] `helmet / chest / shoulder / back` の module kit 改善
- [ ] Wave 1 mesh re-authoring（chest/back/waist/arms）
- [ ] Wave 2 mesh re-authoring（thigh/shin/boot）
- [ ] Wave 3 mesh re-authoring（helmet/hands）

### Phase 4: Track B 強化（XR / 実機）

- [ ] Unity XR 最小接続（Quest Link）
- [ ] `SuitPackage` 読込口の固定
- [ ] mocopi -> Morphotype 前処理導入
- [ ] MediaPipe / WebCam 結果を body simulation 入力へ接続
- [ ] XR PoC レーンの first scene 実装

### Phase 5: 運用品質

- [ ] CI 拡張（lint / type / schema check）
- [ ] セッション成果物の監査ビューア
- [ ] 展示会運用手順の固定

## Re-entry Priorities（2026-03-28）

1. `viewer/body-fit` baseline repair
2. `front/back/pov` と `mirror/world` の採否確定
3. arm orientation の切り分け
4. `mocopi` 前提の live tracking 安定化
5. Game Studio / XR Blocks 向け XR PoC 導線の整備

## XR Lane Split

- current viewer: fitting truth source
- 8thWall: WebAR / camera runtime 検討
- XR Blocks / Game Studio: headset 向け XR UX の高速 PoC

## Reference Docs

- `docs/reentry-hub.md`
- `docs/body-fit-viewer.md`
- `docs/vrm-first-authoring-plan.md`
- `docs/game-studio-xr-poc-brief.md`
- `docs/8thwall-element-integration.md`
- `docs/priority-backlog.md`

## 8thWall Policy（2026-03-03 以降継続）

- 8thWall is treated as a standing technology option across future development phases.
- For WebAR / camera-pipeline / tracking work, each design pass must include an explicit 8thWall evaluation.
- Current usage: `viewer/body-fit` live input already uses an 8thWall-style camera pipeline module architecture.
- Rule: when specs or implementation are updated, document the 8thWall usage and decision in docs.
