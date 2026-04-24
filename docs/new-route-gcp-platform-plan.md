# 新規路線 GCP プラットフォーム段階移行計画

Version: 0.1
Status: Draft
更新日: 2026-04-24

## 0. この計画の立場

この計画は、現行の動くモジュールを捨てずに、GCP 主軸の新規路線へ段階的に移行するための実行計画である。

新規路線とは、単に GCP、PlayCanvas、Unity を導入することではない。正本、配布、実行、記録、監査を分け、各モジュールを同じ契約に従わせることである。

## 1. ロアから来る不変条件

このプロジェクトの中核価値は、強さや派手さではなく Integrity である。体験で見せるものは最小限の手順、ログ、証明であり、裏側には制度、規格、許認可、記録、監査が存在する。

計画上の不変条件は次の通り。

| 不変条件 | 実装上の意味 |
|---|---|
| 認証がある | 誰がスーツを作り、誰が試験したかを記録する |
| 記録が残る | Suit、Trial、Event、Replay は追跡可能にする |
| 許認可がある | AI案や部品選択は必ず Catalog / Resolver を通す |
| 物質定着がある | スーツは気分の絵ではなく Manifest と PartCatalog で成立する |
| 監査可能である | SQL、event log、artifact、version を分離して残す |
| 未解明を残す | UIでロアを説明しすぎず、ログと手順に圧をにじませる |

## 2. 採用する大方針

GCP 主軸で進める。ただし一気に全部を置き換えない。

| 領域 | 新規路線の採用先 | 既存資産の扱い |
|---|---|---|
| Web | React + PlayCanvas + Firebase Hosting | 既存 viewer/dashboard の知見を Suit Forge に移植 |
| Auth | Firebase Authentication | 初期は operator/dev user だけでもよい |
| API | Hono on Cloud Run | 既存 dashboard_server の API 境界を参考にする |
| Canonical DB | Cloud SQL for PostgreSQL | SuitSpec / session 成果物を正規 schema に投影 |
| Live State | Cloud Firestore | 既存 live/mocopi/operator 状態を live docs 化 |
| Asset | Cloud Storage | mesh/texture/manifest/replay artifact を配布単位にする |
| Async | Cloud Tasks | 生成、preview、blueprint、replay補助を非同期化 |
| AI | Vertex AI | EmotionProfile、DesignVector、PartPlan、Blueprint/Emblem に限定 |
| Quest | Unity + OpenXR + Meta Quest Support | Quest Browser/IWSDK は互換検証レーンとして残す |
| 3D | Blender + GLB + PartCatalog | 既存 mesh/VRM/armor-canon を初期 Catalog seed にする |

## 3. 正本の階層

正本を分裂させないため、役割を固定する。

| 契約 | 役割 | 正本性 |
|---|---|---|
| SuitSpec | 制作、編集、生成、body-fit 用の作業契約 | Working draft |
| SuitManifest | Quest 実行、配布、Replay 参照用の固定済み契約 | Runtime canonical |
| PartCatalog | 実在部品、socket、material slot、互換条件の台帳 | Catalog canonical |
| TransformSession | 試験単位の記録 | SQL canonical |
| TransformEvent | 試験中に起きた出来事の追記ログ | Event canonical |
| ReplayScript | Event から作る再生用データ | Derived artifact |
| GLB | 共有、確認、デバッグ用の副生成物 | Derived artifact |

最初の実装では、SuitManifest は SuitSpec からの projection として生成する。これにより現行資産を活かしつつ、Quest/Cloud 側は Manifest だけを読む構造にできる。

## 4. フェーズ計画

### Phase 0: Contract Lock

目的: Web、Backend、Quest、AI が同じ言葉で並行開発できる状態を作る。

成果物:
- SuitManifest JSON Schema
- PartCatalog JSON Schema
- TransformSession / TransformEvent JSON Schema
- ReplayScript JSON Schema
- SuitSpec -> SuitManifest projection spec
- SQL / Firestore / GCS 配置表

