# Quest Deposition Visual Direction - 2026-05-04

## Lore Goal

Quest transformation must read as deposition, not a simple model fade-in.

The user should feel that observed body contours and the will signal are being synchronized, then armor matter condenses onto the body surface. The visible effect should support the existing lore sentence:

> 生成とは、観測された身体輪郭と意志信号を同期し、装甲を身体表面へ確定させる変身プロトコルである。

## Runtime Implementation

- `viewer/quest-iw-demo/quest-demo.js` now creates an `IWSDK-蒸着粒子フィールド` under the Quest rig.
- The field uses `THREE.Points` for glowing deposition particles and `THREE.LineSegments` for short light trails.
- Particles orbit outside the body silhouette, then pull inward toward a body-radius shell as transformation progress increases.
- Armor parts receive a short emissive flash around their staggered reveal moment.
- Existing debug diagnostics remain in the folded debug panel; public route labels show Japanese display text such as `蒸着開始`, `蒸着完了`, and `動き 取得中`.

## Exhibition Acceptance

- Start Quest with a fresh Web Forge code and `?newRoute=1&mockTrigger=1`.
- Press `音声`.
- Mid-transform, the suit must show visible cyan/gold/white particles and short streaks around the torso and limbs.
- The effect must not be only a ring or only an opacity fade.
- Happy-path UI must not expose `DEPOSITION_*`, `CAPTURE`, `VOICE DEBUG`, or `RUNTIME DIAGNOSTIC`.
- End state must still create or verify Replay proof.

## Evidence

- `tests/.tmp/quest-deposition-effects-final-mid-7609.png`
- `tests/.tmp/quest-deposition-effects-final-done-7609.png`
- `python -m pytest tests/test_quest_recall_render_contract.py tests/test_quest_mocopi_motion_source.py -q`
- `npx vite build --config vite.quest.config.js --outDir tests/.tmp/quest-vite-build-20260504-deposition-effects --emptyOutDir`
