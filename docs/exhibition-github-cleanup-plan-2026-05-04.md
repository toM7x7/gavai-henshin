# 展示PC / GitHub push readiness 運用計画 - 2026-05-04

目的: 現在の大きく汚れた作業ツリーを、外部展示PCで動くリリース候補と GitHub に push できる変更単位へ分ける。コードはこの文書では変更しない。既存変更は他者作業を含む前提で、revert / reset / checkout で消さない。

前提となる北極星:

```text
Web がスーツを成立させる。
Quest が変身体験を検証する。
Replay が体験を残す。
```

必須の基準:

- 展示の公開運用は `local-pass` が必須。
- `local-pass` は外部展示PC、または同等のクリーンPC上で判定する。
- GCP、PlayCanvas、mocopi の成功は `local-fail` を上書きできない。
- コアデモは live GCP、インターネット、provider secrets、mocopi なしで動く。
- Web/API は `8010`、Quest Vite は `5173` を固定する。
- recall code `3601` は過去検証の証跡として扱う。最終展示判定では Web Forge が生成した fresh 4桁コードを使う。

## 1. Dirty worktree triage

現在のブランチは `codex/new-route-canonical-identity-lock`。作業ツリーには、Python API、Quest runtime、Web Forge、validation tools、3D assets、tests、docs、Playwright/Quest証跡、`.tmp` 出力が混在している。この状態をそのまま一括 commit / push しない。

最初に棚卸しする:

```powershell
git status --short --branch
git diff --name-only
git ls-files --others --exclude-standard
```

分類ルール:

| 分類 | 例 | GitHub release での扱い |
|---|---|---|
| runtime/API | `src/henshin/**`, `schemas/**`, `examples/*.json` | local-pass の前提なら commit 候補 |
| Web/Quest runtime | `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`, `vite.quest.config.js` | smoke と syntax check 後に commit 候補 |
| 展示ツール | `tools/exhibition_smoke_check.py`, `tools/validate_exhibition_release_package.py`, `tools/start_quest_adb_reverse.ps1` | 展示手順に必要なら commit 候補 |
| 3D asset/catalog | `viewer/assets/armor-parts/**`, `variant_catalog.json`, `.modeler.json`, GLB | validator と GLB smoke 後に commit 候補 |
| docs/runbook | `docs/exhibition-*`, `docs/quest-*`, `docs/web-service-*` | 運用文脈として commit 候補 |
| test code | `tests/test_*.py`, `tools/verify_*.mjs` | 対応実装と同じ commit 群に入れる |
| 一時証跡 | `.playwright-cli/**`, `.playwright-mcp/**`, `tests/.tmp/**`, root の一時 `.png` | 原則 push しない。必要証跡だけ名前付き docs/qa へ移してから検討 |
| ローカル環境 | `.env`, venv, npm cache, shell history | push しない |

重要: GitHub の通常 clone / archive で展示PCに持っていくなら、必要な runtime、asset、schema、example、operator doc は git tracked でなければならない。未追跡のまま zip で持ち出す場合だけ、snapshot として明示する。

