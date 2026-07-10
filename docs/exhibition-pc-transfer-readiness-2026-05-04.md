# Exhibition PC Transfer Readiness - 2026-05-04

## 2026-05-05 canonical carry-in stage table

Use `docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md` as the
operator-facing table for the current carry-in assumptions:

- Windows external PC; GPU unknown and not a gate.
- Quest USB is available and is the preferred route through ADB reverse.
- Shared LAN exists but is fallback only after reachability is verified.
- mocopi hardware exists but has not been used yet, so it starts as
  `mocopi-DEMO-ONLY` or `not-included`.
- BODY/static local fallback is mandatory and must pass before service,
  PlayCanvas, or mocopi labels matter.
- Web serviceization is the anshin lane: useful confidence, not the required
  visitor dependency.

## Transfer checklist export

Before copying the package to the exhibition PC, export the static transfer
checklist from the source package root:

```powershell
python tools/export_exhibition_pc_transfer_checklist.py --report-json
```

Default output:

```text
qa/exhibition-pc-transfer-checklist-latest.json
```

Markdown for operator handoff:

```powershell
python tools/export_exhibition_pc_transfer_checklist.py --format markdown --out qa\exhibition-pc-transfer-checklist-latest.md
```

The checklist must show no `missing_items` for README, `.env.demo.example`,
local stack scripts, runbook, service/release validators, release QA manifest,
and replay QA artifact before transfer. It also records fixed local URLs, USB
Quest steps, manual setup steps, and do-not-copy items such as real `.env`
secrets, dependency caches, and machine-local paths.

## Latest QA artifact interpretation

Current checked artifacts show the local fallback lane is viable, but they do
not prove a Cloud Run visitor path:

- `qa/exhibition_smoke_check_3601_adb_latest.json`: `preflight_gate.operator_label=local-pass`
  with ADB reverse OK. Treat code `3601` as historical evidence only; the
  external PC pass still needs a fresh Web Forge code.
- `qa/service-deployment-contract-local-latest.json`: `mode=local`,
  `status=pass`. This validates `127.0.0.1:8010` and `localhost:5173`, not a
  public HTTPS service.
- `qa/gcp-phase0-service-contract-latest.json`: `mode=local`, `status=pass`,
  `phase0_promotion_status=ready`. This is the local-to-GCP contract export,
  not Cloud Run reachability evidence.
- `qa/exhibition-service-gate-latest.json`: `gate_status=GO`,
  `allowed_runtime_mode=local_fallback`. This means "use local fallback"; it is
  not a GCP service GO.
- `qa/exhibition_release_package_latest.json`: `status=warn` with
  `missing_count=0` and `pattern_gap_count=0`, but it also reports many
  untracked critical files under explicit working-tree snapshot policy. A
  normal git-only archive is therefore not enough unless those files are
  tracked or separately included and audited.
- `qa/exhibition-pc-transfer-checklist-latest.json` is required before copy. If
  it is absent, run the transfer checklist export above and carry the generated
  JSON with the package.

Minimum external-PC local fallback evidence to record on the target PC:

```powershell
python tools/export_exhibition_pc_transfer_checklist.py --out qa\exhibition-pc-transfer-checklist-latest.json --report-json
python tools/validate_exhibition_release_package.py --report-json --allow-untracked-for-local-snapshot > qa\exhibition_release_package_external_pc.json
python tools/validate_service_deployment_contract.py --mode local --web-base-url http://127.0.0.1:8010 --api-base-url http://127.0.0.1:8010 --quest-base-url http://localhost:5173 --env-file .env.demo.example --report-json > qa\service-deployment-contract-local-latest.json
python tools/exhibition_smoke_check.py --forge --require-adb-reverse > qa\exhibition_smoke_check_external_pc.json
python tools/export_gcp_phase0_service_contract.py --env-file .env.demo.example --mode local --out qa\gcp-phase0-service-contract-latest.json --report-json
python tools/validate_exhibition_service_gate.py qa\gcp-phase0-service-contract-latest.json qa\service-deployment-contract-local-latest.json --exhibition-smoke-report qa\exhibition_smoke_check_external_pc.json --report-json > qa\exhibition-service-gate-latest.json
```

