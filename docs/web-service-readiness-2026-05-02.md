# Web Service Readiness - 2026-05-02

Date: 2026-05-02  
Scope: 現行の Python dashboard/API、static viewer、Quest Vite runtime、assets/GLB、Nanobanana、SakuraAI を前提に、Web サービス化へ進むための準備資料。  
Non-goal: PlayCanvas 採用、GCP 採用、Hono/Cloud Run 化、Unity/OpenXR 化をこの時点で決定しきらない。

## 1. 前提と判断軸

現時点の価値は「ローカルで動くデモ」をそのままクラウドへ置くことではなく、Web Forge -> SuitSpec/Manifest -> Quest recall -> Trial/Replay へつながる体験 ID と生成物を壊さずに外へ出せる状態を作ることにある。

既存の中核:

- Python dashboard/API: `npm run dev` で `tools/run_henshin.py serve-dashboard --port 8010 --root .` を起動し、dashboard/API/static 配信を兼ねる。
- static viewer: `viewer/armor-forge`、`viewer/suit-dashboard`、`viewer/body-fit`、`viewer/assets` をローカル配信で確認する。
- Quest Vite: `npm run dev:quest` で `vite.quest.config.js` を使い、`viewer/quest-iw-demo` を Quest Browser / IWSDK 検証レーンとして動かす。
- assets/GLB: `viewer/assets/armor-parts` の canonical / variant / topping GLB、sidecar、preview metadata、`variant_catalog.json` が現行 runtime の実体。
- Nanobanana: Web Forge の texture generation 前提。生成物は texture asset と manifest linkage として扱い、runtime の暗黙状態にしない。
- SakuraAI: LLM / speech / TTS 連携前提。まず adapter と環境変数境界を固定し、provider 直結をアプリ全体へ漏らさない。

判断軸:

- 先に固定するもの: schema、asset path、recall code、manifest linkage、生成物の保存単位、検証コマンド。
- まだ固定しないもの: PlayCanvas か Three.js か、GCP か別クラウドか、Cloud SQL か他 DB か、Firebase Hosting か別 hosting か。
- 絶対に混ぜないもの: canonical DB、artifact storage、live state、local dev cache、provider secret。

## 2. 現行サービス境界

### Python dashboard/API

現行 Python は Web サービス化の初期にも「adapter 実装」として残す。理由は、すでに Web Forge、Quest recall、generation job、mock/real provider 境界、静的 viewer 配信をまとめて検証できるため。

当面の責務:

- local/demo の単一起動面。
- `/api/*` の既存ローカル互換。
- `/v1/*` の新ルート契約の検証。
- SuitSpec / Manifest / recall payload のファイルベース永続化。
- GLB / texture / catalog / Quest viewer の配信。

クラウド化時に分離する責務:

- 静的配信は hosting / CDN へ分離する。
- canonical write は DB 経由にする。
- artifact は object storage 経由にする。
- 長時間生成は worker / queue に逃がす。
- provider secret は Secret Manager 相当へ移す。

### Static viewer

`viewer/*` は最初から「cloud ready な静的成果物」として扱う。まずは Python 配信、次に static hosting、最後に CDN + immutable asset cache へ移行する。

注意点:

- viewer が repo-relative path に依存しすぎると hosting 移行で壊れる。
- GLB、texture、catalog は manifest 経由または well-known asset base URL 経由で解決する。
- local dev では `http://127.0.0.1:8010`、Quest Vite では `QUEST_API_TARGET`、production では `PUBLIC_API_BASE_URL` に集約する。

### Quest Vite

Quest runtime は当面 Vite + Quest Browser / IWSDK の検証レーンとして維持する。Unity/OpenXR への移行や PlayCanvas viewer 統合は、manifest/asset/recall 契約が安定してから判断する。

当面の責務:

- 4 桁 recall code で Web Forge の結果を取得する。
- Manifest / selected variants / topping / texture pointers を読み、Quest 側で同じ装備を再現する。
- Trial event / Replay の最小契約を検証する。
- Quest 実機で asset size、load time、scale、pose の破綻を検出する。

## 3. 段階的な展開構成

### Phase 0: Local contract freeze

目的: 今あるローカル体験を、外部化可能な契約へ寄せる。

