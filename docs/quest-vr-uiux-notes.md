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
- Add a VRC-like live mirror after transformation so hand/controller movement can be checked against a front-facing suit avatar.
- Treat the right hand as the transformation item lane and the left hand as the bracelet/menu lane.
- Use HMD + controllers as the temporary live body anchors. Feet and full-body motion need a later IK/VRM lane.
- Right controller trigger can enter the transformation bank when it is not selecting a menu item.
- The transformation item should glow during voice standby/recording/deposition so the next action is obvious.
- Store compact `quest-live-pose.v0` HMD/controller samples in the trial event log as the bridge toward motion replay.
- Expand recorded live pose samples into compact ReplayScript `deposition_progress` actions and use them for mirror/observer archive replay.
- Estimate a small torso twist from the left/right hand line as a Quest-only fallback, but do not treat it as full body tracking.
- Keep the bracelet panel compact. Its short side should align with the controller laser axis while the menu remains a horizontal rectangle.
- Keep the readable face toward the player by flipping the panel 180 degrees around that laser/short-side axis when the face is reversed.
- Treat the left controller as the bottom-center anchor of the bracelet panel; the compact chip and full horizontal panel should expand upward from that anchor instead of hanging over the player.
- Default the bracelet to a compact `メニュー` state; left trigger opens/closes the full panel.
- Let the full panel switch into a world-locked `固定` state for longer inspection, then return to wrist follow with `追従`.
- Auto-return the open wrist panel to compact mode after a short no-input interval.
- Snap the live mirror into its target position when it first appears so it reads as a stable check mirror rather than a moving panel.
- Show a compact replay motion diagnostic in the PC HUD and VR panel: `LIVE`, `BODY`, `BODY+LIVE`, or `STATIC`, with frame counts when available.

Next UI slice:

- Keep `音声`, `記録再生`, `鏡/観察`, `停止`, `リセット` as the visitor-facing command set.
- Evaluate a lightweight VRM humanoid as the live-suit carrier once the controller/HMD anchor behavior feels correct.
- Keep replay diagnostics visible enough for operator checks, but do not expand the bracelet panel just for telemetry.
- Add a stronger transform-item affordance once the bracelet state feels stable on Quest.

## Fit And Suit Visibility Rule

- First-person transformation can hide helmet/hand parts if they block the view.
- Mirror/archive should show the full body-sim trace where possible.
- Mirror mode is a staged "front-facing suit check", not a real reflection pass yet.
- Full-suit credibility depends on the fit lane, not only the Quest UI lane.
- Current Quest hardware anchors head and hands only. Legs/feet are estimated until full-body IK or VRM retargeting is introduced.
- mocopi remains the likely path for torso twist, hips, and leg motion if the experience needs credible full-body replay.
- Helmet/chest/shoulder/back remain the next high-value fit and silhouette audit targets.
