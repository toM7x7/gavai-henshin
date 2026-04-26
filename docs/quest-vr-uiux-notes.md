# Quest VR UI/UX Notes

Date: 2026-04-26

## Current Rule

- Voice activation is the first-person transformation path.
- Archive replay is a review path. It can switch between `mirror` and `observer`.
- The in-VR menu should not stay head-locked in the center of view.
- Transformation, mirror, and observer confirmation should be world-anchored after activation.
- The menu should be bracelet/controller-adjacent; fallback placement should also be world-anchored, not HMD-locked.
- Visitor-facing controls should be Japanese-first.

## References Checked

- Microsoft Mixed Reality hand menu guidance:
  `https://learn.microsoft.com/en-us/windows/mixed-reality/design/hand-menu`
- Apple immersive experience guidance:
  `https://developer.apple.com/design/human-interface-guidelines/immersive-experiences`
- Unity XR Interaction Toolkit hands demo:
  `https://docs.unity.cn/Packages/com.unity.xr.interaction.toolkit@3.1/manual/samples-hands-interaction-demo.html`
- Unity XR Interaction Toolkit UI interaction setup:
  `https://docs.unity.cn/Packages/com.unity.xr.interaction.toolkit@0.10/manual/index.html`

## Design Takeaways

- Wrist/hand menus should stay small. Large hand-attached menus cause arm fatigue.
- A menu that appears only from a palm/hand pose can false-trigger. A second intent signal is useful.
- Long interaction should allow world-locking, moving, or closing the menu.
- Ray/pinch and poke/touch are both normal XR UI patterns. Controller ray remains the safer baseline for Quest demos.
- Virtual hands or hand UI should not block the main content.

## Implementation Direction

Current slice:

- Move the menu away from head-locked center placement.
- Prefer left-controller/wrist-adjacent placement.
- Fall back to a left-side world dock when controller tracking is not reliable.
- Keep controller ray selection as the stable baseline.
- Keep hand tracking opt-in with `hands=1`.
- Add a visible mirror frame in `mirror` archive mode so the mode is legible in VR.
- Hide helmet and hand parts in first-person view when they would block the player's view.
- Lock the transformation rig to the activation anchor so head movement does not drag the suit, mirror, or observer view.

Next UI slice:

- Add a compact `メニュー` bracelet state.
- Let users open/close the full panel from the compact state.
- Add a world-lock mode for longer inspection.
- Keep `音声`, `記録再生`, `鏡/観察`, `停止`, `リセット` as the visitor-facing command set.

## Fit And Suit Visibility Rule

- First-person transformation can hide helmet/hand parts if they block the view.
- Mirror/archive should show the full body-sim trace where possible.
- Mirror mode is a staged "front-facing suit check", not a real reflection pass yet.
- Full-suit credibility depends on the fit lane, not only the Quest UI lane.
- Helmet/chest/shoulder/back remain the next high-value fit and silhouette audit targets.
