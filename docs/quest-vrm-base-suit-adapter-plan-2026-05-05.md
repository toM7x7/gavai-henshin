# Quest VRM Base Suit Adapter Plan - 2026-05-05

## Purpose

User intent: replace the procedural Quest base suit with a VRM body guide, while keeping first-person view clear above the neck.

This document is an implementation boundary, not an implementation. It defines the minimum acceptance contract for a future VRM adapter before it can replace the current fallback base suit.

## Non-Negotiable View Contract

- Self view must never render VRM head, neck, face, hair, eyes, or helmet-equivalent geometry.
- Self view may render hands, lower body, or a reduced body guide only if it cannot enter the camera frustum as an upper-shell obstruction.
- Mirror view must show a readable human guide, including head and neck, so the user can inspect the full silhouette.
- Armor stand view must show a full human guide, including head and neck, because it is an observer/workshop mode rather than the user's eye position.
- Generated fallback capsules remain forbidden in self view unless they are explicitly proven not to obstruct the camera.

## Adapter Boundary

Future VRM support should enter through a dedicated adapter instead of direct `GLTFLoader` use in the Quest scene loop.

Required adapter surface:

- `loadBaseSuitAvatar(suitspec, runtimePackage)`
- `setBaseSuitAvatarMode("self" | "mirror" | "armor_stand")`
- `applyBaseSuitAvatarPose({ standTransform, bodyPose, reveal })`
- `disposeBaseSuitAvatar()`
- `collectBaseSuitAvatarDebug()`

The adapter must report:

- `source: "vrm"`
- `vrmAssetRef`
- `headNeckMaskReady`
- `firstPersonHeadNeckVisible: false`
- `visibleMode: "self" | "mirror" | "armor_stand"`
- `coordinateSpace: "quest_rig_local_y_up_z_back"`

## Quest Integration Points

The current Quest viewer base-suit behavior is concentrated in these boundaries:

- `refreshBaseSuitSurface()`: creates the procedural base-suit meshes.
- `applyBaseSuitGuidePose({ standbyPreview })`: switches between local body pose and armor-stand pose.
- `updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView, reveal, bodyShellAligned })`: owns first-person masking, mirror visibility, armor-stand visibility, opacity, and wireframe mode.
- `hideLoadedArmorMeshes()`: hides procedural base-suit children together with armor meshes.
- `collectQuestDebugSnapshot()`: reports `baseShell` children and must also report adapter mode when VRM is active.

Future implementation should keep these boundaries stable:

- Add a small `baseSuitAdapter` field to the demo class.
- Let `refreshBaseSuitSurface()` choose either procedural fallback or VRM adapter based on readiness.
- Let `updateBaseSuitVisibility()` be the single place that decides self/mirror/armor-stand visibility.
- Do not let armor mesh loading call VRM loading directly; `loadArmorMeshes()` should only trigger base-suit refresh and then load GLB armor parts.
- Do not move GLB armor placement logic into the adapter.

## Loading Library Candidates

Preferred route:

- Add `@pixiv/three-vrm` and use its VRM-aware loader/plugin path.
- Keep `GLTFLoader` for armor GLB parts and as the underlying transport, but not as the sole VRM semantic layer.
- Use VRM humanoid APIs for bone access where available.

Fallback route:

- If `@pixiv/three-vrm` cannot be added before exhibition, do not render raw `default.vrm` in self view.
- A raw `GLTFLoader` parse may be used only for offline inspection or a non-self-view spike.
- Raw GLTF scene rendering is acceptable in mirror/armor-stand only after it is behind the adapter and debug clearly reports `headNeckMaskReady: false`.

Not accepted:

- Importing `default.vrm` directly into `quest-demo.js` and adding it to `this.rig`.
- Hiding only `J_Bip_C_Head` / `J_Bip_C_Neck` bones and calling that a first-person mask.
- Replacing `runtime_placement` with VRM bone transforms for GLB armor parts.

## Implementation Review Findings

Package state:

- Current `package.json` has `three`, `vite`, `@iwsdk/core`, and `@iwsdk/vite-plugin-dev`.
- Current `package.json` does not include a VRM semantic loader.
- Therefore the first implementation PR must either add `@pixiv/three-vrm` or explicitly remain a non-self-view raw GLTF spike.

Minimum load path:

