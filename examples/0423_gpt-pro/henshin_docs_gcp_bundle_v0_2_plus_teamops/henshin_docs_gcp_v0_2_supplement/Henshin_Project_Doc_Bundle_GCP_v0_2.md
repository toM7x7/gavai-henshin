

---

# 00_README.md

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

# 01_アーキテクチャ決定メモ_GCP.md

# 01_アーキテクチャ決定メモ_GCP

Version: 0.2  
目的: 技術選定を固定し、エンジニア・AI・PMの前提を揃える

---

## 1. 今回の結論

本プロジェクトは、以下の**ハイブリッドGCP案**で進める。

### 採用構成
- **Web UI / Suit Forge**: React + TypeScript + PlayCanvas
- **Web Hosting**: Firebase Hosting
- **認証**: Firebase Authentication
- **APIサーバー**: Hono on Cloud Run
- **Canonical Database**: Cloud SQL for PostgreSQL
- **Realtime / Operator / Live Trial State**: Cloud Firestore
- **Asset Storage**: Google Cloud Storage
- **非同期処理**: Cloud Tasks
- **AI基盤**: Vertex AI
- **秘密情報管理**: Secret Manager
- **Quest Runtime**: Unity + OpenXR + Meta Quest Support
- **3D DCC**: Blender + Blender Python API
- **AI開発補助**: Firebase MCP server（必要時）

---

## 2. この案を選ぶ理由

### 2.1 Cloudflare案をそのまま採用しない理由
Cloudflare案は軽くて美しいが、今回は以下を強く求める。

- 生成AIの反復実行
- バッチ / 非同期処理
- セッション状態の可視化
- 認証と権限
- 将来の分析 / 管理画面拡張
- AIを使った開発自動化

この要求に対し、GCP/Firebaseの方が**AI・認証・運用・非同期**まで含めて一本化しやすい。

### 2.2 PlayCanvasは残す理由
PlayCanvas系は、ブラウザ上で
- GLBを読み込み
- シーングラフを編集し
- エクスポート対象だけをまとめて
- GLBとして吐く

という流れが作りやすい。  
今回の「素体 + パーツ + 表層差分」でスーツを成立させる用途に合う。

### 2.3 QuestはUnity/OpenXRを維持する理由
本編はQuest内での変身試験とReplay。  
ここは演出、状態遷移、音声、ログ再生、体躯適合が絡むので、**ネイティブランタイムを優先**する。

---

## 3. 構成の全体像

```text
[Participant / Operator Input]
  ↓
[Emotion / Context Analyzer]  -- Vertex AI
  ↓
[DesignVector / PartPlan]
  ↓
[Suit Forge Web]
  ├─ PartCatalog 読み込み
  ├─ 素体 + パーツ組み立て
  ├─ Preview
  ├─ SuitManifest作成
  └─ Optional Merged GLB 作成
  ↓
[API Layer : Hono on Cloud Run]
  ├─ Auth / Policy
  ├─ Suit保存
  ├─ Trial保存
  ├─ Replay metadata保存
  ├─ Signed URL発行
  └─ Quest配信用API
  ↓
[Storage / DB]
  ├─ Cloud SQL (canonical)
  ├─ Firestore (live state)
  ├─ Cloud Storage (GLB / PNG / JSON / Archive)
  ├─ Cloud Tasks (async jobs)
  └─ Secret Manager
  ↓
[Quest Transform Runtime]
  ├─ SuitManifest取得
  ├─ Local Part Catalog から再構成
  ├─ Morphotype適用
  ├─ Transform Trial実行
  ├─ TransformSession記録
  └─ Quest Replay再生
```

---

## 4. サービス責務の切り方

### 4.1 Firebase Hosting
責務:
- Suit Forge SPA の配信
- Operator dashboard の配信
- 認証済みクライアント起動点

採用理由:
- Web SPA の配信が単純
- Firebase Auth との連携が素直
- CDN配信が容易

### 4.2 Cloud Run
責務:
- Hono API 実行
- Admin SDK / Vertex AI / DB接続の集約
- Quest / Web 双方からのAPI受け口

採用理由:
- コンテナでAPIを持てる
- Honoと相性が良い
- 長期的に worker / batch / internal API を足しやすい

### 4.3 Cloud SQL (PostgreSQL)
責務:
- 正本データ
- Suit / Version / Catalog / Session / Audit の保存

採用理由:
- スキーマ管理しやすい
- Version / relation / uniqueness を扱いやすい
- Replayや監査ログが将来増えても破綻しにくい

### 4.4 Firestore
責務:
- ライブ状態
- オペレーター画面の即時反映
- Quest接続状態
- 進行中トライアルのリアルタイム状態

採用理由:
- リアルタイム更新が得意
- Cloud SQL に置くほど厳密でないが即時性が欲しい情報に向く

### 4.5 Cloud Storage
責務:
- GLB
- Preview PNG
- Blueprint PNG
- Emblem PNG
- Replay関連生成物
- 将来の MP4 / PDF 出力物

### 4.6 Cloud Tasks
責務:
- 画像生成やプレビュー生成の非同期化
- 重い replay export の後処理
- AIジョブ再試行

### 4.7 Vertex AI
責務:
- EmotionAnalyzer
- DesignVectorGenerator
- PartPlanner
- Blueprint / Emblem 生成
- 将来の画像編集ループ

### 4.8 Secret Manager
責務:
- APIキー
- 外部AI接続情報
- 内部署名鍵
- サービス間秘密情報

