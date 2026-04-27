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

1. Ask for a display name, declared height, protection archetype, palette, generation brief, and selected overlay parts.
2. Call `POST /v1/suits/forge`.
3. Receive a four-character `recall_code`, readiness flags, and public preview data; SuitSpec and SuitManifest are stored internally for Quest recall.
4. Render the T-pose armor stand immediately from the public preview, using the Body Fit baseline VRM where available and declared height as the first body-scale parameter.
5. Show only the Quest input code and Quest recall action on the public page.
6. Explain that local development has two surfaces: dashboard/API on `8010`, Quest VR runtime on Vite `5173`.

This page is allowed to generate a template-based suit before the full AI texture pipeline is complete. The preview must still respect the base suit plus overlay distinction: the fitted base is the substrate, and selected modules are the visible armor overlay.

Internal `suit_id` and `manifest_id` remain required for storage, versioning, DB rows, and artifact paths. They should not be primary public UI. Cloud SQL should later hold suit/version rows, while public Quest lookup remains the short `recall_code`.

## Web Forge Asset Generation Contract

The Web forge now emits an `asset_pipeline` contract alongside the public preview. It keeps the lore route intact while preparing the next generation lane:

- Model substrate: VRM baseline body-fit first, then the 18 canonical overlay part keys.
- Shape contract: current `mesh.v1` overlay assets remain seed/proxy parts; validated GLB/glTF is a derived runtime artifact after fit and bounds checks.
- Fit status: `preview_vrm_bone_metrics` means the Web Forge armor stand is using the baseline VRM bones/body measurements for preview placement, but a saved fit-audit artifact is still the next gate.
- Texture provider: `nano_banana` provider profile, using Gemini-backed image generation through the existing `part_generation.py` provider abstraction.
- Texture mode: `mesh_uv` with UV guide references, `uv_refine=true`, 2K square atlases, and SuitSpec texture write-back as the intended job default.
- Surface status: `planned_not_generated` means the Web forge has issued a suit and generated the job contract, but it has not yet produced final texture atlases or written `texture_path` fields.
- Planned quality gates: mesh bounds, fit clearance, UV contract, and Quest recall readiness must stay visible before the suit is treated as exhibition-ready. Texture quality remains warning-only until the asynchronous generation job completes.

This deliberately separates "the suit is issued and recallable" from "final generated surface assets are complete." The public Web flow can issue a code immediately, then advance texture generation asynchronously without breaking Quest recall.

## Fit-First Platform Boundary

The fitting mechanism is the root contract. Three.js, PlayCanvas, and Unity should consume the same `SuitSpec`/`SuitManifest`/PartCatalog facts instead of each inventing armor placement:

- Current Three.js Web Forge: verification lane for VRM baseline, declared height, and T-pose armor stand preview. It must use VRM bone/body measurements before showing overlay parts.
- Future PlayCanvas surface: browser preview/editor adapter for the same manifest and GLB outputs. It may provide nicer editing UX, but it is not the authoring source of truth.
- Future Unity/OpenXR surface: Quest runtime adapter for transformation, tracking, mirror/replay, and exhibition-grade input. It should consume prepared manifests and assets rather than generating or correcting them live.

The next model-quality milestone is therefore `VRM measurement -> body surface/mounts -> overlay bounds -> UV/texture job`. Texture generation should not be treated as final until the fit and mount gates are good enough to keep parts on the human body.

## Quest Flow

1. Visitor or operator opens the Quest runtime page and enters `recall_code`; in VR this is available from the left-hand spatial menu.
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