1. Keep `GLTFLoader` as the underlying loader.
2. Register the VRM loader/plugin in a small adapter module or adapter section, not throughout `quest-demo.js`.
3. Resolve the asset ref from `suitspec.body_profile.vrm_baseline_ref` first, then `runtimePackage.visual_layers.base_suit.asset_ref`, then `viewer/assets/vrm/default.vrm`.
4. Load the VRM once per recalled suit and cache it behind `baseSuitAdapter`.
5. Add the adapter root under the same rig space used by the procedural `baseSuitGroup`.
6. Drive visibility only through `updateBaseSuitVisibility()`.
7. Dispose adapter scene/materials/textures when recall changes or armor meshes are cleared.

Self-view head mask traps:

- A hidden head bone is not enough when the face/body surface is one SkinnedMesh.
- A transparent head material is not enough unless `depthWrite`, shadowing, and all hair/face submeshes are also handled.
- A clipped head that still writes depth can block armor and particles even if visually transparent.
- A mirror-only VRM guide must not accidentally remain attached to the self-view camera rig after mode switches.
- Helmet hiding and VRM head/neck hiding are the same product requirement: nothing above the neck may be in the user's first-person view.

Fallback traps:

- Do not treat VRM load failure as "no base suit"; fall back to the procedural guide.
- Do not let a mirror-only VRM adapter suppress the procedural self-view mask.
- Do not let adapter errors leave stale visible VRM nodes after `hideLoadedArmorMeshes()`.
- Do not let failed VRM disposal leak textures across repeated recall-code loads.
- Do not let fallback state change GLB armor `mesh.userData.runtimePlacement`.

Review gate before implementation merge:

- Static test proves no raw `default.vrm` first-person load exists without adapter mask readiness.
- Static test proves `updateBaseSuitVisibility()` remains the single view-mode gate.
- Debug snapshot includes adapter source, mode, and mask readiness.
- Browser/Quest QA includes self, mirror, and armor-stand captures.
- Regression test verifies runtime placement tokens are unchanged.

## Head/Neck Mask Acceptance

The VRM adapter is not accepted until one of these is true:

- A headless/body-only VRM or GLB export is used for self view.
- The adapter removes or masks head and neck vertices from the skinned body mesh before first-person rendering.
- The adapter uses a separately authored first-person body proxy that excludes head, neck, face, hair, and upper shell.

Bone visibility alone is not an accepted mask. The current local VRM has `Face` and `Body` as SkinnedMesh nodes, so hiding `J_Bip_C_Head` or `J_Bip_C_Neck` does not prove the skinned surface is gone.

## Fallback Policy

Fallback is a feature, not an error path.

- If VRM load fails, keep the procedural base suit.
- If VRM loads but `headNeckMaskReady` is false, allow VRM only in mirror/armor-stand modes and keep procedural self-view masking.
- If VRM loads and the mask is ready, self view may use the VRM adapter only with `firstPersonHeadNeckVisible: false`.
- If the adapter pose update fails for a frame, keep the last valid pose for mirror/armor stand, and hide self-view VRM for that frame.
- If Quest performance drops or memory pressure is observed, prefer procedural fallback for exhibition.

Debug output should distinguish:

- `source: "procedural"`
- `source: "vrm"`
- `source: "vrm_mirror_only"`
- `source: "fallback_after_vrm_error"`

## GLB Armor Coordinate Contract

Replacing the base suit must not change armor placement semantics.

- Armor GLB parts continue to use `runtime_placement`.
- Quest armor coordinates remain `quest_rig_local_y_up_z_back`.
- Runtime placement offsets still pass through `runtimePlacementOffsetArrayForPart`.
- Runtime placement rotations still pass through `applyRuntimePlacementRotation`.
- Mirror and armor stand can transform the VRM guide, but must not mutate per-part GLB armor offsets, rotations, target sizes, or selected variants.

## Mocopi And Bone Mapping Preparation

Current Quest motion is not full-body IK. It is a pragmatic estimate from:

- `normalizeMotionFrame()`
- `motionFramesFromReplayScript()`
- `updateLiveBodyAnchors()`
- `getLiveBodyPartPosition(part, target)`
- `getMotionBodyPartPosition(part, frame, target)`
- `questBodyRelativeOffsetForPart(part)`

Current motion inputs:

- `head`: HMD or replay head.
- `left_hand` / `right_hand`: controller or replay hands.
- `torso_yaw`: estimated from hands or replay.
- hips, legs, and feet: estimated from `QUEST_HUMAN_BODY_MOCK` / `VR_BODY_PART_POSES` until mocopi/IK/VRM retargeting is connected.