External Cloud Run/GCP can be marked `service-pass` only after a separate
external-mode service deployment contract uses HTTPS public URLs with
`--check-http`, and `validate_exhibition_service_gate.py --strict` returns
`gate_status=GO`. Until then, local fallback is mandatory and the external
service lane remains `not-included`, `DEMO-ONLY`, or `NO-GO`.

今日から外部PCへ持ち出すまでの実行順を固定する。目的は、展示の成立条件を
「ローカル展示PCで Web -> Quest -> Replay が通ること」に閉じ、GCP、
PlayCanvas、mocopi を任意強化として扱うこと。

今日 = 2026-05-04 JST。

## 判断原則

1. 必須ゲートは `local-pass` だけ。
2. `local-pass` は外部PCまたは同等のクリーンPCで判定する。
3. GCP/Web service、PlayCanvas、mocopi は `local-pass` 後にだけ評価する。
4. 任意強化が成功しても `local-fail` は上書きできない。
5. 当日は新しい実装を入れない。最後に通ったパッケージ、URL、コード、手順へ戻す。

## 担当

| 領域 | 担当 | 成果物 | 止める条件 |
|---|---|---|---|
| 進行/判定 | PM/展示責任者 | `local-pass/fail`、任意レーンの最終ラベル | local smoke が赤、担当不明、証跡なし |
| パッケージ | Release owner | 外部PCへコピーする repo/zip、`qa/*.json` | 必須ファイル欠落、未追跡ファイル未確認 |
| Web/API | Web service owner | `8010` 起動、Web Forge、fresh code | `/api/health` 不通、コード生成不可 |
| Quest | Quest owner | `5173` 起動、USB ADB reverse、Quest Browser表示 | `adb unauthorized`、Quest URL不通 |
| Asset/GLB | Asset QA | GLB smoke、variant/catalog整合 | GLB missing、fallback/proxy表示 |
| Replay | Replay owner | replay proof または frozen fallback replay | `C:\...`、`file://`、必要artifact欠落 |
| GCP/Web service | Service owner | `service-pass/fail/not-included` | local-pass前の昇格要求 |
| PlayCanvas | Adapter owner | `playcanvas-pass/fail/not-included` | runtime package snapshotを読まない |
| mocopi | Hardware owner | `mocopi-GO/DEMO-ONLY/NO-GO/not-included` | fallback未確認、診断が`MOCOPI`でない |

## 固定値

| 種別 | 値 |
|---|---|
| 外部PC想定パス | `C:\henshin-demo\gavai-henshin` |
| Web/API port | `8010` |
| Quest Vite port | `5173` |
| PC Web Forge URL | `http://127.0.0.1:8010/viewer/armor-forge/` |
| Quest USB URL | `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>` |
| Quest manual URL | `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1` |
| Quest LAN URL | `http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>` |
| Web/API起動 | `npm run dev` または `python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"` |
| Quest起動 | `npm run dev:quest -- --host 0.0.0.0 --port 5173` |
| USB reverse | `npm run dev:quest:adb` |

## 実行順

### 0. 今日の最初に決める

担当: PM/展示責任者

1. 持ち出し対象を1つに決める: git commit、working-tree snapshot、または zip。
2. 外部PCに持ち込むパスを `C:\henshin-demo\gavai-henshin` に固定する。
3. 任意強化は初期値をすべて `not-included` にする。
4. `3601` は過去証跡として扱い、持ち出し判定では fresh code を使う。
5. 当日の公開判断語彙を固定する:
   `local-pass/fail`, `service-pass/fail/not-included`,
   `playcanvas-pass/fail/not-included`,
   `mocopi-GO/DEMO-ONLY/NO-GO/not-included`。

完了条件: PMが「今日は local-pass を先に取りにいく」と明言している。

### 1. パッケージ候補を作る

担当: Release owner

必須ファイル:

