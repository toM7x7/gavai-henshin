# Replay/Armor Alignment Verification - 2026-05-04

Status: verification note for the current Quest/Web mismatch.

Scope: Web replay, Quest Browser replay, and the runtime package path that feeds
armor GLB placement. This note does not change the active contracts; it defines
how to prove whether the mismatch is coordinate-space, placement, replay motion,
or stale-artifact related.

## Observed Symptom

The deposition particle effect appears correctly positioned and timed, but the
armor/body relationship is wrong:

- Particles look okay relative to the active scene and transformation timing.
- Armor parts do not sit on the expected body shell or replay body positions.
- The mismatch appears as armor/body drift, not as a complete WebGL failure,
  missing GLB load, or particle-system failure.
- Current runtime recall can still report healthy placement data, GLB fetches,
  and `runtime-render-placement.v1`, so "loaded successfully" is not enough
  evidence for alignment.

Interpretation: particles are likely following the scene/replay progress anchor,
while armor meshes are passing through a different body-pose and placement
composition path. The first suspect is coordinate-space conversion or transform
composition, not particle logic.

## Likely Coordinate-Space Causes

Primary spaces already in the current contracts:

- `vrm_humanoid_local_y_up_z_front`: source placement space for VRM/body-facing
  armor offsets.
- `quest_rig_local_y_up_z_back`: Quest runtime placement space after the z-axis
  conversion.
- `mocopi_world_y_up`: raw mocopi provenance before retargeting.
- `body_sim_segment`: replay/body-sim derived segment space.
- `mixed_runtime`: any path that has already combined retargeting, Quest pose,
  and runtime placement.

Likely causes to verify:

1. Z-axis conversion mismatch.
   Runtime placement expects `quest_rig_offset_m = [x, y, -z]` relative to
   `offset_m`. If replay or Quest applies the VRM-space z directly, front/back
   drift will be visible while particles still look correct.

2. Rotation sign or order mismatch.
   Quest runtime placement currently converts placement rotation by negating x
   and y, preserving z, then composing it with the base pose. A replay path that
   applies Euler angles in a different order, applies placement before the base
   pose incorrectly, or skips placement rotation will make armor look twisted or
   side-loaded.

3. Different body anchors for particles and armor.
   Particles can be anchored to replay progress, camera/rig, or a deposition
   field, while armor may be anchored to live head, `VR_BODY_PART_POSES`, mocopi
   frames, or body-sim segment positions. If those anchors are not normalized to
   the same root, particles can pass while armor fails.

4. Replay view mode changing the body-space assumption.
   `self`, `mirror`, and `observer` modes do not share the same visible origin,
   scale, or height offset. A path that is correct for non-XR Web replay can be
   wrong in Quest mirror/observer if body-shell alignment or replay frames are
   selected differently.

5. Runtime placement applied inconsistently across pose paths.
   Live pose, segment pose, standby/armor-stand pose, and replay motion pose
   must all apply target size, Quest offset, and runtime rotation with the same
   sign conventions.

6. Double application or missing application of offsets.
   A clear failure pattern is one path applying `quest_rig_offset_m` before
   body anchoring and another after body anchoring, or one path applying it once
   during reveal and again after reveal.

7. Unit and normalization mismatch.
   GLB geometry is normalized, then scaled to `target_size_array_m`. If one path
   uses normalized mesh units and another uses meters, the part can look
   correctly oriented but too far from the body.

8. Stale replay/runtime artifacts.
   A replay bundle can carry an older runtime package, placement contract, or
   selected variant identity. A fresh recall can be healthy while archive replay
   still uses stale body-sim or placement data.

9. Mocopi/body-sim retargeting boundary unclear.
   Raw mocopi is `mocopi_world_y_up`; Quest display should consume retargeted
   replay/body positions or explicitly declare `mixed_runtime`. If the replay
   treats raw mocopi coordinates as Quest rig local coordinates, armor/body
   alignment will drift even though the motion source label is correct.

10. Timebase mismatch.
   If particle progress and armor replay frames use different timebases, the
   particles can look timed correctly while armor lags or leads the body pose.

## Verification Criteria - Web Replay

Use Web replay as the deterministic alignment baseline before entering the
headset.

Required evidence:

- A fresh recall code generated from the current Web Forge path.
- The replay record or replay script used by Web points at the same
  `manifest_id`, `runtime_package.contract_version`, and
  `runtime_package.render_placement_contract` as the recall.
- `render_placements` exist for every visible armor part.
- For every placement, `coordinate_space` is
  `vrm_humanoid_local_y_up_z_front` and `quest_coordinate_space` is
  `quest_rig_local_y_up_z_back`.
- For every placement, `quest_rig_offset_m[0] == offset_m[0]`,
  `quest_rig_offset_m[1] == offset_m[1]`, and
  `quest_rig_offset_m[2] == -offset_m[2]` within tolerance.
- Web replay displays body shell, armor, and deposition particles from the same
  replay event/time slice.
- In non-XR Web replay, armor part centroids sit on their expected
  `VR_BODY_PART_POSES` or retargeted replay body points.
- Mirror/observer replay does not change part-to-body distances except for the
  documented view-mode scale/anchor transform.
- Particle pass/fail is recorded separately from armor/body pass/fail.

Recommended Web capture set:

- Front, side, and 3/4 screenshots at replay progress 0.25, 0.50, 0.75, and
  completed.
- A diagnostic JSON dump containing per-part body target, mesh centroid,
  runtime offset, runtime rotation, target size, view mode, and replay time.
- Console evidence for `[Quest runtime diagnostic]` or equivalent placement
  counts when using the shared Quest viewer in desktop mode.

## Verification Criteria - Quest

