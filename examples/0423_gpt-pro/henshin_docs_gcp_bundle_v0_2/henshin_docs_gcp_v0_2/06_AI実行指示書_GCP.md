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