Adapter bone targets should use the local VRM naming observed in `viewer/assets/vrm/default.vrm`:

- hips: `J_Bip_C_Hips`
- spine: `J_Bip_C_Spine`
- chest: `J_Bip_C_Chest`
- upper chest: `J_Bip_C_UpperChest`
- neck: `J_Bip_C_Neck`
- head: `J_Bip_C_Head`
- left arm: `J_Bip_L_Shoulder`, `J_Bip_L_UpperArm`, `J_Bip_L_LowerArm`, `J_Bip_L_Hand`
- right arm: `J_Bip_R_Shoulder`, `J_Bip_R_UpperArm`, `J_Bip_R_LowerArm`, `J_Bip_R_Hand`
- left leg: `J_Bip_L_UpperLeg`, `J_Bip_L_LowerLeg`, `J_Bip_L_Foot`, `J_Bip_L_ToeBase`
- right leg: `J_Bip_R_UpperLeg`, `J_Bip_R_LowerLeg`, `J_Bip_R_Foot`, `J_Bip_R_ToeBase`

Minimum retargeting for exhibition:

- Head position follows HMD/replay head for mirror and armor stand only.
- Torso yaw follows `torso_yaw` and rotates hips/spine/chest as a simple chain.
- Hands follow controller/replay hand positions when tracked; otherwise use existing estimated offsets.
- Legs remain stable estimated poses from `QUEST_HUMAN_BODY_MOCK`; no knee IK is required for exhibition.
- Self view does not need full VRM retargeting until the head/neck mask is proven.

Mocopi follow-up:

- Map mocopi hips/chest/head/hands/feet into the same adapter pose object instead of adding mocopi-specific branches inside armor placement.
- Keep mocopi motion source labels such as `REPLAY_MOTION_SOURCE_MOCOPI` in diagnostics.
- Do not let mocopi retargeting change GLB armor `runtime_placement`.

## Exhibition Minimum Scope

Minimum shippable VRM scope before exhibition:

1. Mirror and armor stand can show the VRM guide.
2. Self view remains procedural/headless unless a tested VRM head/neck mask is ready.
3. GLB armor placement remains unchanged and tests continue to pass.
4. Debug snapshot reports adapter source, mode, and mask state.
5. If VRM load fails on Quest, the demo automatically falls back to the current procedural guide.

Out of scope for the first exhibition-safe cut:

- Full-body mocopi IK.
- Spring bone fidelity.
- MToon parity tuning beyond "loads without breaking the demo".
- Per-vertex runtime masking unless it has a screenshot-backed Quest check.
- Replacing armor placement anchors with VRM bone-space placement.

## Acceptance Checklist

- Self view screenshot: no head, neck, face, hair, helmet, or upper-shell obstruction.
- Mirror view screenshot: full VRM human guide is visible and readable.
- Armor stand screenshot: full VRM human guide is visible with armor aligned.
- Debug snapshot reports `firstPersonHeadNeckVisible: false`.
- Debug snapshot reports the VRM adapter source and mode.
- `tests/test_quest_recall_render_contract.py` includes a contract for the adapter boundary.
- Existing Quest runtime placement tests still pass.

## Current Decision

Until the adapter satisfies this contract, keep the procedural base suit policy:

- Hide procedural `head`, `neck`, `spine`, `shoulder_line`, and `torso` in self view.
- Keep mirror and armor stand body guides visible.
- Do not raw-load `viewer/assets/vrm/default.vrm` into first-person Quest rendering.

## Implemented Cut - 2026-05-05

Quest now exposes the VRM boundary as runtime status without raw-loading VRM:

- `resolveBaseSuitVrmAssetRef(suitspec, suitRecord)` detects candidate VRM references, including `suitspec.body_profile.vrm_baseline_ref`.
- `refreshBaseSuitVrmContractStatus()` records the detected asset ref.
- If no VRM asset is present, debug status is `procedural_fallback` with `no_vrm_asset_ref`.
- If a VRM asset is present, debug status is `disabled` with `raw_vrm_disabled_until_head_neck_mask_adapter`.
- `baseShell.vrm` in Quest debug snapshots reports `status`, `assetRef`, and `fallbackReason`.

This keeps the current head-hidden procedural suit working while making the next VRM adapter step observable. The next implementation should add a semantic adapter with a tested first-person head/neck/face/hair mask before any raw VRM scene is visible in self view.