構成:

- Python dashboard/API: local authoritative。
- static viewer: Python static serving。
- Quest Vite: local Vite + ADB reverse / LAN HTTPS。
- storage: repository working tree / `viewer/assets` / generated local files。
- DB: なし。JSON file を仮 canonical として扱う。
- provider: Nanobanana / SakuraAI は mock fallback を許可。

完了条件:

- `POST /v1/suits/forge` から recall code、SuitSpec、Manifest、preview/asset pointers が一貫して返る。
- `GET /v1/quest/recall/{code}` が Quest で再利用できる payload を返す。
- GLB fallback が 0 に近い状態で Web/Quest smoke が通る。
- local `.env` と `.env.example` の必要項目が説明可能。

### Phase 1: Static hosting split

目的: API と viewer 配信を分け、Web サービスの入口を整理する。

構成候補:

- API: まだ Python dashboard/API のままでもよい。
- viewer: static hosting or CDN 相当へ移す。
- Quest Vite build: `vite.quest.config.js` の build artifact を hosting に置けるか検証する。
- asset base URL: `PUBLIC_ASSET_BASE_URL` で切り替える。

判断保留:

- Firebase Hosting、Cloud Storage static website、Cloudflare Pages、Vercel static、GitHub Pages のどれにするか。
- PlayCanvas を preview/editor に入れるか、既存 Three.js viewer を継続するか。

完了条件:

- static viewer が API origin と asset origin を環境変数で切り替えられる。
- CORS、cache header、MIME type、GLB loading が確認済み。
- Quest Browser で HTTPS origin から runtime を開ける。

### Phase 2: Durable artifact storage

目的: GLB、texture、manifest、preview、replay artifact を repository working tree から切り離す。

構成候補:

- object storage: GCS / S3 / R2 / Azure Blob のいずれでもよい。
- local dev: `ARTIFACT_STORE_DRIVER=local`。
- staging/prod: `ARTIFACT_STORE_DRIVER=object`。
- path rule は provider 非依存の logical URI として固定する。

推奨 path:

```text
artifacts/
  catalogs/armor-parts/{catalog_version}/variant_catalog.json
  suits/{suit_id}/versions/{version}/suitspec.json
  suits/{suit_id}/versions/{version}/manifest.json
  suits/{suit_id}/versions/{version}/preview.png
  suits/{suit_id}/versions/{version}/textures/base_suit/albedo.png
  suits/{suit_id}/versions/{version}/textures/base_suit/emissive.png
  suits/{suit_id}/versions/{version}/textures/armor/{module}/albedo.png
  suits/{suit_id}/versions/{version}/glb/{module}.glb
  trials/{trial_id}/events.ndjson
  trials/{trial_id}/replay/replay-script.json
```

完了条件:

- API response は file path ではなく artifact URI / signed URL / public CDN URL のいずれかを返す。
- generated asset は content hash と schema version を持つ。
- cache busting が version/hash で説明できる。

### Phase 3: Canonical DB introduction

目的: recall code、suit、manifest、trial、replay の履歴を file system から DB へ移す。

DB 候補:

- PostgreSQL: もっとも自然。Cloud SQL / Neon / Supabase / RDS などに移植しやすい。
- SQLite: local dev / single operator demo では継続可能。ただし multi-user production の主 DB にはしない。
- Firestore: live state には合うが、canonical history の主 DB にはしない。

最小 tables:

- `projects`: tenant / demo / workspace 単位。
- `suits`: suit の安定 ID、owner、latest_version。
- `suit_versions`: SuitSpec、Manifest、asset pointers、status、schema versions。
- `recall_codes`: 4 桁 code、suit_version_id、expires_at、revoked_at。
- `part_catalog_versions`: catalog version、source hash、asset base URI。
- `generation_jobs`: Nanobanana / SakuraAI / GLB processing job。
- `trials`: Quest trial session。
- `trial_events`: append-only event log。
- `replay_artifacts`: replay script / video / derived assets。
- `audit_logs`: operator action、provider call、deployment migration。

完了条件:

- `POST /v1/suits/forge` が DB transaction と artifact write の整合性を持つ。
- recall code が衝突、期限切れ、再発行、取り消しを扱える。
- local JSON store から DB store へ repository interface で切り替えられる。