snapshot 扱いの判定コマンド:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools/validate_exhibition_release_package.py --report-json --allow-untracked-for-local-snapshot > qa\exhibition_release_package_snapshot_report.json
```

通常の GitHub release / clone を目指す場合は `--allow-untracked-for-local-snapshot` に逃がさない。必要ファイルを commit するか、展示対象から外す。

## 2. Branch / commit segmentation

推奨方針: 現在の mixed branch をそのまま本線に押さず、展示freeze用の整理ブランチで commit を小さく切る。

候補:

```powershell
git switch -c codex/exhibition-release-freeze-2026-05-04
```

既存変更は消さない。ブランチ作成前に他者が同じ作業ツリーを使っている場合は、担当者間で「このブランチで stage する owner」を確認する。

commit の切り方:

1. Contract / API commit
   - `src/henshin/new_route_api.py`
   - `src/henshin/runtime_package.py`
   - `src/henshin/validators.py`
   - `src/henshin/dashboard_server.py`
   - related schemas/examples/tests
   - 目的: `/v1/suits/forge` と `/v1/quest/recall/{code}` の意味を固定する。

2. Quest runtime commit
   - `viewer/quest-iw-demo/**`
   - `vite.quest.config.js`
   - `tools/start_quest_adb_reverse.ps1`
   - Quest telemetry / recall / render contract tests
   - 目的: `5173`、ADB reverse、`runtime-render-placement.v1`、debug/real voice lane を固定する。

3. Web Forge visitor flow commit
   - `viewer/armor-forge/**`
   - Web Forge related tests
   - 目的: 4桁コード生成、Quest link、visitor-first UI、operator/debug の分離を固定する。

4. Asset / catalog / modeler commit
   - `viewer/assets/armor-parts/**`
   - `viewer/assets/armor-parts/variant_catalog.json`
   - `tools/blender/**`
   - modeler validation tools and tests
   - 目的: 18 parts、variant/topping、sidecar、GLB smoke をひとまとまりで検証できるようにする。

5. Exhibition validation commit
   - `tools/validate_exhibition_release_package.py`
   - `tools/exhibition_smoke_check.py`
   - `tools/smoke_web_glb_load.py`
   - `tests/test_exhibition_smoke_check.py`
   - `tests/test_validate_exhibition_release_package.py`
   - 目的: 外部PCで `local-pass` を機械的に判定できるようにする。

6. Docs / runbook commit
   - `docs/exhibition-pc-runbook-2026-05-04.md`
   - `docs/exhibition-day-one-page-checklist-2026-05-04.md`
   - `docs/exhibition-pc-release-package-manifest-2026-05-04.md`
   - `docs/quest-usb-adb-reverse-checklist-2026-05-04.md`
   - `docs/web-ui-service-gcp-playcanvas-direction-2026-05-03.md`
   - `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`
   - この文書
   - 目的: 操作者が同じ判断ラベルと同じポートで動ける状態にする。

7. Evidence commit は原則作らない
   - `.playwright-cli/**`、`.playwright-mcp/**`、`tests/.tmp/**` は通常 push しない。
   - 例外は、展示判定に必要な短い JSON report や人間レビュー用の名前付き画像だけ。置き場所と命名を決めてから stage する。

各 commit 前の確認:

```powershell
git add -p <対象path>
git diff --cached --stat
git diff --cached --check
git diff --cached --name-only
```

push 前の確認:

```powershell
git log --oneline --decorate -n 12
git status --short --branch
```

push は `local-pass` 取得後に行う。どうしても先に共有する場合は、ブランチ名と PR 説明に `local-pass pending` を明記し、展示PC用リリースとは扱わない。

## 3. Required local-pass commands

開発PCでの pre-push gate:

```powershell
cd C:\dev\codex\gavai-henshin
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
npm ci
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py -q
python -m pytest tests\test_exhibition_smoke_check.py tests\test_validate_exhibition_release_package.py tests\test_smoke_web_glb_load.py tests\test_quest_armor_whole_suit_audit.py -q
python -m pytest -q
npm test
npx vite build --config vite.quest.config.js --outDir tests\.tmp\quest-vite-build-prepush --emptyOutDir
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

`package-lock.json` があるため、release / clean clone / 展示PC の再現確認は `npm ci` を使う。`npm install` はローカル開発中の依存更新や lockfile 更新が目的の時だけ使い、展示リリース判定には使わない。

package / asset gate:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_prepush.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_prepush.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_prepush.json --fail-on fail
```

期待値:

- `missing_count=0`
- `pattern_gap_count=0`
- git release の場合は critical untracked がない
- GLB failures がない
- `previewFallbackParts=0`
- whole-suit audit が `status=pass`
- 18 parts の pose、target size、asset が揃っている
- 左右対称、human-fit distance、obvious interpenetration が fail になっていない
- fallback/proxy 表示を public pass と扱っていない

clean clone / exact release branch gate:

このゲートは、現在の dirty working tree ではなく、GitHub に push する exact branch / tag / commit から再現する。展示PCへ GitHub clone で持ち込むなら、この clean clone が通らない限り release ready と呼ばない。

```powershell
$releaseCommit = "<release-commit-sha>"
$checkRoot = "C:\henshin-release-check\$releaseCommit"
New-Item -ItemType Directory -Force $checkRoot | Out-Null
cd $checkRoot
git clone <repo-url> gavai-henshin
cd $checkRoot\gavai-henshin
git fetch --all --tags --prune
git switch --detach $releaseCommit
git rev-parse HEAD
git status --short --branch
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
npm ci
node --check viewer\quest-iw-demo\quest-demo.js
node --check viewer\armor-forge\forge.js
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py tests\test_quest_armor_whole_suit_audit.py -q
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_clean_clone.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_clean_clone.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_clean_clone.json --fail-on fail
```

期待値:

- `git rev-parse HEAD` が `$releaseCommit`、release note、PR、package label に書く commit と一致する。
- `git status --short --branch` に未追跡 runtime file がない。
- validator が `--allow-untracked-for-local-snapshot` なしで通る。
- clean clone から `npm ci` と Python install が通る。
- clean clone の asset / whole-suit gate が開発PCと同じ結果になる。
- この clean clone の `qa\*.json` を、展示PCへ持ち込む release package の証跡として保存する。

Quest/Web server restart gate:

Quest runtime 変更が land した後は、古い server process や古い Vite bundle を掴んだまま合格扱いにしない。server smoke と physical Quest telemetry は、必ず exact release commit の working tree から再起動して行う。

古い demo terminal を閉じた後、port を確認する:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 } |
  Select-Object LocalAddress,LocalPort,OwningProcess
```

まだ port が残る場合は、所有プロセスを確認する:

```powershell
Get-Process -Id <PID> | Select-Object Id,ProcessName,Path
```

`python` / `node` がこの repo の Web/API または Quest Vite を掴んでいると確認できた時だけ止める。別アプリや他者作業の process は止めない。

```powershell
Stop-Process -Id <PID>
```

再起動前の条件:

- `git rev-parse HEAD` が release commit と一致する。
- `git status --short --branch` に release 判定へ混ぜる未追跡 runtime file がない。
- `8010` と `5173` が空いている、または止めるべき古い demo process だけが残っている。
- port conflict を避けるために `5174` などへ逃がさない。port を変える場合は ADB reverse、Quest URL、runbook、smoke scripts を同時に変えるまで release gate は停止する。

server smoke gate:

Terminal A:

```powershell
$releaseRoot = "C:\henshin-release-check\<release-commit-sha>\gavai-henshin"
cd $releaseRoot
git rev-parse HEAD
$env:PYTHONPATH = "$PWD\src"
python tools\run_henshin.py serve-dashboard --port 8010 --root "$PWD"
```

Terminal B:

```powershell
$releaseRoot = "C:\henshin-release-check\<release-commit-sha>\gavai-henshin"
cd $releaseRoot
git rev-parse HEAD
npm run dev:quest -- --host 0.0.0.0 --port 5173
```

開発中の素早い pre-push smoke だけなら `C:\dev\codex\gavai-henshin` でよい。Quest runtime 変更後の release 判定では、上の clean clone の `$releaseRoot` から起動する。

Terminal C:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
python tools\exhibition_smoke_check.py --forge
```

`exhibition_smoke_check.py --forge` の期待値:

- Web/API health OK
- Quest page OK
- fresh 4桁コード生成
- recall OK
- `runtime_contract = runtime-render-placement.v1`
- render placements が 18
- `missing_selected_variant_key_count = 0`
- `selected_variant_mismatch_count = 0`
- `runtime_surface_failure_count = 0`
- `unsafe_public_ref_count = 0`
- `preflight_gate.operator_label = local-pass`

注意: この smoke は PC から `127.0.0.1:5173` と `8010` を叩く HTTP/API gate であり、物理Quest実機gateではない。Quest runtime変更が入った後の release 判定では、次の physical Quest telemetry gate も必須にする。

physical Quest telemetry gate:

前提:

- Terminal A と Terminal B は起動したまま。
- `python tools\exhibition_smoke_check.py --forge` で得た fresh code を使う。
- Quest はUSB接続され、`adb devices -l` が `device`。

Terminal C:

```powershell
adb devices -l
adb reverse --remove tcp:5173 2>$null
adb reverse --remove tcp:8010 2>$null
npm run dev:quest:adb
adb reverse --list
```

Quest Browser:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$questUrl = "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>&replayView=mirror&debug=1&t=$stamp"
adb shell am start -a android.intent.action.VIEW -d "$questUrl"
```

Questを被って表示をONに保ち、必要ならVR/sessionを開始してから確認する:

```powershell
Invoke-RestMethod http://localhost:8010/api/quest-debug/latest | ConvertTo-Json -Depth 12
```

合格条件:

- `adb reverse --list` に `tcp:5173 tcp:5173` と `tcp:8010 tcp:8010` がある。
- `record.payload.query.href` が `http://localhost:5173/viewer/quest-iw-demo/` で始まる。
- `record.payload.query.href` に今回発行した `t=$stamp` が入っている。入っていない場合は古いtabまたはstale telemetryとしてNG。
- `record.payload.query.userAgent` が Quest / Oculus Browser 系。
- `record.payload.query.code` が fresh code。
- `record.payload.xr.session=true` を、VR/session開始後に確認している。
- `record.payload.uxState` を記録している。
- mirror 判定は `uxState=archive_replay_mirror_active`、`xr.viewMode=mirror`、`playing=true`、`progress>0`。
- real voice 判定をする場合は URL に `mockTrigger=1` と `mic=0` がなく、`realMicrophoneExpected=true`。
- `uxState=armor_stand_observer_idle` は observer / workshop evidence として扱い、mirror変身証跡にしない。

stale telemetry 排除:

- `/api/quest-debug/latest` の `href` が `127.0.0.1`、`alignmentProbe`、古い `t=...`、または別 code の場合はPC側検証または古いQuest tabの証跡なのでNG。
- `record.payload.xr.session=false` のままなら、Browser page到達証跡でありVR/session証跡ではない。Questを被って表示をONにし、VR/session開始後に同じ `$questUrl` を reload する。
- `adb shell am start` はURLを開く補助であり、display awake、permission許可、VR/session開始、mirror/replay開始の代替ではない。
- telemetry を更新できない場合は、Quest Browser の古いtabを閉じ、同じ `$questUrl` を再度 `adb shell am start` で開く。なお voice 判定は debug/recovery lane では行わない。

## 4. External exhibition PC path

展示PCの標準パス:

```text
C:\henshin-demo\gavai-henshin
```

GitHub clone で持ち込む場合:

```powershell
cd C:\henshin-demo
git clone <repo-url> gavai-henshin
cd C:\henshin-demo\gavai-henshin
git fetch --all --tags --prune
git switch --detach <release-commit-sha>
git rev-parse HEAD
git status --short --branch
```

`git rev-parse HEAD` は clean clone gate の `$releaseCommit` と一致させる。展示PCで branch tip をそのまま追う運用にすると、準備後に branch が進んだ時に別物を起動してしまうため、show用 package は原則 detached exact commit で固定する。

zip / working-tree snapshot で持ち込む場合:

- folder 名に日付、commit、snapshot か git release かを書く。
- `qa\exhibition_release_package_snapshot_report.json` を同梱する。
- report の `untracked` 一覧が、実際に package 内へ入っていることを operator が確認する。

展示PC install:

```powershell
cd C:\henshin-demo\gavai-henshin
node --version
npm --version
python --version
adb version
npm ci
$env:PYTHONPATH = "$PWD\src"
python -m pip install -e ".[dev]"
```

展示PC package gate:

```powershell
New-Item -ItemType Directory -Force qa | Out-Null
python tools\validate_exhibition_release_package.py --report-json > qa\exhibition_release_package_external_pc.json
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_external_pc.json --fail-on fail
```

展示PC local-pass:

Terminal A, Web/API/static on `8010`。この terminal は終了させない:

```powershell
npm run dev
```

Terminal B, Quest viewer on fixed `5173`。この terminal も終了させない:

```powershell
npm run dev:quest -- --port 5173
```

Terminal C, port readiness と PC-side smoke:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
python tools\exhibition_smoke_check.py --forge
```

PC browser:

```text
http://127.0.0.1:8010/viewer/armor-forge/
```

Quest Browser:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>
```

展示PCでは、PC-side smoke だけで `local-pass` を確定しない。上の physical Quest telemetry gate と同じ順番で、fresh code、Quest/Oculus Browser userAgent、`localhost:5173` href、`xr.session=true`、`uxState`、必要なら real voice を確認する。

## 5. Quest USB / ADB reverse checklist

USB ADB reverse を展示の第一候補にする。会場Wi-Fiの client isolation、captive portal、Firewall、同一LAN不達を避けられるため。

事前条件:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
adb devices -l
```

`adb devices -l` の合格:

```text
<device_id>    device ...
```

`unauthorized` の場合:

```powershell
adb kill-server
adb start-server
adb devices -l
```

それでも駄目なら、Quest を被って USB debugging prompt を許可し、USB port / cable / Quest Developer Mode を確認する。`device` になるまで browser/API を疑わない。

reverse 実行:

```powershell
adb reverse --remove tcp:5173 2>$null
adb reverse --remove tcp:8010 2>$null
npm run dev:quest:adb
adb reverse --list
```

または fresh code を明示:

```powershell
adb reverse --remove tcp:5173 2>$null
adb reverse --remove tcp:8010 2>$null
.\tools\start_quest_adb_reverse.ps1 -QuestPath "/viewer/quest-iw-demo/?newRoute=1" -RecallCode <FRESH_CODE>
adb reverse --list
```

期待値:

```text
tcp:5173 tcp:5173
tcp:8010 tcp:8010
```

Quest URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>
```

`tools\start_quest_adb_reverse.ps1` は reverse を張り、開くべきURLを表示する。Quest Browser を確実にそのURLへ向けるには、physical telemetry gate と同じく `adb shell am start -a android.intent.action.VIEW -d "<URL>"` を使うか、Quest Browser内で手入力/貼り付けする。古いtabが残る場合は、timestamp付きURLへ更新するまで合格にしない。

debug/recovery rendering lane:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>&replayView=mirror&mockTrigger=1&mic=0&debug=1&t=<TIMESTAMP>
```

これは mirror / replay / telemetry 復旧用。real voice の証跡にはしない。

exhibition real voice lane:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>&replayView=mirror&debug=1&t=<TIMESTAMP>
```

real voice の合格条件:

- URL に `mockTrigger=1` がない。
- URL に `mic=0` がない。
- Quest Browser が microphone permission を通している。
- `/api/quest-debug/latest` で `realMicrophoneExpected=true`。
- `voiceState` だけでなく `uxState` も記録されている。

Quest telemetry 確認:

```powershell
Invoke-RestMethod http://localhost:8010/api/quest-debug/latest | ConvertTo-Json -Depth 12
```

確認順:

1. `record.payload.query.href` が `http://localhost:5173/viewer/quest-iw-demo/` で始まる。
2. `record.payload.query.userAgent` が Quest / Oculus Browser 系。
3. `record.payload.query.code` が fresh code。
4. `record.payload.uxState` を `voiceState` より先に読む。
5. mirror acceptance は `uxState=archive_replay_mirror_active`、`xr.viewMode=mirror`、`playing=true`、`progress>0`。
6. `uxState=armor_stand_observer_idle` は observer / stand 証跡であり、mirror 変身証跡ではない。

Quest screenshot を取る場合:

```powershell
New-Item -ItemType Directory -Force tests\.tmp | Out-Null
cmd /c "adb exec-out screencap -p > tests\.tmp\gavai-quest-fresh-code.png"
```

PowerShell の `adb exec-out screencap -p > file.png` は PNG を壊すことがあるため使わない。

LAN fallback は USB が使えない時だけ:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" }
```

```text
http://<PC_LAN_IP>:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>
```

LAN HTTP で microphone / WebXR が詰まる場合は、事前に HTTPS / cert lane へ切り替える:

```powershell
.\tools\new_quest_lan_cert.ps1 -LanIp <PC_LAN_IP>
.\tools\start_quest_lan_https.ps1 -ApiTarget http://127.0.0.1:8010
```

会場で visitor を待たせながら証明書を初設定しない。

## 6. Web service / GCP staging path

GCP は展示本線の代替ではなく、`local-pass` 後に評価する service lane。

staging の最小形:

- Cloud Run: 現行 API/UI 境界を維持して `/v1` contract を公開する。
- Cloud SQL: `suit`, `suit_version`, `recall_code`, `trial`, `transform_event`, `replay_record`, `generation_job`, `consent` を持つ。
- Cloud Storage: GLB、manifest、runtime package snapshot、preview、texture、replay script、motion、voice/audio、export を持つ。
- Cloud Tasks: 生成、validation、preview、replay media などの遅い処理だけを queue 化する。
- Secret Manager: provider keys、DB credentials、signing secrets を持つ。
- Structured logs: `suit_id`, `recall_code`, `manifest_id`, `runtime_package_version`, `trial_id`, `job_id`, mocopi session ref を持つ。

staging へ進める条件:

1. 外部PC local baseline が `local-pass`。
2. `/v1/suits/forge` と `/v1/quest/recall/{code}` の payload shape を変えない。
3. public response に `C:\...`、`file://`、dev LAN IP、provider secrets、raw provider payload が出ない。
4. replay artifact refs が bundle-relative、`gs://`、または承認済み `https://`。
5. staging endpoint でも forge、recall、replay、no-local-path check が通る。

ラベル:

- `service-pass`: staging / hosted endpoint で同等 smoke が通った。
- `service-fail`: 試したが失敗した。visitor path は local に戻す。
- `not-included`: 展示本線では使わない。

禁止:

- Cloud-only show path を `local-pass` 前に採用する。
- Firestore を durable suit / recall / replay history の主 DB にする。
- GKE、service mesh、多数 microservices を展示前の必須作業にする。
- PlayCanvas-hosted state や browser local storage を canonical truth にする。

## 7. PlayCanvas optional track

PlayCanvas は adapter。Web/Quest/Replay の truth を持たせない。

許可する役割:

- runtime package snapshot の 3D preview
- accepted GLB の visual QA harness
- non-Quest user 向け viewer
- exported replay viewer

禁止する役割:

- variant selection
- render placement resolution
- 4桁 recall code lifecycle
- catalog acceptance policy
- Replay derivation
- mocopi provenance / consent / retention の所有

pass 条件:

- exported manifest / runtime package snapshot を読む。
- canonical suit、placement、recall、replay を書き換えない。
- 削除しても Web/Quest/Replay の意味が変わらない。

ラベル:

- `playcanvas-pass`
- `playcanvas-fail`
- `not-included`

## 8. mocopi optional track

mocopi は hardware enhancement。`local-pass` の条件ではない。

Phase 0:

- Quest diagnostic が archive motion source を `BODY` / `MOCOPI` / `MOCOPI+LIVE` と区別できる。
- usable motion frames がない時に `MOCOPI 0f` と誤表示しない。
- missing body-sim / mocopi artifact は viewer を壊さず BODY/static へ fallback する。

Phase 1:

- imported mocopi JSON/export を既存の `--mocopi` / body-sim path へ通す。
- Quest archive replay が `MOCOPI <n>f` を表示する。
- simulated fallback が `BODY <n>f` を表示する。
- public visitor path は BODY/static fallback のまま維持する。

Phase 2:

- live receiver / file drop / app export bridge の候補を1つだけ試す。
- 6 sensors が 60秒以上安定。
- calibration 後に左右が入れ替わらない。
- median visible latency `<= 120 ms`。
- p95 `<= 250 ms`。
- dropped/frozen motion `< 2%`。
- freeze が `500 ms` を超えない。
- 失敗時に 60秒以内で BODY/static fallback へ戻せる。

ラベル:

- `mocopi-GO`: visitor path に出してよい。
- `DEMO-ONLY`: operator-led demo のみ。通常 visitor path は BODY/static。
- `NO-GO`: 使わない。
- `not-included`: 持ち込み対象外。

privacy:

- raw mocopi stream と voice/audio は識別性のあるデータとして扱う。
- consent と retention class がない raw capture を保存しない。
- public screen に sensor ID、phone ID、filename、participant name を出さない。

## 9. Rollback / fallback

GitHub rollback:

- push 前に last-known-good の commit/tag を記録する。
- release branch は小さい commit 群にする。
- 失敗修正は `git revert <commit>` で戻せる単位にしておく。
- force push は共有済み branch では避ける。必要なら新しい `codex/*` branch で出し直す。

展示PC rollback:

- active package と last-known-good package を別 folder / zip で保持する。
- folder 名に date、commit/tag、`local-pass` か snapshot かを書く。
- active package が `local-fail` になったら、GCP や mocopi の成功に関係なく last-known-good package へ戻す。

server / port failure:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 8010,5173 }
```

- 古い terminal を閉じる。
- `8010` と `5173` で再起動する。
- 当日原則として port を変えない。変える場合は Quest URL、ADB reverse、runbook、smoke を同時に更新する必要がある。

Quest USB failure:

1. `adb devices -l`
2. `npm run dev:quest:adb`
3. `adb reverse --list`
4. `unauthorized` なら headset 内で USB debugging を許可。
5. USB が復旧しなければ LAN fallback へ移る。
6. LAN が client isolation で通らない場合は USB 復旧へ戻る。

code / recall failure:

1. Web Forge で fresh code を生成する。
2. 古い Quest Browser tab を閉じる。
3. fresh code の Quest URL を開く。
4. stale armor が残る場合は Quest Browser site data を消す。
5. `3601` は最終判定に使わない。

GLB / runtime failure:

```powershell
python tools\smoke_web_glb_load.py --repo-root . --report-json
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --include-delivered-assets
```

- fallback/proxy rendering を public pass にしない。
- asset 欠落なら last-known-good package へ戻す。

GCP failure:

- `service-fail` と記録する。
- visitor path は local PC の `8010` / `5173` へ戻す。
- service 障害を展示停止理由にしない。

PlayCanvas failure:

- `playcanvas-fail` と記録する。
- Web/Quest/Replay 本線へ戻す。
- PlayCanvas の状態を canonical truth として使わない。

mocopi failure:

- `DEMO-ONLY` または `NO-GO` と記録する。
- BODY/static fallback へ戻す。
- Quest diagnostic が `MOCOPI` でない時に、mocopi active と説明しない。

## 10. Current dirty worktree split review - 2026-05-04 late pass

Inputs used for this pass:

- `git status --short`
- `git diff --name-status`
- `git diff --stat --compact-summary`
- `python tools\validate_exhibition_release_package.py --report-json --allow-untracked-for-local-snapshot`
- Existing release package docs, smoke tools, and validator tests.

Current shape:

- Tracked modifications: 110 files, about 9.3k insertions / 1.1k deletions.
- Untracked paths are dominated by generated evidence: about 600 under `tests/.tmp/**`, 15 under `.playwright-cli/**`, 7 under `.playwright-mcp/**`.
- Release validator has no missing files and no pattern gaps, but reports 280 critical untracked package paths. That is acceptable only for a deliberate working-tree snapshot, not for a GitHub clone/archive release.
- `git diff --check` currently reports one staging blocker: `docs/modeler-wave1pp-practical-handoff.md:104` has a new blank line at EOF.

Risk-ordered split:

1. Commit now, release-critical:
   - Runtime/API contract: `src/henshin/armor_fit_contract.py`, `src/henshin/runtime_package.py`, `src/henshin/new_route_api.py`, `src/henshin/dashboard_server.py`, `src/henshin/forge.py`, `src/henshin/part_generation.py`, `src/henshin/validators.py`, plus untracked `src/henshin/variant_selection.py`.
   - Viewer contract/runtime: `viewer/shared/armor-canon.js`, `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`, `vite.quest.config.js`.
   - Exhibition gates/tools: tracked `tools/smoke_web_glb_load.py`, `tools/start_quest_adb_reverse.ps1`, `tools/validate_armor_part.py`, and untracked `tools/exhibition_smoke_check.py`, `tools/validate_exhibition_release_package.py`, `tools/validate_variant_catalog.py`, `tools/audit_quest_armor_whole_suit.py`, `tools/verify_replay_armor_alignment.mjs`.
   - Package schemas/examples: untracked `schemas/replay-record.v0.2.schema.json`, `examples/replay-record.sample.json`, `examples/modeler_delivery_manifest.sample.json`, `examples/quest-mocopi-motion-source.fixture.json`, plus modified `examples/suitspec.sample.json`.
   - Tests that guard those contracts: modified `tests/test_new_route_api.py`, `tests/test_runtime_package.py`, `tests/test_quest_recall_render_contract.py`, `tests/test_dashboard_server.py`, `tests/test_smoke_web_glb_load.py`, `tests/test_validate_armor_part.py`, plus untracked validator/variant/replay/mocopi tests including `tests/test_body_surface_policy_parity.py`.

2. Commit now if GitHub clone is the exhibition package:
   - Base armor assets already tracked and modified: `viewer/assets/armor-parts/*/*.glb`, `*.modeler.json`, `preview/*.mesh.json`, `source/*.blend`, and `_masters/*.png`.
   - Critical untracked catalog assets: `viewer/assets/armor-parts/variant_catalog.json`, all referenced `variants/**` GLB/modeler/preview files, and all required `toppings/**` GLB/modeler/preview files.
   - Validator currently counts these as 259+ critical armor/catalog paths. A GitHub release must track them, or the external PC clone will not match the local snapshot.

3. Commit as operator docs, but after code/assets are staged:
   - Required operator docs flagged by the validator: `docs/exhibition-pc-runbook-2026-05-04.md`, `docs/exhibition-day-one-page-checklist-2026-05-04.md`, `docs/exhibition-pc-release-package-manifest-2026-05-04.md`, `docs/exhibition-service-mocopi-roadmap-2026-05-04.md`, `docs/quest-mocopi-exhibition-spike-2026-05-04.md`, `docs/web-service-phase0-task-breakdown-2026-05-02.md`, `docs/replay-record-contract.md`, and the P1 limb order/manifest docs.
   - Other planning docs can be a separate documentation commit. Do not let broad docs churn block the runtime release commit.

4. Generated / QA artifact lane:
   - Keep out of normal GitHub commits: `tests/.tmp/**`, `.playwright-cli/**`, `.playwright-mcp/**`, `output/playwright/**`, root `armor-forge-japanese-ui-*.png`, and `qa/logs/**`.
   - `.gitignore` now excludes new local browser/smoke evidence and QA screenshots/logs in those paths. This is a prevention guard for future untracked artifacts only.
   - Important: ignore rules do not affect files already tracked by git. Existing tracked evidence under `.playwright-cli/**` and `tests/.tmp/**`, including modified `tests/.tmp/quest-api-live.err.log`, can still appear in `git status` and can still be staged unless reviewed explicitly.
   - `qa/*.json` reports are intentionally not ignored here because some release/snapshot reports may be curated into a handoff bundle. Treat them as manual evidence: stage only named reports that the release owner explicitly wants.
   - If a piece of evidence is show-critical, promote only a small named report/screenshot into a curated docs/qa location with a short note. Do not stage raw session dumps, vite build directories, or transient server logs.
   - `tests/.tmp/quest-api-live.err.log` is already tracked and modified; treat it as an exclusion/staging blocker unless a reviewer explicitly wants that log update.

5. Exclusion candidates:
   - `.claude/**`, `blender/**`, local Playwright/MCP state, ad-hoc examples screenshots/JPGs/zips, generated docs bundles under `examples/henshin_docs_*`, and transient QA/server logs.
   - These should remain outside the GitHub release unless they are explicitly converted into docs, fixtures, or package inputs.

6. Needs confirmation before staging:
   - `.env.example`: public defaults and Japanese trigger phrase look intentional, but it is config surface; confirm no provider-specific or venue-private value slipped in.
   - `README.md`: broad quickstart/direction update; commit with docs or release-readiness, not with runtime code.
   - `pyproject.toml`: `[project.optional-dependencies].dev = pytest` supports external-PC install and should likely ship.
   - `docs/_smoke_renders/**` and `docs/assets/**`: useful evidence/reference material, but not needed by the release validator. Curate or leave untracked.
   - Tracked artifact cleanup is a separate manual decision. If the team wants already tracked evidence removed from GitHub release history going forward, use an explicit reviewed `git rm --cached` plan; do not rely on `.gitignore` for that.

Recommended staging order:

1. Fix the `git diff --check` blank-line blocker in docs.
2. Stage runtime/API/viewer/tools/tests as one reviewed release candidate.
3. Stage critical asset/catalog paths as a separate large asset commit.
4. Stage required operator docs as a docs/runbook commit.
5. Run the release gates from a clean clone or from a deliberate snapshot report.
6. Leave QA artifacts and local state unstaged; archive only curated evidence if needed for exhibition handoff.

### Post-ignore classification update

Status commands used after the `.gitignore` artifact guard:

- `git status --short --ignored`
- `git ls-files tests/.tmp .playwright-cli`
- `git diff --check`

Read-only helper for the next staging pass:

```powershell
python tools\list_release_stage_candidates.py --json > qa\release_stage_candidates_latest.json
python tools\list_release_stage_candidates.py --summary-json > qa\release_stage_candidates_summary_latest.json
python tools\export_release_stage_manifest.py --out qa\release-stage-manifest-latest.json --sample-limit 5
python tools\validate_release_stage_manifest.py --manifest qa\release-stage-manifest-latest.json --package-report qa\exhibition_release_package_latest.json --report-json
python tools\export_release_stage_review_markdown.py --out docs\release-stage-review-latest.md --report-json
python tools\validate_shareable_qa_evidence_manifest.py --manifest qa\shareable-qa-evidence-latest.json --release-stage-manifest qa\release-stage-manifest-latest.json --strict --report-json
```

This helper only reads
`git status --porcelain=v1 -z --untracked-files=all --ignored`. It does not run
`git add`, `git commit`, or cleanup commands. Use its JSON buckets as a staging
checklist, then still review the actual staged diff before commit. Use `--json`
when the reviewer needs every path. Use `--summary-json` for the dirty worktree
overview because it keeps full ignored/generated path lists out of the report
and returns only counts plus small samples.

Use `tools\export_release_stage_manifest.py` for the push review handoff. It
reuses the summary classification, writes a machine-readable manifest with
category counts, samples, category-level recommended actions, and pre-push
`blockers` / `warnings`, and still never stages, commits, or pushes. Add
`--report-json` when the same manifest should also be printed to stdout.

Use `tools\validate_release_stage_manifest.py` after the package validator has
produced `qa\exhibition_release_package_latest.json`. It fails the push review
when the stage manifest is missing, `release-critical` is not explicit,
`ambiguous` is unresolved, generated artifacts are stage-recommended,
`qa-evidence` / `local-qa-artifact` is missing or stale for existing QA JSON, or
package `untracked_count` / `tracked_candidate_count` is materially out of sync
with the stage manifest. Add `--strict` when warnings must also block the
handoff.

Use `tools\validate_shareable_qa_evidence_manifest.py` after exporting
`qa\shareable-qa-evidence-latest.json`. It checks that `shareable_files` exist,
`blocked_files` are explicit, `recommended_git_stage_paths` contain only curated
QA JSON, and release manifest `qa-evidence` samples do not point at raw
`qa/logs/**`, screenshots, ADB dumps, or other local-only evidence. Use
`--strict` before GitHub push or external-PC transfer so release/stage mismatch
becomes a blocker instead of a warning.

When `package-report-untracked-required-files` appears, use the same JSON report
instead of re-reading the full package validator output. The blocker now includes
`required_untracked_paths_sample`, `recommended_stage_groups`, and
`manual_review_groups`; the top-level `package_manifest_alignment` repeats those
groups for tooling. Stage only the `release-critical`, `operator-docs`, and
`armor-assets` groups after reviewing their samples. Keep manual-review groups
out unless the release owner promotes a named file.

Use `tools\export_release_stage_review_markdown.py` as the final human checklist
before manual staging. It reads or internally generates the release stage
manifest and validation report, then writes
`docs\release-stage-review-latest.md` with sections for `release-critical`,
`operator-docs`, `armor-assets`, `qa-evidence`, `local-only`, `do-not-stage`,
and `final_commands`. The command is read-only with respect to git; it writes
only the Markdown review file.

Tie this report back to the minimum package manifest:

- `release-critical`: compare against the Repository Runtime list in `docs/exhibition-pc-release-package-manifest-2026-05-04.md`; stage the files needed for local Web/API, Quest, schemas, examples, validation tools, and tests.
- `operator-docs`: stage the docs that the manifest/runbook/checklist require; leave broad planning/history docs out unless the release owner explicitly wants them in the package.
- `armor-assets`: stage the base armor assets plus `variant_catalog.json`, `variants/**`, and `toppings/**` needed by catalog references. A clone package cannot drop this bucket.
- `qa-evidence`: shareable QA manifest output only. Stage only `qa/shareable-qa-evidence-latest.json` or another `recommended_git_stage_paths` entry from the shareable QA evidence manifest.
- `local-qa-artifact`: raw or privacy-unvalidated QA JSON such as package validator output, model-quality output, replay summaries, replay records, and runtime snapshots. Do not stage these directly; promote through the shareable QA manifest if the handoff needs proof.
- `reference-docs`: non-operator planning, modeler, replay, and progress docs. Stage only when promoted into the handoff; they are not clone-runtime inputs.
- `reference-artifact`: docs visual references, smoke render images, and old examples doc bundles. Stage only curated artifacts by name.
- `user-feedback-media`: user photos, screenshots, and ad-hoc messages under `examples/**`. Do not stage by default.
- `local-workspace`: `.claude/**` and `blender/**` local workspaces. Do not stage for the GitHub release.
- `generated-artifact`: do not stage for the normal GitHub release. Ignored browser dumps, `tests/.tmp/**`, `output/playwright/**`, `qa/logs/**`, transient server logs, and local screenshots are not package inputs.
- `ambiguous`: manual review for paths that still do not match a release bucket; examples images/zips and exploratory docs stay out unless promoted by name.

When preparing the final stage set, the minimum safe rule is: all required
manifest inputs must be present from `release-critical`, `operator-docs`, and
`armor-assets`; `qa-evidence` contains only shareable-manifest-recommended paths;
`local-qa-artifact`, `user-feedback-media`, `local-workspace`, and
`generated-artifact` stay unstaged; `reference-docs` / `reference-artifact` are
promoted only by name; `ambiguous` is empty unless each file has an explicit
release-owner reason.

Observed state:

- New untracked browser/smoke artifacts now show as ignored (`!!`) under `.playwright-cli/**`, `.playwright-mcp/**`, `tests/.tmp/**`, `output/playwright/**`, root `armor-forge-japanese-ui-*.png`, and `qa/logs/**`.
- `qa/*.json` and `qa/replay/*.json` reports still show as untracked on purpose. The helper expands untracked directories with `--untracked-files=all`, then keeps only shareable QA manifests in `qa-evidence`; package validator output, model-quality output, replay summaries, replay records, and runtime snapshots go to `local-qa-artifact`.
- Former ambiguous examples/docs/workspace paths are now split into `reference-docs`, `reference-artifact`, `user-feedback-media`, and `local-workspace`. These categories reduce the push blocker surface without treating raw media or local workspace files as release-critical.
- `git ls-files tests/.tmp .playwright-cli` still reports 152 tracked artifact paths. `.gitignore` does not affect these.
- `tests/.tmp/quest-api-live.err.log` remains a modified tracked artifact. Do not stage it with release-critical code unless the reviewer explicitly accepts that evidence update.
- `git diff --check` still fails on unrelated tracked docs whitespace: `docs/modeler-wave1pp-practical-handoff.md:104: new blank line at EOF`. Fix before any final push batch, but keep it outside this docs-only classification pass.

Updated release-critical bucket:

- Git hygiene guard: `.gitignore` and this cleanup plan. Stage as a small first commit so later `git status` is readable.
- Runtime/API: `package.json`, `pyproject.toml`, `.env.demo.example`, `src/henshin/**`, including untracked `src/henshin/variant_selection.py`.
- Viewer/runtime: `viewer/shared/**`, `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`, `vite.quest.config.js`.
- Exhibition tools: `tools/run_henshin.py`, `tools/exhibition_smoke_check.py`, `tools/smoke_web_glb_load.py`, `tools/validate_exhibition_release_package.py`, `tools/validate_variant_catalog.py`, `tools/start_quest_adb_reverse.ps1`, plus release-specific audit tools used by the runbook.
- Runtime schemas/examples: `schemas/replay-record.v0.2.schema.json`, `examples/suitspec.sample.json`, `examples/replay-record.sample.json`, `examples/modeler_delivery_manifest.sample.json`, `examples/quest-mocopi-motion-source.fixture.json`.
- Contract tests: modified tracked tests and new `tests/test_*.py` that cover runtime package, Quest recall, replay record, exhibition package validation, variant selection/catalog, mocopi source labeling, and body surface policy parity.
- Armor package: `viewer/assets/armor-parts/variant_catalog.json`, all base 18 part GLB/modeler/preview/source files, and all referenced `variants/**` / `toppings/**` GLB/modeler/preview assets. A GitHub clone will not be exhibition-equivalent without these.

Updated generated bucket:

- Ignored and normally unstaged: `.playwright-cli/**`, `.playwright-mcp/**`, `tests/.tmp/**`, `output/playwright/**`, `qa/logs/**`, root temporary screenshots/logs.
- Already tracked artifacts are not automatically generated-bucket in Git terms. Treat them as "tracked artifact cleanup" and review separately; do not mix a 152-file `git rm --cached` decision into runtime release commits.
- Recommended current handling: leave tracked artifacts untouched, avoid staging any modified tracked artifact, and open a separate cleanup task if the repository should stop carrying historical `.playwright-cli/**` and `tests/.tmp/**` evidence.

Updated QA evidence bucket:

- `qa/shareable-qa-evidence-latest.json`: primary curated QA stage candidate.
- `qa/*mocopi-evidence-package*.json`: shareable only when included by `recommended_git_stage_paths`.
- Do not classify arbitrary `*_latest.json` or replay summaries as `qa-evidence`; privacy/shareable validation must promote them first.

Updated local QA artifact bucket:

- `qa/exhibition_release_package_latest.json`, `qa/model-quality-acceptance-latest.json`, `qa/release-stage-validation-latest.json`, `qa/replay/*.summary.json`, `qa/replay/*.replay-record.json`, `qa/*runtime-package*.snapshot.json`, and `qa/*replay-record*.demo.json`: local/raw or privacy-unvalidated evidence. Do not stage directly for the normal GitHub release.

Updated reference/non-release buckets:

- `reference-docs`: broad planning/modeler/replay/web notes under `docs/**` that are not listed as operator docs. Stage only if the release owner promotes them into the handoff.
- `reference-artifact`: `docs/assets/**`, `docs/_smoke_renders/**`, and old `examples/henshin_docs*_bundle*` outputs. Keep unstaged unless a small named visual/reference is required.
- `user-feedback-media`: ad-hoc `examples/*.jpg`, screenshots, and messages. Do not stage by default.
- `local-workspace`: `.claude/**` and `blender/**`. Keep local.

Updated ambiguous bucket:

- Any remaining `ambiguous` path is a true unknown and blocks push review until it is classified, explicitly excluded, or promoted by name.
- `.env.example`, `README.md`, and `package.json`: public setup surface. Review for venue-private values and command drift before staging.

Minimum next staging units:

1. `release-hygiene`: `.gitignore` plus `docs/exhibition-github-cleanup-plan-2026-05-04.md`.
2. `runtime-contract`: runtime/API/viewer/shared/tools/schemas/examples/tests, excluding generated evidence.
3. `armor-assets`: `viewer/assets/armor-parts/**` base assets, catalog, variants, and toppings.
4. `operator-docs`: exhibition PC runbook, one-page checklist, release package manifest, mocopi/service roadmap, replay contract, and required modeler/P1 acceptance docs.
5. `qa-evidence` only if needed: the shareable QA evidence manifest and any path it explicitly recommends. No raw replay summaries, replay records, runtime snapshots, server logs, vite build directories, or Playwright dumps.

External-PC clone must not miss:

- `package.json`, `package-lock.json`, `pyproject.toml`, `vite.quest.config.js`.
- `src/henshin/**`, including new selection/runtime/package/validator modules.
- `viewer/shared/**`, `viewer/armor-forge/**`, `viewer/quest-iw-demo/**`.
- `viewer/assets/armor-parts/**`, especially `variant_catalog.json`, base GLB/modeler/preview/source files, and all catalog-referenced variants/toppings.
- `schemas/replay-record.v0.2.schema.json` and runtime sample JSON under `examples/`.
- Exhibition tools and docs listed in the release package manifest.
- Tests are not needed to run the demo, but they are required before declaring the pushed branch clone-safe.

Release stage gate update:

- `tools/export_release_stage_manifest.py` now emits `stage_decision` with three machine-readable groups: `stage_candidates`, `manual_review`, and `do_not_stage`.
- `stage_candidates` is limited to `release-critical`, `operator-docs`, and `armor-assets`.
- `manual_review` contains `qa-evidence`, `reference-docs`, `reference-artifact`, and `ambiguous`; these are never automatic `git add` inputs.
- `do_not_stage` contains `local-qa-artifact`, `user-feedback-media`, `local-workspace`, and `generated-artifact`; this is the mechanical exclude set for normal GitHub push review.
- `tools/validate_release_stage_manifest.py` now blocks stale manifests without `stage_decision`, blocks do-not-stage category policy drift, and blocks manifest samples that place raw/local QA JSON in `qa-evidence`.
- `tools/export_release_stage_review_markdown.py` includes a `stage_summary` section so the human review mirrors the JSON split before manual staging.

## 11. Final push / exhibition release checklist

push 前:

| Check | Pass condition |
|---|---|
| Worktree triage | stage 対象が commit segmentation と一致している |
| No accidental evidence | `.playwright-*`, `tests/.tmp/**`, root一時画像を混ぜていない |
| Deterministic install | release / clean clone / 展示PCでは `npm ci` を使う |
| Clean clone | exact release branch/tag/commit から検証し、未追跡runtime fileがない |
| Syntax | `node --check` が Web/Quest で通る |
| Unit/integration | `python -m pytest -q` が通る |
| npm validation | `npm test` が通る |
| Quest build | `npx vite build --config vite.quest.config.js ...` が通る |
| Catalog | `validate_variant_catalog.py` が通る |
| Package | `validate_exhibition_release_package.py --report-json` が通る |
| GLB | `smoke_web_glb_load.py --report-json` が通る |
| Whole-suit audit | `audit_quest_armor_whole_suit.py --fail-on fail` が通る |
| PC-side local smoke | `exhibition_smoke_check.py --forge` が `local-pass` |
| Server restart | exact release commit から Web/API `8010` と Quest `5173` を再起動し、古いprocessを掴んでいない |
| Physical Quest telemetry | Quest/Oculus UA、`localhost:5173` href、fresh code、今回の `t=$stamp`、`xr.session=true`、`uxState` を確認した |
| Fresh code | 最終確認に fresh code を使用した |
| Public refs | `unsafe_public_ref_count=0` |
| Optional labels | `service-*`, `playcanvas-*`, `mocopi-*` を local 判定の後に記録した |

展示PCへ持ち出し OK:

- `local-pass`
- exact release branch/tag/commit の clean clone gate が通っている
- `npm ci` で依存が再現されている
- `adb devices -l` が `device`
- `adb reverse --list` に `5173` と `8010`
- Web Forge fresh code と Quest recall code が一致
- `/api/quest-debug/latest` が物理Quest由来で、今回の `t=$stamp`、`xr.session=true`、判定対象 `uxState` を記録している
- whole-suit audit が `status=pass`
- Replay proof または frozen fallback replay が portable
- last-known-good package が別途存在
- operator が rollback 手順を読める

展示PCへ持ち出し NG:

- `local-fail`
- exact release branch/tag/commit の clean clone で再現できない
- `npm install` では動くが `npm ci` が失敗する
- `8010` または `5173` が固定で起動しない
- Quest が USB 経由で `localhost:5173` を開けない、かつ LAN fallback も未検証
- `/api/quest-debug/latest` がPC Playwright由来、古いtab由来、古い `t=...`、または `xr.session=false` のまま
- whole-suit audit が fail
- GLB fallback/proxy を public pass と扱っている
- GitHub release に必要な untracked runtime file が残っている
- GCP、PlayCanvas、mocopi の成功だけで本線を通そうとしている