- `package.json`
- `pyproject.toml`
- `vite.quest.config.js`
- `tools/run_henshin.py`
- `tools/exhibition_smoke_check.py`
- `tools/smoke_web_glb_load.py`
- `tools/validate_exhibition_release_package.py`
- `tools/validate_variant_catalog.py`
- `tools/start_quest_adb_reverse.ps1`
- `src/**`
- `viewer/armor-forge/**`
- `viewer/quest-iw-demo/**`
- `viewer/assets/armor-parts/**`
- `schemas/**`
- `examples/suitspec.sample.json`
- `examples/modeler_delivery_manifest.sample.json`
- `docs/exhibition-pc-runbook-2026-05-04.md`
- `docs/exhibition-day-one-page-checklist-2026-05-04.md`
- `docs/exhibition-pc-release-package-manifest-2026-05-04.md`
- `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`
- `docs/exhibition-pc-transfer-readiness-2026-05-04.md`
- `docs/web-service-phase0-task-breakdown-2026-05-02.md`
- `docs/quest-mocopi-exhibition-spike-2026-05-04.md`

任意で同梱:

- frozen sample suit / manifest / trial / replay seed
- `viewer/assets/vrm/**` が使われる場合のVRM一式
- `qa/waivers/**` がある場合の展示用waiver
- mocopi機材メモ。ただし `GO` または `DEMO-ONLY` 判断がない限り必須にしない

禁止:

- 開発PCの絶対パス依存
- `.env` の秘密値
- `C:\dev\codex\gavai-henshin` 前提
- 古いQuestタブ、ブラウザキャッシュ、古いrecall code前提

完了条件: パッケージ候補が1つだけあり、名前に日付、commit/zip名、作成者がある。

### 2. ローカル検証を開発PCで先に通す

担当: Release owner、Asset QA

PowerShell:

```powershell
cd C:\dev\codex\gavai-henshin
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_pretransfer.json
python tools/smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_pretransfer.json
```

判定:

- `missing_count=0`
- `pattern_gap_count=0`
- GLB failuresなし
- `previewFallbackParts=0`
- untracked がある場合は、通常releaseなら止める。working-tree snapshotなら
  `--allow-untracked-for-local-snapshot` のJSONを保存し、一覧の実在を確認する。

完了条件: QA JSONが保存され、Release ownerが持ち出し候補として認める。

### 3. 外部PCへコピーする

担当: Release owner、外部PC operator

1. 外部PCに `C:\henshin-demo\gavai-henshin` を作る。
2. パッケージ候補をコピーまたは展開する。
3. Node/Python/ADBを確認する。

PowerShell:

```powershell
cd C:\henshin-demo\gavai-henshin
node --version
npm --version
python --version
adb version
npm install
python -m pip install -e ".[dev]"
```

完了条件: 外部PC単独で依存インストールが終わる。開発PCの共有フォルダやサーバーを参照していない。

### 4. 外部PCで必須preflightを走らせる

担当: Release owner、Asset QA、Replay owner

PowerShell:

```powershell
cd C:\henshin-demo\gavai-henshin
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools/smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
```

判定:

- release package validator が赤なら `local-fail` 候補。先にコピー内容を直す。
- GLB smoke が赤なら `local-fail` 候補。fallback/proxy表示は公開passにしない。
- Replay seedを使う場合、artifact refs が bundle-relative、`gs://`、承認済み
  `https://` のいずれかであること。`C:\...` と `file://` は不可。

完了条件: ファイル/GLB/Replayの事前確認が外部PC上で通る。

### 5. 外部PCでWeb/APIとQuestを起動する

担当: Web service owner、Quest owner

Terminal A:

```powershell
cd C:\henshin-demo\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python tools/run_henshin.py serve-dashboard --port 8010 --root "$PWD"
```

Terminal B:

```powershell
cd C:\henshin-demo\gavai-henshin
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

確認:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

期待:

```text
8010 Web/API/static
5173 Quest viewer
```

完了条件: `8010` と `5173` が固定でlistenしている。portをずらして逃げない。

### 6. Quest USB/ADB reverseを確立する

担当: Quest owner

1. QuestをUSB-Cデータケーブルで外部PCへ接続する。
2. ヘッドセット内でUSB debuggingを許可する。
3. PowerShell:

```powershell
adb devices -l
npm run dev:quest:adb
adb reverse --list
```

期待:

```text
<device_id>    device ...
tcp:5173 tcp:5173
tcp:8010 tcp:8010
```

`unauthorized` の場合:

```powershell
adb kill-server
adb start-server
adb devices -l
```

それでも `unauthorized` なら、ヘッドセットを装着して許可プロンプトを確認し、
USBポート/ケーブル/Quest Developer Modeを見直す。`device` になるまで公開判定へ進まない。

完了条件: Quest BrowserがUSB経由で `localhost:5173` を開ける状態。

### 7. local-pass smokeを実行する

担当: PM/展示責任者、Web service owner、Quest owner、Replay owner

PowerShell:

```powershell
cd C:\henshin-demo\gavai-henshin
python tools/exhibition_smoke_check.py --forge
```

必須判定:

- API health OK
- Quest page OK
- fresh 4-digit code 生成
- recall成功
- `runtime_contract = runtime-render-placement.v1`
- `render_placement_count >= 18`
- `missing_selected_variant_key_count = 0`
- `selected_variant_mismatch_count = 0`
- `runtime_surface_failure_count = 0`
- `unsafe_public_ref_count = 0`
- `preflight_gate.operator_label = local-pass`

Web確認:

```text
http://127.0.0.1:8010/viewer/armor-forge/
```

Quest確認:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>
```

完了条件: PMが `local-pass` を記録する。ここで初めて任意強化を見てよい。

## 任意強化レーン

### Web service/GCP

担当: Service owner

扱い:

- 初期値は `not-included`。
- `local-pass` 前にGCPを展示本線へ昇格しない。
- GCP endpointを使う場合も、同じ forge、recall、replay、no-local-path check を通す。
- Cloud Run/Cloud SQL/GCS/Cloud Tasks/Secret Manager は将来マッピング対象であり、
  外部PCローカルfallbackの代替条件ではない。

ラベル:

- `service-pass`: hosted/service endpointで同等smokeが通った
- `service-fail`: 試したが不成立
- `not-included`: 展示本線では使わない

### PlayCanvas

担当: Adapter owner

扱い:

- 初期値は `not-included`。
- PlayCanvasはpreview/editor/QA adapter。
- runtime package snapshotまたはexported artifact bundleを読むだけにする。
- suit selection、render placement、recall code、Replay historyを所有しない。

ラベル:

- `playcanvas-pass`: snapshot consumerとして表示でき、canonical stateを変更しない
- `playcanvas-fail`: 読み込み不成立、または権限境界が曖昧
- `not-included`: 展示本線では使わない

### mocopi

担当: Hardware owner、Quest owner

扱い:

- 初期値は `not-included`。
- mocopiはhardware enhancementであり、local-pass条件ではない。
- Quest診断が `MOCOPI` を示さない場合、公開上はmocopi有効と扱わない。
- BODY/static fallbackへ60秒以内に戻せることを必須にする。

`mocopi-GO` 条件:

- 6センサーが60秒以上安定
- calibration後に左右入れ替わりなし
- Quest diagnosticが `MOCOPI`
- median visible latency `<= 120 ms`
- p95 `<= 250 ms`
- frozen/dropped motion `< 2%`
- BODY/static fallback rehearsed
- raw motionの同意/保持方針が明記済み

ラベル:

- `mocopi-GO`: visitor pathへ出してよい
- `DEMO-ONLY`: operator-led demoだけ。通常visitor pathはBODY/static
- `NO-GO`: 使わない
- `not-included`: 持ち出し対象に含めない

## 持ち出し判定

PM/展示責任者は次を1枚に記録してからPCを持ち出す。

| 項目 | 記録 |
|---|---|
| package name | date + commit/zip name |
| external PC path | `C:\henshin-demo\gavai-henshin` |
| `local-pass/fail` | 必須 |
| fresh code used | 4桁 |
| Web URL | `http://127.0.0.1:8010/viewer/armor-forge/` |
| Quest USB URL | `http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>` |
| `adb devices -l` | `device` であること |
| `adb reverse --list` | `5173` と `8010` があること |
| release package JSON | `qa\exhibition_release_package_external_pc.json` |
| GLB smoke JSON | `qa\smoke_web_glb_load_external_pc.json` |
| local smoke output | `preflight_gate.operator_label=local-pass` |
| service label | `service-pass/fail/not-included` |
| PlayCanvas label | `playcanvas-pass/fail/not-included` |
| mocopi label | `mocopi-GO/DEMO-ONLY/NO-GO/not-included` |
| fallback package | last-known-good package名 |
| operator note | 既知リスク、waiver、当日連絡先 |

