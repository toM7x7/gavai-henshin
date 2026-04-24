# 変身試験プラットフォーム ドキュメント一式（GCP版）

Version: 0.2  
方針: **PlayCanvas + GCP/Firebase + Unity/OpenXR**  
用途: 別アプリのAI、エンジニア、PMが同じ前提で進めるための基準文書

---

## この版で固定したこと
- バックエンド基盤は **GCP** を採用する
- Webは **PlayCanvas + React** を基本線とする
- Quest本編は **Unity + OpenXR + Meta Quest Support** を基本線とする
- スーツの正本は **SuitManifest** とし、GLBは副生成物とする
- Replay は **Quest内で視聴する** ことを必須要件に格上げする
- MVPでは **完全自動3D生成を本線にしない**。AIは「文脈理解」「構成提案」「画像生成」「量産補助」に使う

---

## ファイル一覧
1. `01_アーキテクチャ決定記録_GCP.md`
   - なぜGCPを採用するか
   - どのサービスを採用するか
   - どの選択肢を見送るか

2. `02_定義書.md`
   - 何を作るか
   - 何を作らないか
   - 用語
   - サービス境界
   - AIの役割

3. `03_仕様書.md`
   - システム構成
   - データモデル
   - Web / API / Quest の責務
   - API一覧
   - 3Dアセット規格
   - 非機能要件

4. `04_進捗差分とロードマップ.md`
   - 現在の決定事項
   - 未決定事項
   - リスク
   - フェーズ別開発計画
   - 直近の作業

5. `05_AI実行指示書.md`
   - 別アプリのAIへ投げるための作業単位
   - ロール別プロンプト
   - 出力フォーマット
   - Done条件 / NG条件

6. `Henshin_Project_GCP_Bundle_v0_2.md`
   - 上記の要点を一つにまとめた統合版

---

## 推奨の読み順
- PM / オーナー: `01 → 02 → 04`
- エンジニア: `01 → 03 → 04`
- 別アプリのAI: `05` に `02` と `03` を添付

---

## 重要な前提
このプロダクトは「ヒーロー画像生成アプリ」ではない。  
**感情・文脈を起点にスーツを設計し、Quest上で変身試験を実行し、Quest内でReplayするプラットフォーム**である。


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


# 02_定義書

Version: 0.2  
用途: プロジェクト定義、前提固定、別AI/別エンジニアへ渡す共通基盤  
対象: PM、テックリード、XRエンジニア、Webエンジニア、3D担当、AI担当

---

## 1. プロジェクト名（仮）
**変身試験プラットフォーム / Henshin Trial Platform**

---

## 2. プロダクトの一文定義
ユーザーの **感情・思い・文脈** を起点に、  
**AIがスーツ案を提案し、Webでスーツを成立させ、Questで変身試験を行い、Quest内で試験Replayまで確認できる** プラットフォームを作る。

---

## 3. 体験の骨格
### 3.1 事前設計
- 参加者入力を受け取る
- AIが EmotionProfile / DesignVector / PartPlan を作る
- オペレーターが Suit Forge 上で調整する

### 3.2 試験本編
- Quest上で適合確認
- 仮組み
- 掛け声
- 蒸着 / 変身完了

### 3.3 試験後
- Quest内でReplay
- 必要なら管理画面または外部出力へ

---

## 4. 中核思想
### 4.1 変身は「完成品の配布」ではない
ユーザーは既製ヒーローになるのではなく、**自分の文脈から立ち上がったスーツを試験する**。

### 4.2 AIは提案者・鍛造補助である
AIは以下に限定する。
- 感情 / 文脈整理
- デザイン方向性提案
- パーツ構成案提案
- 青写真 / 紋章 / 説明文生成
- 量産補助

### 4.3 3Dは成立性を優先する
MVPでは **素体 + パーツ + 表層差分** でスーツを成立させる。  
完全自動3D生成は研究線とする。

---

