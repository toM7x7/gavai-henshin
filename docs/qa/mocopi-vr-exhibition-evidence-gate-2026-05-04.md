# mocopi / VR Exhibition Evidence Gate - 2026-05-04

目的: mocopiを理想ラインとして検証しつつ、展示本番ではBODY/staticへ戻せる
ことと、共有物に生ログ・画像・秘密値を混ぜないことを同時に守る。

## Review Finding

- mocopi計画は `mocopi-GO/DEMO-ONLY/NO-GO`、BODY baseline、MOCOPI
  candidate、fallback recoveryの三点証跡を前提にできている。
- QA証跡分類は `validate_qa_evidence_privacy.py`、
  `export_shareable_qa_evidence_manifest.py`、
  `validate_shareable_qa_evidence_manifest.py --strict` の順で使う。
- 不足していた点: 現行の `release-stage-manifest.v4` /
  `release-stage-manifest-validation.v4` と
  `shareable-qa-evidence-manifest.v1` がprivacy/shareable allowlistの実運用
  とずれる可能性があった。共有候補は現行契約名で再検査する。
- `mocopi-evidence-evaluation.json` と `mocopi-rehearsal-plan-latest.json`
  は作業JSON。pack pathや評価理由を含むため、GitHub/別PC共有は
  `mocopi-evidence-package-latest.json` に要約してから行う。

## Exhibition QA Order

1. Start local baseline only: Web/API `8010`, Quest Vite `5173`, USB
   `adb reverse` for `5173` and `8010`.
2. Prove `local-pass` with the normal Web -> Quest -> Replay route before
   touching mocopi.
3. Capture BODY baseline:

   ```powershell
   .\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline
   ```

4. Rehearse imported/physical mocopi in an operator-only lane. Do not change the
   default visitor route.
5. Capture MOCOPI candidate. Add `-Screencap` only when visual mismatch needs a
   local-only image:

   ```powershell
   .\tools\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap
   ```

6. Disable/bypass mocopi and capture fallback recovery within 60 seconds.
7. Evaluate and package:

   ```powershell
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
     --evidence-dir qa\logs\quest-3601-<mocopi> `
     --out qa\mocopi-evidence-package-latest.json `
     --report-json
   ```

8. Privacy/share gate:

   ```powershell
   python tools\export_release_stage_manifest.py `
     --out qa\release-stage-manifest-latest.json `
     --sample-limit 5

   python tools\validate_qa_evidence_privacy.py `
     --qa-root qa `
     --mode share `
     --release-stage-manifest qa\release-stage-manifest-latest.json `
     --report-json

   python tools\export_shareable_qa_evidence_manifest.py `
     --qa-root qa `
     --out qa\shareable-qa-evidence-latest.json `
     --report-json

   python tools\validate_shareable_qa_evidence_manifest.py `
     --manifest qa\shareable-qa-evidence-latest.json `
     --release-stage-manifest qa\release-stage-manifest-latest.json `
     --strict `
     --report-json
   ```

## Share / Keep Local

Share only files that actually appear in `qa/shareable-qa-evidence-latest.json`
`recommended_git_stage_paths`. Typical candidates are:

- `qa/shareable-qa-evidence-latest.json`
- `qa/release-stage-manifest-latest.json`
- `qa/release-stage-validation-latest.json`
- `qa/mocopi-evidence-package-latest.json`

Keep local by default:

- `qa/logs/**`
- `adb-devices.txt`, `adb-reverse.txt`, `operator-summary.txt`,
  `quest-debug-latest.json`
- `screencap.png`, photos, videos, raw mocopi captures, raw replay records,
  runtime snapshots, server logs
- `qa/mocopi-evidence-evaluation.json`
- `qa/mocopi-rehearsal-plan-latest.json`
- any JSON with secret-like keys, unknown contract, localhost-only proof, or
  local absolute paths unless it is re-packaged into a sanitized manifest

## GO / DEMO-ONLY / NO-GO Evidence

- `mocopi-GO`: local baseline pass, all three packs present, Quest shows usable
  `MOCOPI` frames, centerline QA has no unresolved runtime/hard-sync blocker,
  latency/freeze/left-right checks pass, consent/retention noted, fallback to
  BODY/static proven within 60 seconds.
- `mocopi-DEMO-ONLY`: BODY/static is safe, but mocopi is import/replay-only,
  operator-assisted, latency-warn, centerline-warn, or lacks full physical
  sensor evidence.
- `mocopi-NO-GO`: local baseline missing, Quest cannot produce audit telemetry,
  `MOCOPI` is absent/`0f`, ADB is unauthorized, fallback fails, left/right swaps,
  freezes exceed the gate, consent/retention is missing, or mocopi destabilizes
  BODY/static.

GitHub staging rule: never run `git add qa/`. Stage only named files from
`recommended_git_stage_paths` after `validate_shareable_qa_evidence_manifest.py
--strict` passes.
