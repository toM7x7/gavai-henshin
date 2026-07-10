# Exhibition UI Redesign Backlog - 2026-05-04

## Principle

Existing Web Forge and Quest UI are not sacred. They should keep the demo runnable, but exhibition quality wins when a root rewrite clearly improves the experience.

The current route remains:

```text
Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す
```

## High-Value Redesign Targets

1. Web Forge kiosk mode
   - Visitor-facing screen should be Japanese-first, with one dominant action: generate a suit and issue the Quest code.
   - Operator diagnostics should collapse behind a small panel.
   - Hero preview should emphasize the cool tri-view suit direction, not form complexity.

2. Quest transform stage
   - Priority is body-surface deposition: particles, light trails, reveal shine, and a clear moment of completion.
   - Current implementation now has a runtime particle field; next pass should tune density, scale, color timing, and Quest framerate on hardware.
   - Raw event IDs must stay hidden from happy-path visitor UI.

3. Armor quality review surface
   - Add a compact front/side/back/3Q review wall for model acceptance.
   - Per-part size/position micro-adjustments should show before/after deltas in millimeters.
   - `fidelity_hold` assets must be visually separated from accepted runtime assets.

4. Replay proof surface
   - Replay should feel like a keepsake, not a debug artifact.
   - Japanese event labels should come from ReplayRecord `presentation`.
   - mocopi provenance should be visible as experience quality metadata, but private IDs should stay off public screens.

## Mocking Lane

- Use generated concept images or edited screenshots for high-level mood only: kiosk layout, Quest HUD density, deposition look, replay card style.
- Do not use generated bitmap mockups as acceptance evidence for actual model fidelity.
- Useful mock prompt direction: `Japanese exhibition kiosk UI, armored transformation suit, cyan/gold deposition particles, compact operator diagnostics, dark stage lighting`.

## Acceptance Gate Additions

- Quest deposition visual status: `pass`, `fix`, or `waived`.
- Japanese happy path: no raw `DEPOSITION_*`, `CAPTURE`, `VOICE DEBUG`, or `RUNTIME DIAGNOSTIC`.
- Hardware pass still required before show-day freeze because particles and bloom-like density can cost Quest framerate.

## 2026-05-04 日本語UI一次対応

- Web Forge: 入力、生成状態、Questコード導線、主要サポート診断を日本語優先にした。
- Quest demo: HUD、呼び出し、セッション表示、主要aria-labelを日本語化した。
- 共通copy: `準備中`、`認識中`、`生成完了`、`要確認` と黄/紫/青/赤の説明を `viewer/shared/exhibition-copy.js` に集約した。
- 残り: 詳細デバッグ、XR内の細かい診断文、実機での見え方確認は次回対応。

## 2026-05-04 Web Forge 展示モード

- `?mode=exhibition` または `?exhibition=1` で、結果パネル上部に展示用要約を出す。
- 優先表示は4桁コード、身長、選択variant、Questで開く/試す、Replay保存導線。
- サポート診断、モデル/manifest系の内部情報は閉じたまま低優先表示。通常モードの構成は維持。

## 2026-05-04 展示モードQA

- 静的QA: `python -m pytest tests/test_exhibition_operator_japanese_copy.py tests/test_exhibition_smoke_check.py::test_operator_urls_include_quest_usb_path_with_code`
- ローカル確認URL: `http://127.0.0.1:8010/viewer/armor-forge/?mode=exhibition`
- QA観点: 4桁コード、Quest導線、Replay導線、身長/variant表示、モバイル幅の1カラム化。
