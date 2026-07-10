# Quest Armor Stand Interaction Plan - 2026-05-04

Status: design proposal plus P0 implementation note.  
Ownership: Quest viewer runtime, Quest render contract tests, and this document.

P0 implemented on 2026-05-04:

- Right trigger no longer starts voice recognition while armor-stand preview is active.
- Right trigger rotates the stand in 30 degree steps as an inspection affordance.
- Stand pose has a `0.24m` floor lift to keep feet from sinking below the floor.
- Debug telemetry reports stand active state, yaw, floor lift, right-trigger mode, and interaction count.
- Full hover/select/focus/distance interaction remains future work.

## Purpose

Design the Quest armor-stand interaction as an exhibition-grade inspection mode, not a search engine or loose debug viewer. The stand should let an operator or visitor:

- touch / select the suit or a part
- rotate the armor safely
- move closer without losing orientation
- inspect a specific part
- return to mirror replay without confusion

The core tension is useful: armor stand is great for "look at the product", but dangerous if the operator mistakes it for "the transformation succeeded". The design must keep that distinction explicit.

## Design Principles

- Mirror replay remains the acceptance path. Armor stand is inspection, staging, and recovery.
- Existing Quest UI should keep working. Add interaction affordances around current modes before replacing them.
- Every interaction must have an obvious escape path: return to mirror, reset view, and cancel selection.
- Controller actions must tolerate nervous exhibition operation: accidental trigger presses, hand drift, headset recentering, and operators talking to visitors while using the device.
- Telemetry should explain what happened after the fact: mode, selected part, distance, rotation, input source, return-to-mirror result, and whether the operator used reset.

## Interaction Model

### 1. Touch / Select

Goal: let the operator identify that a part is interactive without requiring precision desktop-style pointing.

Quest controller operation:

- Right ray hover highlights the nearest armor part under the ray.
- Right trigger short press selects the highlighted part.
- Left trigger short press clears selection.
- A/B button opens a compact part action menu only after a part is selected.
- Grip is reserved for spatial manipulation, not selection.

Behavior:

- Hover highlight uses a subtle outline or emissive rim, not a huge UI card.
- Selection locks the outline and shows the part name in the wrist/status area.
- Selected part does not detach by default. Exhibition visitors should not accidentally dismantle the suit.
- If no part is hit, short trigger selects the whole armor stand.

Mistake avoidance:

- Require hover to be stable for about 150-250 ms before selection can change.
- Ignore repeated trigger presses within a short debounce window.
- Never let a single accidental trigger press leave mirror replay; mode changes require an explicit labeled control.

Telemetry:

```text
armorStand.hoverPart
armorStand.selectedPart
armorStand.selectionSource: ray / wholeStand / cleared
armorStand.selectionStableMs
armorStand.misfireIgnoredCount
```

### 2. Rotate

Goal: inspect the suit from front, side, and back without forcing the user to physically walk around the play space.

Quest controller operation:

- Hold right grip while pointing at the stand: rotate armor yaw by horizontal controller movement.
- Right thumbstick left/right: snap rotate in 15 or 30 degree steps.
- Left thumbstick click or a reset button: return to canonical front angle.

Behavior:

- Rotation is yaw-only in P0/P1. Pitch/roll are blocked to avoid disorienting the visitor and breaking fit perception.
- Rotation pivots around the armor stand root, not the selected part.
- If a part is selected, rotation still rotates the whole suit unless the operator enters a later "part detail" mode.

Mistake avoidance:

- Grip rotation begins only after a small movement threshold.
- Rotation speed is capped.
- Rotation stops immediately on grip release.
- Snap rotation emits telemetry and updates the visible orientation label.

Telemetry:

```text
armorStand.rotationYawDeg
armorStand.rotationInput: gripDrag / thumbstickSnap / reset
armorStand.rotationDeltaDeg
armorStand.rotationResetCount
```

### 3. Move Closer / Distance

Goal: let the operator inspect material, silhouette, and part fit without physically leaning into unsafe boundaries or clipping into the suit.

Quest controller operation:

- Right thumbstick up/down: move the stand closer/farther within a clamped range.
- Optional: hold left grip + right thumbstick up/down for slower precision distance.
- Reset button returns distance to the exhibition-safe default.

Behavior:

- Move the stand or virtual inspection anchor, not the user's XR origin.
- Clamp distance so the armor never intersects the headset camera and never disappears behind the user.
- Keep a floor/contact cue or shadow so distance changes do not feel like scale changes.

Mistake avoidance:

- No free six-axis dragging in the first implementation.
- Do not bind distance changes to trigger; trigger is already selection.
- Show a small "near / normal / far" status in debug or wrist UI, but avoid blocking the model.

Telemetry:

