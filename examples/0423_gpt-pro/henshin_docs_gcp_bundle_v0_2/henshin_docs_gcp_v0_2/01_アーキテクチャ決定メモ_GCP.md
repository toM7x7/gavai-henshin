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
