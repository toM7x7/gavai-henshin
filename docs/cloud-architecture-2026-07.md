# クラウドアーキテクチャ確定版 (2026-07-05)

Status: Active — 本ドキュメントが cloud lane の現行 source of truth。
Supersedes: `new-route-gcp-platform-plan.md` (2026-04-24 Draft) のスタック選定部分。
Inherits: `web-service-readiness-2026-05-02.md` のドライバ分離方針 / `exhibition-service-mocopi-roadmap-2026-05-04.md` のレーン統治(GCPは任意レーン、local-passを覆せない)。

## 0. 確定事項(divergence の解消)

過去3世代のドキュメントで割れていた点を以下に確定する:

| 論点 | 旧計画 (04-24) | 確定 (本書) |
| --- | --- | --- |
| APIランタイム | Hono/TypeScript 書き直し | **既存 Python サーバをそのままコンテナ化**(契約の正はコード) |
| AI | Vertex AI | **Gemini API (nano_banana profile) + Sakura AI Engine** 現行のまま |
| Quest | Unity/OpenXR | **WebXR (現行 quest-iw-demo)**、PlayCanvas はスナップショット消費アダプタのみ |
| env命名 | NEW_ROUTE_* | **`.env.example` の PUBLIC_* / *_DRIVER 系**(infra/gcp/env.example を同期済み) |
| データ境界 | 同左 | Cloud SQL=正 / GCS=アーティファクト / Firestore=liveのみ / Secret Manager=鍵 (変更なし) |

## 1. 段階計画(蒸着工程になぞらえる)

各フェーズに既存の検証ツールを「承認ゲート」として割り当てる。ゲートを通らない昇格は**起動拒否**。

### Phase 0 — 仮組み (DRY_FIT_SIM): lift-and-shift ✅ scaffolded 2026-07-05
- `Dockerfile` + `.dockerignore` + `infra/gcp/cloudbuild.yaml` を追加済み。
- 既存サーバを Cloud Run 1インスタンス(max-instances=1)で起動。状態はインスタンス内 JSON(揮発を許容するスモーク用)。
- 秘密鍵は Secret Manager バインド(cloudbuild.yaml に設定済み)。`.env` はイメージに入らない(.dockerignore)。
- ゲート: `export_gcp_phase0_service_contract.py` → `validate_service_deployment_contract.py --mode external` → `validate_exhibition_service_gate.py --strict`。
- 前提条件(コード側、未完了):
  1. **認証境界**: 現状 API は無認証。最低限、変異系 `/api/*` `/v1/*` POST に共有シークレットヘッダを入れる。
  2. **CORS実装**: `CORS_ALLOWED_ORIGINS` は現在デッド設定(サーバが読んでいない)。allowlist 実装が必要。
  3. 機微パス静的配信ガード → **2026-07-05 実装済み**(dashboard_server の send_head ガード)。
  4. `GET /v1/trials/{id}/replay` の書き込み副作用除去(HTTPセマンティクス/キャッシュ安全)。

### Phase 1 — 承認 (APPROVED): 状態の外部化
- `SuitStore` / `TrialStore` プロトコル(get/put/find_by_recall_code)を切り、現行ファイルシステム実装を1バックエンドに。
- Cloud SQL ドライバ実装(`infra/gcp/cloudsql/schema.sql` — recall_codes / generation_jobs テーブル追加済み)。
- アーティファクトを GCS へ(`ARTIFACT_STORE_DRIVER=gcs`)。カタログは `catalogs/parts/{catalogVersion}/` に version+hash 付きで配置。
- recall-code 照合の per-request ディレクトリ走査を廃し、インデックス化。
- 解放される制約: max-instances=1 → オートスケール。

### Phase 2 — 蒸着 (DEPOSITION): 非同期化と live state
- GenerationJobManager(インメモリ)→ generation_jobs テーブル + Cloud Tasks(`QUEUE_DRIVER=cloud-tasks`)。
- SSE は Cloud Run 対応(HTTP/1.1 streaming可)だが、多インスタンス化に伴い job イベントは DB/pubsub 経由へ。
- Firestore live state(quest_devices / live_trials)導入。mocopi はローカルUDP→クラウドへは WebSocket/SSE リレー(展示会場PCがブリッジ)。

### Phase 3 — 封印 (SEALING): 公開境界
- Firebase Auth(operator console と visitor flow の分離)。
- 監査ログ(audit_logs)を全変異操作に接続 — ロア的にも「記録院」がここで成立する。
- 独自ドメイン + CDN(GLB/テクスチャ配信)。

## 2. サービス構成(Phase 1 以降の目標形)

```text
[Browser: Web Forge]        [Quest Browser: Henshin Trial]
        │ https                     │ https (TLS標準 → quest-lan証明書ツール群は廃止)
        ▼                           ▼
   Cloud Run: henshin-api-ui (Python, 現行サーバ)
        │             │                    │
   Cloud SQL      GCS bucket          Firestore (live)
   (suits/trials/ (GLB/テクスチャ/     (quest_devices,
    recall_codes)  replay/manifest)    live_trials)
        │
   Cloud Tasks → henshin-worker (part_generation, 将来分離)
   Secret Manager (GEMINI / SAKURA)
```

- 静的 viewer 3アプリは当面 henshin-api-ui が同一オリジンで配信(現行と同型)。分離する場合も armor-forge は `?apiBase=/assetBase=` 対応済み。suit-dashboard の remote-base 対応は未実装(要 shared/api-client.js 抽出 — リファクタ計画参照)。
- Quest クライアントの `DEFAULT_BODY_SIM_LATEST = http://localhost:8021` はクラウドでは不成立。相対パス化 + vite proxy `/body-sim` 追加が必要(既知ブロッカー)。

## 3. GitHub 公開前の必須クリーンアップ(cloud とは独立に着手可)

1. `origin/main` に **node_modules 1,711ファイル(~197MiB pack)がコミット済み** — `git rm -r --cached node_modules` + 公開前に `git filter-repo` で履歴からも除去。
2. `.playwright-cli/` 57ファイル + `.tmp-dashboard.*` の tracked 削除をコミット確定。
3. `examples/` のユーザーフィードバック媒体7件(スクショ/録画/PDF)の削除コミット確定。個人が写る場合は履歴パージ判断。
4. 未追跡の tools 44本・tests 57本・バリアント資産86式・variant_catalog.json をレーン別にコミット(post-exhibition-main-cleanup-plan の6レーン計画に従う)。
5. 鍵ローテーション: `.env` の Gemini キー / Sakura トークンは LAN 展示で配信可能だった期間があるため**ローテーション推奨**。quest-lan.pfx はパスフレーズが tracked example に載っていたため**証明書再生成推奨**(example は 2026-07-05 にプレースホルダ化済み)。

## 4. 今日時点の残ブロッカー一覧(優先順)

1. 認証 + CORS 実装(Phase 0 前提)
2. main のクリーンアップコミット(§3)
3. new_route_api.py の分割(routes / stores / forge_planner / replay)— Phase 1 の SuitStore 差し込みシーム作りを兼ねる
4. suit-dashboard の remote-base 対応(shared/api-client.js 抽出)
5. 外部モードのリハーサル実績ゼロ(`*-external.json` 検証成果物が未生成)— Phase 0 ゲートで初回実施