---

## 5. Firestore と Cloud SQL の役割分担

### Firestoreに置くもの
- 現在接続中の Quest デバイス状態
- 進行中の trial の current_step
- Operator UI のライブ監視情報
- 一時的な queue / status

### Cloud SQLに置くもの
- Project
- Operator
- Participant
- EmotionProfile
- DesignVector
- PartPlan
- Suit
- SuitVersion
- PartCatalog
- TransformSession
- TransformEvent
- ReplayScript
- AuditLog

### 判断ルール
- **正本・履歴・一意性・joinが必要** → Cloud SQL
- **ライブ監視・現在値・購読更新** → Firestore

---

## 6. 他の選択肢をどう扱うか

### 6.1 Firebase App Hosting
今回は見送る。  
理由: 現時点では Web が SPA 中心で、SSR前提ではないため。  
ただし将来 Next.js 等へ寄せる場合は候補。

### 6.2 Firestoreのみで全部持つ
見送る。  
理由: SuitVersion / PartCatalog / Replay / Audit を Firestore だけで厳密に管理すると、後で設計が荒れやすい。

### 6.3 Cloud Storage for Firebase を正本ストレージにする
今回は見送る。  
理由: サーバー主導の signed URL / backend upload を主軸にしたいので、まずは Cloud Storage を正とする。

### 6.4 WebXR本編化
見送る。  
理由: Quest本編とReplayはネイティブ優先。

---

## 7. 3Dパイプライン方針

### 7.1 本線
- 素体 + パーツ + 表層差分
- Webで組む
- SuitManifest を正本に保存
- 必要なら GLB を副生成物として保存

### 7.2 自動化補助
- Blender Python でパーツのバリエーション量産
- LLMで PartPlan 提案
- Resolver で実在カタログへ落とす

### 7.3 研究線
- 画像→3D粗生成
- MCPでBlender操作
- 生成三面図の補助

---

## 8. 主要な技術判断

### 決定済み
- Backend 主軸は GCP
- Quest本編は Unity/OpenXR
- Replay は Quest主
- Webは Suit Forge 中心
- 正本は SuitManifest

### 未決
- Prisma or Drizzle
- Firestore の具体コレクション構成
- Cloud Run サービス分割数
- Signed URL と proxy 配信の使い分け
- Vertex AI 呼び出しの同期/非同期境界

---

## 9. 直近の意思決定項目

1. `Cloud SQL schema` を初版でどこまで切るか
2. `Firestore live model` をどこまで持つか
3. `Quest device registration` をどの単位で扱うか
4. `SuitManifest` と `PartCatalog` の schema 初版
5. `Cloud Storage path rule` の命名規約
6. `Cloud Tasks` 対象ジョブの初期範囲

---

## 10. 今回の技術方針を一文で

**ブラウザでスーツを成立させ、GCPで正本とAIと運用を支え、Questで変身試験とReplayを完走させる。**


---

# 02_定義書_GCP.md

# 02_定義書_GCP

Version: 0.2  
用途: プロジェクトの定義・用語・スコープを固定する

---

## 1. プロジェクト名
**変身試験プラットフォーム / Henshin Trial Platform**

---

## 2. プロダクト定義
ユーザーの**感情・思い・文脈**を起点に、  
AIがスーツ案を提案し、Web上でスーツを成立させ、Quest上で変身試験を実行し、**Quest内で試験Replayまで確認できる**サービスを作る。

---

## 3. これは何のサービスか
これは「ヒーロー生成アプリ」ではない。  
これは **変身試験サービス** である。

体験者は「なりきり」をするのではなく、
- 設計されたスーツを
- 試験条件で
- 起動し
- 記録し
- 再確認する

という流れを体験する。

---

## 4. 体験の中核フロー

### 4.1 事前入力
- 思い
- 文脈
- なりたい像
- 守りたいもの
- 気分や価値観タグ

### 4.2 スーツ成立
- AIが方向性を解釈
- PartPlan を提案
- Web上で素体 + パーツを成立させる
- SuitManifest を保存

### 4.3 Quest試験
- 適合確認
- 仮組み
- 掛け声
- 蒸着完了

### 4.4 Quest Replay
- 主要イベントの再生
- ステップごとの見返し
- 解説付きReplay

---

## 5. 中核思想

### 5.1 AIは設計者であって、全自動鍛造機ではない
AIの役割は次に限定する。
- Emotion / Context の構造化
- DesignVector の生成
- PartPlan の提案
- Blueprint / Emblem / 解説文の生成

AIが直接フル3D完成品を毎回本番採用することは、MVPでは目指さない。

### 5.2 3Dは成立性優先
3Dは **素体 + パーツ + 表層差分** で成立させる。  
MVPでの完全自動3D生成は本線にしない。

### 5.3 ReplayはQuest主
Replay は「あとでWebで見る」のではなく、**試験直後にQuest内で見返せる**ことを主目標にする。

---

## 6. スコープ

### 6.1 MVPに含む
- Suit Forge Web
- Firebase Auth による operator 認証
- SuitManifest の保存
- Cloud SQL / Firestore / Cloud Storage による管理
- Quest 変身試験
- Quest Replay
- LLMによる PartPlan 提案

### 6.2 MVPに含まない
- WebXR 本編
- 毎回完全自動フル3D生成
- Webカム変身本編
- 自動SE / 自動BGM本格生成
- 一般ユーザー公開向けフルSNS共有機能