既存資産:
- schemas/suitspec.v0.2.schema.json
- schemas/morphotype.v0.2.schema.json
- viewer/shared/armor-canon.js
- docs/roadmap.md
- docs/quest3-local-demo.md

完了条件:
- 1つの sample SuitSpec から sample SuitManifest が生成できる
- PartCatalog に最低限の helmet/chest/back/shoulder/arm/waist/leg/boot/hand が載る
- TransformEvent enum が MVP 範囲で閉じている

軌道修正ゲート:
- 既存 SuitSpec と Manifest の差が大きすぎる場合、Manifest を小さくする
- PartCatalog が膨らみすぎる場合、ACTIVE / EXPERIMENTAL / RETIRED の status で分ける

### Phase 1: GCP Backbone

目的: 新規路線の背骨だけを立てる。見た目や Unity より先に、保存と配布を成立させる。

成果物:
- Cloud Run API skeleton
- Cloud SQL schema draft
- Cloud Storage bucket / path rule
- Firebase Auth minimum setup
- health / suits / manifests / catalogs の最小 API

初期 API:
- GET /health
- GET /v1/catalog/parts
- POST /v1/suits
- GET /v1/suits/:suitId
- POST /v1/suits/:suitId/manifest
- GET /v1/manifests/:manifestId

完了条件:
- ローカル sample ではなく、Cloud Run API 経由で Manifest を保存/取得できる
- GCS に manifest.json と preview artifact を置ける
- SQL が canonical、GCS が artifact、Firestore が live という境界が壊れていない

軌道修正ゲート:
- API 実装が重い場合、まず local Hono + local Postgres で契約検証する
- Cloud SQL 接続が遅い場合、DB schema draft を優先して deploy は後ろへ送る

### Phase 2: Live Trial Layer

目的: 変身試験の現在状態を見えるようにする。ロア上の監査可能な手順を live state と event log に分ける。

成果物:
- Firestore live_trials
- Firestore quest_devices
- Firestore operator_dashboards
- TransformEvent append API
- Operator Monitor minimum view

完了条件:
- Trial 開始、現在 step 更新、event append、完了が追える
- Firestore に置く値は current state に限定され、正本履歴は SQL に残る

軌道修正ゲート:
- Firestore に履歴を持ち始めたら設計を戻す
- Operator Monitor が UI 先行になったら、Event / State を先に固める

### Phase 3: Suit Forge MVP

目的: Web でスーツを成立させる。ここで PlayCanvas を導入するが、正本は scene ではなく Manifest に置く。

成果物:
- React Suit Forge
- PlayCanvas preview
- Emotion input
- AI proposal placeholder
- Part selection
- Material preset
- Manifest save
- Send to Quest request

完了条件:
- 1着を Web で組み、Manifest として保存できる
- Web preview と Manifest の parts/materials が一致する
- PlayCanvas の scene graph が正本になっていない

軌道修正ゲート:
- PlayCanvas 導入が詰まる場合、既存 Three.js viewer を preview adapter として一時利用する
- UI が増えすぎる場合、Emotion、Parts、Preview、Save の4操作に戻す

### Phase 4: AI Proposal Integration

目的: AIを自由生成ではなく、構造化提案と Resolver に限定する。

成果物:
- EmotionProfile generator
- DesignVector generator
- PartPlan generator
- PartPlan resolver
- substitutions / warnings 表示

完了条件:
- AI は part_id を自由生成しない
- PartPlan は必ず PartCatalog に解決される
- 解決できない提案は warnings と substitutions を持つ

軌道修正ゲート:
- AIが派手だが実装不能な案を出す場合、PartPlan schema を狭める
- Vertex AI 接続が重い場合、既存 part_generation.py の provider 抽象を暫定利用する

### Phase 5: Quest Trial MVP

目的: Quest 内で変身試験を完走する。Unity/OpenXR は Manifest runtime として実装する。

