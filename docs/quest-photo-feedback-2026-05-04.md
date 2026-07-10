# Quest Photo Feedback - 2026-05-04

Status: user headset-photo observation note for the Quest transformation path.

Scope: photo-derived Quest feedback and follow-up implementation record. The
first revision was a documents-only analysis note; the 2026-05-04 follow-up now
records code/test changes made in response to the latest headset photos.

Primary evidence available in this thread:

- User-provided physical Quest photos / visual observation.
- Current Quest debug snapshot notes: XR is active, but the observed state can
  still be `viewMode=observer`, `playing=false`, `progress=0`, and
  `armorStandPreview=true`.
- Current runtime load note: armor GLB path is healthy enough to show
  `18 loaded`, `18 GLB`, `0 fallback`, and `18 placed`.
- Current debug URL note: `mockTrigger=1&mic=0` disables real voice recognition,
  so that URL is for recovery/diagnostics rather than public voice validation.

## Executive Summary

The photos should be treated as a mode-state and physical-fit review, not as a
single rendering failure. The most important split is this:

- If the headset is in observer / armor-stand preview, the user may see a
  standing suit or parts in space, but not the mirror transformation result.
- If the URL uses `mockTrigger=1&mic=0`, voice recognition is intentionally not
  being exercised.
- If GLB counts are all loaded and placed, the next problem is fit, scale,
  anchoring, or mode clarity, not asset availability.

The implementation direction should therefore avoid broad visual rewrites. Make
the active mode obvious, keep diagnostic/recovery URLs separate from exhibition
URLs, preserve GLB/runtime placement as the source of truth, and verify changes
inside the physical headset after entering XR mirror/replay.

## Latest Feedback Addendum - 2026-05-04

Latest user feedback reframes the next work as an interaction/rigging problem,
not only a visual placement problem:

- `Cannot return from armor stand`: treat as P0 UX failure. The operator and
  visitor need a right-hand return path from armor stand to mirror/replay or
  `transform arming`; relying on the left-hand menu alone is not acceptable.
- `Grab a single rig`: the stand should be manipulated as one
  human-shaped armor rig. Right grip moves the whole rig; both grips scale,
  yaw-rotate, and move the whole rig; right trigger opens/closes parts under that rig. Individual
  armor parts should not become separately rotating objects in the baseline.
- `Place by human understanding`: stand, mirror, replay, and later live body
  should derive part positions from a shared humanoid anchor frame. Runtime
  placement offsets remain asset corrections after semantic body anchoring, not
  the primary way to invent body anatomy.

Documentation implication:

- `docs/quest-workshop-interaction-spec-2026-05-04.md` should be read as the
  current interaction source of truth: right grip moves the whole armor, both
  grips scale/yaw/move it, right trigger explodes/returns parts, and right
  grip + trigger exits armor stand.
- Photos in armor stand mode should be judged by rig clarity and returnability,
  not by transformation success. Transformation acceptance still requires
  mirror/replay or transform progress.
- The next headset pass should record whether the user can return from stand
  with the right hand in under 10 seconds, whether the armor behaves as one
  rig, and whether chest/back/limbs/boots align to understandable body anchors.

## Latest Photo Read - Human Axis Failure

New photos `a4b66a44`, `6e1eac43`, `631bc359`, and `9f139d51`
show that the remaining issue is not a small local rotation error. The suit is
not yet organized around an explicit human axis:

- The gold ring reads like a body/spine guide, but the armor centers do not
  consistently sit around that guide.
- The chest/back mass reads as a large slab near the viewer instead of a
  front/back shell around a ribcage.
- Arm and leg parts are sized better, but they still read as floating cylinders
  rather than sleeves around shoulder-elbow-wrist and hip-knee-ankle chains.
- Armor stand spawn can begin diagonally, which makes front/back/left/right
  judgement difficult before the user even starts manipulating the suit.
- The simplified base suit was either invisible or blob-like; it did not give
  a useful body reference for judging fit.

Implementation response:

- Add `QUEST_HUMAN_BODY_MOCK` as the Quest-side mock body source of truth.
  Armor centers now derive from named body points plus part offsets, with
  literal `center_m` retained for the static audit.