### Phase 4: API runtime split

目的: Python dashboard/API の責務を、本番 API runtime と local tool runtime に分ける。

構成候補:

- 継続案: Python API をそのまま ASGI/FastAPI 等へ寄せる。
- 移行案: Node/Hono on Cloud Run 等へ移す。
- 折衷案: public API は新 runtime、existing Python は worker / tool server として残す。

判断基準:

- 現行 Python の asset/tooling 連携を捨てるコスト。
- provider SDK / async worker / image processing / Blender tooling との相性。
- deploy target の cold start、secret 管理、observability。
- team が TypeScript API と Python worker の二重運用に耐えられるか。

完了条件:

- `/v1/*` の public contract が Python 実装依存ではなく schema/test で保証される。
- local dashboard は production DB/API に対して operator client として動ける。
- provider secret は runtime ごとに最小権限で分離される。

### Phase 5: Queue / provider worker

目的: Nanobanana、SakuraAI、GLB validation、preview render、replay generation を synchronous API から分離する。

構成候補:

- Queue: Cloud Tasks / Pub/Sub / BullMQ / Celery / GitHub Actions manual worker のいずれか。
- Worker: Python の既存 tooling を活かすのが第一候補。
- API: job request を受け、job state と artifact pointers だけを返す。

完了条件:

- generation job は retry、timeout、cancel、idempotency key を持つ。
- provider failure 時に fallback / partial result / manual retry が区別できる。
- user-facing result と operator diagnostics が分かれている。

### Phase 6: Production hardening

目的: 複数ユーザー、展示、本番デモ、外部公開に耐える状態へ上げる。

追加するもの:

- auth / role policy。
- rate limit / quota。
- audit viewer。
- backup / restore。
- data retention。
- release promotion。
- error budget / monitoring。
- asset migration runbook。

## 4. 環境変数

### Local / common

| Name | Purpose | Required | Notes |
|---|---|---:|---|
| `APP_ENV` | `local` / `staging` / `production` | yes | default は `local`。 |
| `PUBLIC_API_BASE_URL` | viewer から見る API origin | yes | local は `http://127.0.0.1:8010`。 |
| `PUBLIC_ASSET_BASE_URL` | viewer/Quest から見る asset origin | yes | local は API static origin でもよい。 |
| `PUBLIC_VIEWER_BASE_URL` | recall link / QR link の viewer origin | recommended | Web/Quest deep link 生成用。 |
| `CORS_ALLOWED_ORIGINS` | API CORS allowlist | yes before hosting split | `*` は local のみに限定。 |
| `LOG_LEVEL` | runtime logging | recommended | `debug` / `info` / `warn` / `error`。 |

### Quest

| Name | Purpose | Required | Notes |
|---|---|---:|---|
| `QUEST_HOST` | Vite dev host | local | current `.env.example` にあり。 |
| `QUEST_PORT` | Vite dev port | local | default `5173`。 |
| `QUEST_API_TARGET` | Quest dev runtime から見る API | local | ADB reverse / LAN HTTPS で切替。 |
| `QUEST_HTTPS_PFX` | LAN HTTPS 証明書 | local optional | Quest Browser microphone/WebXR 用。 |
| `QUEST_HTTPS_PFX_PASSWORD` | PFX password | local optional | secret 扱い。 |
| `QUEST_HTTPS_CERT` | PEM cert | local optional | LAN HTTPS 用。 |
| `QUEST_HTTPS_KEY` | PEM key | local optional | secret 扱い。 |

### Provider

