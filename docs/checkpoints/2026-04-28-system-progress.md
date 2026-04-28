# System Progress Checkpoint - 2026-04-28

Purpose: PC電源OFF後に、最短で同じ地点へ戻るための進捗チェックポイント。

参照元:
- `README.md`
- `docs/new-route-phase1-implementation-plan.md`
- `docs/base-suit-overlay-contract.md`
- `docs/new-route-design-coherence-audit.md`
- `docs/new-route-gcp-platform-plan.md`
- `docs/new-route-gcp-readiness.md`
- `docs/backend-gcp-migration-notes.md`
- `docs/new-route-operator-checklist.md`
- `docs/quest-vr-henshin-experience-design.md`
- `docs/quest-vr-uiux-notes.md`
- `docs/priority-backlog.md`
- `docs/vrm-first-authoring-plan.md`
- `examples/henshin_docs_bundle_v0_1/`
- `examples/henshin_docs_gcp_bundle_v0_2/henshin_docs_gcp_v0_2/`
- `examples/message (1).txt`

## 現在地

合言葉は引き続きこれ。

```text
Web: Suit Forge -> Quest: Henshin Trial -> Replay: Archive
```

プロダクト上の不変条件は `Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す`。ただし現時点の Web/dashboard は外部公開用の完成画面ではなく、生成、契約確認、Quest送信前チェック、trial/replay proof を見る内部オペレーター面。

現在動いている主線:
- `SuitSpec` を authoring source として保存する。
- `SuitSpec -> SuitManifest` を projection し、Web preview / Quest / Replay の runtime contract にする。
- Web Forge は4文字の `recall_code` を発行し、Quest は内部IDではなく `GET /v1/quest/recall/{recallCode}` で準備済み suit/manifest を読む。
- Quest trial は `TransformSession` と canonical event log を作り、`ReplayScript` へ落とす。
- durable 化は未完了。現ローカル実装は `sessions/new-route/...` 配下の JSON 保存が中心で、Cloud SQL / GCS / Firestore への本書き込みは次段。

第一 canonical suit seed:

```text
config/new-route.canonical.json
examples/suitspec.sample.json
VDA-AXIS-OP-00-0001
```

この seed は `legacy / stoic / clear_white` の identity lock 済み。`texture_fallback.mode = palette_material` と `fit_contract` により、ignored な `sessions/...` texture がない fresh checkout でも palette material へ落ちる設計。

## Quest

Quest runtime は dashboard port ではなく Vite app の `5173`。Quest Browser が `localhost` 404 になる場合は `adb reverse` か LAN IP / LAN HTTPS を使う。

最短ローカル smoke:

```powershell
npm run dev
npm run dev:quest -- --host 0.0.0.0
```

Quest LAN smoke URL:

```text
http://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

実装済み/設計済みの要点:
- 既存 Quest/IWSDK demo は新規路線の integration harness。古いmockの再評価ではなく、`TransformSession`、canonical events、`ReplayScript` の橋渡し確認用。
- `mockTrigger=1` はローカル smoke bypass。実音声認識/TTS は Sakura AI Engine path。
- VR内の操作は `SpatialControlPanel` と左手/左コントローラー寄りの compact menu 方向。visitor-facing controls は日本語優先。
- first-person transformation は音声起動、archive replay は mirror / observer review path。
- HMD + controllers を暫定 live anchors として使い、`quest-live-pose.v0` samples を trial event log へ入れる方針。
- replay diagnostic は `LIVE` / `BODY` / `BODY+LIVE` / `STATIC` をPC HUDとVR panelに出す方向。
- helmet/hand は first-person 視界を塞ぐなら非表示可。mirror/archive は full body-sim trace を見せる。

確認すべき成功シグナル:
- Quest page status panel に `SUIT FORGE: NEW` が出る。
- Voice/mock trigger で `TransformSession` が作られる。
- `REPLAY ARCHIVE: RPL-...` まで進む。
- floating VR panel に forge / fit / trial / archive 状態が出る。
- status line に active fit contract と texture fallback が出る。

電源復帰後の replay proof:

```powershell
Invoke-RestMethod http://localhost:8010/v1/trials/latest | ConvertTo-Json -Depth 6
```

見る項目:
- `summary.state` が `ACTIVE`
- `summary.event_count > 0`
- `summary.replay_script_path` が `sessions/new-route/trials/.../replay-script.json`
- PC dashboard の `HENSHIN TRIAL / Replay Archive` card と一致

## Web

現Webの役割は「公開LP」ではなく、まず suit establishment と route proof。

主要URL:

```text
http://localhost:8010/viewer/suit-dashboard/
http://localhost:8010/viewer/armor-forge/
```

Web Forge の現在の contract:
- public form payload から `POST /v1/suits/forge` を呼ぶ。
- display name、declared height、archetype、palette、brief、selected armor parts を受ける。
- `recall_code`、readiness flags、public preview data を返す。
- internal `suit_id` / `manifest_id` は保存・versioning・DB rows・artifact paths 用。public UI の主役にしない。
- preview は base VRM/body baseline + armor overlay の T-pose armor stand。
- dashboard/API は `8010`、Quest runtime は `5173` という local split を明示する。

重要な可視化ルール:
- `visual_layers.contract_version = base-suit-overlay.v1`
- `base_suit_surface` と `armor_overlay_parts` の両方が必須。
- `vrm_only_is_valid = false`
- required overlay core は `helmet`, `chest`, `back`
- `minimum_visible_overlay_parts = 3`

つまり、VRMだけが表示されて「recallできた」は成功ではない。visible overlay parts がない recall は invalid generated-suit state。

2026-04-28時点の追加整理:
- `src/henshin/runtime_package.py` を追加し、`SuitSpec` / `SuitManifest` / `visual_layers` / `render_contract` を Quest/Web runtime 向けの `RuntimeSuitPackage` に正規化する境界を作った。
- `GET /v1/quest/recall/{recallCode}` は `runtime_package` を返す。Quest/IWSDK viewer は当面従来の `suitspec` / `manifest` を読むが、Unity/OpenXR / PlayCanvas / Cloud Run 版へ移す時は `runtime_package` を import checklist にできる。
- `runtime_package.runtime_checks.vrm_only_is_valid = false`。VRM単体表示は成功扱いにしない。
- `runtime_package.manifest.parts[*].texture_path` は最新SuitSpecから投影されるため、texture generation後に古いmanifestが残ってもruntime返却で表面情報が欠けない。

確認済み:

```powershell
$env:PYTHONPATH='src'; python -m pytest -q -p no:cacheprovider tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_new_route_api.py tests\test_dashboard_server.py
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
```

結果: `45 passed, 42 subtests passed`。

## 生成

現状の生成は「最終3D自動生成」ではなく、Fit-first / catalog-first の補助線。

既存実装/方針:
- Gemini API経由の blueprint/emblem 画像生成と module単位の部位別画像生成は既存。
- Web Forge の asset pipeline は `nano_banana` provider profile、`mesh_uv`、`uv_refine=true`、2K square atlas、SuitSpec texture write-back を想定。
- ただし `surface_generation_status=planned_not_generated` は「code発行とpreview成立はしたが、final texture atlas はまだ」という意味。
- `model_rebuild_job` が body fit / mesh rebuild の blocking track。
- `texture_probe_job` は seed/proxy mesh 上での速度確認や一時 write-back まで。
- `generate-parts` は並列化、cache、計測、summary order安定化済み。未変更partを明示skipする差分生成は未実装。

生成で守る線:
- AIは part_id を自由生成しない。EmotionProfile -> DesignVector -> PartPlan -> Resolver -> PartCatalog の順で実在パーツへ落とす。
- 実在 catalog に落ちない提案は warning / substitution にする。
- AIは「全部を生成する神」ではなく、提案者・鍛造補助。
- final texture lock は `mesh_fit_before_texture_final` が通るまで保留。

Tabetaine資料からの取り込み候補:
- PlayCanvas scene graph を成果物構造にし、`ExportEntity` 相当の親に base + added parts を束ねて GLB export するパターンは参考になる。
- ただし、このプロジェクトでは PlayCanvas scene を正本にしない。正本は `SuitSpec` / `SuitManifest` / `PartCatalog`。scene graph export は derived artifact の候補。

## GCP

GCP化の最初の対象は「全部載せ替え」ではなく、ローカルで既に動いている route の durable 版。

対象 shape:

```text
SuitSpec -> SuitManifest -> TransformSession -> TransformEvent -> ReplayScript
```

durable split:
- Cloud Run: API surface
- Cloud SQL PostgreSQL: source rows, versions, trials, events, audit log
- GCS: JSON artifacts, generated textures, previews, GLB, replay scripts, media
- Firestore: live Quest/operator state only
- Cloud Tasks: preview、GLB merge、replay media、heavy AI jobs など後続 async
- Secret Manager: DB credentials / optional API keys

Phase 1 skeleton の API cut:

```text
GET /health
GET /v1/catalog/parts
POST /v1/suits
GET /v1/suits/:suitId
POST /v1/suits/:suitId/manifest
GET /v1/manifests/:manifestId
```

defer:
- Emotion / Design / PartPlan APIs
- Quest send APIs
- Trial/Event/Replay APIs
- devices registration/status APIs
- async job APIs

理由は、catalog/manifest と trial event model が動く前に AI / Quest / jobs をCloud側へ寄せると境界が崩れるため。

準備メモ:
- GCP project name
- Artifact Registry repository
- Cloud Run service
- Cloud SQL PostgreSQL instance/database/API user
- GCS artifact bucket
- Firestore database
- Firebase Auth project/config
- Cloud Run service account
- Secret Manager secrets

## モデル品質

現在の品質判断は `VRM First -> Armor Authoring -> Parametric Variation`。画像/UV texture は最後に乗せる。

現baseline:
- `viewer/assets/vrm/default.vrm`
- `viewer/assets/vrm/baselines.json`
- `viewer/assets/meshes` に18 canonical `mesh.v1` seed parts
- current assets は seed/proxy。final authoring ceiling ではない。

最新 authoring audit snapshot:

```text
rebuild 11 / tune 3 / keep 4
```

Wave 1 P0:
- `chest`
- `back`
- `waist`
- `left_upperarm`
- `right_upperarm`
- `left_forearm`
- `right_forearm`

次の高価値 visual pass:
- helmet / chest / shoulder silhouette continuity
- chest / back / waist の torso shell 接続
- left/right pair symmetry
- committed material assets が必要かどうかの判断

判定ソース:
- viewerの見た目だけではなく `fit-regression` と `authoring-audit`
- `surface_attachment_preview` は telemetry。現時点では Quest runtime parts を動かさない。

再開コマンド:

```powershell
python tools/run_henshin.py authoring-audit --root . --output-json sessions/authoring-audit.json --output-md sessions/authoring-audit.md
python tools/run_henshin.py fit-regression --root .
python tools/run_henshin.py design-coherence-audit --output-md tests/.tmp/design-coherence-audit.md
```

## DB保管

現ローカル:
- suits / manifests は `sessions/new-route/suits/...`
- trials / events / replay は `sessions/new-route/trials/...`
- `POST /v1/trials`、`POST /v1/trials/{trialId}/events`、`GET /v1/trials/{trialId}/replay` はローカル JSON 書き込みで shape を証明する段階。

Cloud SQL 正本候補:
- `projects`
- `suits`
- `suit_versions`
- `part_catalog`
- `part_assets`
- `audit_logs`
- 後続で `transform_sessions`, `transform_events`, `replay_scripts`

GCS artifact path:

```text
gs://{bucket}/catalogs/parts/{catalogId}/part-catalog.json
gs://{bucket}/suits/{suitId}/versions/{version}/suitspec.json
gs://{bucket}/suits/{suitId}/versions/{version}/manifest.json
gs://{bucket}/trials/{trialId}/transform-session.json
gs://{bucket}/trials/{trialId}/events.ndjson
gs://{bucket}/trials/{trialId}/replay/replay-script.json
```

Firestore allowed:

```text
quest_devices/{deviceId}
live_trials/{trialId}
operator_dashboards/{operatorId}
```

Firestore forbidden as source of truth:
- `SuitSpec`
- `SuitManifest`
- `TransformSession`
- `TransformEvent`
- `ReplayScript`

判断ルール: canonical / archive / history は SQL + GCS。Firestore は live mirror だけ。

## 次タスク

電源復帰後の最初の10分:
1. `git status --short` で担当外変更を確認する。既存の未追跡/変更ファイルは戻さない。
2. `npm run dev` と `npm run dev:quest -- --host 0.0.0.0` を起動する。
3. PCで `http://localhost:8010/viewer/armor-forge/` を開き、4文字 `recall_code` を確認する。
4. QuestまたはPC browserで `http://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1` を開く。
5. trial/replay 後に `/v1/trials/latest` を確認する。