- Keep the body guide visible in armor-stand preview, using the same stand
  yaw/pitch/scale/offset transform as the armor so the guide is diagnostic
  rather than another drifting object.
- Default `baseSuitGuide` to on, but render it as a thin wireframe guide in XR
  so it does not become the previous rugby-ball blocker.
- Split observer anchoring by profile: `armor_stand` versus
  `replay_observer`. Armor stand now faces the user with
  `yaw + Math.PI` instead of the earlier `Math.PI * 0.82` diagonal.
- Snap the rig to the captured anchor on XR session start, armor-stand entry,
  and armor-stand exit so the initial spawn does not slowly drift from the
  browser fallback pose.
- Move the gold rings to the same body z-center during armor stand, so the
  ring guide and armor/body mock share one centerline.

Current caveat: this is still a mock humanoid guide, not a VRM body. It is the
baseline required before mocopi/VRM retargeting can make the wearer feel the
armor is actually on their own body.

## 2026-05-04 Follow-Up Implementation

Status note: this section records an earlier same-day fix. The latest target is
the `Latest Feedback Addendum` above: right grip moves one armor rig, both grips
scale/yaw/move it, right trigger explodes/returns parts, and right grip +
trigger exits armor stand. Any older 30-degree trigger
rotation wording below is historical context, not the final UX target.

Latest user photos and text added five sharper findings:

- Armor stand cannot be interacted with; the natural right-controller trigger
  conflicts with the transformation command.
- Armor stand feet appear below the floor.
- Armor stand / body-fitted parts read as about 90 degrees off from the body
  axes.
- The self transformation again shows a rugby-ball-like base shape, likely the
  simplified base-suit shell.
- Particles feel absent in the latest pass.

Applied changes:

- `viewer/quest-iw-demo/quest-demo.js`
  - Right trigger is no longer a voice shortcut while armor-stand preview is
    active. Earlier in the day it rotated the stand by 30 degree steps and
    logged `armor-stand-interact` telemetry; that temporary affordance is
    superseded by the latest right-grip whole-rig rotation target.
  - Armor stand pose is lifted by `ARMOR_STAND_FLOOR_LIFT_M = 0.24` to pull
    boots/legs above the floor.
  - GLB meshes with `runtime-render-placement.v1` no longer receive the legacy
    extra `Math.PI / 2` X base rotation. Fallback/non-placed meshes still keep
    the legacy base rotation.
  - The simplified capsule-like base-suit shell is suppressed in Quest XR by
    default. It can be re-enabled only for diagnosis with `baseSuitGuide=1`.
  - Mirror-view deposition particles are no longer fully hidden; they are
    moved slightly behind the mirror target and dimmed by
    `MIRROR_DEPOSITION_DIMMING = 0.42`.
  - Debug telemetry now includes `armorStand.active`, `armorStand.yawDeg`,
    `armorStand.floorLiftM`, `armorStand.rightTriggerMode`, and
    `armorStand.interactionCount`.
- `tests/test_quest_recall_render_contract.py`
  - Added contracts for armor-stand right-trigger behavior, stand lift/yaw,
    runtime placement base rotation, base-suit guide gating, and mirror particle
    dimming.

Verification:

```text
node --check viewer/quest-iw-demo/quest-demo.js
python -m pytest tests/test_quest_recall_render_contract.py -q
python -m pytest tests/test_dashboard_server.py -q
npx vite build --config vite.quest.config.js --outDir tests/.tmp/quest-vite-build-20260504-stand-yaw-base-guide --emptyOutDir
node tools/verify_replay_armor_alignment.mjs --code 3601 --trigger both --samples 0.25,0.5,0.75 --output-dir tests/.tmp/replay-armor-alignment-3601-stand-yaw-base-guide --max-settled-excess-m 0.05
python -m pytest -q
```

Result: `315 passed, 192 subtests passed`; Quest Vite build success; recall
code `3601` alignment `ok=true`, `settledMaxExcessDistanceM=0`.

Interpretation:

- This fix addresses the likely runtime placement and mode-control causes of
  the latest photos.
- It does not replace the simplified base shell with a real VRM body yet. The
  shell is hidden by default so it stops blocking the headset view.