成果物:
- Unity OpenXR project
- Firebase/Auth or device binding
- Manifest fetch
- Local PartCatalog load
- Morphotype apply
- Transform state machine
- Event upload

完了条件:
- Quest で 1着の Manifest を読み、試験を完走できる
- Trial の event log が SQL に残る
- Firestore に live step が反映される

軌道修正ゲート:
- Unity の初期負荷が大きい場合、Quest Browser/IWSDK で Manifest fetch と Trial log を先に検証する
- Quest 実機で asset load が重い場合、GLB を軽量化し、parts catalog を分割する

### Phase 6: Quest Replay MVP

目的: Replay を動画ではなく、TransformEvent から再構成される体験記録として成立させる。

成果物:
- ReplayScript generator
- Quest Replay player
- event jump
- camera/fx segment
- Replay artifact save

完了条件:
- Trial 完了直後に Quest 内で Replay を見られる
- ReplayScript は TransformEvent から説明できる
- MP4 は副生成物扱いのまま保つ

軌道修正ゲート:
- Replay が演出過多になった場合、event + camera + fx の最小構成へ戻す
- 動画書き出し要望が強くなった場合も、まず ReplayScript 正本を維持する

### Phase 7: Production Hardening

目的: 展示、複数ユーザー、監査、運用品質へ進む。

成果物:
- CI
- migration
- audit viewer
- role policy
- asset validation
- fallback mode
- deployment runbook

完了条件:
- 新しいスーツ、試験、Replay を追跡できる
- 障害時に local/demo mode へ戻せる
- schema 変更が version と migration で管理される

## 5. プラットフォーム導入順

| 順位 | 導入 | 理由 |
|---:|---|---|
| 1 | Schema / adapter | ここがないと全員が別のものを作る |
| 2 | Cloud Run + Cloud SQL + GCS | 正本保存と配布が先 |
| 3 | Firestore | live state は Trial が見えてから |
| 4 | PlayCanvas | Manifest の preview/editor として導入 |
| 5 | Vertex AI | Catalog / Resolver ができてから投入 |
| 6 | Unity/OpenXR | Manifest runtime として着手 |
| 7 | Cloud Tasks | 重い処理が見えた段階で本格化 |

## 6. 判断の型

毎回の設計判断は、次の質問に答えられるものだけ採用する。

1. これはロア上の「認証・記録・許認可・定着・監査」のどれを支えるか
2. 正本はどこか
3. これは MVP 必須か
4. 後で変えると何が壊れるか
5. 既存モジュールを adapter として使えるか
6. 失敗したときに local/demo mode に戻れるか

## 7. 初期チケット

P0:
- SuitManifest schema を作る
- SuitSpec -> SuitManifest projection を作る
- PartCatalog seed を armor-canon / mesh assets から作る
- TransformEvent enum を閉じる
- SQL / Firestore / GCS の配置表を作る

P1:
- Hono API skeleton を作る
- local Postgres or Cloud SQL schema draft を作る
- GCS artifact path rule を実装に落とす
- Firestore live docs を3コレクションで始める
- Operator Monitor minimum view を作る

P2:
- PlayCanvas Suit Forge preview
- Vertex AI prompt / structured output
- Quest Unity Manifest loader
- ReplayScript generator

## 8. やらないこと

今は次を主戦場にしない。

- 完全自動 3D 生成
- Unity prefab を正本にする
- PlayCanvas scene を正本にする
- Firestore に canonical history を置く
- Replay を MP4 書き出し前提にする
- UI の見た目を先に磨き込む

## 9. 次の実行順

1. SuitManifest schema v0.1
2. PartCatalog schema v0.1
3. SuitSpec -> SuitManifest adapter
4. sample manifest 生成
5. API skeleton
6. SQL / Firestore / GCS 配置表
7. Suit Forge MVP
8. Quest Trial MVP
9. Replay MVP

この順番なら、新規路線を仕込みながら、既存モジュールを失わずに進められる。
