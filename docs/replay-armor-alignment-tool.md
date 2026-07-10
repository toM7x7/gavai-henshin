# Replay Armor Alignment Tool

Use `tools/verify_replay_armor_alignment.mjs` to turn the current manual
Playwright Quest viewer check into a reusable artifact.

It opens the Quest viewer with `qa=1`, `debug=1`, `newRoute=1`,
`mockTrigger=1`, and `mic=0`, loads a 4-character recall code, triggers the mock
voice/replay path, samples armor mesh positions at fixed replay progress values,
and writes screenshots plus per-part armor/base deltas.

## Prerequisites

Run the local API/dashboard and Quest Vite viewer:

```powershell
npm run dev
npm run dev:quest -- --port 5173
```

The Quest Vite proxy should point at the API origin. By default the tool leaves
`apiBase` empty so browser fetches use the viewer origin and Vite proxies `/v1`,
`/api`, and `/sessions` to `http://127.0.0.1:8010`.

## Command

```powershell
node tools/verify_replay_armor_alignment.mjs --code 3601
```

Useful overrides:

```powershell
node tools/verify_replay_armor_alignment.mjs `
  --url http://127.0.0.1:5173/viewer/quest-iw-demo/ `
  --code 3601 `
  --trigger both `
  --view-mode mirror `
  --samples 0.25,0.5,0.75,1 `
  --output-dir output/playwright/replay-armor-alignment/3601
```

Only pass `--api-base` when the target viewer page can call that API origin
directly, or when you are intentionally bypassing the Vite same-origin proxy.

## Outputs

The tool writes:

- `alignment-report.json`: full diagnostic payload with recall metadata,
  trigger result, console/page errors, screenshot paths, base shell positions,
  armor mesh positions, runtime placement fields, per-part deltas, and replay
  debug state.
- `alignment-parts.csv`: flat table for quick spreadsheet review.
- `alignment-<view>-pNNN.png`: screenshots for each sampled replay progress.

Interpret `distance_m` as an inspection metric, not an automatic pass/fail gate.
Helmet/chest/waist/back should usually be tightest; hands and boots are noisier
because their endpoints may be estimated.

The JSON summary intentionally separates:

- `summary.maxExcessDistanceM`: the largest visible-part excess across every
  sampled progress point. This can include early deposition motion while parts
  are still sliding into place.
- `settledSummary.maxExcessDistanceM`: the same metric for samples at replay
  progress `>= 0.5`. Use this as the first exhibition read for "is the armor
  attached to the body after formation?"

Hidden or nearly transparent parts are written to CSV for debugging, but they
do not affect the summary metrics. This avoids false alarms from hand/leg parts
that are still at origin before their deposition segment becomes visible.

For current Quest alignment investigations, each `samples[]` entry also carries
a backward-compatible `debug` object. It records the sampled `viewMode`,
`playing`, numeric `progress`, `armorStandPreview`, `microphone`, `baseShell`,
`depositionEffects`, `mirrorFrame`, `liveMirror`, `uxState`, and `experience`
state. `uxState` is the compact viewer state name, while `experience` carries
the richer mode/expectation details supplied by the viewer debug snapshot. When
running against an older viewer that does not expose those top-level fields, the
tool writes a best-effort fallback `experience` with visible status text, route
badges, button disabled flags, replay source, voice state, and related UI state.
The report also includes a compact top-level `debugTimeline[]` so reviewers can
scan those flags without opening every sampled part record. Existing part
metrics and CSV columns are unchanged.
