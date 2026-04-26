# gavai-henshin

## New Route Runbook

Lore standard:

```text
Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す
```

Use this route when validating the current new-route stack locally.

Current route copy standard:

```text
Web: Suit Forge -> Quest: Henshin Trial -> Replay: Archive
```

### 1. Start Local Services

Terminal 1: API, dashboard, static files.

```powershell
npm run dev
```

Terminal 2: Quest/IWSDK Vite app.

```powershell
npm run dev:quest -- --host 0.0.0.0
```

PC dashboard:

```text
http://localhost:8010/viewer/suit-dashboard/
```

Quest LAN smoke URL:

```text
http://{PC_LAN_IP}:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1
```

### 2. Quest Trial

For HTTP LAN smoke, `mockTrigger=1` lets the Voice button exercise the new-route API without microphone permission. This is only a local smoke-test bypass.

Real voice recognition and TTS remain on the Sakura AI Engine path. Use the real voice path with either ADB reverse or LAN HTTPS.

ADB reverse path:

```powershell
adb devices
npm run dev:quest:adb
```

Quest Browser URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1
```

Expected Quest signals:

- The page status panel shows `SUIT FORGE: NEW`.
- Voice creates a `TransformSession`.
- Replay generation ends with `REPLAY ARCHIVE: RPL-...`.
- In immersive mode, the floating VR panel shows forge, fit, trial, and archive status.

### 3. Replay Proof

After the Quest trial, confirm the latest durable record:

```powershell
Invoke-RestMethod http://localhost:8010/v1/trials/latest | ConvertTo-Json -Depth 6
```

Success criteria:

- `summary.state` is `ACTIVE`.
- `summary.event_count` is greater than 0.
- `summary.replay_script_path` points to `sessions/new-route/trials/.../replay-script.json`.
- The PC dashboard `HENSHIN TRIAL / Replay Archive` card shows the same latest trial.

### 4. Active New-Route Branches

Current local route branches:

| Branch | Purpose |
|---|---|
| `codex/new-route-quest-status-panel` | Quest page route/API/trial/replay status plus latest-trial API. |
| `codex/new-route-dashboard-latest-trial` | PC dashboard card for latest Quest trial. |
| `codex/new-route-vr-trial-readout` | Floating VR control panel route/trial/replay readout. |
| `codex/new-route-canonical-identity-lock` | Canonical suit identity, fit contract, texture fallback, and lore-copy coherence. |

Design coherence and visual brush-up tracking:

- `docs/new-route-design-coherence-audit.md`

Loreを基点に、Blueprintを実行可能にするための **SIM-first プロトタイピング基盤** です。  
現段階は「技術検証デモを高速に回す」ことを目的に、仮案ルールで構築しています。

## 目的
- Track A: Suit Forge（生成/3D試着の土台）
- Track B: Transform Stage（B->C->D->蒸着->封印の状態遷移）
- Archive: セッション成果物の保存（物証化）

## 現在の実装範囲
- 仮案IDルールと設定ファイル
- `SuitSpec` / `Morphotype` のスキーマ（`schemas/`）
- `SuitManifest` / `PartCatalog` / `TransformSession` / `ReplayScript` の新規路線契約
- `SuitSpec` から `SuitManifest` への projection CLI
- 生成ドラフト出力（JSON）
- Gemini API経由の画像生成（Blueprint/Emblem）
- Gemini API経由の部位別画像生成（module単位）
- プロトコル状態遷移（happy/refused）
- セッション保存（ログ/要約/ダミー成果物）
- 右腕ドック装着シミュレーション（PoC参照統合）
- 全身セグメント装着シミュレーション（PoC汎化）
- CLI実行 (`henshin`)
- 単体テスト（標準ライブラリ `unittest`）

## ディレクトリ
- `src/henshin/`: 実行コード
- `schemas/`: JSON Schema
- `config/`: 仮案ルール
- `examples/`: サンプルJSON
- `docs/`: 実行準備ドキュメント
- `docs/roadmap.md`: ロードマップ
- `docs/execution-plan.md`: 直近の実行計画
- `docs/progress-log.md`: 進捗ログ
- `docs/id-policy.md`: ID運用ポリシー
- `docs/armory-io-contract.md`: Armory連携I/O契約
- `docs/rightarm-integration.md`: 右腕PoC統合メモ
- `docs/body-fit-viewer.md`: 全身当てはめビューア手順
- `docs/suit-dashboard.md`: スーツ別 生成/確認ダッシュボード手順
- `sessions/`: デモ出力先（Git管理は `.gitkeep` のみ）

## クイックスタート
```powershell
$env:PYTHONPATH="src"
python -m henshin demo --mode happy
python -m henshin demo --mode refused --refusal-code AUDIT_MISMATCH
python -m henshin validate --kind suitspec --path examples/suitspec.sample.json
python tools/run_henshin.py project-manifest --suitspec examples/suitspec.sample.json --output examples/suitmanifest.sample.json
python tools/run_henshin.py validate --kind suitmanifest --path examples/suitmanifest.sample.json
python -m unittest discover -s tests -v
```

### Gemini APIキー設定
```powershell
$env:GEMINI_API_KEY="YOUR_API_KEY"
```

または、プロジェクト直下の `.env` に設定（CLIが自動読込）:
```dotenv
GEMINI_API_KEY=YOUR_API_KEY
```

## CLI
```powershell
python -m henshin new-session
python -m henshin draft --session-id S-20260228-A1B2 --series AXIS --role OP
python -m henshin demo --mode happy
python -m henshin validate --kind morphotype --path examples/morphotype.sample.json
python tools/run_henshin.py validate --kind partcatalog --path examples/partcatalog.seed.json
python tools/run_henshin.py project-manifest --suitspec examples/suitspec.sample.json --partcatalog examples/partcatalog.seed.json --output examples/suitmanifest.sample.json
python -m henshin generate-image --kind blueprint --suitspec examples/suitspec.sample.json
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --dry-run
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --texture-mode mesh_uv --dry-run
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --update-suitspec
python -m henshin generate-parts --suitspec examples/suitspec.sample.json --fallback-dir sessions/S-20260228-JBJK/artifacts/parts --prefer-fallback
python -m henshin simulate-rightarm --input examples/rightarm_sequence.sample.json --output sessions/rightarm-sim.json
python -m henshin simulate-body --input examples/body_sequence.sample.json --output sessions/body-sim.json
python -m henshin serve-viewer --port 8000
python -m henshin serve-dashboard --port 8010
```

## Phase 1 API skeleton

新規路線の Cloud Run / Hono API に移す前段として、同じ契約をローカル dashboard server からも返せるようにします。現時点の skeleton は seed/sample を読むだけで、Cloud SQL / GCS / Firestore への書き込みはまだ行いません。

```text
GET /health
GET /v1/catalog/parts
POST /v1/suits
GET /v1/suits/{suitId}
POST /v1/suits/{suitId}/manifest
GET /v1/suits/{suitId}/manifest
GET /v1/manifests/{manifestId}
POST /v1/trials
GET /v1/trials/{trialId}
POST /v1/trials/{trialId}/events
GET /v1/trials/{trialId}/replay
```

Phase 1 write path is now `SuitSpec -> SuitManifest`: `POST /v1/suits` saves the SuitSpec as the authoring source, and `POST /v1/suits/{suitId}/manifest` projects a validated SuitManifest with PartCatalog references. The local implementation writes JSON under `sessions/new-route/suits/...`; Cloud Run can keep the same contract while replacing that repository with Cloud SQL for source/version rows and GCS for artifacts.

Phase 2 local trial path starts the Quest/replay bridge: `POST /v1/trials` creates a schema-valid `TransformSession`, and `POST /v1/trials/{trialId}/events` appends canonical transform events with server-side event ids and sequence numbers. Local storage writes under `sessions/new-route/trials/...`; later GCP should map sessions/events to Cloud SQL and live state to Firestore.

Phase 3 local replay path closes the first loop: `GET /v1/trials/{trialId}/replay` derives and stores a schema-valid `ReplayScript` from the canonical `TransformSession` events. Video/audio remain derived artifacts; the durable source stays event log plus replay script.

Canonical seed and platform preparation are tracked in `config/new-route.canonical.json`, `docs/new-route-operator-checklist.md`, `docs/new-route-gcp-readiness.md`, and `infra/gcp/`.

まずは API 形、schema validation、PartCatalog / SuitManifest の参照を固定する。永続化の正本は次段で Cloud SQL、artifact は GCS、live state は Firestore に分ける。

## GitHub運用
- CI: `.github/workflows/ci.yml`（unittest実行）
- ライセンス: MIT
- コントリビュート規約: `CONTRIBUTING.md`

## 新規路線ブランチ対比

新規路線は、既存モジュールを捨てずに `SuitManifest` / `PartCatalog` / `TransformEvent` を正本化して GCP / Quest / Replay へ段階移行する方針です。差分が混ざらないよう、以下のブランチ単位で退避・レビューします。

| ブランチ | 目的 | レビュー順 |
|---|---|---:|
| `codex/new-route-phase0-contracts` | Phase 0 契約。`SuitManifest`、`PartCatalog`、`TransformSession`、`ReplayScript`、`SuitSpec -> SuitManifest` projection、GCP移行メモ。 | 1 |
| `codex/quest-iw-mocopi-work` | Quest Browser / IWSDK / mocopi bridge / operator monitor 周辺の実機・展示レーン。 | 2 |
| `codex/uv-part-generation-work` | UV guide、texture quality gate、prompt bench、part generation 改善。 | 3 |
| `codex/new-route-source-docs` | 2026-04-23 の GPT Pro / GCP 方針資料原本。実装差分ではなく参照資料。 | 4 |

基本順序は、まず Phase 0 契約をレビューし、その上に Quest / UV / source docs を必要に応じて積む。`main` へ入れる判断は、契約、実機、生成品質、資料の順で分ける。

## 次の実装候補
1. SuitSpecサンプルを増やしてモジュール差し替え検証を追加
2. APIキー投入後の実画像生成スモークテスト
3. mocopi入力をMorphotype推定に変換する前処理実装