## 5. MVPで作るもの
- Webのスーツ鍛造画面
- Emotion / Context Analyzer
- Part Planner
- SuitManifest 保存
- Questでの変身試験
- Quest内Replay
- Archive / Session保存

## 6. MVPで作らないもの
- 毎回完全新規のフル3D自動生成
- WebXR本編
- Webカム蒸着体験
- 一般ユーザー向け大規模公開運用

---

## 7. 論理サービス
### 7.1 Emotion / Context Analyzer
入力を構造化し、EmotionProfile を作る。

### 7.2 Design Resolver / Part Planner
EmotionProfile をスーツ方向性とパーツ案へ変換する。

### 7.3 Suit Forge Web
素体とパーツを組み立て、SuitManifest を成立させる。

### 7.4 Suit Registry
SuitManifest、PartCatalog、Artifact、Version を保持する。

### 7.5 Transform Runtime / Replay Runtime
Quest上で試験とReplayを実行する。

---

## 8. 用語
### 8.1 EmotionProfile
感情・思い・態度の構造化データ。

### 8.2 DesignVector
EmotionProfile から変換したデザイン中間表現。

### 8.3 PartPlan
AIが出力する抽象的なパーツ構成案。

### 8.4 PartCatalog
実在パーツ辞書。

### 8.5 SuitManifest
スーツ成立の正本。

### 8.6 Merged GLB
共有・確認用の副生成物。

### 8.7 Morphotype
参加者の体躯情報。

### 8.8 TransformSession
1回の試験セッション。

### 8.9 ReplayScript
Quest内Replayの再生指示データ。

---

## 9. 3Dモデル方針
### 9.1 レイヤー
#### 素体
- 密着スーツ
- 基礎体型

#### パーツ
- ヘルメット
- チェスト
- ショルダー
- アーム
- ベルト
- レッグ
- バックユニット
- エンブレム

#### 表層差分
- マテリアル
- 発光ライン
- 紋章
- 刻印 / テクスチャ

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

### 9.3 量産方針
#### 本線
- 規格化パーツをカタログ化
- AIは構成案を出す
- システムが組む

#### 補助線
- Blender Python による派生パーツ量産
- 必要に応じてMCPでBlender制御

#### 研究線
- Hunyuan3Dなどの粗3D生成
- 直接本番へ入れない

---

## 10. GCP方針
### 10.1 正本
- Cloud SQL(PostgreSQL)
- Cloud Storage

### 10.2 実行
- Cloud Run
- Cloud Tasks

### 10.3 AI
- Vertex AI

### 10.4 補助
- Firebase Auth
- Firestore（必要時のみ）

---

## 11. WebとQuestの関係
### 11.1 Web
- スーツを成立させる場所
- 設計・保存・登録

### 11.2 Quest
- 試験を実行する場所
- 変身 / Replay

### 11.3 接続
- `SuitID + SuitManifest` でつなぐ
- 本編は GLB を正本にしない

---

## 12. 体験のロアの扱い
世界観は前面に出さない。  
ただし以下にロアの厚みを埋め込む。
- 状態名
- Replay注釈
- 記録用語
- 封印 / 適合 / 仮組み などの工程名

これにより、サービス画面では説明過多にせず、体験の厚みだけを残す。


# 03_仕様書

Version: 0.2  
用途: エンジニア向け実装叩き台（GCP版）

---

## 1. システム全体構成

```text
[Participant / Operator Input]
  ↓
[Emotion / Context Analyzer]
  ↓
[DesignVector / PartPlan]
  ↓
[Suit Forge Web]
  ├─ PartCatalog 読み込み
  ├─ 素体 + パーツ組み立て
  ├─ プレビュー
  ├─ SuitManifest保存
  └─ optional: Merged GLB生成
  ↓
[Cloud Run APIs]
  ├─ Suit Registry API
  ├─ Session API
  ├─ Replay API
  └─ AI Orchestrator API
  ↓
[Primary Data Layer]
  ├─ Cloud SQL(PostgreSQL)
  └─ Cloud Storage
  ↓
[Quest Transform Runtime]
  ├─ SuitManifest取得
  ├─ ローカルパーツ再構成
  ├─ Morphotype適用
  ├─ 変身試験
  ├─ TransformSession記録
  └─ ReplayScript取得/生成
  ↓
[Quest Replay Runtime]
  └─ ReplayScriptで再生
```