---

## 7. 論理サービス定義

### 7.1 Emotion / Context Analyzer
入力テキストを EmotionProfile に落とす。

### 7.2 Design Vector Generator
EmotionProfile からデザイン方向性を作る。

### 7.3 Part Planner
DesignVector をもとに PartPlan YAML/JSON を出す。

### 7.4 Resolver
PartPlan を PartCatalog に照らして実在構成へ落とす。

### 7.5 Suit Forge Web
素体 + パーツを組み、保存する。

### 7.6 Suit Registry API
Suit / Session / Replay / Asset を保存・配信する。

### 7.7 Quest Transform Runtime
変身試験を実行する。

### 7.8 Quest Replay Runtime
ReplayScript に基づいて Quest 内再生を行う。

---

## 8. 用語定義

### EmotionProfile
感情・態度・価値観を構造化したもの。

### DesignVector
EmotionProfile をスーツ設計方向に変換したもの。

### PartPlan
LLMが提案する抽象構成案。

### PartCatalog
実在するパーツ辞書。

### SuitManifest
スーツの正本。Questが読む。

### Morphotype
体躯プロファイル。Quest適合に使う。

### TransformSession
1回の試験の記録単位。

### ReplayScript
Quest Replay の再生指示。

---

## 9. 3Dモデルの定義

### 9.1 3レイヤー構造
#### Base Layer
- 密着スーツ
- ベース身体
- グローブ基礎
- ブーツ基礎

#### Armor Layer
- ヘルメット
- 胸部
- 肩
- 前腕
- ベルト
- 脚部
- 背部ユニット

#### Surface Layer
- エンブレム
- 発光ライン
- 材質プリセット
- テクスチャ差分

### 9.2 ソケット規格
- head_socket
- chest_socket
- shoulder_l_socket
- shoulder_r_socket
- arm_l_socket
- arm_r_socket
- belt_socket
- leg_l_socket
- leg_r_socket
- back_socket
- emblem_socket

---

## 10. 成果物定義

### 10.1 正本
- SuitManifest
- TransformSession
- ReplayScript

### 10.2 副生成物
- merged.glb
- preview.png
- blueprint.png
- emblem.png
- replay export (将来)

---

## 11. 進め方の原則

### 11.1 仕様先行で固定するもの
- Schema
- Socket naming
- PartCatalog
- State machine

### 11.2 実装で後から詰めるもの
- 画面の細かなUI表現
- 演出の質感
- MCP自動化の範囲
- 3D粗生成の研究線

---

## 12. 一文でいうと

**このプロジェクトは、感情と文脈を起点にスーツを設計し、Quest上でその変身試験とReplayを成立させるための基盤である。**


---

# 03_仕様書_GCP.md

# 03_仕様書_GCP

Version: 0.2  
用途: Web / Backend / Quest / AI の実装仕様を揃える

---

## 1. システム全体構成

```text
[User / Operator]
  ↓
[Firebase Auth]
  ↓
[Suit Forge Web (React + PlayCanvas)]
  ├─ Emotion Input
  ├─ AI Proposal View
  ├─ Part Selection
  ├─ Preview
  └─ Save / Send to Quest
  ↓
[API Gateway (Hono on Cloud Run)]
  ├─ /emotion
  ├─ /design
  ├─ /plans
  ├─ /suits
  ├─ /trials
  ├─ /replays
  └─ /devices
  ↓
[Data / Infra]
  ├─ Cloud SQL PostgreSQL
  ├─ Cloud Firestore
  ├─ Cloud Storage
  ├─ Cloud Tasks
  ├─ Vertex AI
  └─ Secret Manager
  ↓
[Quest Transform Runtime]
  ├─ Login / Device binding
  ├─ Suit fetch
  ├─ Trial
  ├─ Session log
  └─ Replay
```

---

## 2. Web仕様

### 2.1 画面群

#### A. Operator Dashboard
役割:
- 参加者選択
- Quest接続状態確認
- スーツ送信
- 試験開始

#### B. Suit Forge
役割:
- 感情・文脈入力
- AI提案確認
- パーツ構成編集
- 保存
- Quest送信

#### C. Trial Monitor
役割:
- 進行中試験の現在ステップ表示
- Questデバイス状態表示
- セッションログ確認

#### D. Archive Browser
役割:
- 過去セッション一覧
- Suit / Session / Replay 参照

---

### 2.2 Suit Forge 画面仕様

#### 必須UI要素
- 左: 感情・文脈入力
- 中央: 3D Preview
- 右: パーツ構成
- 下部: 色 / 材質 / 保存 / Quest送信

#### 機能
- Emotion 入力更新
- AI提案取得
- PartPlan 表示
- パーツ手動変更
- 材質プリセット適用
- SuitManifest 保存
- Quest送信要求

#### 非機能
- 主要操作は 1〜2秒以内に応答
- AI提案は非同期でよい
- 3D Preview は編集可能だが、本編級描画は不要

---

## 3. Backend仕様

### 3.1 API責務

#### `/v1/emotion/analyze`
入力テキストから EmotionProfile を生成する。

#### `/v1/design/vector`
EmotionProfile から DesignVector を生成する。

#### `/v1/part-plans`
DesignVector から PartPlan を生成する。

#### `/v1/part-plans/resolve`
PartPlan を PartCatalog に解決する。

#### `/v1/suits`
Suit の作成 / 更新 / 取得を行う。

