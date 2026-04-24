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
