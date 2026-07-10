# Quest Workshop Current Implemented Truth - 2026-05-04

This is the latest source of truth for the Quest armor-stand workshop after the May 4 text feedback. Use it when older Japanese text renders incorrectly in a terminal.

## P0 Interaction Contract

- Exit: while armor stand is active, right grip + trigger exits to mirror/replay before any hovered UI action.
- One-rig manipulation: right grip moves the whole humanoid armor rig. It does not rotate individual parts and does not treat each part as a separate center.
- Two-hand manipulation: both grips scale, yaw-rotate, and move the whole rig from the two-hand center.
- Part state: right trigger without grip explodes/returns parts for inspection.
- Controller safety: a missing left/right controller remains missing; one physical controller must not be reused as both hands.
- Coordinate safety: controller world-space movement is converted into the Quest rig's local-space offset before it moves the armor.

## Fit Contract

- Stand, mirror, and replay placement are grounded in `QUEST_HUMAN_ANCHOR_CONTRACT.center_m`.
- The audit verifies left/right side signs, centerline, vertical body-chain order, and chest/back depth meaning.
- Static audit pass does not prove final Quest visual fit. It is a gate that prevents obvious non-human placement before headset review.

## Operator Acceptance

- Staff can explain the workshop as: grab the whole suit, inspect it, then return to transformation.
- No staff script should mention 30-degree steps or per-part rotation centers.
- Headset confirmation must check that right grip + trigger exits even while the ray is hovering over reset/replay/close.
- Wearing fit must be judged after exiting to mirror/replay, not while in armor stand inspection.

## Next Phase After P0 Pass

1. Close `quest-foundation-pass/fail` with fresh Quest telemetry and labeled photos.
2. Run an external exhibition PC `local-pass` from a clean clone and exact commit.
3. Only then proceed to Web service/GCP staging, PlayCanvas adapter, and mocopi enhancement as optional lanes.