#### `/v1/suits/:suitId/send-to-quest`
選択スーツを Quest device に割り当てる。

#### `/v1/trials`
Trial を開始する。

#### `/v1/trials/:trialId/events`
進行イベントを追記する。

#### `/v1/trials/:trialId/replay`
ReplayScript を取得する。

#### `/v1/devices`
Quest device の登録 / 状態参照を行う。

---

### 3.2 Cloud Run サービス分割

#### 初期構成（推奨）
- `api-service`
  - Hono 本体
  - Auth検証
  - Suit / Trial API
- `worker-service`
  - Cloud Tasks 受信
  - AI生成ジョブ
  - サムネイル / 副生成物生成

#### 将来分割候補
- `replay-export-service`
- `ai-service`
- `catalog-admin-service`

---

### 3.3 Cloud SQL 仕様

#### 初期テーブル
- operators
- participants
- projects
- suits
- suit_versions
- part_catalog
- part_assets
- emotion_profiles
- design_vectors
- part_plans
- transform_sessions
- transform_events
- replay_scripts
- audit_logs

#### 初期採用ルール
- canonical data は SQL
- version 管理は SQL
- 一意な外部IDを各エンティティに持つ

---

### 3.4 Firestore 仕様

#### 初期コレクション
- `live_trials/{trialId}`
- `quest_devices/{deviceId}`
- `operator_dashboards/{operatorId}`

#### 用途
- 現在ステップ
- Quest接続状態
- ライブ適合率
- 現在の進行ログ断片

#### 非用途
- canonical history の保存
- 永続監査の正本

---

### 3.5 Cloud Storage path rule

```text
gs://bucket/
  suits/{suitId}/versions/{version}/
    manifest.json
    preview.png
    blueprint.png
    emblem.png
    merged.glb
  trials/{trialId}/
    transform-session.json
    replay-script.json
    captures/
  catalogs/
    parts/
    materials/
    emblems/
```

---

### 3.6 Cloud Tasks 対象ジョブ

#### 初期対象
- Blueprint生成
- Emblem生成
- Preview画像レンダ
- Replay補助メタ生成

#### 後で対象にする
- MP4書き出し
- PDFレポート生成
- 重い画像編集ループ

---

## 4. AI仕様

### 4.1 Emotion Analyzer
入力:
- text
- tags

出力:
- EmotionProfile JSON
- confidence
- assumptions

### 4.2 Design Vector Generator
入力:
- EmotionProfile

出力:
- DesignVector JSON

### 4.3 Part Planner
入力:
- DesignVector

出力:
- PartPlan YAML / JSON
- rationale
- alternatives

### 4.4 Resolver
入力:
- PartPlan
- PartCatalog

出力:
- ResolvedPartPlan
- substitutions
- warnings

### 4.5 画像生成
対象:
- Blueprint
- Emblem
- 将来はUI補助やバリエーション画像

---

## 5. Quest仕様

### 5.1 Questアプリの責務
- device binding
- SuitManifest 取得
- local asset catalog から再構成
- trial state machine 実行
- session log 記録
- Quest内Replay 再生

### 5.2 状態遷移

```text
IDLE
  → FIT_CHECK
  → DRY_FIT
  → VOICE_WAIT
  → TRANSFORMING
  → SEALED
  → RESULT
  → REPLAY_READY
```

### 5.3 Quest内 Replay

#### 要件
- 試験直後に見返せる
- 主要イベントへジャンプできる
- シンプルで読みやすいUI
- 外部動画依存を最小化する

#### MVP方式
- 動画Replayではなく**ログReplay主体**
- State + camera cue + subtitle を再生
- 主要イベント:
  - 適合確定
  - 仮組み完了
  - 掛け声受理
  - 蒸着完了
  - アーカイブ保存

### 5.4 Morphotype
#### 初期取得方法
- 手入力
- Quest側簡易計測
- 将来 mocopi 連携

#### 初期適用内容
- overall scale
- shoulder width offset
- arm / leg length correction
- chest / belt / back unit の位置補正

---

## 6. 3D仕様

### 6.1 PartCatalog 初期カテゴリ
- base_body
- helmet
- chest
- shoulder
- arm
- belt
- leg
- back_unit
- emblem
- material_preset

### 6.2 初期命名規約
```text
base_frame_alpha
helmet_visor_03
chest_core_05
arm_bracer_02
belt_driver_01
leg_strider_03
back_wing_01
emblem_solar_01
```

### 6.3 ソケット規格
- head_socket
- chest_socket
- shoulder_l_socket
- shoulder_r_socket
- arm_l_socket
- arm_r_socket
- belt_socket
- leg_l_socket
- leg_r_socket
- back_socket
- emblem_socket

---

## 7. 非機能要件

### 7.1 安定性
- Quest本編はネットワーク不安定時にも落ちにくい構成にする
- SuitManifest を取得後、最低限はローカルで完走できること

### 7.2 運用性
- operator が 1画面で状態を追える
- Firestore にライブ状態を流す
- Cloud Logging で API / worker / trial を追える

### 7.3 拡張性
- 将来 WebXR を追加できる
- 将来 画像→3D粗生成 を差し込める
- 将来 複数の生成モデルを差し替えられる

---

## 8. API例

### POST `/v1/suits`
```json
{
  "project_id": "PRJ-001",
  "emotion_profile": {"...": "..."},
  "design_vector": {"...": "..."},
  "part_plan": {"...": "..."},
  "resolved_parts": {"...": "..."},
  "manifest": {"...": "..."}
}
```