- mocopi will help only after the suit placement/orientation baseline is sane.
  It supplies body motion/pose data; it does not automatically fix a wrong GLB
  axis, floor height, or UI mode conflict.

## Human-Body Anchor Direction

Design owner note: the next placement pass should stop treating stand, mirror,
replay, and live self-view as separate coordinate hacks. The target is a
single human-shaped anchor contract that every view mode can produce and every
armor part can consume.

### Current runtime placement split

The Quest runtime currently has these placement sources:

- Neutral assembly: `VR_BODY_PART_POSES` plus `QUEST_ASSEMBLY_ADJUSTMENTS`,
  exposed by `questAssemblyPoseForPart()`. This feeds the stand path,
  centered replay/segment paths, and the live-mirror avatar.
- Armor stand: `armorStandPoseForPart()` wraps the neutral assembly in stand
  yaw, pitch, scale, and exploded-part transforms. It is a staging mannequin,
  not a measured body.
- XR mirror/observer root: `captureWorldAnchor()` places the whole rig from
  the headset camera with view-specific distance, height, scale, and yaw. This
  chooses where the body appears in the room, but it does not define hips,
  shoulders, knees, or feet.
- Replay/body-sim motion: `applyMotionSuitPose()` can either use
  `getMotionBodyPartPosition()` from replay head/hand/torso-yaw estimates, or
  discard that motion when `centered=true` and snap back to
  `questAssemblyPoseForPart()`.
- Live self-view: `updateLiveBodyAnchors()` and `getLiveBodyPartPosition()`
  estimate a body from Quest HMD/controllers. Torso, hips, legs, and feet are
  still inferred offsets, not tracked bones.
- Runtime correction layer: `applyRuntimePlacementOffset()`,
  `applyRuntimePlacementRotation()`, and `questGlbScaleForPart()` are applied
  after the chosen body source. These should remain final part-local
  corrections, but they should not be responsible for inventing the body.

This split explains why the photos can look inconsistent even when GLBs are
loaded and runtime placements exist: each mode can be correct relative to its
own small pose table while still failing as a believable human body.

### Proposed anchor contract

Introduce a conceptual `HumanoidAnchorFrame` before any further placement
tuning. It should be defined in Quest rig-local coordinates:

- `x`: wearer right, `y`: up, `z`: wearer back. Negative `z` is the body front.
- Required body anchors: `root`, `floor`, `pelvis`, `spine_low`,
  `chest`, `neck`, `head`, left/right `shoulder`, `elbow`, `wrist`, `hip`,
  `knee`, `ankle`, `foot`.
- Each anchor carries position, forward/up basis, confidence, and source
  (`neutral`, `replay_body_sim`, `mocopi`, `quest_live_estimate`, `stand`).
- A frame also carries body measures: height, shoulder width, chest depth,
  pelvis width, upper/lower limb lengths, foot length, and floor contact.

Armor parts should then bind to semantic surfaces instead of raw per-mode
coordinates:

- `helmet`: head/neck anchor, centered above eye line, with front clearance.
- `chest`: chest/sternum anchor, front surface offset.
- `back`: same chest/spine anchor, dorsal surface offset.
- `waist`: pelvis anchor, front/side belt envelope.
- `shoulder`: shoulder anchor plus outward lateral surface.
- `upperarm`, `forearm`, `thigh`, `shin`: segment midpoint between two joints,
  oriented along the bone, with radial armor clearance.
- `hand`, `boot`: wrist/foot anchors with palm/sole and toe/heel direction.

Runtime placement offsets and GLB target envelopes should be applied after this
semantic anchor binding, as asset-local corrections. If a part still needs a
large runtime offset to look human, the anchor or asset envelope is wrong.

### Mode adapters

The practical migration is to make each current view mode produce the same
anchor frame shape:

- Stand adapter: build a neutral mannequin anchor frame from body measures,
  then apply stand yaw/pitch/scale/explode once to the frame. Stand preview and
  mirror fixed-body should use the same neutral human dimensions.
- Mirror/replay fixed adapter: place the neutral anchor frame at the mirror
  root from `captureWorldAnchor()`. This preserves exhibition stability while
  making the pose explicitly human-shaped.