---

## 2. 採用技術
### 2.1 Web
- React
- TypeScript
- PlayCanvas / `@playcanvas/react`
- Firebase Hosting

### 2.2 Backend
- Cloud Run
- Cloud SQL for PostgreSQL
- Cloud Storage
- Cloud Tasks
- Vertex AI
- Firebase Authentication
- optional: Firestore

### 2.3 Quest
- Unity
- OpenXR
- Meta Quest Support
- optional: glTFast

### 2.4 3D制作
- Blender
- Blender Python API
- optional: Blender MCP

---

## 3. バウンデッドコンテキスト
### 3.1 Suit Forge Context
責務:
- Emotion入力
- AI提案表示
- PartCatalogからの組み立て
- SuitManifest成立
- 登録

### 3.2 Registry Context
責務:
- Suit 正本管理
- Version 管理
- Artifact 管理
- 参照用メタデータ管理

### 3.3 Trial Context
責務:
- Quest変身試験
- 適合確認
- 状態遷移
- セッション記録

### 3.4 Replay Context
責務:
- ReplayScript生成
- Quest内Replay再生
- 必要に応じたエクスポート準備

---

## 4. データモデル

### 4.1 EmotionProfile
```json
{
  "emotion_profile_id": "EP-0001",
  "bravery": 0.85,
  "restraint": 0.70,
  "protectiveness": 0.90,
  "mysticism": 0.55,
  "context_tags": ["正義", "未来志向", "仲間想い"],
  "raw_input": "仲間を守り、未来を切り開く存在になりたい。"
}
```

### 4.2 DesignVector
```json
{
  "design_vector_id": "DV-0001",
  "silhouette": "sharp",
  "armor_mass": "medium",
  "helmet_type": "visor",
  "shoulder_volume": "high",
  "palette_family": "silver_red_cyan",
  "emissive_style": "core_line",
  "combat_bias": "speed_close_range"
}
```

### 4.3 PartPlan
```yaml
theme: vanguard
helmet:
  style: visor
  aggression: medium
  silhouette: sharp
chest:
  emphasis: core
  armor_mass: medium
arms:
  type: bracer
legs:
  mobility: high
back_unit:
  type: wing_booster
palette:
  primary: carmine
  secondary: titanium
  accent: cyan
```

### 4.4 SuitManifest
```json
{
  "suit_id": "SUIT-X01-0241",
  "version": 3,
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
  }
}
```

### 4.5 Morphotype
```json
{
  "morphotype_id": "M-0032",
  "height": 173,
  "shoulder_width": 44.2,
  "hip_width": 31.0,
  "arm_length": 59.4,
  "leg_length": 92.0,
  "torso_length": 58.2,
  "scale": 1.0,
  "source": "manual|quest|mocopi",
  "confidence": 0.82
}
```

### 4.6 TransformSession
```json
{
  "session_id": "TS-20260527-012",
  "suit_id": "SUIT-X01-0241",
  "morphotype_id": "M-0032",
  "participant_id": "P-250527-012",
  "status": "completed",
  "events": [
    { "t": 0.0, "type": "fit_start" },
    { "t": 2.8, "type": "fit_confirmed" },
    { "t": 5.1, "type": "dry_fit_complete" },
    { "t": 8.7, "type": "voice_prompt" },
    { "t": 10.4, "type": "voice_detected" },
    { "t": 10.8, "type": "transformation_begin" },
    { "t": 14.6, "type": "deposition_complete" },
    { "t": 16.1, "type": "seal_complete" }
  ],
  "compatibility_score": 0.936
}
```