```text
armorStand.distanceM
armorStand.distanceBucket: near / normal / far
armorStand.distanceInput: thumbstick / precision / reset
armorStand.distanceClampHit: none / near / far
```

### 4. Inspect Part

Goal: let operators explain or diagnose individual armor parts without leaving the Quest flow.

Quest controller operation:

- Select part with right trigger.
- Press A/B to cycle actions: focus part, isolate part, show all.
- Right thumbstick up/down in focus mode adjusts viewing distance slightly.
- Left trigger or "show all" exits part focus.

Behavior:

- Focus part: camera/stand framing or model emphasis centers the selected part while keeping the whole suit faintly present.
- Isolate part: optional P2 mode that dims other parts, not removes them entirely.
- Show all: restores full armor visibility and clears part isolation.

Mistake avoidance:

- P0 should avoid true part detachment. Detaching parts is powerful, but in an exhibition it creates a high recovery burden.
- Isolation must auto-expire or provide a clear return action.
- Any focus mode should preserve the "Return to mirror" command.

Telemetry:

```text
armorStand.partFocusActive
armorStand.focusPart
armorStand.focusMode: highlight / focus / isolate
armorStand.focusDurationMs
armorStand.focusExitReason: clear / showAll / returnMirror / timeout
```

### 5. Return To Mirror

Goal: make the operator's escape hatch impossible to miss. This is the most important control.

Quest controller operation:

- Dedicated wrist/menu action: "Return to mirror".
- Long press B or menu button: return to mirror replay from any armor-stand submode.
- Optional two-step only when replay would reset progress: first press previews the action, second confirms.

Behavior:

- Return clears hover, selected part, part focus, stand rotation overrides, and inspection distance unless the operator chooses to preserve view.
- Return sets or requests the mirror/replay state and restarts replay if needed.
- If return fails, show a concise error state and keep the operator in stand mode with reset available.

Mistake avoidance:

- Do not hide return inside a part menu.
- Do not overload "back" with both clear selection and return mirror unless long press clearly differs from short press.
- After return, telemetry must prove whether the app reached mirror/replay, not merely that the button was pressed.

Telemetry:

```text
mode.previous
mode.target
mode.current
mode.transitionReason: operatorReturnMirror / replayStart / reset / error
armorStand.returnMirrorRequested
armorStand.returnMirrorSucceeded
armorStand.returnMirrorLatencyMs
replay.playing
replay.progress
armorStandPreview
```

## State Transition Proposal

Keep the mental model small. Avoid adding many public modes if the same behavior can be represented as substate.

```text
mirrorReplay
  -> armorStand.idle
  -> armorStand.hover
  -> armorStand.selected
  -> armorStand.rotating
  -> armorStand.distanceAdjust
  -> armorStand.partFocus
  -> mirrorReplay
```

Recommended state rules:

- `mirrorReplay` is the default public success state.
- `armorStand.idle` is entered only by explicit operator action, debug URL, or recovery path.
- `hover` is transient and should not be logged as a mode switch unless it produces a selection.
- `selected`, `rotating`, `distanceAdjust`, and `partFocus` are substates under armor stand, not separate top-level view modes.
- Any armor-stand substate can transition to `mirrorReplay` through the dedicated return action.
- Any error substate must preserve `Return to mirror` and `Reset stand`.

Minimum debug snapshot fields:

```text
viewMode: mirror / observer / self
armorStandPreview: true / false
armorStandInteractionState: idle / hover / selected / rotating / distanceAdjust / partFocus / returningMirror / error
armorStandSelectedPart:
armorStandRotationYawDeg:
armorStandDistanceM:
armorStandReturnMirrorSucceeded:
playing:
progress:
```

## Error And Misoperation Guardrails

High-probability exhibition mistakes:

- Operator presses trigger repeatedly and accidentally changes selection.
- Visitor expects armor stand to be final transformation result.
- Operator rotates the suit and forgets how to restore the front view.
- Stand is moved too close and appears oversized or clipped.
- Part focus remains active, then the next user sees a confusing partial suit.
- Voice/debug URL mock path is mistaken for real mic validation.

Guardrails:

- Make mode label explicit: "Armor stand inspection" vs "Mirror replay".
- Keep "Return to mirror" visible from every armor stand substate.
- Provide one reset action for stand orientation, distance, and part focus.
- Clamp all spatial movement.
- Do not allow destructive or persistent changes from Quest stand inspection.
- Log mode and substates in telemetry so photos can be interpreted later.

## P0 / P1 / P2 Implementation Plan

### P0 - Safe Exhibition Patch

Objective: improve operator confidence without breaking existing Quest UI.

Deliverables:

- Explicit mode label for armor stand vs mirror replay.
- Dedicated "Return to mirror" action in the existing wrist/menu UI.
- Stand reset action: front angle, default distance, clear selection/focus.
- Basic whole-stand rotation by thumbstick snap or one safe input path.
- Telemetry for return-to-mirror request/success, current mode, progress, and armorStandPreview.

Non-goals:

- No part detachment.
- No free 6DoF manipulation.
- No new complex radial menu.

Acceptance:

- Operator can enter stand inspection, rotate once, reset, and return to mirror replay in under 10 seconds.
- `/api/quest-debug/latest` can distinguish armor stand inspection from mirror replay.
- Failed return-to-mirror produces an NG-reportable state.

### P1 - Inspectable Suit

Objective: make armor stand useful as a product explanation and debugging tool.

Deliverables:

- Ray hover and part selection.
- Selected-part outline and part name in compact status UI.
- Focus part mode that emphasizes one part without hiding the return path.
- Distance adjustment with near/normal/far clamp.
- Telemetry for selected part, focus mode, rotation, distance, and reset.

Non-goals:

- No persistent per-part edits from Quest.
- No asset tuning from stand-only evidence.
- No automatic mirror acceptance from stand mode.

Acceptance:

- Operator can select helmet/chest/waist/limb, focus it, show all, and return to mirror without stale selection.
- Photos can be labeled with mode, selected part, distance, yaw, and progress.

### P2 - Advanced Exhibition Interaction

Objective: turn armor stand into a polished interactive exhibit while keeping the transformation path safe.

Deliverables:

- Optional radial action menu for selected part: focus, isolate, compare mirror, show all.
- Optional guided inspection sequence: front, side, back, key parts, return mirror.
- Optional dual-mode comparison: stand inspection on one side, mirror replay on the other, if performance allows.
- Optional operator lock mode to prevent visitors from changing debug/inspection state.
- Rich telemetry event stream for exhibition analytics.

Risks:

- Radial menus in VR can be slower than direct controls under crowd pressure.
- Isolate/compare modes can blur the mental line between inspection and transformation.
- Extra visual UI can cover the armor, especially in Quest Browser/WebXR.

Acceptance:

- Advanced interactions improve explanation value without increasing recovery time.
- The default path still returns to mirror replay quickly.
- Operator can disable advanced controls for public throughput.

## Compatibility With Existing UI

Conservative approach:

- Add labels, return action, reset action, and telemetry around current mode structure.
- Treat armor stand interaction state as a substate under existing `observer` / `armorStandPreview`.
- Keep current buttons and URLs stable.
- Add controller shortcuts only where they do not conflict with existing trigger/voice/mirror behavior.

Why this is likely right for the next pass:

- It reduces exhibition risk.
- It gives operators a reliable escape path.
- It produces better evidence for future UI and placement changes.
- It avoids rewriting the Quest interaction model while the mirror/voice path is still being validated.

## Radical Redesign Worth Considering

There is one deeper fix that may be worth breaking UI for later: split the Quest experience into two explicit apps or top-level scenes.

Option:

```text
1. Transformation Mirror
2. Armor Gallery / Stand Inspection
```

Benefits:

- The visitor never confuses stand inspection with transformation success.
- Each scene can have purpose-built controls.
- Telemetry becomes cleaner because `gallery` and `mirror` are not overloaded inside one observer/mirror state machine.
- Exhibition staff can choose a throughput mode: fast mirror demo or slower gallery explanation.

Costs:

- It breaks the current compact flow.
- It requires new navigation, new acceptance checks, and likely new operator training.
- It may duplicate asset loading or scene setup work unless carefully shared.
- It risks making the experience feel like a menu app instead of a magical transformation.

Critical judgment:

- Do not do this as P0. The short-term failure mode is not lack of grand architecture; it is unclear mode state and weak recovery.
- Revisit after P1 telemetry shows operators repeatedly using armor stand as a separate explanation space.
- If gallery behavior becomes half the exhibition value, then the split is justified. If armor stand remains mostly diagnostic, keep it as a submode.

## Open Decisions

- Should right trigger select parts, or is trigger already too overloaded by voice/activation behavior?
- Should rotation be grip-drag first or thumbstick-snap first for P0?
- Should part names be public visitor-facing labels or debug/operator-only labels?
- Should return-to-mirror preserve the last replay progress or restart from the transformation beginning?
- Should the stand mode auto-timeout back to mirror after inactivity during public operation?

## Recommended Next Step

Implement P0 only after confirming the current controller bindings in the Quest runtime. The first valuable change is not "more interaction"; it is a reliable operator loop:

```text
enter stand -> rotate/reset -> return mirror -> telemetry proves mirror replay
```

That loop turns armor stand from an ambiguous failure-looking state into a controlled exhibition tool.
