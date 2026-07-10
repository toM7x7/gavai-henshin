# Quest Armor Anchor Centerline Notes - 2026-05-05

## Purpose

Latest evidence reported:

```text
centerline QA fail/runtime_anchor anchor=NG hard=WARN part=0 glb=0
```

This shape does not identify whether the active runtime placement path was `web_preview_parity` or the default `quest_rig` path. The Quest debug payload now includes explicit anchor diagnostics so the next capture can separate XR anchor/runtime sync failures from placement-offset failures.

## New Debug Fields

Each `meshes.records[]` entry now includes:

- `anchorDiagnostics.activeMode`: active placement mode, either `web_preview_parity` or `quest_rig`.
- `anchorDiagnostics.activeOffsetSource`: which offset candidate matched the applied clamped offset.
- `anchorDiagnostics.questRigOffsetClamped`: Quest-space clamped offset candidate.
- `anchorDiagnostics.webPreviewOffsetClamped`: Web/VRM-space clamped offset candidate.
- `anchorDiagnostics.questVsWebOffsetDeltaM` and `questVsWebOffsetDistanceM`: direct candidate difference.

`centerlineQa.anchorDiagnostics` now includes:

- `runtimePlacementModeCounts`
- `activeOffsetSourceCounts`
- `dominantRuntimePlacementMode`
- `dominantActiveOffsetSource`
- `runtimeOffsetImplicated`
- `likelySource`
- `triageHint`

The centerline display line also appends:

```text
mode=<dominantRuntimePlacementMode> offset=<dominantActiveOffsetSource>
```

## Triage Reading

If the same evidence repeats as:

```text
anchor=NG hard=WARN part=0 glb=0
```

and `centerlineQa.anchorDiagnostics.likelySource` is `runtime_anchor_not_runtime_offset`, the immediate suspect is XR world anchor / rig synchronization, not Web parity or Quest rig offset math.

If `part>0` and `likelySource` starts with `runtime_offset_`, compare `dominantActiveOffsetSource` and per-part `questVsWebOffsetDistanceM` to decide whether the failing path is `web_preview_parity`, `quest_rig`, or mixed/custom.

## 2026-05-05 04:18 Update

The first fix for the later `part=5` armor-stand warning was to stop comparing an armor-stand preview mesh against the untransformed worn-body anchor. `questPartCenterDebugSnapshot()` now resolves its debug anchor through `questDebugAnchorLocalForPart()`, which applies the armor stand yaw, pitch, scale, explode state, and user offset before measuring mesh drift.

Local Playwright verification reproduced the operator-adjusted armor stand transform (`scale=1.29`, offset `[0.0626, 0.0622, 0.001]`) and produced:

```text
centerline QA pass/pass anchor=SKIP hard=OK part=0 glb=0 mode=quest_rig offset=quest_rig
```

This confirms the previous `part=5` reading was at least partly a QA-frame mismatch: the mesh was measured after armor-stand transform, while the anchor was still measured in canonical worn-body space.

Quest evidence could not be refreshed in the same pass because `adb shell dumpsys activity activities` reported the Oculus Browser task with `isSleeping=true`. The browser intent did contain the updated URL:

```text
http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&qa=centerline&debug=1&autoplayReplay=1&replayView=mirror&replay=/sessions/S-IW-MOCOPI-TEST-3601-OK/artifacts/iwsdk-deposition-replay.json&code=3601&reload=1777922106858
```

Next physical QA should wake/wear the headset first, then capture a new snapshot. The expected display line should include the new `mode=... offset=...` suffix; if it does not, the capture is stale.

Verification run after this change:

```text
node --check viewer\quest-iw-demo\quest-demo.js
python -m pytest tests/test_prepare_mocopi_rehearsal_preflight.py tests/test_probe_mocopi_udp.py tests/test_quest_mocopi_motion_source.py tests/test_dashboard_server.py tests/test_quest_recall_render_contract.py tests/test_audit_repo_readiness.py tests/test_runtime_package_surface_gate.py -q
npx vite build --config vite.quest.config.js
```

Result:

```text
99 passed, 153 subtests passed
Quest Vite production build passed
```
