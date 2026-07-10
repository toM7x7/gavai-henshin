# Quest基礎体験安定後の実装/確認フェーズ計画 - 2026-05-04

目的: 新規路線「Webでスーツ成立、Questで変身試験、Replayで体験を残す」を展示フェーズの実装順に落とす。Webサービス化、GCP、PlayCanvas、mocopiは、Quest基礎体験が物理実機で安定した後に進める。

この文書は `docs/current-progress-next-schedule-2026-05-04.md` の次フェーズ整理であり、現場判断では `docs/exhibition-github-cleanup-plan-2026-05-04.md` の release gate と合わせて使う。

## 判断原則

- Webがスーツを成立させる。Web Forgeは `suit_id`、`suit_version_id`、fresh 4桁 `recall_code`、runtime package、Quest link、previewを作る。
- Questが変身試験をする。Questは4桁コードで同じスーツを呼び出し、観察、変身、mirror/replay確認を物理HMDで成立させる。
- Replayが体験を残す。Replayは見た目の証跡ではなく、`suit_id`、`recall_code`、runtime package version、trial、events、artifact refsを持つ可搬記録にする。
- `local-pass` が展示本線の入口。GCP、PlayCanvas、mocopiは `local-pass` を上書きできない。
- Questの `armor_stand_observer_idle` は観察証跡であり、変身成功証跡ではない。変身/mirrorの合格は `archive_replay_mirror_active` か transform進行状態で判定する。
- `3601` は過去検証コード。最終フェーズ判定ではWeb Forgeが発行したfresh codeを使う。

## Phase 0: Quest基礎体験の物理安定

狙い: Quest実機で「スーツが見える」ではなく、「正しい状態で観察でき、変身に進み、mirror/replayで体験を確認できる」まで固定する。

必須ゲート:

```powershell
node --check viewer\quest-iw-demo\quest-demo.js
python -m pytest tests\test_quest_recall_render_contract.py tests\test_dashboard_server.py tests\test_quest_armor_whole_suit_audit.py -q
npx vite build --config vite.quest.config.js --outDir tests\.tmp\quest-vite-build-quest-foundation --emptyOutDir
python tools\audit_quest_armor_whole_suit.py --output qa\quest_armor_whole_suit_foundation.json --fail-on fail
```

物理Quest確認:

1. exact release commitからWeb/API `8010` とQuest Vite `5173` を再起動する。
2. `adb reverse --remove tcp:5173` と `adb reverse --remove tcp:8010` を実行してから `npm run dev:quest:adb` を張り直す。
3. Web Forgeでfresh codeを発行する。
4. timestamp付きURLをQuest Browserへ投げる。

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$questUrl = "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<FRESH_CODE>&replayView=mirror&debug=1&t=$stamp"
adb shell am start -a android.intent.action.VIEW -d "$questUrl"
Invoke-RestMethod http://localhost:8010/api/quest-debug/latest | ConvertTo-Json -Depth 12
```

合格条件:

- `query.href` が `http://localhost:5173/viewer/quest-iw-demo/` で、今回の `t=$stamp` を含む。
- `query.userAgent` がQuest/Oculus Browser由来。
- `query.code` がfresh code。
- VR/session開始後に `xr.session=true`。
- 鎧立て観察では `uxState=armor_stand_observer_idle` として記録する。
- 変身/mirror合格は `uxState=archive_replay_mirror_active`、`xr.viewMode=mirror`、`playing=true`、`progress>0`。
- real voice確認はURLに `mockTrigger=1` と `mic=0` がなく、`realMicrophoneExpected=true`。
- 右グリップ回転、両グリップ拡縮、右トリガー展開/戻しが音声変身を誤爆しない。

このPhaseの出口:

- `quest-foundation-pass` または `quest-foundation-fail` を記録する。
- `quest-foundation-fail` の間は、Webサービス化、GCP、PlayCanvas、mocopiを展示本線へ昇格しない。

## Phase 1: Web -> Quest -> Replay のローカル展示ループ

狙い: Quest基礎が通った同じcommitで、Webの成立、Quest試験、Replay保存を1本の来場者ループとして確認する。

実装対象:

- Web Forgeのvisitor-first導線: 名前、身長、短いコンセプト、生成、4桁コード、Quest link、preview。
- Quest側の状態整理: 観察、変身待機、変身中、mirror/replayを `uxState` で明確化。
- Replayの最小保存: `suit_id`、`recall_code`、runtime package version、trial id、events、artifact refs。
- operator/debug情報はvisitor画面から退避する。

確認コマンド:

```powershell
python -m pytest tests\test_new_route_api.py tests\test_runtime_package.py tests\test_replay_record_contract.py -q
python tools\exhibition_smoke_check.py --forge
```

合格条件:

- Web Forgeがfresh codeを生成する。
- Questが同じfresh codeをrecallする。
- `runtime-render-placement.v1`、18 render placements、selected variant mismatchなし。
- Replay proofまたはfrozen fallback replayが、bundle-relative、`gs://`、承認済み `https://` のいずれかで可搬。
- `C:\...`、`file://`、dev LAN URL、古いbrowser cacheへ依存しない。

このPhaseの出口:

- `local-loop-pass`。
- ここまでが「展示として見せてよい最小体験」の核。

## Phase 2: 外部展示PC baseline / GitHub release readiness

狙い: 開発PCではなく、外部展示PCまたは同等のclean PCで展示ループを再現する。

必須:

- GitHubへ出す exact release commit を固定する。
- clean cloneで `npm ci` とPython installを通す。
- `validate_exhibition_release_package.py` を `--allow-untracked-for-local-snapshot` なしで通す。
- `smoke_web_glb_load.py` と `audit_quest_armor_whole_suit.py` を通す。
- Web/API `8010`、Quest Vite `5173`、USB ADB reverseを固定する。

確認順:

1. clean clone / exact commit gate。
2. package / asset / whole-suit gate。
3. PC-side `exhibition_smoke_check.py --forge`。
4. physical Quest telemetry gate。
5. Replay可搬性確認。
6. last-known-good packageとrollback手順確認。

このPhaseの出口:

- `local-pass`。
- `local-pass` がない限り、以降のクラウド/adapter/hardware成果は展示本線へ昇格しない。

## Phase 3: Webサービス化の準備

狙い: GCPへ載せる前に、現行ローカルAPIの意味を固定し、store/artifact境界を抽象化する。ここではまだCloud Runを展示依存にしない。

実装対象:

- `/v1/suits/forge` と `/v1/quest/recall/{code}` のpayload shape固定。
- `POST /v1/trials`、`POST /v1/trials/{trial_id}/events`、`GET /v1/trials/{trial_id}/replay` の最小contract整理。
- local JSON/file store と将来DB storeの境界整理。
- artifact refsを物理pathではなくlogical refsへ寄せる。
- public responseからlocal path、secret、raw provider payload、debug-only stateを除外する。

合格条件:

- Web、Quest、Replayが同じruntime package snapshotを参照する。
- 4桁codeは短命lookup handleであり、durable identityではない。
- Replayのdurable anchorは `suit_id`、`suit_version_id`、`trial_id`、manifest id、runtime package version。
- GCPへ写す前に、local contract testsが通る。

このPhaseの出口:

- `service-contract-freeze`。

## Phase 4: GCP staging

狙い: `service-contract-freeze` 後に、GCPを耐久サービス/アーカイブ基盤として接続する。展示本線の代替ではなく、staging rehearsalとして扱う。

最小構成:

- Cloud Run: current API/UI boundaryを維持。
- Cloud SQL: suits、suit_versions、recall_codes、trials、transform_events、replay_records、generation_jobs、consent。
- Cloud Storage: GLB、manifest、runtime package snapshot、preview、texture、replay script、motion、voice/audio、export。
- Cloud Tasks: 生成、validation、preview、replay mediaなど遅い処理。
- Secret Manager: provider keys、DB credentials、signing secrets。
- structured logs: `suit_id`、`recall_code`、manifest id、runtime package version、trial id、job id。

合格条件:

- staging endpointでもforge、recall、Replay、no-local-path checkが通る。
- local external-PC loopはGCPなしで継続できる。
- `service-pass/fail/not-included` を、`local-pass` の後にだけ記録する。

