# 01_アーキテクチャ決定記録_GCP

Version: 0.2  
目的: GCP版の採用理由と境界条件を固定する

---

## 1. 採用アーキテクチャ

### 1.1 採用方針
**Web: PlayCanvas + React**  
**Backend: GCP / Firebase**  
**Quest: Unity + OpenXR**

### 1.2 採用サービス
#### Web / Front
- React
- PlayCanvas / `@playcanvas/react`
- Firebase Hosting（静的配信）
- 必要に応じて Firebase Authentication

#### Backend / Data / AI
- Cloud Run（API / ワーカー）
- Cloud SQL for PostgreSQL（正本DB）
- Cloud Storage（GLB / PNG / Blueprint / Emblem / Export）
- Vertex AI（LLM / 画像生成 / 将来の評価補助）
- Cloud Tasks（非同期ジョブ）
- Firebase Authentication（ユーザー / オペレーター認証）
- Firestore（任意。ライブセッション状態のミラー用）

#### Quest
- Unity
- OpenXR
- Meta Quest Support
- optional: glTFast（確認 / デバッグ / 補助用途）

---

## 2. なぜこの構成にするか

### 2.1 Web側は「スーツ成立」に集中したい
今回のWebは、業務アプリ的な管理画面ではあるが、中心機能は **3Dスーツの組み立て** である。  
そのため、GLBの読み込み、シーングラフ編集、プレビュー、必要ならGLBエクスポートまでを自然に繋げやすい PlayCanvas を軸にする。

### 2.2 Backendは「保存箱」以上の役割を持つ
このプロダクトのサーバーは、単なるGLB保存箱ではない。  
以下を担う必要がある。
- SuitManifest の正本管理
- PartCatalog / SuitVersion の整合管理
- AI生成パイプライン
- Replay / Session の履歴管理
- 将来の分析・評価・運用監査

このため、**オブジェクト保管 + 軽量KVだけ** ではなく、
- 関係性の強い正本データ
- 非同期ジョブ
- AI生成基盤
を同居させやすい GCP を採用する。

### 2.3 Quest本編はネイティブ優先
Questでの体験は「ブラウザ閲覧」ではなく **変身試験の本編** である。  
そのため、
- 状態遷移
- 音声トリガ
- 蒸着演出
- Quest内 Replay
を細かく制御しやすい Unity ネイティブを採用する。

---

## 3. なぜCloud SQLを正本DBにするか
Firestore はライブ状態やオペレーターダッシュボードには強いが、今回の正本は以下のような**関係性が強いデータ**である。
- PartCatalog
- SuitManifest
- SuitVersion
- ArtifactVersion
- TransformSession
- ReplayScript
- PartCompatibilityRule

これらは
- JOIN
- 制約
- バージョン管理
- 監査ログ
が重要になるため、**Cloud SQL for PostgreSQL** を正本DBにする。

### 3.1 Firestoreの位置づけ
Firestore は optional とする。用途は以下のみ。
- ライブセッション状態の配信
- 管理画面のリアルタイム表示
- 実験的な operator console 同期

つまり、**Cloud SQL が正本、Firestore はキャッシュ / 投影モデル** とする。

---

## 4. なぜCloud Storageを採用するか
保存対象は大きく2種類ある。
1. **正本JSON / 関係データ** → Cloud SQL
2. **大きなバイナリ** → Cloud Storage

Cloud Storage には以下を置く。
- preview.png
- blueprint.png
- emblem.png
- merged.glb
- replay thumbnails
- operator export video

Quest本編では Manifest を読んで再構成するため、**GLBは正本ではない**。しかし共有・検証・外部連携で有用なので保持する。

---

## 5. なぜCloud RunをAPI本体にするか
APIは以下の性質を持つ。
- Hono でも Express/Fastify でも載せられる
- Webからの同期API
- 非同期ジョブの呼び出し元
- QuestからのManifest取得先
- 社内ツール/AI実行基盤からも叩く

Cloud Run なら
- コンテナで統一
- 非同期処理との相性が良い
- ステージングと本番の差分を抑えやすい
ので、バランスが良い。

---

## 6. Vertex AIの役割
Vertex AIは以下に使う。

### 6.1 本線
- Emotion / Context Analyzer
- DesignVector 生成
- PartPlan 生成
- Blueprint / Emblem 画像生成

### 6.2 研究線
- スーツ三面図生成
- 将来のラフ3D評価
- Replay用説明文の自動生成支援

### 6.3 位置づけ
AIは「全部を作る神」ではない。  
**設計支援・提案・量産補助** が主であり、最終3Dの成立はカタログパーツとルールで担保する。

---

## 7. 採用しない / 後回しにするもの
### 7.1 WebXR本編
後回しにする。  
理由: 本編は Quest ネイティブの方が演出・安定性・Replay の作り込みに向く。

### 7.2 Firestore単独構成
採用しない。  
理由: 正本データに関係制約が多い。

### 7.3 完全AI生成3D本線
採用しない。  
理由: 品質・接続規格・Quest運用で不安定。

### 7.4 Firebase App Hosting の全面採用
現時点では保留。  
理由: Web前提が React + PlayCanvas の静的/SPA 寄りなので、まずは Firebase Hosting + Cloud Run で十分。

---

## 8. 参考にした設計思想
今回のWeb構成は、**ブラウザ上で素体＋追加要素を組み、シーングラフをそのままGLB化し、サーバーは保管と配信に徹する** という考え方をかなり参考にしている。Tabetaine 資料でも、PlayCanvas Scene 上の `ExportEntity` を `glTF Exporter` でダンプし、Cloudflare側はGLBを保管・配信する箱として使っている。【170:0†Tabetaine 3Dモデル生成パイプライン 技術解説†L8-L15】【170:0†Tabetaine 3Dモデル生成パイプライン 技術解説†L18-L50】

ただし今回の差分は以下。
- 目的は VRChat 再配布ではなく **Quest変身試験 + Quest Replay**
- 正本は GLB ではなく **SuitManifest**
- Backend は Cloudflare ではなく **GCP**

---

## 9. 最終採用文
本プロジェクトの標準構成は以下とする。

- Web: React + PlayCanvas + Firebase Hosting
- API / Worker: Cloud Run
- Primary DB: Cloud SQL for PostgreSQL
- Object Storage: Cloud Storage
- Optional Live State: Firestore
- Auth: Firebase Authentication
- AI: Vertex AI
- Quest: Unity + OpenXR + Meta Quest Support

これを **Balanced GCP Architecture** と呼ぶ。