- Replay motion adapter: map body-sim or mocopi-derived frames into the same
  anchors. If only head/hands/torso-yaw are available, synthesize hips, knees,
  ankles, and feet with constraints rather than letting each part choose its
  own offset table.
- Live adapter: convert Quest HMD/controller estimates into the same anchor
  frame. Keep it behind `liveBody=1` until the inferred hips/feet are stable.

The important rule: `applyStandbySuitPose()`, `applyMotionSuitPose()`,
`applySegmentPose()`, and `applyLiveSuitPose()` should eventually differ only
in how they obtain a `HumanoidAnchorFrame`; part binding and runtime correction
should be shared.

### Concrete next design gates

- Draw the neutral anchor skeleton over the current hidden base shell and GLB
  parts in stand, mirror, and replay screenshots.
- Add telemetry for anchor source, body height, shoulder width, pelvis height,
  floor contact, and per-part semantic anchor name.
- Check chest/back as a pair: chest must sit on the front side of the chest
  anchor, back must sit on the dorsal side, with no shared center shortcut.
- Check limbs as bone segments, not capsules at memorized coordinates:
  upperarm shoulder-to-elbow, forearm elbow-to-wrist, thigh hip-to-knee, shin
  knee-to-ankle, boot ankle-to-foot.
- Treat `questGlbScaleForPart()` target sizes as envelope validation. A GLB
  whose vertical/depth axes contradict the human anchor should fail the fit
  gate instead of being visually compensated by offsets.
- Accept physical headset evidence only when the mode is pinned:
  stand preview, mirror replay, replay observer, and live self-view should each
  report the anchor source they are using.

## Observation Matrix

### 1. 鏡が見えない / Mirror Is Not Visible

#### 現象

- In the headset photos, the mirror can read as absent or not meaningfully
  visible.
- The current debug state can still be `viewMode=observer`,
  `playing=false`, `progress=0`, and `armorStandPreview=true`.
- In that state, what is visible is closer to an armor-stand / observer
  preview than the intended mirror transformation view.

#### 推定原因

- Observer mode can hide or visually de-emphasize the mirror frame/glass.
- Replay may not have started, so the mirror scene has no transformation result
  to present.
- Previous fixes intentionally hid base-suit shell and deposition effects in XR
  mirror to prevent body-shell or particle obstruction; that can make the mirror
  target feel too empty if the mirror frame itself is also weak.
- Browser cache or stale URL state may leave the headset in a recovery/debug
  mode while the operator expects the public mirror path.

#### 実装方針

- Treat `mirror`, `observer`, and `self` as distinct public states. The UI must
  show the active state with action labels that describe the next action, not
  just the current internal mode.
- Mirror mode should have a strong visual target even when base shell and
  deposition effects are suppressed in XR. Frame/glass affordance can be
  stronger; body-shell obstruction should remain suppressed.
- Do not re-enable the old opaque base body or particle field in front of the
  mirror as a quick fix. That risks restoring the previous rugby-ball-like
  obstruction.
- Recovery/debug URLs should not be used as the final public mirror validation
  URL unless the note explicitly says it is a diagnostic pass.

#### 実機再確認手順

1. Open a fresh Quest URL with a cache-busting `t=...` value and the target
   recall code.
2. Enter XR, then explicitly switch to `mirror` / replay view.
3. Confirm `/api/quest-debug/latest` reports the Quest headset URL, not a
   PC-side Playwright/alignment URL.
4. Confirm `record.payload.xr.session=true`.
5. Confirm the active view mode is mirror/replay, not observer preview.
6. Start replay or transformation; record whether the mirror frame/glass is
   visible before, during, and after transformation.
7. Capture at least one headset photo or ADB screenshot with the mirror target
   in frame.

### 2. 鎧立て操作 / Armor-Stand Operation

#### 現象

- The photos can be interpreted as "armor exists, but it is on a stand or in an
  observer preview", not as armor successfully fitted to the user's mirrored
  body.
- Current state notes include `armorStandPreview=true`, `playing=false`, and
  `progress=0`.
- Latest feedback adds that the user can feel trapped in armor stand if the
  return path is unclear or left-hand-menu dependent.

