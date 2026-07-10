# Web/Quest Runtime Placement Resolver Unification Review - 2026-05-05

## Scope

This is an implementation-oriented review based on local code and docs only.

Do not treat this as an implemented runtime change. Parent-side work may edit Web Forge and Quest viewer, so this document names the shared contracts and resolver seams without changing:

- `viewer/armor-forge/forge.js`
- `viewer/quest-iw-demo/quest-demo.js`
- `viewer/shared/armor-canon.js`

## Current Read

`runtime-render-placement.v1` is already the portable placement record. `viewer/shared/armor-canon.js` already owns the shared surface policy layer:

- `wearableSurfaceFitPolicyForPart(partName)`
- `clampSurfaceOffsetForPart(partName, offset, space = "vrm")`
- `normalizeVec3(input, fallback)`
- VRM anchor baselines, attachment-slot aliases, fit defaults, and body-surface clamp policies

The remaining Web/Quest difference is not the clamp table itself. It is that Web Forge and Quest each independently resolve:

- which placement record is selected
- which target-size field wins
- which offset field wins
- which rotation sign convention wins
- which diagnostics explain the applied choice
- whether armor stand follows the same placement-mode resolver as self/mirror/replay

## Current Consumer Functions

### Web Forge

Current Web Forge placement helpers in `viewer/armor-forge/forge.js`:

- `isRuntimePlacementRecord(value)`
- `runtimePlacementMatchesPreviewVariant(part, placement, variantKey, assetRef)`
- `variantRuntimePlacementForPreviewPart(part, variantKey, assetRef, module)`
- `previewVariantKeyForRuntimePlacement(part, module)`
- `previewAssetRefForRuntimePlacement(part, variantKey, module)`
- `runtimePlacementForPreviewPart(part, module)`
- `runtimeTargetSizeForPreviewPart(part, module)`
- `runtimeOffsetForPreviewPart(part, module)`
- `runtimeRotationForPreviewPart(part, module)`
- `setRuntimePlacementForPreviewPart(part, placement)`

Web semantics today:

- selected variant/asset can override the module placement through variant placement tables
- target size uses `target_size_array_m` before `target_size_m`
- offset uses `surface_offset_clamped_m` / `surface_anchor.offset_clamped_m`, then Web/VRM `offset_m`
- rotation applies `rotation_deg` directly
- clamp space is `vrm`

### Quest Viewer

Current Quest placement helpers in `viewer/quest-iw-demo/quest-demo.js`:

- `runtimeRenderPlacement(runtimePackage, part)`
- `webPreviewParityPlacement(runtimePackage, placement)`
- `runtimePlacementForMesh(mesh)`
- `useWebPreviewRuntimePlacement(placement)`
- `targetSizeArrayFromPlacement(placement, fallback)`
- `questOffsetArrayFromPlacement(placement)`
- `questSurfaceOffsetArrayFromPlacement(placement)`
- `webPreviewOffsetArrayFromPlacement(placement)`
- `webPreviewSurfaceOffsetArrayFromPlacement(placement)`
- `clampedQuestOffsetArrayFromPlacement(part, placement)`
- `runtimePlacementOffsetArrayForPart(part, placement)`
- `questRotationArrayFromPlacement(placement)`
- `webPreviewRotationArrayFromPlacement(placement)`
- `runtimePlacementRotationArray(placement)`
- `questGlbScaleForPart(mesh, part, reveal)`
- `applyRuntimePlacementOffset(mesh, part, reveal, yaw)`
- `applyRuntimePlacementRotation(mesh, baseX, baseY, baseZ)`
- `questRuntimePlacementAnchorDiagnosticsForPart(part, placement)`

Quest semantics today:

- default mode is `quest_rig`
- query/runtime contract can opt into `web_preview_parity`
- target size can change precedence by mode
- `quest_rig` offset uses `quest_surface_offset_clamped_m` / `surface_anchor.quest_rig_offset_clamped_m`, then `quest_rig_offset_m`
- `web_preview_parity` offset uses Web fields
- `quest_rig` rotation negates x/y and preserves z
- `web_preview_parity` rotation applies Web signs directly
- self/mirror/replay paths use `runtimePlacementOffsetArrayForPart`
- armor stand currently calls `clampedQuestOffsetArrayFromPlacement()` inside `armorStandRigPoseForPart()`, so it does not fully share the parity-aware offset resolver

## Proposed Shared Module