### POST `/v1/suits/{suitId}/send-to-quest`
```json
{
  "device_id": "QUEST-01",
  "participant_id": "P-250527-012"
}
```

### POST `/v1/trials`
```json
{
  "suit_id": "SUIT-X01-0241",
  "device_id": "QUEST-01",
  "participant_id": "P-250527-012",
  "morphotype": {"...": "..."}
}
```

---

## 9. MVPの受け入れ条件

### Web
- Suit Forge で1着保存できる
- Quest送信が押せる
- Operator画面で Quest 接続を見られる

### Backend
- Suit / Trial / Replay の最小 CRUD がある
- Firestore でライブ状態が見える
- Cloud Storage に副生成物を保存できる

### Quest
- 1着以上を読み込み、試験を完走できる
- 試験直後に Replay を見られる

### AI
- 入力→EmotionProfile→DesignVector→PartPlan→Resolve が一周する


---

# 04_データ契約_GCP.md

# 04_データ契約_GCP

Version: 0.2  
用途: Web / Backend / Quest / AI で共有する schema の初版

---

## 1. EmotionProfile

```json
{
  "emotion_profile_id": "EP-0001",
  "bravery": 0.85,
  "restraint": 0.70,
  "protectiveness": 0.90,
  "mysticism": 0.55,
  "context_tags": ["正義", "未来志向", "仲間想い"],
  "raw_input": "仲間を守り、未来を切り開く存在になりたい。...",
  "confidence": 0.74,
  "assumptions": ["入力は守護志向と解釈した"]
}
```

---

## 2. DesignVector

```json
{
  "design_vector_id": "DV-0001",
  "silhouette": "sharp",
  "armor_mass": "medium",
  "helmet_type": "visor",
  "shoulder_volume": "high",
  "palette_family": "carmine_titanium_cyan",
  "emissive_style": "core_line",
  "combat_bias": "speed_close_range"
}
```

---

## 3. PartPlan (抽象案)

```yaml
theme: vanguard
helmet:
  style: visor
  silhouette: sharp
  aggression: medium
chest:
  emphasis: core
  armor_mass: medium
arms:
  type: bracer
legs:
  mobility: high
back_unit:
  type: wing_booster
emblem:
  motif: solar
palette:
  primary: carmine
  secondary: titanium
  accent: cyan
```

---

## 4. ResolvedPartPlan

```json
{
  "base_body": "base_frame_alpha",
  "helmet": "helmet_visor_03",
  "chest": "chest_core_05",
  "arm_l": "arm_bracer_02",
  "arm_r": "arm_bracer_02",
  "belt": "belt_driver_01",
  "leg_l": "leg_strider_03",
  "leg_r": "leg_strider_03",
  "back": "back_wing_01",
  "emblem": "emblem_solar_01",
  "warnings": [],
  "substitutions": []
}
```

---

## 5. SuitManifest (正本)

```json
{
  "suit_id": "SUIT-X01-0241",
  "version": 3,
  "project_id": "PRJ-001",
  "display_name": "X-01 ヴァンガード",
  "base_body": "base_frame_alpha",
  "parts": {
    "helmet": "helmet_visor_03",
    "chest": "chest_core_05",
    "arm_l": "arm_bracer_02",
    "arm_r": "arm_bracer_02",
    "belt": "belt_driver_01",
    "leg_l": "leg_strider_03",
    "leg_r": "leg_strider_03",
    "back": "back_wing_01",
    "emblem": "emblem_solar_01"
  },
  "materials": {
    "undersuit": "m_under_black_01",
    "armor_main": "m_armor_titanium_03",
    "armor_sub": "m_armor_carmine_01",
    "emissive": "m_emit_cyan_01"
  },
  "design_source": {
    "emotion_profile_id": "EP-0001",
    "design_vector_id": "DV-0001",
    "part_plan_id": "PP-0001"
  },
  "artifacts": {
    "preview_png": "gs://.../preview.png",
    "blueprint_png": "gs://.../blueprint.png",
    "emblem_png": "gs://.../emblem.png",
    "merged_glb": "gs://.../merged.glb"
  },
  "status": "READY_FOR_QUEST"
}
```

---

## 6. Morphotype

```json
{
  "morphotype_id": "M-0032",
  "height": 173,
  "shoulder_width": 44.2,
  "hip_width": 31.0,
  "arm_length": 59.4,
  "leg_length": 92.0,
  "torso_length": 58.2,
  "scale": 1.00,
  "source": "manual|quest|mocopi",
  "confidence": 0.82
}
```

---

## 7. TransformSession

```json
{
  "trial_id": "TRIAL-0047-Q",
  "project_id": "PRJ-001",
  "participant_id": "P-250527-012",
  "device_id": "QUEST-01",
  "suit_id": "SUIT-X01-0241",
  "morphotype_id": "M-0032",
  "status": "COMPLETED",
  "fit_score": 0.987,
  "started_at": "2026-04-23T08:30:00Z",
  "ended_at": "2026-04-23T08:31:15Z"
}
```

---

## 8. TransformEvent

```json
{
  "event_id": "EVT-0001",
  "trial_id": "TRIAL-0047-Q",
  "seq": 1,
  "t_ms": 3210,
  "type": "FIT_CONFIRMED",
  "payload": {
    "fit_score": 0.936
  }
}
```