#### 推定原因

- The viewer is in preview/observer mode rather than the live transformation or
  replay mirror mode.
- Operator-facing controls may not make it clear whether a button toggles to
  armor stand, mirror, or replay.
- The state machine can look visually successful because GLBs are loaded and
  placed, while the intended user-facing mode has not been entered.
- Armor stand controls can be discoverable for rotation/explode but still fail
  as an exhibit if the same hand cannot close the mode and return to the main
  flow.

#### 実装方針

- Keep armor-stand preview as a useful diagnostic and staging mode, but do not
  treat it as transformation acceptance.
- Public Quest labels should distinguish "stand preview" from "mirror replay"
  in Japanese and in the debug snapshot.
- The wrist/menu action should describe the destination state, for example
  "to mirror" or "to observer", so the operator is not interpreting an internal
  enum.
- Acceptance should require evidence after replay/progress starts, not only the
  static stand preview at `progress=0`.
- P0 must include a right-hand return path. Recommended rule: short right
  trigger opens/closes parts; long right trigger or right-hand `return` exits
  armor stand.
- Armor should be grabbed as one rig root. Grip rotation and scale affect the
  entire armor rig, including exploded part offsets, not individual part roots.

#### 実機再確認手順

1. Start from the exact exhibition URL, not the recovery URL unless testing
   recovery.
2. Note the initial view label shown in the headset.
3. Toggle the view control once and record the label before and after.
4. Verify debug fields for `viewMode`, `armorStandPreview`, `playing`, and
   `progress`.
5. In armor stand, use right grip to move the whole rig, both grips to
   scale/yaw/move the whole rig, and right trigger to explode/return parts.
6. Use only the right-hand return path to leave armor stand. If return takes
   more than 10 seconds or needs left-hand-menu rescue, file it as P0 UX NG.
7. Accept armor-stand mode only if the test objective is staging/preview.
8. For transformation acceptance, continue until `playing=true` or progress
   advances, then verify the mirror/replay result.

### 3. トラッキング / Tracking

#### 現象

- The headset can be in XR while the observed armor relationship still appears
  detached from a live body or replay body.
- Current notes indicate `liveBody=1` is intentionally not part of the standard
  Quest path, and the standard path should use a fixed body pose rather than
  unstable live-body inference.

#### 推定原因

- Quest XR session state and body/armor tracking state are different gates.
  `xr.session=true` proves XR entry, but does not prove body anchor correctness.
- Live body estimation can introduce small floating or wandering artifacts in
  headset conditions.
- Mirror, observer, and replay modes can use different roots or height offsets;
  a mode change can make a healthy GLB load look mis-tracked.

#### 実装方針

- Keep the exhibition default on the stable fixed/replay body path unless a
  deliberate `liveBody=1` test is being run.
- Separate "XR session active", "body pose source", "armor placement loaded",
  and "armor follows body/replay" in the debug and acceptance language.
- Do not tune part offsets from a photo taken in an unknown view mode. First
  pin the mode, body source, recall code, and replay progress.
- If live tracking is tested, record it as a separate lane with fallback to the
  stable path.
- Treat the next placement pass as humanoid-anchor work. Each mode should
  explain which body anchors produced helmet, chest, back, waist, limbs, and
  boots before per-part offsets are changed.
- If the armor reads as a non-human aggregate, check the shared anchor frame
  first: pelvis/chest relationship, shoulder width, limb segment direction, and
  floor/foot anchors.

#### 実機再確認手順

1. Confirm `record.payload.xr.session=true`.
2. Confirm the intended body source: stable default path or deliberate
   `liveBody=1`.
3. Check the same recall code in `self`, `mirror`, and `observer` if those modes
   remain public.
4. At progress 0.25, 0.50, 0.75, and completed, verify helmet/chest/waist stay
   centered on the expected body/replay anchor.
5. Record whether chest is on the body front, back is on the dorsal side, and
   limbs follow bone segments rather than memorized floating coordinates.
6. Record if drift is tied to a mode switch, a time point, a specific anchor,
   or a specific part.

### 4. 音声認識 / Voice Recognition

#### 現象

