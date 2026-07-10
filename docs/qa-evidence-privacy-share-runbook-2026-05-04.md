# QA Evidence Privacy / Share Runbook - 2026-05-04

展示PC、別PC、GitHubへQA証跡を渡す前に見る1ページ。原則は
`qa/logs/**` をローカル保管、共有は curated JSON manifest だけに絞る。

## 共有してよいもの / だめなもの

| 判定 | 対象 | 運用 |
|---|---|---|
| 共有OK候補 | `qa/shareable-qa-evidence-latest.json` | 最終的な共有候補一覧。GitHub stagingはこの中の `recommended_git_stage_paths` だけを見る。 |
| 共有OK候補 | `qa/release-stage-manifest-latest.json` | release stage側の `qa-evidence` と shareable manifest の整合確認に使う。 |
| 共有OK候補 | `qa/mocopi-evidence-package-latest.json` | mocopi/BODY fallbackの最小共有パック。raw evidence dirの中身そのものは含めない。 |
| 原則ローカル | `qa/mocopi-rehearsal-plan-latest.json`, `qa/mocopi-evidence-evaluation.json` | 展示リハーサルの作業JSON。pack pathや評価理由を含むため、共有は `qa/mocopi-evidence-package-latest.json` に要約してから行う。 |
| 共有OK候補 | release ownerが名前で選んだ `qa/*_clean_clone*.json`, `qa/*_external_pc*.json`, `qa/replay/*.summary.json` | release packageや別PC受け渡しで必要な小さいJSONだけ。 |
| ローカル限定 | `qa/logs/**` | Quest実機、ADB、operator summary、debug latestの一次証跡。GitHubへ入れない。 |
| ローカル限定 | `quest-debug-latest.json`, `operator-summary.txt`, `adb-devices.txt`, `adb-reverse.txt` | `capture_quest_debug_snapshot.ps1` の生出力。必要な事実は curated manifestへ転記する。 |
| ローカル限定 | `*.png`, `*.jpg`, `*.webp`, `*.mp4`, screencap, Quest screenshot | 個人情報、会場、参加者、画面状態が混ざる前提。共有対象外。 |
| ローカル限定 | raw replay record, runtime package snapshot, raw mocopi stream, raw ADB dump, raw server log | 量が大きい、個人/端末/ローカルパスが混ざる。release ownerが別管理する。 |
| ブロッカー | token/password/secret/api key系のJSON key/value | `validate_qa_evidence_privacy.py --mode share` で検出したら共有前に除去。 |
| 注意 | `localhost`, `127.0.0.1`, local path | local evidenceでは許容。外部共有では「そのPCでしか意味がない証跡」としてwarning扱い。 |

## 実行コマンド順

PowerShellをリポジトリrootで開いて実行する。Quest/mocopiの一次証跡が不要な
場合は mocopi evidence block を飛ばしてよい。

### 1. mocopi/BODY fallback証跡がある場合

```powershell
.\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline

python tools/evaluate_mocopi_evidence_pack.py `
  --body-baseline qa\logs\quest-3601-<body> `
  --mocopi-candidate qa\logs\quest-3601-<mocopi> `
  --fallback-recovery qa\logs\quest-3601-<fallback> `
  --report-json > qa\mocopi-evidence-evaluation.json

python tools/export_mocopi_rehearsal_plan.py `
  --evaluation-json qa\mocopi-evidence-evaluation.json `
  --out qa\mocopi-rehearsal-plan-latest.json `
  --report-json

python tools/package_mocopi_evidence.py `
  --evaluation-json qa\mocopi-evidence-evaluation.json `
  --rehearsal-plan qa\mocopi-rehearsal-plan-latest.json `
  --evidence-dir qa\logs\quest-3601-<timestamp> `
  --out qa\mocopi-evidence-package-latest.json `
  --report-json
```

`-Screencap` は視覚状態を残す必要がある時だけ使う。生成された画像は
共有対象ではなく、`qa/logs/**` のローカル証跡として扱う。