### 4.7 ReplayScript
```json
{
  "session_id": "TS-20260527-012",
  "timeline": [
    { "t": 2.8, "label": "適合確定", "camera": "front_close" },
    { "t": 10.8, "label": "変身開始", "camera": "wide_center" },
    { "t": 14.6, "label": "蒸着完了", "camera": "orbit_right" },
    { "t": 16.1, "label": "封印完了", "camera": "front_hero" }
  ],
  "annotations": [
    { "t": 2.8, "text": "身体適合が確定しました。" },
    { "t": 10.8, "text": "変身シーケンスを起動。" },
    { "t": 14.6, "text": "装甲定着完了。" }
  ]
}
```

---

## 5. Cloud SQLテーブル案
### 5.1 suits
- id
- suit_id
- current_version
- status
- created_at
- updated_at

### 5.2 suit_versions
- id
- suit_id
- version
- suit_manifest_json
- preview_path
- blueprint_path
- emblem_path
- merged_glb_path
- created_at

### 5.3 part_catalog
- id
- part_type
- part_key
- display_name
- asset_path
- socket_name
- compatible_base_bodies
- tags_json
- is_active

### 5.4 emotion_profiles
- id
- raw_input
- profile_json
- created_at

### 5.5 design_vectors
- id
- emotion_profile_id
- vector_json
- created_at

### 5.6 part_plans
- id
- design_vector_id
- yaml_text
- resolved_json
- created_at

### 5.7 transform_sessions
- id
- session_id
- participant_id
- suit_id
- morphotype_id
- status
- compatibility_score
- started_at
- completed_at

### 5.8 transform_events
- id
- session_id
- event_time
- event_type
- payload_json

### 5.9 replay_scripts
- id
- session_id
- replay_script_json
- created_at

---

## 6. Cloud Storage オブジェクト配置案
```text
gs://henshin-assets/
  suits/
    SUIT-X01-0241/
      v3/
        preview.png
        blueprint.png
        emblem.png
        merged.glb
  sessions/
    TS-20260527-012/
      replay-thumb-01.png
      export-video.mp4
```

---

## 7. API一覧
### 7.1 Emotion / Design
- `POST /v1/emotion/analyze`
- `POST /v1/design/resolve`
- `POST /v1/parts/plan`

### 7.2 Suit Forge / Registry
- `GET /v1/parts/catalog`
- `POST /v1/suits`
- `GET /v1/suits/{suitId}`
- `POST /v1/suits/{suitId}/versions`
- `POST /v1/suits/{suitId}/artifacts:upload-url`

### 7.3 Session / Trial
- `POST /v1/sessions`
- `POST /v1/sessions/{sessionId}/events`
- `POST /v1/sessions/{sessionId}/complete`
- `GET /v1/sessions/{sessionId}`

### 7.4 Replay
- `POST /v1/sessions/{sessionId}/replay-script:generate`
- `GET /v1/sessions/{sessionId}/replay-script`

### 7.5 Operator / Live
- `GET /v1/operator/queue`
- `GET /v1/operator/session/{sessionId}/live`

---

## 8. Web側責務
### 8.1 Emotion入力
- テキスト入力
- タグ入力
- AI解析呼び出し

### 8.2 Suit Forge
- PartCatalog読み込み
- 素体＋パーツ組み立て
- プレビュー
- 色 / マテリアル調整
- 保存
- Quest送信準備

### 8.3 Artifact生成
- preview.png
- blueprint.png
- emblem.png
- optional merged.glb

---

## 9. Quest側責務
### 9.1 Transform Runtime
- SuitManifest取得
- ローカルパーツ再構成
- Morphotype適用
- 適合確認
- 仮組み
- 掛け声
- 蒸着完了

### 9.2 Replay Runtime
- ReplayScript取得
- タイムライン再生
- 注釈表示
- 必要なら録画 / 共有出力

### 9.3 Quest内で必須の状態遷移
- `fit_confirm`
- `dry_fit`
- `voice_prompt`
- `transform_begin`
- `deposition_complete`
- `seal_complete`
- `replay_ready`

---

