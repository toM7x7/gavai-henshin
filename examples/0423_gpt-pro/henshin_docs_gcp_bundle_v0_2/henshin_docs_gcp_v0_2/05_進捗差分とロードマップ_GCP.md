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