- The current debug/recovery URL includes `mockTrigger=1&mic=0`.
- Under that URL, the user can see transformation behavior, but it is not proof
  that real microphone capture or real speech recognition worked.

#### 推定原因

- `mockTrigger=1` bypasses the real voice trigger path.
- `mic=0` disables microphone capture.
- Quest Browser microphone permission and secure-origin requirements can differ
  between localhost/ADB reverse, LAN HTTP, and HTTPS routes.

#### 実装方針

- Keep recovery and real voice validation as separate test routes.
- Public voice acceptance must use a URL with real capture enabled and must
  record microphone permission state.
- Debug telemetry should state microphone capability and whether capture is
  actually enabled, not merely whether a voice button exists.
- The right-hand device color/state should make "ready", "recording",
  "recognizing", "detected", and "rejected" visually distinct.

#### 実機再確認手順

1. Open a real-voice test URL without `mockTrigger=1` and without `mic=0`.
2. Grant microphone permission in Quest Browser.
3. Confirm debug telemetry says capture is enabled.
4. Speak the target phrase and record the state transitions.
5. Repeat once after page reload to catch permission/cache behavior.
6. If using ADB reverse over `http://localhost`, document whether Quest Browser
   allows microphone capture on that origin. If not, test the HTTPS/LAN route or
   document voice as blocked by origin policy.

### 5. 右手デバイス色 / Right-Hand Device Color

#### 現象

- The photos/feedback call out the right-hand device color as a user-facing
  clarity issue.
- If too many states share the same color, the operator cannot tell whether the
  device is waiting, recording, recognizing, complete, or rejected.

#### 推定原因

- The device was functioning as a compact status indicator, but the visual
  language was under-specified for headset photos and exhibition operation.
- Debug/recovery mode can further confuse interpretation because a mocked
  trigger may skip real recording/recognition states.

#### 実装方針

- Use a fixed state-color contract:
  - green: ready / arming
  - orange: recording / speak now
  - purple: analyzing / recognizing
  - cyan: detected / complete
  - red: rejected / error
- Keep the same mapping across public UI, wrist device, and documentation.
- Do not use color alone for operator debugging if a text/status field can also
  be shown in debug mode.

#### 実機再確認手順

1. In mock mode, confirm green -> cyan path for a successful fake trigger.
2. In real voice mode, confirm green -> orange -> purple -> cyan for a
   successful voice trigger.
3. Intentionally fail or timeout once and confirm red is visible.
4. Capture one headset photo per state if time allows; otherwise record the
   observed sequence in the operator log.

### 6. 基礎スーツ装着感 / Base-Suit Wearing Feel

#### 現象

- The feedback asks whether the base suit feels worn by the user, not merely
  drawn as a capsule/shell or hidden by armor.
- Current notes say the XR mirror path suppresses the base shell so it does not
  block the mirror. That avoids obstruction, but can also reduce the "wearing"
  cue.

#### 推定原因

- The earlier base suit/body shell was visually too dominant in mirror view.
- Suppressing it entirely protects readability, but may make the result feel
  like floating armor rather than a suited body.
- Armor-stand preview is especially likely to feel unworn because it is not
  anchored to a live/replay body.

#### 実装方針

- Base suit in XR mirror should be a subtle guide, not an opaque body shell.
- Use low-opacity silhouette/contour or material cues only where they improve
  wearing feel without covering the mirror, armor, or face/body landmarks.
- Keep observer/armor-stand preview suppression stricter than mirror replay,
  because observer mode is for inspection and can otherwise revive the old
  obstruction.
- Treat wearing feel as a fit/anchoring acceptance item, separate from GLB load
  success.

#### 実機再確認手順

1. Verify the scene in mirror replay, not only armor-stand preview.
2. At completed transformation, check whether chest, waist, helmet, shoulders,
   and limbs read as attached to a body volume.
3. Confirm the base-suit guide, if visible, does not block the mirror target.
4. Capture front and side headset photos.
5. Record whether the issue is "base suit absent", "base suit obstructive", or
   "armor not anchored to the base suit".

### 7. パーツサイズ感 / Part Size Feel

#### 現象

