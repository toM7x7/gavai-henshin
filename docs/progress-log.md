# Progress Log（都度更新用）

運用ルール:
- 日付は `YYYY-MM-DD` で記録する
- 1エントリに `実施 / 結果 / 次アクション` を最低1行ずつ書く
- 失敗・保留も記録して判断履歴を残す

---

## 2026-03-01

### 実施
- `docs/id-policy.md` を追加し、`SuitID / ApprovalID / MorphotypeID / SessionID` の発行・採番ルールを固定
- `docs/armory-io-contract.md` を追加し、Armory Viewer連携の入力JSON・座標・エラー契約を固定
- `docs/roadmap.md` の Phase 1 を完了状態へ更新
- `docs/gate0-checklist.md` のID発行関連チェックを更新
- `generate-parts` に `--fallback-dir` / `--prefer-fallback` を追加
- `generate-parts` に `--texture-mode mesh_uv` を追加（メッシュ貼り込み向け）
- 既存資産 `sessions/S-20260228-JBJK/artifacts/parts` を使ってフォールバック生成を実行確認
- `serve-dashboard` コマンドと `viewer/suit-dashboard` UI を追加
- `python -m unittest discover -s tests -v` を実行

### 結果
- Phase 1 の未完了項目だった「IDポリシー確定」「Armory I/O契約化」をドキュメント上で完了
- CLI実装（`ids.py` / `simulate-body`）とViewer読込仕様（`viewer/body-fit`）の間に、参照可能な契約文書を配置
- APIキー未設定時でも、既存パーツ画像から `generate-parts` を完走可能にした
- 部位ごとの個別3D確認と、ダッシュボード上からの生成実行が可能になった
- 単体テスト 27件がすべて成功（`OK`）

### 次アクション
- APIキー投入後の実画像生成スモークテスト
- Track Aの最初のWear Build完走
- SuitSpecテンプレート拡充（最低10パターン）

---

## 2026-02-28

### 実施
- Lore/Blueprintの確認とGate 0下準備ドキュメントを作成
- SuitSpec/Morphotypeの初期Schemaを追加
- リポジトリ基盤（CLI/CI/test/docs）を整備
- Gemini画像生成連携（REST）と `generate-image` コマンドを追加
- ロードマップ文書と進捗ログ文書を分離し、都度更新運用を開始
- `.env` / `.env.example` を追加し、Gemini APIキーのローカル管理を整備
- Geminiキー解決ロジックを `.env` 自動読込対応へ拡張
- `examples/henshin-rightarm-poc` の実装を分析し、右腕ドック装着ロジックを本体に移植
- `simulate-rightarm` CLI とサンプル入力を追加
- 全身セグメント追従 `simulate-body` を追加
- 部位別画像生成 `generate-parts` を追加
- `SuitSpec` のモジュール構成を全身パーツ単位へ拡張
- Browserベースの全身当てはめビューア（`viewer/body-fit`）を追加

### 結果
- `demo`（happy/refused）実行でセッション成果物を保存できる状態
- バリデーションおよびユニットテストが通過
- APIキー未投入でも、連携コードは呼び出し可能な準備段階に到達
- `generate-image` はキー未設定時に明示エラーで停止することを確認
- `.env` を使った運用と環境変数運用の両方に対応
- 右腕装着判定・追従計算をレンダラー非依存で再利用可能な形へ分離完了
- 部位別パーツ単位での画像生成に進める基盤を用意
- 三面図中心から「部位別パーツ生成」への移行路を確立
- 3D当てはめ先行で分割/配置を検証できる運用に移行

### 次アクション
- APIキー投入後の実画像生成スモークテスト
- 生成失敗時フォールバック実装
- Armory Viewer連携I/O仕様の固定

- 2026-03-02: suit-dashboard��UV�W�J�m�F�^�u�ƃ{�f�B�O�i�^�u��ǉ��Bmesh_uv�v�����v�g���ʎw�W�t���ɋ����B