Add a new pure shared module rather than overloading `armor-canon.js`:

```text
viewer/shared/runtime-placement-resolver.js
```

The resolver should import surface policy utilities from `armor-canon.js`, not duplicate them.

Recommended dependency direction:

```text
armor-canon.js
  owns: part policy, fit policy, VRM anchor baselines, surface clamps, vector normalization

runtime-placement-resolver.js
  imports from armor-canon.js
  owns: runtime-render-placement.v1 parsing, candidate selection, display-mode resolution, diagnostics

Web Forge / Quest viewer
  import resolver outputs
  own: scene graph application, Three.js mesh mutation, XR/view-mode transforms
```

Do not put Three.js objects in the shared resolver. Return plain arrays/numbers/strings so it can be used by Web, Quest, tests, and future PlayCanvas/GCP adapters.

## Shared Resolver Contract

### 1. Placement Record Detection

Share:

```js
isRuntimeRenderPlacementRecord(value)
```

Equivalent current code:

- Web: `isRuntimePlacementRecord(value)`
- Runtime package validator: `_is_runtime_render_placement_record(value)` in Python

Minimum behavior:

- accept `contract_version === "runtime-render-placement.v1"`
- accept defensive records with `target_size_m`, `target_size_array_m`, `offset_m`, or `rotation_deg`
- reject non-object values

### 2. Placement Identity Matching

Share:

```js
runtimePlacementMatchesIdentity({ part, placement, selectedVariantKey, assetRef })
```

Equivalent current code:

- Web: `runtimePlacementMatchesPreviewVariant(...)`
- Quest: implicit matching already happens earlier through `runtimePackage.render_placements[part]`

Minimum behavior:

- placement `part` must match when present
- selected variant key comparison must normalize `part:slug` and `slug`
- asset refs must compare normalized logical refs
- missing variant/asset does not fail if the other identity is authoritative

### 3. Candidate Selection

Share:

```js
selectRuntimePlacementForPart({
  part,
  module,
  runtimePackage,
  previewData,
  selectedVariantKey,
  assetRef,
})
```

Equivalent current code:

- Web: `runtimePlacementForPreviewPart(...)`, `variantRuntimePlacementForPreviewPart(...)`
- Quest: `runtimeRenderPlacement(runtimePackage, part)` plus module projection

Minimum behavior:

1. variant-specific placement that matches selected variant and asset
2. module-level `runtime_placement`
3. runtime package `render_placements[part]`
4. mirrored preview/asset-pipeline/visual-layer records
5. `null`

Important constraint:

The selected runtime package record remains authoritative for Quest recall. Web may inspect candidate variant tables, but selected public recall must resolve to one chosen record.

### 4. Placement Mode

Share:

```js
resolveRuntimePlacementMode({
  placement,
  runtimePackage,
  query,
  displayMode,
  defaultMode = "quest_rig",
})
```

Modes:

- `web_preview`
- `quest_rig`
- `web_preview_parity`

Display modes:

- `web_forge_preview`
- `quest_self`
- `quest_mirror`
- `quest_replay_observer`
- `quest_armor_stand`
- `playcanvas_preview`

Rules:

- Web Forge default: `web_preview`
- Quest visitor default: `quest_rig`
- Quest parity QA: `web_preview_parity`
- Armor stand must be explicitly decided:
  - either it honors the same resolver mode as self/mirror/replay
  - or it declares `quest_armor_stand` as Quest-rig-only inspection mode

### 5. Target Size

Share:

```js
resolveRuntimeTargetSize({
  placement,
  mode,
  fallbackTargetSizeM,
})
```

Equivalent current code:

- Web: `runtimeTargetSizeForPreviewPart(...)`
- Quest: `targetSizeArrayFromPlacement(...)`

Rules:

- Normalize both `target_size_array_m` and object/array `target_size_m`
- Return positive xyz meters
- `web_preview` / `web_preview_parity`: prefer `target_size_m`, then `target_size_array_m` if the product wants exact Web parity
- `quest_rig`: prefer `target_size_array_m`, then `target_size_m`, preserving current Quest behavior unless consciously changed

Open design decision:

If `target_size_array_m` and `target_size_m` are always serialized from the same source, this precedence difference is harmless. If they can diverge, resolver diagnostics must expose the source.

### 6. Offset

Share:

```js
resolveRuntimeOffset({
  part,
  placement,
  mode,
})
```