- The photos indicate part size needs physical-headset review.
- Current runtime load counts are healthy: all 18 GLBs are loaded, no fallback,
  and all 18 are placed. Therefore the issue is not simply missing assets.
- Existing placement notes still call out possible bbox / envelope concerns on
  some parts such as chest, waist, upperarms, and shins.

#### 推定原因

- Runtime placement can be technically present while some GLB dimensions or
  target envelopes still feel too large, too small, or too far from the body in
  headset scale.
- Quest perception exaggerates clearance and hand/controller interference
  compared with desktop screenshots.
- If the photo was captured in observer/stand mode, apparent size can differ
  from mirror/replay wearing size.

#### 実装方針

- Keep `runtime-render-placement.v1` as the single placement source of truth.
  Do not add a Quest-only scale table unless a part is explicitly waived and the
  waiver is recorded.
- Record per-part size observations separately from global scale observations.
- Prioritize high-impact public parts first: helmet, chest, waist, shoulders,
  forearms/hands, shins/boots.
- Any tuning request should include view mode, recall code, progress/time,
  photo angle, and whether the part is in self/mirror/observer mode.

#### 実機再確認手順

1. Use the same fresh recall code verified on Web.
2. Confirm `18 loaded`, `18 GLB`, `0 fallback`, and `18 placed` before judging
   size.
3. Capture front, side, and 3/4 headset photos in completed mirror/replay.
4. For each flagged part, record:
   - too large / too small / too far from body / intersects body
   - left/right symmetry
   - whether the issue appears in stand preview, mirror replay, or both
5. Cross-check against Web replay screenshots before requesting asset or
   placement changes.

## Minimal Acceptance For Next Quest Pass

- Quest headset is awake and inside XR.
- URL, recall code, and cache-busting timestamp are recorded.
- `/api/quest-debug/latest` is confirmed to come from Quest Browser.
- Active mode is recorded: `self`, `mirror`, or `observer`.
- Voice test route is identified as mock or real microphone.
- Armor load counts are recorded before visual fit judgment.
- Headset photos are labeled with mode, progress, and whether they are
  stand-preview or mirror/replay evidence.

## Current Documentation Decision

Use this document as the detailed photo-feedback record. Keep
`docs/current-progress-next-schedule-2026-05-04.md` to a minimal pointer plus the
immediate next operational risk, so parallel workers can keep using it as a
compact schedule note.

## 2026-05-04 Follow-Up From Latest Photos

Implemented fixes:

- Armor stand inspection has been moved from unclear 30-degree stepping to workshop-style manipulation:
  - right grip: move the whole humanoid armor rig as one object
  - both grips: scale, yaw-rotate, and move the whole rig from the two-hand center
  - right trigger: part explode/return when not holding grip
  - right grip + trigger: exit armor stand back to mirror/replay before any hovered UI action
- In armor-stand mode, the right grip + trigger escape now wins before wrist-panel hover actions. This keeps inspection controls from trapping the visitor in stand mode.
- Grip drag now filters Quest controller jitter with a small deadzone and movement cap.
- Quest debug telemetry now includes controller/gamepad/button diagnostics under `armorStand.input`, so "cannot interact" can be separated from "button mapping missing".
- Static armor placement for stand/mirror/replay now routes through the same assembly adjustment path instead of mixing raw pose tables.
- The selected `3601` sleek chest/back/shin runtime target dimensions are now blueprint canonical envelopes, not raw sidecar bbox. This is the main fix for the suspected axis/size mismatch that made the suit look like a non-human aggregate.

Still needs headset confirmation:

- Whether the armor stand floor lift feels correct with the user's physical floor height.
- Whether the exploded/assembled part positions read like a Tony Stark workshop inspection object rather than a broken body.
- Whether completed mirror/replay wearing fit no longer has impossible part intersections.
- Whether right/left grip mapping appears as `gamepad.buttons[1]` in Quest Browser telemetry.
- Whether particles remain visible after the new runtime and view-mode path; PC replay still passes, but headset brightness/comfort must be judged in XR.

Operator check sequence:

1. Wake/wear Quest and open `http://127.0.0.1:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&debug=1&qa=1`.
2. Enter VR and select armor stand.
3. Use right grip to move the whole assembled armor rig, both grips to scale/yaw/move, right trigger to explode/return, and right grip + trigger to exit.
4. Read `/api/quest-debug/latest` and save `armorStand.input` if any control fails.
5. Switch to mirror/replay before judging body-worn fit.
6. Take front/side/3q photos for helmet, chest/back/waist, shoulders/arms, thighs/shins/boots.

## 2026-05-04 Rig/Exit Follow-Up From Text Feedback

Latest implemented changes:

- Armor stand no longer treats each part as an independent rotation center. The stand pose is resolved through `armorStandRigPoseForPart()`, so all parts keep the humanoid relationship while shared offset, scale, yaw, pitch, and explode state are applied.
- Right grip + trigger is now the highest-priority exit chord in armor-stand mode. It exits before hover actions such as reset/replay/close can steal the trigger.
- Right grip movement is converted from controller world-space into the Quest rig's local-space offset before it moves the armor. This prevents direction drift when the observer/user yaw changes.
- `getControllerByHand()` no longer assigns the same stale controller to both hands during workshop controls. Missing left/right controllers remain missing instead of creating false two-hand input.
- The static whole-suit audit now reads `QUEST_HUMAN_ANCHOR_CONTRACT.center_m` from the Quest runtime, then verifies side signs, centerline, vertical body-chain order, and chest-front/back-depth meaning.

Still needs physical headset confirmation:

- Right grip + trigger exits from armor stand every time, including while the ray is hovering over reset/replay/close.
- One-hand movement feels like grabbing a single nested humanoid suit object, not dragging individual parts.
- Two-hand scale/yaw keeps the assembled suit readable and does not scatter parts.
- Mirror/replay wearing fit is judged after leaving armor stand, because armor stand remains an inspection mode rather than a transformation-success proof.

## 2026-05-04 Anchor-Point / Body-Surface Follow-Up

Latest headset feedback:

- Global facing axis and whole-body relation are improving.
- A small forward offset may still come from Quest HMD/world-anchor centering, so it must be separated from armor authoring errors in telemetry.
- The stronger remaining issue is per-part anchoring: waist parts can intersect or collapse into each other instead of reading as a close belt loop around the pelvis.
- This is a Web + Quest issue, because the same part origin, sidecar offset, and runtime placement contract feed both previews.

Implemented changes:

- Added `BODY_SURFACE_FIT_POLICIES` in `viewer/shared/armor-canon.js` as the shared Web/Quest body-surface fit contract.
- Web Forge now routes worn preview offsets through `clampSurfaceOffsetForPart(part, ..., "vrm")`.
- Quest now routes `quest_rig_offset_m` through `clampedQuestOffsetArrayFromPlacement(part, ...)` before applying runtime offsets in live, mirror, motion, and armor-stand paths.
- Quest debug snapshots now include `runtimeOffsetClamped`, `surfaceFitRole`, and `surfaceFitContact` per part so QA can compare raw sidecar/runtime offsets against displayed offsets.
- Waist is explicitly classified as `pelvis_belt_loop`; its runtime forward/back offset is now much tighter than the raw sidecar offset so the belt stays centered on the pelvis body volume.

Current asset-level finding:

- `python tools/validate_armor_part.py waist --report-json --no-color` still reports `no_body_intersection_at_reference_pose` as warn with clearance about `-0.069m`.
- Chest and back also report body-intersection warnings, so the runtime clamp is a short-term fit improvement, not the final asset-quality fix.
- Next asset pass should rebuild or adjust the torso/waist GLBs so the geometry itself carries the intended body-surface loop/shell clearance instead of relying on viewer-side clamp compensation.

Next QA focus:

1. In Quest debug mode, compare `runtimeOffset` and `runtimeOffsetClamped` for `waist`, `chest`, and `back`.
2. If the whole suit is still slightly forward while clamped offsets are centered, treat that as HMD/world-anchor calibration work.
3. If waist plates still visibly intersect after clamping, move the issue to the GLB authoring pipeline and tighten the validator from warn toward fail for belt-loop clearance.
4. Confirm Web Forge preview shows the same closer waist fit, because it now uses the same shared policy.
