# Web/Quest Model Parity Design Review - 2026-05-05

## Scope

This review uses only local code and local docs. It does not change runtime code.

Parent-side work is currently touching:

- `viewer/quest-iw-demo/quest-demo.js`
- `tests/test_quest_recall_render_contract.py`

Those files are intentionally left untouched by this review. The goal here is to name where Web Forge preview and Quest diverge, why Web preview cannot simply be copied into Quest, and what order of implementation should close the gap without breaking the exhibition route.

## Executive Conclusion

`runtime-render-placement.v1` is necessary, but it is not sufficient for visual parity.

It standardizes selected asset identity, target size, offset, surface clamp, and rotation. The mismatch now lives in the composition layers around that contract:

1. Web Forge preview consumes VRM/Web fields in a static preview/body-stand context.
2. Quest self/mirror/replay consumes the same record after XR anchor capture, rig recentering, live/replay body estimation, view-mode scaling, and Quest-space sign conversion.
3. Quest armor stand is an inspection/workshop mode with its own stand transform, floor lift, pitch/yaw/scale/explode, and a direct Quest-offset path.

Therefore "Quest should use Web preview exactly" is not a single switch. It requires choosing which layer owns body anchors, which layer owns coordinate conversion, and which display modes are allowed to reuse Web fields.

## Current Contract Shape

`src/henshin/runtime_package.py` builds each selected placement with:

- `contract_version: "runtime-render-placement.v1"`
- `coordinate_space: "vrm_humanoid_local_y_up_z_front"`
- `quest_coordinate_space: "quest_rig_local_y_up_z_back"`
- `offset_m`
- `quest_rig_offset_m`
- `surface_offset_clamped_m`
- `quest_surface_offset_clamped_m`
- `rotation_deg`
- `target_size_m`
- `target_size_array_m`
- `scale_policy: "fit_source_bbox_to_target_size_m"`

The public contract already carries both Web/VRM and Quest fields. That is the right shape. The unresolved question is which consumer path picks which field, and whether body anchors are equivalent.

## Layer Map

| Layer | Web Forge preview | Quest self/mirror/replay | Quest armor stand | Divergence risk |
| --- | --- | --- | --- | --- |
| Asset selection | Variant tables and selected preview module choose `asset_ref` and placement. | Recall runtime package projects selected asset and placement into module. | Same loaded mesh map. | Low if recall/runtime package is fresh. |
| Mesh normalization | Preview GLB size is evaluated against source bbox and target size. | GLB geometry is merged, normalized, then scaled by `questGlbScaleForPart()`. | Same GLB scale helper, additionally multiplied by stand scale. | Medium: normalized geometry and target axis meaning must match. |
| Target size | Prefers `target_size_array_m`, then `target_size_m`. | Default prefers `target_size_array_m`; web parity path can prefer `target_size_m`. | Same scale helper, but stand transform changes apparent size. | Low/medium. |
| Offset | Prefers `surface_offset_clamped_m` / `surface_anchor.offset_clamped_m`, then `offset_m` in VRM/Web space. | Default uses `quest_surface_offset_clamped_m` / `quest_rig_offset_m`; web parity path can use Web fields. | `armorStandRigPoseForPart()` currently reads the Quest clamped offset directly. | High for parity claims across all Quest modes. |
| Rotation | Applies `rotation_deg` directly in Web preview orientation. | Default converts rotation signs for Quest; web parity path can use direct Web rotation. | Adds inspection pitch/yaw after runtime rotation. | High for 90/180 degree or sign-order issues. |
| Body anchor | Web preview has static preview pose and declared height/baseline VRM direction. | Quest uses `QUEST_HUMAN_ANCHOR_CONTRACT`, live HMD/controller estimates, body-sim/replay frames, and view-mode alignment. | Uses `questAssemblyPoseForPart()` plus floor lift and workshop transform. | Highest. |
| Root/rig | Browser preview root is stable. | XR world anchor can be recaptured, snapped, scaled, or be stale. | Observer/armor stand anchor faces user and has separate distance/height/scale. | Highest for `runtime_anchor` failures. |
| Evidence | Web screenshots and preview QA. | `quest-debug` payload, `centerlineQa`, headset screenshot. | Same telemetry but different UX state. | High if evidence mode is confused. |