### 想定イベント種別
- FIT_STARTED
- FIT_CONFIRMED
- DRY_FIT_STARTED
- DRY_FIT_DONE
- VOICE_WAIT
- VOICE_ACCEPTED
- TRANSFORM_BEGIN
- DEPOSITION_FINISHED
- SEALED
- RESULT_READY
- REPLAY_READY
- ARCHIVED

---

## 9. ReplayScript

```json
{
  "replay_id": "RPL-0001",
  "trial_id": "TRIAL-0047-Q",
  "mode": "QUEST_REPLAY",
  "segments": [
    {
      "at_ms": 3210,
      "title": "適合確定",
      "subtitle": "適合率 93.6% を確認",
      "camera": "front_close",
      "fx": "fit_glow"
    },
    {
      "at_ms": 7640,
      "title": "変身開始",
      "subtitle": "掛け声を受理",
      "camera": "center_full",
      "fx": "core_flash"
    },
    {
      "at_ms": 15230,
      "title": "蒸着完了",
      "subtitle": "装甲展開を確認",
      "camera": "orbit_half",
      "fx": "deposition_finish"
    }
  ]
}
```

---

## 10. PartCatalog (最小モデル)

```json
{
  "part_id": "helmet_visor_03",
  "category": "helmet",
  "display_name": "Phoenix Visor",
  "socket": "head_socket",
  "compatible_base_bodies": ["base_frame_alpha"],
  "material_slots": ["armor_main", "armor_sub", "emissive"],
  "bounds_profile": "medium_head",
  "status": "ACTIVE"
}
```

---

## 11. Firestore live model

### `quest_devices/{deviceId}`
```json
{
  "deviceId": "QUEST-01",
  "status": "CONNECTED",
  "lastSeenAt": "2026-04-23T08:30:10Z",
  "currentTrialId": "TRIAL-0047-Q",
  "operatorId": "OP-001"
}
```

### `live_trials/{trialId}`
```json
{
  "trialId": "TRIAL-0047-Q",
  "currentStep": "VOICE_WAIT",
  "progress": 0.63,
  "fitScore": 0.987,
  "questConnection": "LIVE",
  "updatedAt": "2026-04-23T08:30:40Z"
}
```

---

## 12. Cloud SQL relation rough map

```text
projects ─┬─ suits ─┬─ suit_versions
          │         └─ transform_sessions ─┬─ transform_events
          │                                └─ replay_scripts
          ├─ participants
          ├─ emotion_profiles
          ├─ design_vectors
          ├─ part_plans
          └─ audit_logs

part_catalog ─┬─ part_assets
              └─ compatibility_rules
```

---

## 13. Schema固定の優先順位

### 今すぐ固定
- SuitManifest
- PartCatalog
- TransformSession
- TransformEvent type
- ReplayScript

### 次に固定
- Operator / Participant / Project
- Firestore live docs
- Asset path rule

### 後で拡張
- analytics
- export jobs
- reporting


---

# 05_進捗差分とロードマップ_GCP.md

# 05_進捗差分とロードマップ_GCP

Version: 0.2  
用途: 現在地と、ここからの進め方を固定する

---

## 1. 現在の進捗

### 1.1 決まっていること
- 企画は「変身試験」である
- ロアは内部設定として保持する
- Webでスーツを成立させる
- Questで変身試験を成立させる
- Replay は Quest主
- 正本は SuitManifest
- 3Dは素体 + パーツ方式
- AIは YAML / JSON で PartPlan を提案する
- GCP を主軸にする

### 1.2 まだドラフト段階のもの
- Web技術の最終フレームワーク細部
- Cloud SQL schema 実装詳細
- Firestore live docs の最終構造
- Quest state machine の細部
- PartCatalog 初版の中身
- Blender量産手順

---

## 2. 現時点の成果物の質評価

### すでに強い
- 企画の芯
- Web / Quest の責務分離
- Replay をQuest内に寄せる発想
- AIを「構成提案」に使う考え方
- GCP採用による運用基盤の見通し

### まだ弱い
- 正式 schema の固定
- エンジニアが即着手できる API / DB 詳細
- AIへ投げる単位の明確化
- 3D制作ルールの明文化

---

## 3. 直近で解消すべきギャップ

### G1. SuitManifest がまだ“概念”の域
対応:
- JSON Schema を正式化
- versioning rule を確定
- PartCatalog との整合条件を明記

### G2. Firestore と Cloud SQL の境界がまだ文書レベル
対応:
- 1画面で表にする
- live / canonical / archive を切り分ける

### G3. Quest Replay の実装方式が粗い
対応:
- state-based replay として固定
- event type を先に決める
- UIモックより state machine を先に固める

### G4. AIぶん回しの投入順が未最適化
対応:
- Stream順序と受け入れ条件を固定する
- 別AIへ投げる prompt と返却形式を固定する

---

## 4. 優先順位

### P0（今週固定）
- SuitManifest 初版
- PartCatalog 初版
- TransformSession / Event 初版
- GCP 構成図
- API一覧

### P1（次に固定）
- Firestore live docs
- Operator Dashboard 要件
- Quest state machine
- ReplayScript 初版

### P2（その次）
- Blender量産ルール
- MCP導入ルール
- Vertex AI プロンプト管理ルール

---

## 5. フェーズ別ロードマップ

### Phase 0: GCP仕様固定（1週）
成果物:
- このドキュメント束 v0.2
- JSON/YAML schema 初版
- GCP サービス責務一覧