## 10. 3Dアセット規格
### 10.1 素体
- 人型基準向け1〜2種
- ソケット命名は固定
- スケール基準統一

### 10.2 パーツ
- 各ソケットに対して1対1対応
- 変形やスケール補正を許す範囲を定義
- 左右対称パーツは別IDまたはmirror ruleを明示

### 10.3 材質
- `undersuit`
- `armor_main`
- `armor_sub`
- `emissive`

### 10.4 命名規則
- `helmet_visor_03`
- `chest_core_05`
- `arm_bracer_02`
- `back_wing_01`
- `emblem_solar_01`

---

## 11. 非機能要件
### 11.1 安定性
- Quest本編は Manifest再構成方式を基本とする
- GLB直読みは補助

### 11.2 性能
- Webは初回読み込みとプレビュー応答を重視
- Questは変身演出中のフレーム維持を重視

### 11.3 可観測性
- Cloud Logging
- セッションごとの event log
- 失敗理由の分類

### 11.4 セキュリティ
- 管理APIは Firebase Auth または社内認証で保護
- アセットアップロードは署名URL経由

---

## 12. 将来拡張
- Firestoreによるライブセッション同期
- WebXR companion view
- 生成三面図からの半自動3D試作
- AIによる Replay 解説高度化


# 04_進捗差分とロードマップ

Version: 0.2  
用途: 現在地の整理と次の打ち手の固定

---

## 1. 現在決まっていること
### 1.1 プロダクト
- 体験は「変身試験」である
- Replay は Quest内で確認したい
- Webカム蒸着は別議論に切り離す

### 1.2 アーキテクチャ
- Webでスーツを成立させる
- Questで試験を実行する
- QuestでReplayを見る
- `SuitManifest` を正本とする
- GCP balanced architecture を採用する

### 1.3 3D方針
- 素体 + パーツ + 表層差分
- AIは完全3D生成ではなく、構成提案・量産補助

### 1.4 参考設計思想
- ブラウザ側でシーングラフを組み、その結果を成果物にする考え方を参考にする【170:0†Tabetaine 3Dモデル生成パイプライン 技術解説†L8-L15】
- ただし本件ではGLBを正本にしない

---

## 2. この版で変わったこと
### 2.1 Cloudflareベース案からGCP案へ更新
旧案:
- Hono + Workers + R2 + D1

新案:
- Firebase Hosting
- Cloud Run
- Cloud SQL
- Cloud Storage
- Vertex AI
- Cloud Tasks
- optional Firestore

### 2.2 Replay要件の格上げ
旧案:
- Replayは保存/後確認

新案:
- **Quest内 Replay が必須**

### 2.3 正本の明確化
旧案:
- GLBも強い存在感を持っていた

新案:
- 正本は SuitManifest
- GLBは共有・確認用の副生成物

---

## 3. 未決定事項
### 3.1 Web側
- Emotion入力は自由記述のみか、質問フォーム併用か
- AI提案をどこまで自動反映するか
- Blueprint / Emblem 生成をMVPに含めるか

### 3.2 Backend側
- FirestoreをMVPで使うか
- 認証をFirebase Authで先に入れるか、社内限定で後回しか
- ReplayScript生成を同期APIにするか非同期ジョブにするか

### 3.3 Quest側
- Morphotype取得方法（手入力 / Quest簡易測定 / mocopi）
- Voice triggerの実装方式
- Replay中のカメラ制御粒度

### 3.4 3D側
- 素体の初期バリエーション数
- PartCatalogの最初のスロット構成
- Blender Python 自動化の優先度

---

## 4. リスク
### 4.1 リスクA: 3Dの規格が先に固まらない
影響:
- WebとQuestで見た目が一致しない
- AI提案が実在パーツへ落ちない

対策:
- まず PartCatalog 最小版を先に作る
- ソケット規格を固定する

### 4.2 リスクB: Backendが重くなりすぎる
影響:
- 早期PoCが遅れる

対策:
- Firestoreは optional にする
- APIは Cloud Run 単一サービスから始める