## Why Web Preview Cannot Be Copied Into Quest As-Is

1. Coordinate spaces are not the same.
   Web placement is `vrm_humanoid_local_y_up_z_front`; Quest display is `quest_rig_local_y_up_z_back`. The z sign conversion is explicit in the contract. A direct copy of Web offset into Quest can flip front/back unless the consumer is deliberately in `web_preview_parity` mode.

2. Web preview has a stable camera/root, Quest has an XR anchor.
   The latest failure shape `centerline QA fail/runtime_anchor anchor=NG hard=WARN part=0 glb=0` points first at XR anchor/rig sync, not per-part model placement. If anchor is wrong, perfect Web placement still looks wrong in headset.

3. Quest has multiple body sources.
   Quest self view can use live HMD/controller estimates. Mirror/replay can use archive/body-sim/mocopi frames. Armor stand uses the static human anchor contract. Web preview does not have to decide among these runtime sources.

4. Armor stand is not wearing proof.
   Existing docs already treat armor stand as inspection/workshop mode. It adds floor lift, observer anchor, stand scale, yaw, pitch, root movement, and explode state. That is deliberately not the same transform as "self wearing" or "mirror replay".

5. Armor stand has a separate offset consumption path.
   In Quest, `armorStandRigPoseForPart()` currently resolves `runtimeOffset` with `clampedQuestOffsetArrayFromPlacement()`. Self/mirror/replay placement paths call `runtimePlacementOffsetArrayForPart()`, which can distinguish `quest_rig` from `web_preview_parity`. This means a parity switch can affect self/mirror/replay without fully affecting armor stand position.

6. Rotation composition differs by mode.
   Web applies `rotation_deg` directly. Quest default negates x/y and preserves z before multiplying by base rotation. Armor stand then premultiplies inspection yaw/pitch. A correct Web rotation can still be wrong after Quest composition if the mode is not explicit.

7. GLB origin/bounds is a separate failure class.
   `runtime-render-placement.v1` can be correct while a GLB's local origin or merged bounds center is off. Quest centerline QA separates `part_anchor_runtime_offset` from `glb_origin_bounds` for this reason.

8. Quest self view has visibility constraints.
   VRM/base body and helmet/head/neck visibility cannot be copied from Web preview. Self view must avoid first-person obstruction; mirror and armor stand need full-body readability.

9. Runtime package freshness is not guaranteed by visual similarity.
   Web Forge preview, recall payload, replay archive, and Quest Browser cache can be stale independently. A fresh code and telemetry payload are required before tuning.

10. Exhibition success is not pixel parity.
   The visitor route needs stable recall, clear transformation, return from armor stand, and a non-blocking self view. Pixel-identical Web/Quest placement is a stronger engineering target than the exhibition minimum.

## Where The Difference Most Likely Occurs

### A. Runtime Anchor Layer

Symptoms:

- `centerlineQa.classification=runtime_anchor`
- `anchor=NG`
- `part=0`
- `glb=0`

Interpretation:

The rig/root is not aligned to the expected XR world anchor. Do not tune Web parity, offsets, rotations, or GLB origins first. Re-enter VR, recapture/snap anchor, confirm fresh URL, and record `xr.anchorToRigDistanceM`, `xr.anchorToRigYawDeltaDeg`, and `xr.xrWorldAnchorProfile`.

### B. Body Anchor Layer

Symptoms:

- Centerline passes anchor, but chest/waist/helmet sit consistently off body.
- `partAnchorRuntimeOffset.parts` lists human-centered parts.
- Similar error appears in self and mirror, but not necessarily in armor stand.