Quest must be verified separately because XR origin, height, view mode, and
browser cache behavior can hide Web-only assumptions.

Required evidence:

- Quest opens the current viewer from either LAN or adb reverse and uses the
  exact same fresh recall code verified on Web.
- The Quest status/diagnostic path confirms `runtime-render-placement.v1`,
  visible armor count, placement count, offset count, rotation count, and target
  count.
- All visible armor GLBs load from the selected runtime asset refs; no silent
  canonical fallback is accepted for this check.
- Test each replay view mode that will be used publicly: `self`, `mirror`, and
  `observer`.
- In `self`, armor follows the live/body anchor without front/back inversion.
- In `mirror` and `observer`, replay armor follows the replay body shell rather
  than the headset/camera root alone.
- The completed transformation pose keeps helmet/chest/waist centered on the
  body shell; limbs are symmetric unless the replay motion intentionally breaks
  symmetry.
- The deposition particle field can pass independently, but it does not waive
  armor/body alignment failure.
- Quest Browser tab reload/cache state is recorded. A failed check must state
  whether the tab was freshly opened, hard-reloaded, or cache-cleared.

Physical Quest notes:

- Check from normal exhibition stance height, not only desktop emulation.
- Record transport path: LAN URL, HTTPS URL, or adb reverse localhost.
- Record Quest device/browser version if visible.
- Capture headset screenshots or external camera video for at least one front
  and one side view.

## Recommended Numeric Tolerances

Use meters and degrees. These tolerances are intentionally tighter than a casual
visual pass so the team can detect coordinate mistakes before exhibition.

Coordinate contract tolerances:

- `quest_rig_offset_m` z sign conversion: absolute error <= 0.001 m.
- x/y offset copy from `offset_m`: absolute error <= 0.001 m.
- Runtime target size serialization: absolute error <= 0.001 m per axis.
- Replay frame timestamp normalization: <= 0.033 s for 30 fps sources, hard
  fail above 0.050 s unless documented as lower-frame-rate source data.

Armor-to-body positional tolerances:

- Helmet, chest, back, waist centroid to expected body anchor: <= 0.030 m
  preferred, <= 0.050 m maximum.
- Shoulders, upperarms, forearms, thighs, shins: <= 0.050 m preferred,
  <= 0.070 m maximum.
- Hands and boots: <= 0.070 m preferred, <= 0.090 m maximum because controller,
  foot, and estimated endpoint data are noisier.
- Left/right symmetric part pair distance delta: <= 0.040 m when the replay pose
  is intended to be symmetric.
- Completed-pose whole-suit average centroid error: <= 0.040 m, hard fail above
  0.060 m.

Rotation tolerances:

- Helmet/chest/waist/back orientation error: <= 3 deg preferred, <= 5 deg
  maximum.
- Limb orientation error: <= 5 deg preferred, <= 8 deg maximum.
- Obvious 90 deg or 180 deg flips are immediate coordinate-space failures, not
  visual-polish issues.

Scale and bbox tolerances:

- GLB bbox vs `target_size_array_m`: <= 5% per axis preferred.
- 5-8% per axis is warning and requires visual sign-off.
- Above 8% per axis is a gate failure for final replay/Quest parity unless a
  part-specific exception is written down.

Particle/armor timing tolerance:

- Particle reveal progress and armor reveal progress should differ by <= 0.05
  normalized progress.
- Particle completion and armor completed pose should differ by <= 0.100 s.

## Follow-Up Gates And Tests

Gate 1 - Contract consistency:

- Add or run a contract check that compares recall runtime package,
  replay-record runtime package, and replay-script artifact refs for the same
  `recall_code`.
- Assert placement part set equals visible armor part set.
- Assert z inversion and rotation conversion policy are present for every
  visible part.

Gate 2 - Web deterministic replay:

- Add a desktop replay alignment probe that samples body anchors and armor mesh
  centroids at fixed progress values.
- Store per-part errors in JSON and fail on the tolerances above.
- Save front/side screenshots as evidence.

Gate 3 - Quest desktop smoke:

- Use the Quest viewer in desktop browser mode to confirm no WebGL errors, no
  missing GLB loads, and runtime diagnostic placement counts match the recall.
- Include `self`, `mirror`, and `observer` view-mode checks where the mode is
  reachable without a headset.

Gate 4 - Physical Quest pass:

- Run the same fresh recall code in the headset.
- Verify armor/body alignment in `self`, `mirror`, and `observer`.
- Record Quest transport mode, URL, device/browser state, screenshots/video,
  and pass/fail notes.

Gate 5 - Stale artifact prevention:

- Before accepting any replay result, preflight the replay bundle and reject it
  if the runtime package snapshot is missing, the placement contract is stale,
  artifact refs are absolute local paths, or selected variant keys do not match
  the recall.

Gate 6 - Regression tests:

- Keep unit coverage for runtime placement fields and Quest rotation/offset
  application.
- Add an integration fixture with one asymmetric z offset and one non-zero
  rotation so sign errors are visible numerically.
- Add a replay fixture with mocopi/body-sim provenance and assert raw
  `mocopi_world_y_up` is not consumed as Quest rig local space without an
  explicit retargeting/derived artifact step.

## Working Assumptions

- The current symptom is not a particle renderer defect because particles are
  visually acceptable while armor/body alignment is not.
- The current active placement contract is `runtime-render-placement.v1`.
- Quest display consumes `quest_rig_local_y_up_z_back`; source placement data
  can originate from `vrm_humanoid_local_y_up_z_front`.
- Replay provenance may include mocopi, body-sim, live Quest pose, or mixed
  runtime data; the verification must state which one is active.
- This note is a verification target, not a code fix. Any implementation should
  happen in a later change after one failing gate identifies the exact path.