| Name | Purpose | Required | Notes |
|---|---|---:|---|
| `GEMINI_API_KEY` | Nanobanana / Gemini image provider | by provider | production は Secret Manager 相当。 |
| `GEMINI_MODEL_ID` | default image model | by provider | `.env.example` の値を引き継ぐ。 |
| `GEMINI_FAST_MODEL` | fast draft | optional | mock fallback と分岐。 |
| `GEMINI_REFINE_MODEL` | refine | optional | quality path。 |
| `GEMINI_HERO_MODEL` | hero/base suit generation | optional | model name は固定しすぎない。 |
| `GEMINI_FALLBACK_MODEL` | fallback image model | optional | provider outage 時の候補。 |
| `SAKURA_AI_ENGINE_TOKEN` | SakuraAI auth | by provider | secret。 |
| `SAKURA_AI_ENGINE_BASE_URL` | SakuraAI endpoint | by provider | staging/prod で切替可能にする。 |
| `SAKURA_LLM_MODEL` | LLM model | by provider | current assumption: `gpt-oss-120b`。 |
| `SAKURA_WHISPER_MODEL` | STT model | optional | voice route 用。 |
| `SAKURA_TTS_MODEL` | TTS model | optional | voice route 用。 |
| `SAKURA_TTS_VOICE` | TTS voice | optional | voice route 用。 |
| `SAKURA_TTS_FORMAT` | TTS output format | optional | `wav` 等。 |
| `VOICE_TRIGGER_PHRASE` | Quest/voice trigger | local/demo | 文字化けや locale 差分に注意。 |

### Storage / DB / queue

| Name | Purpose | Required | Notes |
|---|---|---:|---|
| `STORE_DRIVER` | `json` / `postgres` | yes after Phase 3 | repository interface で切替。 |
| `DATABASE_URL` | canonical DB | Phase 3+ | local/staging/prod を分ける。 |
| `ARTIFACT_STORE_DRIVER` | `local` / `object` | Phase 2+ | object storage provider 非依存名。 |
| `ARTIFACT_BUCKET` | object storage bucket/container | Phase 2+ | GCS に限らず抽象名で扱う。 |
| `ARTIFACT_PUBLIC_BASE_URL` | public/CDN URL | Phase 2+ | signed URL 運用なら optional。 |
| `ARTIFACT_SIGNING_SECRET` | signed URL/token | optional | CDN 方式に依存。 |
| `LIVE_STATE_DRIVER` | `memory` / `firestore` / `redis` | Phase 4+ | Firestore を固定しすぎない。 |
| `QUEUE_DRIVER` | `inline` / `cloud_tasks` / `pubsub` / `celery` / `bullmq` | Phase 5+ | local は `inline`。 |
| `JOB_TIMEOUT_SECONDS` | generation timeout | Phase 5+ | provider ごとに上書き可。 |
| `JOB_MAX_RETRIES` | retry policy | Phase 5+ | idempotency とセット。 |

### Auth / observability

| Name | Purpose | Required | Notes |
|---|---|---:|---|
| `AUTH_DRIVER` | `none` / `firebase` / `oidc` / `basic` | staging+ | local は `none` 可。 |
| `OIDC_ISSUER` | OIDC issuer | if OIDC | Firebase に固定しない。 |
| `OIDC_AUDIENCE` | API audience | if OIDC | multi-client を想定。 |
| `ADMIN_EMAIL_ALLOWLIST` | initial operator allowlist | staging | MVP 用。 |
| `SENTRY_DSN` | error reporting | optional | provider 非依存でよい。 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | traces/metrics | optional | Cloud Trace 等へ移植可能。 |

## 5. ストレージ設計

### 分類

| Class | Source of truth | Examples | Storage |
|---|---|---|---|
| canonical metadata | DB | suit, suit_version, recall_code, trial, event pointer | PostgreSQL 等 |
| artifact | object storage | manifest JSON copy, GLB, texture, preview, replay script | local/object storage |
| live state | volatile store | Quest connection, operator selected trial, current step | memory/Firestore/Redis |
| source asset | repository or asset registry | canonical GLB, sidecar, variant catalog | git + release artifact |
| provider diagnostic | restricted log/artifact | prompt, provider response, token usage, failure reason | DB + private artifact |

### 重要ルール

- DB は「検索・履歴・権限・参照整合性」のために使う。
- object storage は「大きい生成物・配布物」のために使う。
- live state は「現在値」のために使い、履歴の主保管先にしない。
- `viewer/assets/armor-parts` の repository assets は release seed として扱い、本番 write path にしない。
- GLB / texture / manifest の public 配信可否は artifact ごとに決める。provider prompt や user raw input は安易に public にしない。

### Cache policy

- catalog: versioned path なら long cache 可。
- GLB: content hash or versioned path なら long cache 可。
- generated texture: suit version path なら long cache 可。
- recall payload: short cache / no-store 推奨。
- signed URL: expiry を短くし、Quest の load 時間と展示運用を考慮する。