優先タスク:
- P0: first canonical suit seed を本当にこのまま公式にしてよいか確認する。
- P0: GCP resource names を決める。
- P0: Cloud SQL schema draft と GCS path rule を実装へ落とす。
- P0: `SuitManifest` / `PartCatalog` / `TransformSession` / `TransformEvent` / `ReplayScript` の schema drift を止める。
- P0: helmet/chest/shoulder/back の visual pass を始める。
- P1: Hono Cloud Run skeleton を立てる。ただし local API contract と schema validation を壊さない。
- P1: Firestore live docs は3 collection contract だけ先に固定し、product API から fake write しない。
- P1: Quest archive replay の mirror/observer mode と live pose samples の扱いを固める。
- P1: generate-parts の差分生成を入れる。

PM判断で先に潰す曖昧さ:
- Firebase Hosting でSPA配信する前提を確定してよいか。
- Cloud SQL ORM を Prisma に寄せるか。
- Quest device binding は participant 単位か operator 単位か。
- Replay は完全ログ駆動か、一部動画風演出を混ぜるか。
- PlayCanvas は preview/editor adapter か、GLB export helper か。正本にしないことだけは固定。

## ユーザー操作メモ

基本起動:

```powershell
npm run dev
npm run dev:quest -- --host 0.0.0.0
```