### 4.3 リスクC: Quest Replayが後回しになって設計が崩れる
影響:
- 変身本編のログ粒度が足りない

対策:
- 変身状態遷移と ReplayScript を同時設計する

### 4.4 リスクD: AIが“それっぽいが使えない案”を出す
影響:
- 工数だけ増える

対策:
- LLMの出力は抽象案まで
- Resolverで実在カタログに解決する

---

## 5. フェーズ別ロードマップ
### Phase 0: 基準固定（1週）
成果物:
- SuitManifest schema
- PartCatalog schema
- ソケット命名規約
- GCP構成決定

Done:
- 仕様の正本が固定される

### Phase 1: Web最小成立（2週）
成果物:
- React + PlayCanvas の Suit Forge
- 素体1種 + パーツ数点
- 保存せずにプレビューできる

Done:
- 画面上でスーツが成立する

### Phase 2: Registry + 保存（2週）
成果物:
- Cloud Run API
- Cloud SQL
- Cloud Storage
- SuitManifest保存
- preview生成

Done:
- SuitIDを払い出せる

### Phase 3: AI提案導入（2週）
成果物:
- EmotionAnalyzer
- PartPlanner
- Resolver

Done:
- 入力→AI提案→Web反映が回る

### Phase 4: Quest本編（3週）
成果物:
- Unity/OpenXRプロジェクト
- SuitManifest取得
- 変身状態遷移

Done:
- Questで1着の試験ができる

### Phase 5: Quest Replay（2週）
成果物:
- TransformSessionログ
- ReplayScript
- Quest内Replay UI

Done:
- QuestでReplay確認できる

### Phase 6: 量産と運用（継続）
成果物:
- Blender Python自動化
- PartCatalog拡張
- Operator Console整備

---

## 6. 今週やるべきこと
### 6.1 PM / オーナー
- このGCP版構成を承認する
- MVP範囲を再確認する

### 6.2 Web / 3D
- ソケット規格の初版を決める
- 素体1種と主要パーツの最小セットを切る

### 6.3 Backend
- Cloud Run / Cloud SQL / Cloud Storage の最小構成を作る
- SuitManifest の保存APIを生やす

### 6.4 Quest
- Unity + OpenXR + Meta Quest Support の初期プロジェクトを立ち上げる
- SuitManifest mock を読み込む

### 6.5 AI
- EmotionProfile / DesignVector / PartPlan の出力フォーマットを固定する

---

## 7. 直近のマイルストーン
### M1
- SuitManifest v0.1 固定
- PartCatalog v0.1 固定

### M2
- Web Suit Forge が一着成立

### M3
- SuitID を Quest へ送れる

### M4
- Quest で変身試験完走

### M5
- Quest内 Replay 完走


# 05_AI実行指示書

Version: 0.2  
用途: 別アプリのAIにそのまま流し込むための実行指示

---

## 0. 共通ルール
### 0.1 固定前提
以下は変更しないこと。
- Webは PlayCanvas + React
- Backendは GCP balanced architecture
- Quest本編は Unity + OpenXR
- 正本は SuitManifest
- Replayは Quest内で行う
- MVPでは完全自動3D生成を本線にしない

### 0.2 AIの役割
AIは以下を支援する。
- 構造化
- 設計提案
- スキーマ作成
- API定義
- 状態遷移定義
- タスク分解

AIは勝手にアーキテクチャを変更しないこと。

### 0.3 出力のルール
- Markdownで出す
- 必ず見出しをつける
- 必ず「前提」「出力」「未解決」を分ける
- JSON/YAMLはコードブロックで出す
- 曖昧な点は仮定を明記する

---

## 1. Architecture AI への依頼
### 入力
- `01_アーキテクチャ決定記録_GCP.md`
- `02_定義書.md`
- `03_仕様書.md`

### 指示
以下を出力せよ。
1. GCP構成図
2. サービス一覧
3. データフロー
4. リスク一覧
5. MVPに必要な最小GCP構成

