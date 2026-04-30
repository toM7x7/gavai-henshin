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

2026-04-30 clarification: the base suit is the VRM surface texture, not a plain single-color underlayer. It should carry the toku-suit surface design: rubber/fabric grain, panel seams, fine geometric linework, color blocking, and glow guides. It must look intentional in the gaps between overlay parts.

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

2026-04-30 clarification: overlay parts are additional parts on top of the base suit, not the entire suit. Nanobanana should be prompted with a whole-suit `unified_design` first, then split the motif across `base_suit_surface` and `armor_overlay_parts` so the generated result does not look like unrelated toppings on a plain body.

### Variant And Topping Minimal Metadata

To prepare for branching parts and add-on toppings without changing the canonical 18 module keys yet, modeler handoff notes and future sidecars may record:

- `part_family`: broad category such as `helmet`, `chest`, `shoulder`, `arm`, `waist`, `leg`, or `boot`.
- `variant_key`: replacement style within a family, such as `sleek`, `heavy`, `tech`, `organic`, or `heroic`.
- `base_motif_link`: the base-suit line, panel, or color motif the overlay must continue.
- `topping_slots`: named add-on mount points such as `crest`, `visor_trim`, `chest_core`, `shoulder_fin`, `belt_buckle`, or `shin_spike`.
- `conflicts_with`: variants or toppings that should not be combined because they collide or overfill the silhouette.

This keeps current runtime compatibility while giving the generation prompt a path toward branchable armor choices.

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
- Job split: `model_rebuild_job` is the blocking track for body fit and mesh rebuilding; `texture_probe_job` is allowed only as a Nano Banana speed check and temporary write-back path on seed/proxy meshes. A generated part record reports `provider_profile=nano_banana`; `source=nano_banana_*` means a Nano Banana job produced a texture, while `source=cache` or `source=fallback_asset` means reuse and must not be presented as newly generated output.
- Fallback assets are preview/recovery inputs only. Even when the model quality gate passes, the backend does not write a fallback asset into `modules[*].texture_path` as a final Nano Banana texture.
- Generation summaries expose `texture_generation_summary.status_counts`, `generated_now_count`, and `final_texture_writeable_count`; fallback assets are counted as `fallback_asset_reused` and never contribute to final writeable counts.
- Planned quality gates: mesh bounds, fit clearance, UV contract, and Quest recall readiness must stay visible before the suit is treated as exhibition-ready. Texture quality remains warning-only until the asynchronous generation job completes.

This deliberately separates "the suit is issued and recallable" from "final generated surface assets are complete." The public Web flow can issue a code immediately, then advance texture generation asynchronously without breaking Quest recall.

### Visual Layer Data Contract

The API must make the visual split explicit in saved SuitSpec generation data and in public responses. This is the guard against a generated suit that recalls successfully but renders as only the baseline VRM.

`POST /v1/suits/forge`, its nested `preview`, and `GET /v1/quest/recall/{recallCode}` expose:

- `visual_layers.contract_version = base-suit-overlay.v1`.
- `visual_layers.base_suit.layer_id = base_suit_surface`.
- `visual_layers.base_suit.kind = vrm_body_surface`.
- `visual_layers.base_suit.role = body_conforming_substrate`.
- `visual_layers.base_suit.asset_ref` points to the VRM/body baseline.
- `visual_layers.armor_overlay.layer_id = armor_overlay_parts`.
- `visual_layers.armor_overlay.kind = multi_part_mesh_overlay`.
- `visual_layers.armor_overlay.role = visible armor collection`.
- `visual_layers.armor_overlay.selected_parts` is the enabled overlay module list.
- `visual_layers.armor_overlay.part_count` is the selected overlay count.

The matching `render_contract` is runtime-facing and deliberately blunt:

- `required_layers = ["base_suit_surface", "armor_overlay_parts"]`.
- `vrm_only_is_valid = false`.
- `base_suit_surface_required = true`.
- `armor_overlay_required = true`.
- `minimum_visible_overlay_parts = 3`.
- `required_overlay_parts = ["back", "chest", "helmet"]`.
- `missing_required_overlay_parts` must be empty before the suit is considered generated correctly.

Runtime adapters may still choose their own rendering stack, but they should treat this contract as the import checklist: load the body surface, then load visible overlay parts. A recall that has a manifest but zero visible overlay parts is an invalid generated-suit state, not a successful minimal render.

Quest recall normalizes the runtime manifest from the latest SuitSpec before returning it. If asynchronous texture generation has written `modules[*].texture_path` after the original manifest projection, the recall response projects those surface fields back into `manifest.parts[*]` so the runtime package does not split mesh placement from surface data.

### Forge Save Gate

Before saving a Web Forge suit, the API checks that every enabled overlay part has:

- `asset_ref`
- `attachment_slot`
- `vrm_anchor`

The required overlay core is `helmet`, `chest`, and `back`; user-selected parts are added on top. This keeps the base VRM from becoming the only visible generated artifact even when the request supplies a very small `parts` list.

## Fit-First Platform Boundary

The fitting mechanism is the root contract. Three.js, PlayCanvas, and Unity should consume the same `SuitSpec`/`SuitManifest`/PartCatalog facts instead of each inventing armor placement:

- Current Three.js Web Forge: verification lane for VRM baseline, declared height, and T-pose armor stand preview. It must use VRM bone/body measurements before showing overlay parts.
- Future PlayCanvas surface: browser preview/editor adapter for the same manifest and GLB outputs. It may provide nicer editing UX, but it is not the authoring source of truth.
- Future Unity/OpenXR surface: Quest runtime adapter for transformation, tracking, mirror/replay, and exhibition-grade input. It should consume prepared manifests and assets rather than generating or correcting them live.

The next model-quality milestone is therefore `VRM measurement -> body surface/mounts -> overlay bounds -> UV/texture job`. Texture generation should not be treated as final until the fit and mount gates are good enough to keep parts on the human body.

### Authoring Audit Snapshot

Latest local audit: 2026-04-27, `authoring-audit --mode current`.

- Result: `rebuild 11 / tune 3 / keep 4`.
- Wave 1 P0 rebuild/tune focus: `chest`, `back`, `waist`, `left_upperarm`, `right_upperarm`, `left_forearm`, `right_forearm`.
- Immediate interpretation: the current `mesh.v1` files are acceptable as seed/proxy preview parts, but they are not yet the final surface target for Nano Banana texture work.
- Web Forge may still run texture generation as a speed check and temporary texture write-back path, but the final texture lock is blocked by the model-quality gate: `mesh_fit_before_texture_final`.
- Public Web Forge readiness now keeps Quest recall available while exposing `model_quality_ready=false`, `final_texture_ready=false`, and `exhibition_ready=false` until the model rebuild gate passes.

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