Interpretation:

The body anchor source is different from the Web preview assumption. The fix is to unify body anchor semantics, not to edit GLB assets.

### C. Offset/Surface Clamp Layer

Symptoms:

- `partAnchorRuntimeOffset.parts` lists specific parts.
- New `anchorDiagnostics.activeOffsetSource` differs between captures.
- `questVsWebOffsetDistanceM` is meaningful on failing parts.

Interpretation:

This is the actual `web_preview_parity` vs `quest_rig` decision point. Compare default Quest lane and parity lane using the same fresh recall code.

### D. Rotation Layer

Symptoms:

- Parts are centered but visibly twisted, side-loaded, or 90/180 degrees off.
- Offset distances can pass while appearance fails.

Interpretation:

Quest rotation sign/order or armor-stand inspection rotation is the suspect. Keep offset tuning frozen until rotation is separated.

### E. GLB Origin/Bounds Layer

Symptoms:

- `glbOriginBounds.parts` is non-empty.
- Origin-to-bounds-center distance is high.
- Web/Quest both show the same asset as oddly displaced after normalization.

Interpretation:

Model asset origin/bounds must be fixed or compensated. Runtime placement should not become a hidden model-origin repair table unless that policy is explicitly accepted.

## Implementation Order To Bring Web Preview Closer To Quest

### Phase 0 - Evidence Discipline

Goal: never tune from ambiguous evidence.

- Use a fresh recall code.
- Capture Web preview evidence and Quest evidence against the same runtime package.
- Require `debug=1` or `qa=centerline`.
- Record `uxState`: self, mirror replay, observer replay, or armor stand.
- If `runtime_anchor` appears, fix/retry anchor before touching placement.

Exit:

- We can say whether the failure is anchor, body anchor, offset, rotation, GLB origin, or stale artifact.

### Phase 1 - Make Placement Mode Explicit Per Display Mode

Goal: no implicit mode drift.

- Keep `quest_rig` as the visitor default until parity is proven.
- Keep `web_preview_parity` as an operator QA lane.
- Add/keep telemetry for active mode and active offset source.
- Decide whether armor stand should honor `runtimePlacementOffsetArrayForPart()` or intentionally remain Quest-rig-only.

Important design call:

If the product claim is "Web preview and Quest armor stand are identical", then armor stand must use the same runtime placement mode resolver as self/mirror. If the claim is "armor stand is Quest inspection mode", then keep Quest-rig-only but do not use armor stand screenshots as Web parity proof.

### Phase 2 - Unify Body Anchor Tables

Goal: one semantic source for part centers.

- Promote `QUEST_HUMAN_ANCHOR_CONTRACT` semantics into a shared documented body anchor contract.
- Map Web Forge preview body points to the same names and meaning.
- Verify chest/back front-depth, waist loop, shoulders, shins, boots with left/right signs.
- Add a static doc/test table for expected centerline and side signs if not already covered.

Exit:

- Web and Quest are comparing the same "where should this part be on a human" answer before any offset is applied.

### Phase 3 - Normalize Offset And Rotation Consumers

Goal: `runtime-render-placement.v1` fields have one consumer policy per mode.

- Define a placement resolver:
  - input: placement record, part, display mode, parity mode
  - output: target size, offset, rotation, coordinate space label
- Use it in all Quest paths:
  - segment/body-sim pose
  - live self pose
  - mirror avatar pose
  - replay motion pose
  - armor stand pose, if parity claim includes armor stand
- Keep Web resolver and Quest resolver side by side in docs/tests until identical where intended.

Exit:

- A telemetry payload can state not only "placement exists", but "which resolver output was applied".

### Phase 4 - Body Guide / VRM Adapter

Goal: stop comparing armor against different bodies.