### Done条件
- Cloud Run / Cloud SQL / Cloud Storage / Vertex AI / Firebase Auth の役割が明確
- Firestore が optional 扱いになっている
- Quest Replay の位置が欠落していない

---

## 2. Schema AI への依頼
### 指示
以下の完全版を出力せよ。
- SuitManifest JSON Schema
- PartCatalog JSON Schema
- EmotionProfile JSON Schema
- DesignVector JSON Schema
- PartPlan YAML spec
- TransformSession JSON Schema
- ReplayScript JSON Schema

### 制約
- 互いの参照関係を明記する
- `id`, `version`, `created_at`, `updated_at` の扱いを揃える

### Done条件
- バリデーション可能な粒度になっている
- WebとQuestで同じ定義を使える

---

## 3. Backend AI への依頼
### 指示
以下を出力せよ。
1. Cloud SQL テーブル定義（DDL案）
2. Cloud Run API一覧
3. Cloud Storage パス設計
4. Cloud Tasks 利用箇所
5. 認証・権限設計の最小案

### 制約
- SuitManifest を正本とする
- GLBは副生成物として扱う
- Firestoreは必須にしない

### Done条件
- MVPで過剰でない
- ローカル開発からステージングへ移行しやすい

---

## 4. Web AI への依頼
### 指示
以下を出力せよ。
1. Suit Forge の画面状態一覧
2. PlayCanvas と React の責務分離
3. PartCatalog のロード方式
4. 保存フロー
5. Quest送信フロー

### 制約
- 管理画面的すぎず、実用品として成立すること
- WebXR本編は含めないこと

### Done条件
- 左:入力 / 中央:プレビュー / 右:パーツ の基本構成が保たれる
- 保存とQuest送信が別状態として扱われる

---

## 5. Quest AI への依頼
### 指示
以下を出力せよ。
1. Transform Runtime の state machine
2. Replay Runtime の state machine
3. SuitManifest 読み込みから再構成までの流れ
4. Morphotype の適用順序
5. 変身試験中に記録すべきイベント一覧

### 制約
- Quest内Replayを必須要件として扱うこと
- Voice trigger を状態遷移に入れること
- Manifest再構成方式を前提にすること

### Done条件
- 変身本編とReplayが別runtimeまたは別modeとして整理されている
- ReplayScript に必要な最小イベントが定義されている

---

## 6. 3D / Blender AI への依頼
### 指示
以下を出力せよ。
1. ソケット規格表
2. 素体の要件
3. パーツの要件
4. 命名規則
5. Blender Python で量産できる作業の一覧

### 制約
- MVPでは規格化パーツを本線にする
- 完全AI生成3Dを前提にしない

### Done条件
- WebとQuestで共通利用できる
- PartCatalog登録に必要な属性が漏れていない

---

## 7. AI提案ロジックAIへの依頼
### 指示
以下を出力せよ。
1. EmotionProfile生成ルール
2. DesignVector変換ルール
3. PartPlan生成ルール
4. Resolverルール
5. NG組み合わせルール

### 制約
- LLMが直接 `helmet_visor_03` のような最終IDを決め切らないこと
- まず抽象案、次にResolverで実在パーツへ落とすこと

### Done条件
- 抽象案→実在パーツ の二段構えが明確
- カタログ変更に耐えられる

---

## 8. AIにそのまま投げるテンプレ
```text
あなたはこのプロジェクトの実装支援AIです。
以下の固定前提を変更せずに、指定された成果物だけを出力してください。

固定前提:
- Web: PlayCanvas + React
- Backend: GCP balanced architecture
- Quest: Unity + OpenXR
- 正本: SuitManifest
- Replay: Quest内必須
- MVP: 規格化パーツ本線、完全自動3D生成は研究線

今回ほしい成果物:
{ここに Architecture / Schema / Backend / Web / Quest / 3D / AI提案ロジック のいずれかを明記}

出力条件:
- Markdown
- 見出しあり
- JSON/YAMLはコードブロック
- 仮定があれば明記
- 未解決事項を最後に列挙
```