完了条件:
- エンジニアと AI が同じ言葉で会話できる

---

### Phase 1: Data Contract 実装（1週）
成果物:
- SuitManifest JSON Schema
- PartCatalog JSON Schema
- TransformSession JSON Schema
- ReplayScript JSON Schema
- Prisma schema draft

完了条件:
- Web / Backend / Quest が並行実装可能

---

### Phase 2: Backend Skeleton（1〜2週）
成果物:
- Firebase project
- Firebase Auth 初期設定
- Cloud Run API skeleton
- Cloud SQL 接続
- Firestore live collection 初版
- Cloud Storage bucket 構築

完了条件:
- `GET /health`
- `POST /suits`
- `GET /suits/:id`
- `POST /trials`
- Firestore への live state 書き込み

---

### Phase 3: Suit Forge MVP（2週）
成果物:
- React + PlayCanvas 画面
- Emotion 入力
- AI PartPlan 表示
- パーツ差し替え
- 保存
- Quest送信

完了条件:
- 1着を保存して SuitManifest が作れる

---

### Phase 4: AI Integration（1〜2週）
成果物:
- Vertex AI 接続
- Emotion Analyzer
- DesignVector Generator
- Part Planner
- Resolver

完了条件:
- テキスト入力からスーツ提案まで一周する

---

### Phase 5: Quest Trial MVP（2〜3週）
成果物:
- Unity OpenXR プロジェクト
- SuitManifest 読み込み
- パーツ再構成
- 試験 state machine
- Trial log 送信

完了条件:
- Questで 1着以上の試験を完走

---

### Phase 6: Quest Replay MVP（1〜2週）
成果物:
- ReplayScript 読み込み
- イベントジャンプ
- Quest内再生UI

完了条件:
- 試験直後に Quest 内で見返せる

---

### Phase 7: 量産自動化（継続）
成果物:
- Blender Python 自動化
- PartCatalog 拡充
- MCP / R&D線の導入

---

## 6. 直近の会議で決めるべきこと

1. Firebase Hosting でSPA配信する前提を確定してよいか
2. Cloud SQL ORM を Prisma に寄せるか
3. Firestore live docs の初版を3コレクションで始めるか
4. Quest device binding を participant 単位にするか operator 単位にするか
5. Replay を完全ログ駆動にするか、一部動画風演出を混ぜるか

---

## 7. 現時点のおすすめ進行順

1. Data Contract を AIで叩く
2. Backend skeleton を人が立てる
3. Suit Forge と Quest を並行着手
4. Vertex AI を後追いで接続
5. Replay を Quest 実装の直後に入れる

---

## 8. やらないことリスト（今は封印）
- WebXR本編化
- 毎回完全自動3D
- AIにPart IDを直接自由生成させる
- Replay を動画書き出し前提にする
- UIモックを先に磨きすぎる


---

# 06_AI実行指示書_GCP.md

# 06_AI実行指示書_GCP

Version: 0.2  
用途: 別アプリのAIを多並列で回すための統一指示書

---

## 0. 基本方針

- AIには **狭い責務** だけを渡す
- 出力形式を固定する
- 実在カタログに落ちない自由提案は禁止
- 勝手な仕様拡張は禁止
- すべての出力に `ASSUMPTIONS / RISKS / OPEN_QUESTIONS` を付ける
- 返却は**差分提案**とし、正本ファイルを書き換えない

---

## 1. Stream一覧

### Stream A: Architecture Reviewer
目的:
- GCP構成の矛盾や過不足を洗う

入力:
- `01_アーキテクチャ決定メモ_GCP.md`
- `03_仕様書_GCP.md`

出力:
- service dependency map
- missing infra list
- simplification proposal

---

### Stream B: Data Contract Refiner
目的:
- 各JSON/YAML schema を厳密化する

入力:
- `04_データ契約_GCP.md`

出力:
- JSON Schema draft
- enum list
- naming inconsistencies
- validation rules

---

### Stream C: Backend API Drafter
目的:
- Cloud Run API のエンドポイント仕様を切る

入力:
- `03_仕様書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- endpoint list
- request/response spec
- auth rules
- error code list

---

### Stream D: Firestore / Cloud SQL Split Reviewer
目的:
- Firestore と Cloud SQL の責務分担を点検する

入力:
- `01_アーキテクチャ決定メモ_GCP.md`
- `03_仕様書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- firestore_collections
- sql_tables
- anti_patterns
- migration risks

---

### Stream E: Suit Forge Spec Assistant
目的:
- Web側の component / state / events を定義する

入力:
- `02_定義書_GCP.md`
- `03_仕様書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- component tree
- state design
- event flows
- screen acceptance criteria

---

### Stream F: Quest Runtime Spec Assistant
目的:
- Quest の state machine と replay behavior を厳密化する

入力:
- `02_定義書_GCP.md`
- `03_仕様書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- state machine
- event transitions
- replay segments
- HUD elements

---

### Stream G: Vertex AI Prompt Designer
目的:
- Emotion / Design / PartPlanner / Blueprint / Emblem のプロンプトを固定する