Equivalent current code:

- Web: `runtimeOffsetForPreviewPart(...)`
- Quest: `runtimePlacementOffsetArrayForPart(...)`
- Quest armor stand exception: `armorStandRigPoseForPart()` currently uses `clampedQuestOffsetArrayFromPlacement(...)`

Rules:

- `web_preview`: `surface_offset_clamped_m` / `surface_anchor.offset_clamped_m`, then clamp `offset_m` with `space="vrm"`
- `web_preview_parity`: same as Web
- `quest_rig`: `quest_surface_offset_clamped_m` / `surface_anchor.quest_rig_offset_clamped_m`, then clamp `quest_rig_offset_m` with `space="quest"`
- return:
  - `offsetM`
  - `source`
  - `space`
  - `wasClamped`
  - `rawOffsetM`

This is the most important shared resolver because it is where the current visible parity question lives.

### 7. Rotation

Share:

```js
resolveRuntimeRotation({
  placement,
  mode,
})
```

Equivalent current code:

- Web: `runtimeRotationForPreviewPart(...)`
- Quest: `questRotationArrayFromPlacement(...)`, `webPreviewRotationArrayFromPlacement(...)`, `runtimePlacementRotationArray(...)`

Rules:

- `web_preview` / `web_preview_parity`: degrees to radians, direct xyz signs
- `quest_rig`: degrees to radians with current Quest sign policy: `[-x, -y, z]`
- return:
  - `rotationRad`
  - `source`
  - `space`
  - `eulerOrder` if needed later

Do not compose with base pose in the shared resolver. Scene consumers compose the returned rotation with their body/view transform.

### 8. Scale

Share:

```js
resolveRuntimeScale({
  targetSizeM,
  normalizedSourceSize,
  reveal = 1,
})
```

Equivalent current code:

- Quest: `questGlbScaleForPart(...)`
- Web: preview scale paths around `runtimeTargetSizeForPreviewPart(...)`

Rules:

- Works on normalized source xyz and target xyz
- Returns xyz scale
- Does not know about armor stand global scale, reveal animation, or Web scene scale beyond the passed scalar

### 9. Diagnostics

Share:

```js
resolveRuntimePlacementDiagnostics({
  part,
  placement,
  mode,
  resolvedTargetSize,
  resolvedOffset,
  resolvedRotation,
})
```

Equivalent current code:

- Quest: `questRuntimePlacementAnchorDiagnosticsForPart(...)`
- Quest centerline payload
- Web preview QA panels and runtime placement source labels

Minimum fields:

- `contractVersion`
- `part`
- `mode`
- `targetSizeSource`
- `offsetSource`
- `offsetSpace`
- `rotationSource`
- `selectedVariantKey`
- `assetRef`
- `questVsWebOffsetDeltaM`
- `questVsWebOffsetDistanceM`

## What Should Stay Outside The Shared Resolver

Do not share these as resolver responsibilities:

- Three.js `Mesh` mutation
- XR anchor capture/snap/recenter
- Web camera/lighting controls
- Quest self-view visibility masking
- armor stand floor lift, pitch, yaw, root offset, explode state
- mocopi/body-sim retargeting
- GLB loading and geometry merge
- fallback procedural geometry generation

Those layers can consume resolver outputs, but they should not be inside the resolver.

## Armor Stand Decision Point

The most important product decision:

Should Quest armor stand be a Web parity proof or a Quest inspection mode?

### Option A - Armor Stand Honors Shared Resolver

Change future `armorStandRigPoseForPart()` behavior to consume `resolveRuntimeOffset({ mode })`.

Pros:

- One placement mode across self/mirror/replay/stand.
- Web parity QA can use armor stand screenshots.
- Fewer hidden exceptions.

Cons:

- Existing Quest inspection placement can shift.
- Stand floor lift/yaw/pitch/scale still prevents exact visual equality.
- More risk near exhibition if current stand looks acceptable.

### Option B - Armor Stand Remains Quest-Rig Inspection

Keep armor stand offset in `quest_rig`, but make this explicit in diagnostics and docs.

Pros:

- Lower risk for exhibition.
- Preserves current workshop behavior.
- Avoids over-claiming visual parity from an inspection mode.

Cons:

- Web parity flag does not mean all Quest modes use Web fields.
- Operators must judge wearing fit in mirror/replay, not armor stand.

Recommendation:

For exhibition, use Option B unless a fresh evidence pack proves armor stand is the primary parity proof surface. For platform cleanup after exhibition, move to Option A if the team wants one resolver across every display mode.

## Proposed Implementation Order

1. Add `viewer/shared/runtime-placement-resolver.js` with pure vector and placement functions.
2. Move/duplicate no behavior initially; write tests against current resolver output using fixture placements.
3. Replace Web helpers:
   - `isRuntimePlacementRecord`
   - `runtimePlacementMatchesPreviewVariant`
   - `runtimeTargetSizeForPreviewPart`
   - `runtimeOffsetForPreviewPart`
   - `runtimeRotationForPreviewPart`
4. Replace Quest helpers:
   - `targetSizeArrayFromPlacement`
   - `runtimePlacementOffsetArrayForPart`
   - `runtimePlacementRotationArray`
   - diagnostic offset comparison logic
5. Decide armor stand policy and either:
   - route `armorStandRigPoseForPart()` through the resolver
   - or record `displayMode: "quest_armor_stand"` with `mode: "quest_rig"` as an intentional exception
6. Add a fixture parity test:
   - same placement record
   - Web mode returns Web offset/rotation
   - Quest mode returns Quest offset/rotation
   - Web parity mode returns Web offset/rotation inside Quest
   - surface clamps match `armor-canon.js`
7. Only then remove old duplicate helpers.

## Test Strategy

Add tests before implementation:

- `tests/test_runtime_placement_resolver_contract.py`
  - validates fixture records for Web, Quest, and Web parity modes
  - asserts z sign conversion behavior
  - asserts clamp source selection
  - asserts rotation sign policy
  - asserts diagnostics include source fields

Keep existing tests:

- `tests/test_body_surface_policy_parity.py`
- `tests/test_armor_forge_variant_payload.py`
- `tests/test_quest_recall_render_contract.py`
- `tests/test_runtime_package.py`

Do not replace integration tests with resolver unit tests. The resolver only proves field selection; Web/Quest still need scene-level evidence.

## Acceptance Criteria

A resolver unification PR is acceptable when:

- Web Forge still renders the same selected parts for a known fixture.
- Quest default `quest_rig` output matches pre-refactor output for the same runtime package.
- Quest `web_preview_parity` output matches Web offset/rotation/target selection by construction.
- Diagnostics name mode, target size source, offset source, rotation source, and selected placement identity.
- Armor stand policy is explicit and tested.
- `runtime-render-placement.v1` remains the single selected placement record shape.
- `armor-canon.js` remains the owner of surface clamp policy, not duplicated tables.

## Review Position

Do not share scene code. Share resolver semantics.

The right shared boundary is a pure resolver that turns a `runtime-render-placement.v1` record plus mode into:

```js
{
  placement,
  mode,
  targetSizeM,
  offsetM,
  offsetSpace,
  rotationRad,
  rotationSpace,
  scale,
  diagnostics
}
```

Web and Quest should then apply that result in their own scene graphs. This keeps Web preview, Quest XR, armor stand, and future PlayCanvas aligned at the data-contract level without pretending their cameras, roots, body guides, and interaction modes are the same.

## Implemented Cut - 2026-05-05

The first shared resolver cut is now in `viewer/shared/runtime-placement-resolver.js`.

Implemented pure functions:

- `isRuntimeRenderPlacementRecord(value)`
- `resolveRuntimePlacementMode({ placement, webPreviewParity })`
- `resolveRuntimeTargetSize({ placement, fallback, mode })`
- `resolveRuntimeOffset({ part, placement, mode })`
- `resolveRuntimeRotation({ placement, mode })`
- `runtimePlacementMatchesIdentity({ part, placement, selectedVariantKey, assetRef })`

Current usage:

- Web Forge uses the resolver for runtime placement record detection, target size, offset, and rotation in preview mode.
- Quest uses the resolver for mode selection, target size, offset, and rotation while keeping scene-specific rig/armor stand application local.
- `armor-canon.js` remains the clamp owner through `clampSurfaceOffsetForPart(part, offset, "vrm" | "quest")`.

Remaining follow-up:

- Move Quest diagnostic raw source comparisons into the resolver once fixture coverage is added.
- Decide whether armor stand should consume `quest_rig`, `web_preview_parity`, or its own explicit `quest_armor_stand` display mode.
- Add numeric fixture tests for one representative placement record across Web, Quest, and Quest web-preview parity modes.
