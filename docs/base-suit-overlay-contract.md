# Base Suit + Armor Overlay Contract

Updated: 2026-04-27

## Purpose

The new route should treat the body as a stable fitting substrate first, then add armor overlays on top of it. The lore stays the same: Web establishes the suit, Quest performs the transformation trial, and replay preserves the experience. The implementation boundary changes so the system can grow without forcing every generated part to solve full-body fit on its own.

## Current Baseline

- Base VRM exists at `viewer/assets/vrm/default.vrm`.
- VRM baseline measurements exist at `viewer/assets/vrm/baselines.json`.
- Current armor assets are 18 `mesh.v1` seed parts under `viewer/assets/meshes`.
- Current authoring source is `SuitSpec`; runtime projection is `SuitManifest`.
- `surface_attachment_preview` is telemetry only. It reports whether a part can be explained by surface regions and mounts, but it does not move Quest runtime parts yet.

## Identity Boundary

- `suit_id` remains the durable internal ID, for example `VDA-AXIS-OP-00-0001`.
- `recall_code` is the public Quest input code. It is exactly four uppercase alphanumeric characters, for example `A1B2`.
- `recall_code` is not authentication. It is a short exhibition/operator lookup key.
- Dashboard and storage may use full `suit_id`; Quest should prefer `GET /v1/quest/recall/{recallCode}`.
- Quest recall should read an already prepared suit and manifest. PC/dashboard is responsible for issuing IDs, saving SuitSpec, and creating the manifest.

## Authoring Layers

### Base Suit

The base suit is the body-conforming layer. It should absorb fit-sensitive elements:

- inner suit silhouette
- continuous torso/limb material
- gloves or sleeves when they need deformation
- low-frequency texture fields
- surface glow lines that must follow the body

This layer belongs to VRM/body-fit and future surface shell work. It should not be rebuilt as many rigid mesh parts unless there is a clear hard-surface silhouette reason.

### Armor Overlay

The overlay is the replaceable outer armor. It should carry:

- helmet shell and visor
- chest plate and back unit
- shoulder armor
- forearm gauntlets
- waist belt or buckle
- shin guards and boot exterior
- hand back plates or knuckle plates

These parts may remain rigid, mounted, and visually expressive. They should be generated, audited, and stored as parts.

## Canonical Part Split

Keep the current 18 canonical module keys as the compatibility surface:

`helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`, `left_hand`, `right_hand`, `left_thigh`, `right_thigh`, `left_shin`, `right_shin`, `left_boot`, `right_boot`.

Rebuild direction:

- Keep as overlay first: `helmet`, `chest`, `back`, `waist`, `left_shoulder`, `right_shoulder`, `left_forearm`, `right_forearm`, `left_shin`, `right_shin`, `left_boot`, `right_boot`.
- Move toward base suit first: `left_upperarm`, `right_upperarm`, `left_thigh`, `right_thigh`, broad glove surfaces.
- Treat hands as hybrid: base glove plus optional outer hand plate.

## Asset Rules

Current `mesh.v1` files are seed/proxy assets, not the final authoring ceiling. The next asset standard should add:

- stable `part_id`
- `wear_layer`: `base_suit`, `outer_shell`, `hardpoint`, or `terminal`
- `attachment_slot`
- local pivot and forward/up axes
- bounds and scale unit
- material slots such as `base_surface`, `accent`, `emissive`, `trim`
- UV contract per part
- optional `surface_attachment` expectation with region and mount name

Future GLB/glTF assets should preserve those fields through metadata or sidecar JSON.

## Dashboard Flow

1. Issue internal `suit_id` and four-character `recall_code`.
2. Save or update `SuitSpec`.
3. Project `SuitManifest`.
4. Show the T-pose armor-stand preview.
5. Display the Quest input code prominently.
6. Use Quest preflight to confirm that the suit can be recalled.

The dashboard can be redesigned, but this contract should remain visible: base suit, overlay parts, armor stand, recall code.

## Standalone Web Forge

The standalone Web forge is the public-facing slice of the same route. It should not expose the full internal dashboard. Its job is narrower:

1. Ask for a display name, protection archetype, palette, generation brief, and selected overlay parts.
2. Call `POST /v1/suits/forge`.
3. Receive a ready `suit_id`, four-character `recall_code`, SuitSpec, and SuitManifest.
4. Render the T-pose armor stand immediately.
5. Provide the Quest recall URL based on the same `recall_code`.

This page is allowed to generate a template-based suit before the full AI texture pipeline is complete. The preview must still respect the base suit plus overlay distinction: the fitted base is the substrate, and selected modules are the visible armor overlay.

## Quest Flow

1. Visitor or operator enters `recall_code`.
2. Quest calls `/v1/quest/recall/{recallCode}`.
3. The scene imports the prepared suit with an import/standby animation.
4. Transformation starts from first-person view.
5. Mirror/observer replay uses recorded motion where available.

Quest should not overwrite SuitSpec for a recalled suit. If no manifest is ready, Quest should stop with a clear "manifest not ready" state.

## Quality Gates

- Mesh quality: valid positions, normals, UVs, indices, bounds, and non-degenerate triangles.
- Fit quality: base suit follows VRM/body proxy; overlay stays within mount/clearance policy.
- UV quality: base suit is seam-safe and low-frequency; overlay reserves hero motif zones.
- Runtime quality: `recall_code` lookup works, manifest exists, and Quest can create a trial without rewriting authoring data.