- Implement the VRM base suit adapter boundary described in `quest-vrm-base-suit-adapter-plan-2026-05-05.md`.
- Self view must mask head/neck/face/hair.
- Mirror and armor stand can show full body.
- The adapter reports coordinate space and visible mode.

Exit:

- Web preview and Quest compare armor against a related human guide, not Web's preview body versus Quest's procedural capsule/body mock.

### Phase 5 - Acceptance And Waivers

Goal: decide what "same enough" means.

- Numeric gate:
  - centerline anchor pass
  - no `runtime_anchor`
  - no `glb_origin_bounds` unless waived
  - per-part anchor deltas under documented thresholds
- Visual gate:
  - front, side, 3/4 captures in Web and Quest
  - self view not obstructed
  - mirror/replay body relationship readable
  - armor stand clearly labeled as inspection if not parity-proof

## Key Risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| False placement tuning while XR anchor is broken | Can make Web and Quest both worse once anchor is fixed. | Treat `runtime_anchor` as first-order blocker. |
| Armor stand mistaken for wearing fit | Stand has extra transforms and may use a different offset path. | Judge wearing fit in mirror/replay; label stand as inspection. |
| Web parity flag over-applied | Direct Web offsets in Quest can invert front/back if mode assumptions are wrong. | Keep parity behind query/runtime flag and telemetry. |
| Quest rig path under-tested after parity work | Exhibition route may regress while QA lane improves. | Test both `quest_rig` and `web_preview_parity` with same code. |
| VRM adapter creates first-person obstruction | A full Web body in self view can block the wearer. | Require head/neck masking before acceptance. |
| GLB origin repaired through runtime offset | Hides asset quality problems and creates per-mode inconsistency. | Use `glb_origin_bounds` classification to route to modeler/asset fix. |
| Stale replay/runtime package | Old artifacts can look like coordinate bugs. | Fresh recall code and telemetry manifest/runtime ids are mandatory. |
| Rotation sign/order conflated with offset | Center can be right while visual orientation is wrong. | Separate offset QA and rotation QA; do not tune both together. |

## Exhibition-Oriented Compromise

For the next exhibition pass, do not require full Web/Quest pixel parity before proceeding. Require stable, explainable Quest behavior.

Recommended public lane:

- Visitor route uses `quest_rig` default.
- Operator has a hidden `webPreviewParity` QA URL for comparison only.
- If `centerlineQa` reports `runtime_anchor`, the run is invalid evidence; recenter/re-enter/relaunch and retry.
- If `centerlineQa` passes and visual fit is acceptable in mirror/replay, accept even if Web preview is not pixel-identical.
- Armor stand is accepted as workshop/inspection mode, not final wearing proof.
- Self view prioritizes no obstruction over full Web body fidelity.
- Use fresh recall code and capture logs for final sign-off.

Minimum public acceptance:

- Quest loads the selected suit with `runtime-render-placement.v1`.
- No silent fallback for intended GLB parts.
- `centerlineQa.verdict` is pass, or a documented non-placement warning is waived by operator.
- Visitor can leave armor stand and return to mirror/replay.
- Mirror/replay visually reads as a coherent armored human.
- Any `web_preview_parity` difference is documented as non-public QA, not a visitor-facing guarantee.

## Recommended Next Engineering Tickets

1. Decide armor stand parity policy.
   Either make armor stand use the shared placement resolver or explicitly document that it is Quest-rig inspection mode.

2. Add a shared placement resolver contract doc.
   It should define selected fields per display mode and parity mode.

3. Add an evidence comparison checklist.
   Same fresh code, same runtime package id, Web screenshot, Quest debug payload, Quest screenshot, and centerline line.

4. Promote body anchor semantics.
   Move `QUEST_HUMAN_ANCHOR_CONTRACT` meaning into a shared spec, then map Web preview to it.

5. Continue VRM adapter work.
   It is the right long-term path to make Web body and Quest body comparable, but only after first-person masking is solved.