入力:
- `02_定義書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- prompt templates
- input variables
- output schemas
- failure fallback

---

### Stream H: 3D Catalog Planner
目的:
- PartCatalog の初期リストと Blender制作順を決める

入力:
- `02_定義書_GCP.md`
- `04_データ契約_GCP.md`

出力:
- part backlog
- socket map
- material slot matrix
- QA checklist

---

### Stream I: Blender Automation Planner
目的:
- Blender Python / MCP で自動化する範囲を定義する

入力:
- `02_定義書_GCP.md`
- `05_進捗差分とロードマップ_GCP.md`

出力:
- automatable tasks
- scripts to build first
- human QA checkpoints
- things not to automate yet

---

## 2. AI共通出力ルール

すべてのAI出力は以下の章立てを必須にする。

```text
# SUMMARY
# OUTPUT
# ASSUMPTIONS
# RISKS
# OPEN_QUESTIONS
```

構造化データを返す場合は `OUTPUT` の中で JSON / YAML / Markdown Table を使う。

---

## 3. 実行順序（おすすめ）

### Wave 1
- Stream B: Data Contract Refiner
- Stream D: Firestore / Cloud SQL Split Reviewer
- Stream F: Quest Runtime Spec Assistant

### Wave 2
- Stream C: Backend API Drafter
- Stream E: Suit Forge Spec Assistant
- Stream H: 3D Catalog Planner

### Wave 3
- Stream G: Vertex AI Prompt Designer
- Stream I: Blender Automation Planner
- Stream A: Architecture Reviewer

---

## 4. 受け入れ条件

### A. Data Contract 系
- enum が固定されている
- ID命名規則がある
- versioning 方針がある
- 必須 / 任意が明示されている

### B. API 系
- request/response がJSONで定義済み
- auth前提が明示されている
- error code がある

### C. Quest 系
- state machine が閉じている
- Replay イベントが定義済み
- Voice trigger の失敗時挙動がある

### D. 3D 系
- socket名が固定されている
- part category が固定されている
- 量産順序がある

---

## 5. Stream別プロンプト雛形

### Stream B: Data Contract Refiner
```text
あなたは Data Contract Refiner です。
目的は、変身試験プラットフォームの schema を厳密化することです。

入力:
- 04_データ契約_GCP.md

制約:
- SuitManifest, PartCatalog, TransformSession, TransformEvent, ReplayScript を優先
- enum と命名規則を明示
- versioning rule を提案
- 実装可能性を優先
- 勝手にサービスを増やさない

出力形式:
# SUMMARY
# OUTPUT
- JSON Schema or Markdown tables
# ASSUMPTIONS
# RISKS
# OPEN_QUESTIONS
```

### Stream C: Backend API Drafter
```text
あなたは Backend API Drafter です。
目的は、Cloud Run 上の Hono API の外部仕様を定義することです。

入力:
- 03_仕様書_GCP.md
- 04_データ契約_GCP.md

制約:
- REST風でよい
- request/response JSON を必ず書く
- 認証必須/任意を明記
- Suit, Trial, Replay, Device を優先
- Firestore と Cloud SQL の責務混線を避ける

出力形式:
# SUMMARY
# OUTPUT
- endpoint tables
- request/response examples
# ASSUMPTIONS
# RISKS
# OPEN_QUESTIONS
```

### Stream F: Quest Runtime Spec Assistant
```text
あなたは Quest Runtime Spec Assistant です。
目的は、Quest上の変身試験とReplayを成立させる state machine を定義することです。

入力:
- 02_定義書_GCP.md
- 03_仕様書_GCP.md
- 04_データ契約_GCP.md

制約:
- Replay は Quest主
- ステップは IDLE→FIT_CHECK→DRY_FIT→VOICE_WAIT→TRANSFORMING→SEALED→RESULT→REPLAY_READY を基本とする
- TransformEvent type と整合する
- UIより先に state を閉じる

出力形式:
# SUMMARY
# OUTPUT
- state table
- transition table
- replay behavior table
# ASSUMPTIONS
# RISKS
# OPEN_QUESTIONS
```

### Stream G: Vertex AI Prompt Designer
```text
あなたは Vertex AI Prompt Designer です。
目的は、EmotionAnalyzer / DesignVectorGenerator / PartPlanner / Blueprint / Emblem の prompt template を定義することです。

入力:
- 02_定義書_GCP.md
- 04_データ契約_GCP.md

制約:
- JSON/YAML出力を壊さない
- 推論過剰を避ける
- 実在パーツへ落ちる表現を使う
- fallback を必ず書く

出力形式:
# SUMMARY
# OUTPUT
- prompt templates
- variables
- expected outputs
- fallback strategy
# ASSUMPTIONS
# RISKS
# OPEN_QUESTIONS
```

---

## 6. AIに渡す優先ファイル

### 最小セット
- `02_定義書_GCP.md`
- `04_データ契約_GCP.md`

### Backend系に追加
- `03_仕様書_GCP.md`

### 進行管理系に追加
- `05_進捗差分とロードマップ_GCP.md`

---

## 7. AIぶん回しの実務ルール

- 1回のAI実行で1テーマだけ扱う
- 1回の出力で1ファイルを完成させようとしない
- まず schema → 次に API → 次に UI / XR の順で回す
- 仕様と実装を同時に出させる場合は、仕様章と実装章を分離させる
- 不明点は埋めさせず、OPEN_QUESTIONSに残させる

---

## 8. いま最初に回すべきAIタスク

1. `SuitManifest JSON Schema 初版`
2. `PartCatalog JSON Schema 初版`
3. `TransformEvent enum 一覧`
4. `Cloud SQL table rough draft`
5. `Firestore live collections 初版`
6. `Quest state machine 初版`

これが揃うと、人間側で実装キックオフしやすくなる。