禁止:

- Cloud-only show pathを `local-pass` 前に採用する。
- Firestoreをdurable suit/recall/replay historyの主DBにする。
- GKE、service mesh、多数microservicesを展示前の必須作業にする。

## Phase 5: PlayCanvas adapter

狙い: PlayCanvasをプラットフォーム本体ではなく、runtime package snapshot consumerとして評価する。

許可する役割:

- Web preview / shareable 3D viewer。
- accepted GLBのvisual QA harness。
- exported replay viewer。

禁止する役割:

- variant selection。
- render placement resolution。
- recall code lifecycle。
- catalog acceptance policy。
- Replay derivation。
- mocopi provenance / consent / retentionの所有。

合格条件:

- exported manifest/runtime package snapshotを読む。
- Web/Quest/Replayのcanonical stateを書き換えない。
- 削除してもWeb、Quest、Replayの意味が変わらない。

このPhaseの出口:

- `playcanvas-pass/fail/not-included`。

## Phase 6: mocopi enhancement

狙い: Quest基礎体験とlocal exhibition loopが安定した後、mocopiを任意の身体性強化として入れる。mocopiは展示本線の成立条件ではない。

順序:

1. Phase 0 diagnostic: Questが `BODY`、`MOCOPI`、`MOCOPI+LIVE` を誤表示なく区別する。
2. Phase 1 imported JSON: mocopi exportを既存body-sim/replay pathへ通し、`MOCOPI <n>f` と `BODY <n>f` を比較できる。
3. Phase 2 live receiver: real sensors、calibration、latency、left/right consistency、fallbackを実機で確認する。

live receiver合格条件:

- 6 sensorsが60秒以上安定。
- median visible latency `<= 120 ms`。
- p95 `<= 250 ms`。
- dropped/frozen motion `< 2%`。
- 左右入れ替わりなし。
- 60秒以内にBODY/static fallbackへ戻せる。
- raw mocopi motionとvoice/audioにconsent/retention方針がある。

ラベル:

- `mocopi-GO`: visitor pathに出せる。
- `DEMO-ONLY`: operator-led demoのみ。
- `NO-GO`: 使わない。
- `not-included`: 持ち込み対象外。

## 全体順序

| Order | Phase | Gate | 次へ進む条件 |
|---:|---|---|---|
| 0 | Quest基礎体験 | `quest-foundation-pass/fail` | 物理Questでfresh code、XR session、uxState、mirror/voice/stand操作が確認済み |
| 1 | Web -> Quest -> Replay local loop | `local-loop-pass/fail` | Web成立、Quest試験、Replay可搬proofが1本で通る |
| 2 | 外部展示PC / GitHub release | `local-pass/fail` | clean clone、`npm ci`、package、GLB、whole-suit、physical telemetryが通る |
| 3 | Webサービス化準備 | `service-contract-freeze/pending` | local `/v1` contract、store/artifact境界、Replay anchorが固定 |
| 4 | GCP staging | `service-pass/fail/not-included` | GCPがlocal truthをforkせず、同等smokeを通す |
| 5 | PlayCanvas adapter | `playcanvas-pass/fail/not-included` | snapshot consumerに留まり、canonical stateを持たない |
| 6 | mocopi enhancement | `mocopi-GO/DEMO-ONLY/NO-GO/not-included` | Quest基礎とfallbackが安定し、実機sensor gateを通す |

## 直近の実行順

1. Quest実機を起こし、timestamp付きfresh code URLで `xr.session=true` のtelemetryを取る。
2. 鎧立ての右グリップ回転、両グリップ拡縮、右トリガー展開/戻しを確認する。
3. mirror/replayへ戻し、`archive_replay_mirror_active` で変身証跡を取る。
4. real voice laneを別URLで確認し、debug/recovery laneと混ぜない。
5. `audit_quest_armor_whole_suit.py` とphysical Quest写真/telemetryを合わせ、全身装着の大破綻がないか判断する。
6. exact release commitからclean cloneし、外部展示PC `local-pass` を取る。
7. その後にだけ、Webサービス化、GCP staging、PlayCanvas adapter、mocopi enhancementを順番に進める。