### 2. release stage候補を作る

```powershell
python tools\export_release_stage_manifest.py `
  --out qa\release-stage-manifest-latest.json `
  --sample-limit 5
```

この時点で `qa-evidence` に raw log、画像、`qa/logs/**`、runtime snapshotが
入っていたら、release ownerが分類を直すまでGitHub stagingしない。

### 3. privacy gateを通す

```powershell
python tools\validate_qa_evidence_privacy.py `
  --qa-root qa `
  --mode share `
  --release-stage-manifest qa\release-stage-manifest-latest.json `
  --report-json > qa\qa-evidence-privacy-share-report.json
```

判定:

- `status=pass`: 次へ進む。
- `warning`のみ: `localhost` やlocal-only候補が理由なら、共有manifest側で除外されていることを確認して次へ進む。
- `blocker`: 秘密値候補、raw共有候補、release manifest混入を除去するまで停止。

### 4. shareable manifestを出す

```powershell
python tools\export_shareable_qa_evidence_manifest.py `
  --qa-root qa `
  --out qa\shareable-qa-evidence-latest.json `
  --report-json
```

見る項目:

- `shareable_files`: GitHub/別PCへ渡せる候補。
- `local_only_files`: PC内に残す証跡。stageしない。
- `blocked_files`: 共有前に必ず処理するファイル。
- `recommended_git_stage_paths`: GitHubへstageしてよい候補の唯一の入口。

### 5. release stageとの矛盾を止める

```powershell
python tools\validate_shareable_qa_evidence_manifest.py `
  --manifest qa\shareable-qa-evidence-latest.json `
  --release-stage-manifest qa\release-stage-manifest-latest.json `
  --strict `
  --report-json
```

`--strict` がfailなら、`qa-evidence` と `recommended_git_stage_paths` のどちらかが
古い。manifestを再生成するか、release ownerが `qa-evidence` の対象を絞る。

## GitHub staging判断

GitHubへstageしてよいのは、次を全て満たした時だけ。

1. `validate_qa_evidence_privacy.py --mode share` に blocker がない。
2. `validate_shareable_qa_evidence_manifest.py --strict` が pass。
3. `qa/shareable-qa-evidence-latest.json` の `blocked_files` が空、またはGitHub外で扱う理由が明記済み。
4. `recommended_git_stage_paths` に `qa/logs/**`, 画像/動画, raw log, runtime snapshot, raw replay recordがない。
5. `release-stage-manifest-latest.json` の `qa-evidence` が `recommended_git_stage_paths` と矛盾していない。

stageする時は `recommended_git_stage_paths` を手で読み、必要な小さいJSONだけを
名前指定する。`git add qa/` は禁止。

例:

```powershell
git add qa\shareable-qa-evidence-latest.json
git add qa\release-stage-manifest-latest.json
git add qa\mocopi-evidence-package-latest.json
```

`qa-evidence-privacy-share-report.json` は調査用レポートとして便利だが、共有対象に
するかはrelease ownerが名前で決める。自動的にstageしない。

## 別PCへ渡す最小セット

別PCの運用者に渡すのは、原則として次だけ。

- `qa/shareable-qa-evidence-latest.json`
- `qa/release-stage-manifest-latest.json`
- 必要な場合だけ `qa/mocopi-evidence-package-latest.json`
- release ownerが選んだ clean-clone / external-PC / replay summary JSON

渡さないもの:

- `qa/logs/**`
- `adb-*.txt`
- `quest-debug-latest.json`
- `operator-summary.txt`
- screencap、写真、動画
- raw mocopi / raw replay / runtime snapshot / server log
- `qa/mocopi-evidence-evaluation.json` と `qa/mocopi-rehearsal-plan-latest.json` は、`shareable-qa-evidence-latest.json` の `recommended_git_stage_paths` に入らない限り渡さない。

別PCで「実機で何が起きたか」を見たい場合は、生ログではなく
`mocopi-evidence-package-latest.json` と `shareable-qa-evidence-latest.json` を見る。