持ち出しOK:

- `local-pass`
- Quest USB/ADB reverseが `device` で通る
- fresh codeでWeb/Quest一致
- Replay proofまたはfrozen fallback replayがある
- 任意強化のラベルが記録済み

持ち出しNG:

- `local-fail`
- `8010` または `5173` が固定で起動できない
- QuestがUSBで `localhost:5173` を開けない
- GLB fallback/proxyを公開pass扱いしている
- 任意強化の成功だけで本線を通そうとしている

## 当日障害時のfallback

### Server/port failure

担当: Web service owner、Quest owner

1. 古いTerminalを閉じる。
2. port確認:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

3. `8010` と `5173` で再起動する。
4. portを変えた場合はADB reverse、Quest URL、掲示手順を全部変える必要があるため、
   当日は原則としてport変更しない。

### Quest USB failure

担当: Quest owner

1. `adb devices -l`
2. `npm run dev:quest:adb`
3. `adb reverse --list`
4. `unauthorized` ならヘッドセットでUSB debuggingを許可。
5. USBが復旧しない場合だけLAN fallbackへ移る。

LAN fallback:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

Quest URL:

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>
```

LANがclient isolationで通らない場合、USB復旧へ戻る。

### Code/recall failure

担当: Web service owner、Quest owner

1. Web Forgeで新しい4桁コードを生成する。
2. Questの古いタブを閉じる。
3. 新しいQuest URLを開く。
4. manual URLで入力する場合も newest code だけを使う。
5. 古いarmorが出る場合はQuest Browserのsite dataを消す。

### GLB/runtime failure

担当: Asset QA

PowerShell:

```powershell
python tools/smoke_web_glb_load.py --repo-root . --report-json
python tools/validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

fallback/proxy表示を公開passにしない。last-known-good packageへ戻す。

### GCP/Web service failure

担当: Service owner

- `service-fail` と記録する。
- local PCの `8010`/`5173` へ戻す。
- visitor pathは止めない。GCP障害はlocal-passを壊さない。

### PlayCanvas failure

担当: Adapter owner

- `playcanvas-fail` と記録する。
- Web/Quest/Replay本線へ戻す。
- PlayCanvasの状態をcanonical truthとして使わない。

### mocopi failure

担当: Hardware owner、Quest owner

- `DEMO-ONLY` または `NO-GO` と記録する。
- BODY/static fallbackへ戻す。
- Quest diagnosticが `MOCOPI` でない状態をmocopi activeと説明しない。
- raw motionの保存判断をその場で増やさない。保存は同意/保持方針がある場合だけ。

## 最終チェックリスト

| Check | 担当 | Pass条件 |
|---|---|---|
| Package copied | Release owner | 外部PCに1つだけ存在 |
| Required files | Release owner | validator missing/pattern gapなし |
| Asset smoke | Asset QA | GLB failureなし、fallbackなし |
| Web/API | Web service owner | `8010` listen、health OK |
| Quest Vite | Quest owner | `5173` listen |
| USB ADB reverse | Quest owner | `device`、reverse `5173`/`8010` |
| Web Forge | Web service owner | fresh code生成 |
| Quest recall | Quest owner | same fresh codeでrecall |
| Runtime contract | PM/Quest owner | `runtime-render-placement.v1` |
| Public refs | Release owner | `unsafe_public_ref_count=0` |
| Replay | Replay owner | portable proof or frozen fallback |
| Local label | PM | `local-pass` |
| GCP label | Service owner | `service-pass/fail/not-included` |
| PlayCanvas label | Adapter owner | `playcanvas-pass/fail/not-included` |
| mocopi label | Hardware owner | `mocopi-GO/DEMO-ONLY/NO-GO/not-included` |
| Fallback | PM | last-known-good package名が明記済み |
