# Henshin Trial Platform Docs Bundle v0.2 (GCP方針)

用途: 別アプリのAI / エンジニア / PM が同じ前提で議論・実装するための基準文書群  
更新日: 2026-04-23  
前提: **GCPを主軸にした構成**で進める。Replayは**Quest内が主**。

---

## この版の結論

本プロジェクトは以下の構成で進める。

- **Web**: React + PlayCanvas + Firebase Hosting
- **Auth**: Firebase Authentication
- **API**: Hono on Cloud Run
- **Canonical DB**: Cloud SQL for PostgreSQL
- **Live State / Operator Monitor**: Cloud Firestore
- **Asset Storage**: Google Cloud Storage
- **Async Jobs**: Cloud Tasks
- **AI**: Vertex AI (Gemini text / image)
- **Secrets**: Secret Manager
- **Quest**: Unity + OpenXR + Meta Quest Support
- **3D制作**: Blender + Blender Python API
- **AI開発補助**: Firebase MCP server（必要に応じて）

---

## この構成の考え方

### 採用したい思想
- Webで**スーツを成立**させる
- Questで**変身試験とReplay**を成立させる
- Browser-side compose/export の良さは残す
- ただしバックエンドは GCP/Firebase に寄せて、AI実行・認証・監視・非同期処理を強くする

### 何を正本にするか
- 正本は **SuitManifest**
- GLB は副生成物（確認 / 共有 / デバッグ用）

### 何をAIにやらせるか
- Emotion / Context の構造化
- DesignVector 生成
- PartPlan（YAML/JSON）提案
- Blueprint / Emblem 生成
- 実装ドキュメント・テストケース・APIドラフト作成

### 何をAIにやらせすぎないか
- 毎回完全新規の本番3Dモデル自動生成
- Quest本編のロジック全生成
- 実在カタログを無視した自由構成

---

## ファイル一覧

1. `01_アーキテクチャ決定メモ_GCP.md`
   - GCP方針の決定理由
   - 他案との違い
   - サービス責務の切り方

2. `02_定義書_GCP.md`
   - プロダクト定義
   - 用語定義
   - 体験定義
   - スコープ定義

3. `03_仕様書_GCP.md`
   - システム構成
   - サービス仕様
   - API責務
   - Quest / Web / Replay 仕様

4. `04_データ契約_GCP.md`
   - SuitManifest
   - EmotionProfile
   - DesignVector
   - PartPlan
   - TransformSession
   - Firestore / Cloud SQL データ配置

5. `05_進捗差分とロードマップ_GCP.md`
   - 現在地
   - 既決事項 / 未決事項
   - Phase別ロードマップ
   - 直近の意思決定項目

6. `06_AI実行指示書_GCP.md`
   - 別AIへ渡す実行指示
   - Stream別プロンプト
   - 出力フォーマット固定
   - 優先順位と受け入れ条件

---

## まず読む順番

### PM / あなた
1. `01_アーキテクチャ決定メモ_GCP.md`
2. `02_定義書_GCP.md`
3. `05_進捗差分とロードマップ_GCP.md`

### Web / Backend エンジニア
1. `03_仕様書_GCP.md`
2. `04_データ契約_GCP.md`
3. `05_進捗差分とロードマップ_GCP.md`

### XRエンジニア
1. `03_仕様書_GCP.md`
2. `04_データ契約_GCP.md`
3. `05_進捗差分とロードマップ_GCP.md`

### 別AIに投げるとき
1. `02_定義書_GCP.md`
2. `04_データ契約_GCP.md`
3. `06_AI実行指示書_GCP.md`

---

## 直近の最重要アウトプット

この版を踏まえて、次に固定するべきものは以下。

1. `SuitManifest` 初版確定
2. `PartCatalog` 初版確定
3. `TransformStateMachine` 初版確定
4. Firestore に置くライブ状態の最小定義
5. Cloud SQL に置く canonical schema の最小定義
6. AI出力の YAML / JSON 形式の固定

---

## ドキュメントの使い方

- この束は **仕様そのもの** であり、議事メモではない
- 曖昧な箇所は TODO / ASSUMPTION / RISK として明示する
- 仕様更新時は **v0.2.x** のように版管理する
- 各AIの出力はこの束に**上書きではなく差分提案**として返させる


---

## 混合チーム向けの補助文書（追加）

7. `07_混合チーム運用ガイド.md`
   - PM / エンジニア / AI の役割整理
   - 会話レイヤーの分離
   - 危険信号と対策

8. `08_リスク・壁・打ち手管理表.md`
   - 次の一手
   - 現在の壁
   - 優先順位付き打ち手

9. `09_意思決定ログと会議設計.md`
   - 会議体の設計
   - Decision Log テンプレ
   - PM / エンジニア保護ルール

10. `10_PM向けワンページ要約.md`
   - PMがまず把握するべき現在地の1枚まとめ