PC dashboard:

```text
http://localhost:8010/viewer/suit-dashboard/
```

Web Forge:

```text
http://localhost:8010/viewer/armor-forge/
```

Quest smoke:

```text
http://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

ADB reverse path:

```powershell
adb devices
npm run dev:quest:adb
```

Quest Browser URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

LAN HTTPS path:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp {PC_LAN_IP}
npm run dev
npm run dev:quest:lan
```

Quest Browser URL:

```text
https://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

Sakura AI Engine:
- real voice recognition and TTS は Sakura path。
- `mockTrigger=1` は開発用。展示/本番体験の成功扱いにしない。

GCP準備でユーザーが決めるもの:
- project name
- artifact bucket name
- Cloud SQL instance/database/user
- Firebase Auth / Firestore を同一GCP projectに寄せるか
- Quest 3 検証経路: same LAN HTTPS か `adb reverse`

作業時の注意:
- このworktreeには担当外の既存変更/未追跡ファイルがある前提で扱う。
- `sessions/` と `tests/.tmp/` はローカル proof / artifacts が多い。資料化や確認には使えるが、勝手に整理しない。
- public UI の主役は `recall_code`。internal ID は storage / audit / operator の道具。
- fresh checkout で `sessions/...` texture がない状態でも、palette fallback が成立するかを見る。