## 6. DB 設計メモ

### 最小 entity

`suits`

- `id`
- `project_id`
- `owner_id`
- `latest_version`
- `created_at`
- `updated_at`

`suit_versions`

- `id`
- `suit_id`
- `version`
- `status`: `draft` / `generated` / `ready_for_quest` / `retired` / `failed`
- `suitspec_json`
- `manifest_json`
- `catalog_version`
- `artifact_manifest_uri`
- `preview_uri`
- `schema_versions`
- `created_at`

`recall_codes`

- `code`
- `suit_version_id`
- `expires_at`
- `revoked_at`
- `created_at`
- unique active code constraint

`generation_jobs`

- `id`
- `suit_version_id`
- `job_type`: `nanobanana_texture` / `sakura_variant_selection` / `glb_validate` / `preview_render`
- `provider`
- `status`
- `idempotency_key`
- `input_hash`
- `result_artifact_uri`
- `error_code`
- `created_at`
- `updated_at`

`trials` / `trial_events`

- Trial は session metadata。
- Event は append-only。
- Replay は event から派生した artifact。

### Migration stance

- Phase 0/1 では migration tool を決めなくてよい。
- Phase 3 の直前に migration runner を決める。
- DB schema は `schema_version` と application compatibility を明示する。
- destructive migration は production data export / restore rehearsal 後に限定する。

## 7. CI 構成

### Phase 0 CI

最初に必要なチェック:

```powershell
npm ci
python -m pip install -e .
python -m pytest -q
npm run test
node --check viewer/quest-iw-demo/quest-demo.js
node --check viewer/armor-forge/forge.js
```

補助:

```powershell
python tools/validate_modeler_delivery_manifest.py --manifest examples/modeler_delivery_manifest.sample.json
python tools/validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

### Phase 1 CI

追加:

- static build check。
- Quest Vite build check。
- GLB MIME / file existence check。
- generated manifest schema validation。
- no-secret-in-bundle check。

候補:

```powershell
npm run dev:quest -- --host 127.0.0.1
vite --config vite.quest.config.js build
```

実際の script 名は repository に合わせて追加する。資料時点では CI command を固定しすぎない。

### Phase 2+ CI

追加:

- artifact store integration smoke。
- DB migration dry-run。
- API contract tests against staging URL。
- recall code round trip。
- Web Forge -> Quest recall payload snapshot。
- Playwright screenshot smoke for Web viewer。
- Quest 実機は手動ゲート、または nightly/manual workflow。

### Branch / deploy gates

- PR: unit + schema + static syntax + catalog validation。
- main: integration + artifact dry-run。
- staging deploy: migration dry-run + smoke。
- production deploy: tagged release + backup confirmation + rollback plan。

## 8. デプロイ前チェック

### Contract

- SuitSpec schema と SuitManifest schema が通る。
- PartCatalog / variant catalog が module、variant_key、topping path と一致する。
- Nanobanana output contract が manifest linkage を持つ。
- SakuraAI variant selection が unknown variant を直接 runtime に流さない。
- Quest recall payload が Web Forge の selected variants / toppings / textures を反映する。

### Asset

- GLB が glTF 2.0 binary として読める。
- canonical 18 module の欠損がない。
- variant/topping の sidecar と path が一致する。
- Quest で重すぎる GLB / texture を検知している。
- `previewFallbackParts=0` または fallback 理由が明示されている。

### API

- `/api/health` or `/health` が環境名、version、store driver を返す。
- `/v1/catalog/parts` が catalog version を返す。
- `/v1/suits/forge` が idempotency を扱える。
- `/v1/quest/recall/{code}` が期限切れ/未存在/取り消しを区別する。
- CORS allowlist が production で広すぎない。
- API error envelope が UI/Quest で処理可能。

### Storage / DB

- DB backup / restore 手順がある。
- artifact bucket/container に lifecycle と public/private policy がある。
- generated artifact は suit version に紐づく。
- local path が production response に漏れない。
- secret が DB / artifact / static bundle に混入していない。

### Provider

- Nanobanana key が production runtime のみで読まれる。
- SakuraAI token が production runtime のみで読まれる。
- provider timeout / retry / rate limit が設定されている。
- mock fallback と real provider result が UI 上で区別できる。
- prompt / raw input の保存方針が privacy 的に説明できる。

### Quest

- Quest Browser で HTTPS origin を開ける。
- microphone/WebXR/IWSDK の permission が想定通り。
- ADB reverse 依存が production path に残っていない。
- recall code 入力後に古い cached suit を誤表示しない。
- Trial 開始前、成功後、失敗後の状態表示が残る。

### Rollback

- static viewer は前 release artifact へ戻せる。
- API は前 image / previous deployment へ戻せる。
- DB migration は backward compatible か、restore point がある。
- artifact は delete ではなく retire を基本にする。
- provider outage 時は local/demo mode or manual retry に逃がせる。

## 9. リスクと対策

| Risk | Impact | Early signal | Mitigation |
|---|---|---|---|
| PlayCanvas/GCP を早く決めすぎる | 現行 viewer/API の学びを捨てる | 実装前に platform 固有語が schema へ混入 | contract-first にし、runtime adapter として扱う |
| Python dashboard が肥大化する | production と local tool が混ざる | `/api/*` と `/v1/*` の責務が曖昧 | repository/provider/static 配信を interface 化 |
| local path が API contract に漏れる | hosting/object storage 移行で破綻 | response に `viewer/assets/...` 前提が増える | artifact URI と asset base URL へ寄せる |
| GLB/texture が重い | Quest load failure / frame drop | Quest 実機だけで破綻する | size budget、LOD、texture cap、Quest smoke gate |
| Nanobanana output が runtime に未連携 | 見た目は生成されたが Quest で再現しない | texture file だけ増え manifest が更新されない | manifest linkage を必須 output にする |
| SakuraAI が自由すぎる variant を返す | catalog にない装備が混入 | unknown key / fallback 増加 | resolver が catalog へ正規化し warnings を返す |
| recall code が脆い | 他人の suit 表示 / 古い suit 表示 | code collision / cache reuse | expiry、revocation、version binding、no-store |
| live state と履歴が混ざる | replay/audit が再現不能 | Firestore/volatile store に履歴を置き始める | event log は DB append-only、live は current only |
| CI が見た目を見ない | Web/Quest 表示が壊れる | unit は通るが canvas/GLB が空 | Playwright/web smoke、Quest manual gate |
| secrets が static bundle に入る | provider key leakage | `PUBLIC_` env に secret が入る | public/private env naming と bundle scan |
| provider cost/rate limit | デモ中断 / 請求事故 | retry storm / parallel jobs | quota、job queue、idempotency、operator approval |
| DB migration 事故 | recall/trial 履歴喪失 | destructive migration without export | backup, dry-run, backward compatible rollout |

## 10. 直近の推奨タスク

1. `PUBLIC_API_BASE_URL` / `PUBLIC_ASSET_BASE_URL` / `STORE_DRIVER` / `ARTIFACT_STORE_DRIVER` を設計上の名前として固定する。
2. `/v1/quest/recall/{code}` の response に `schema_version`、`catalog_version`、`artifact_base_url`、`cache_policy` を明示する。
3. generated Nanobanana assets の manifest linkage を validation 対象に入れる。
4. `viewer/assets/armor-parts` を release seed として扱うため、catalog version と source hash を出す。
5. local JSON store と future DB store の repository interface 境界を作る。
6. static viewer の production build / hosted origin smoke を 1 本作る。
7. Quest 実機チェックを deploy gate の手動項目として明文化する。

## 11. 暫定結論

現時点では「GCP に載せる」「PlayCanvas に寄せる」より先に、既存 Python dashboard/API と static viewer と Quest Vite が共有する契約を Web サービス向けに硬くするのが正解。

推奨する順番は、contract freeze -> static hosting split -> artifact storage -> canonical DB -> API runtime split -> queue/provider worker -> production hardening。これなら、PlayCanvas を入れる場合も preview adapter として入れられ、GCP を採る場合も Cloud Run / Cloud SQL / GCS / Firestore に自然に写像できる。逆に、今 platform を決め打つと、GLB/Nanobanana/SakuraAI/Quest recall の一番おいしい知見が platform 移行作業に埋もれる。
