# Web Forge per-part texture/UV contract plan

Date: 2026-05-05

## Goal

Web Forge surface generation must be inspectable per armor part. The generation job can still use the existing payload shape, but each selected part now carries a local texture contract under:

```text
surface_design_hints.per_part_texture_contracts.<part>
```

The same records are projected into the runtime package at:

```text
per_part_texture_contracts.<part>
visual_layers.armor_overlay.per_part_texture_contracts.<part>
render_contract.per_part_texture_contract_parts
runtime_checks.per_part_texture_contract_parts
```

## Contract fields

Each part record uses `contract_version: web-forge-per-part-texture.v1`.

Required inspection fields:

- `part`: canonical module id, for example `helmet`.
- `selected_variant_key`: selected Web Forge variant, for example `helmet:sleek`.
- `provider_profile`: currently locked to `nano_banana`.
- `texture_prompt_contract`: currently `nanobanana-texture-prompt.v1`.
- `texture_mode`: normally `mesh_uv`.
- `asset_ref`: selected GLB, fallback GLB, remote GLB, or seed/proxy mesh JSON.
- `shape_role`: body-surface role, anchor/contact intent, and fit basis.
- `uv_availability`: whether final mesh-UV texture generation is allowed.
- `uv_policy`: resolved UV engineering policy for motif zones, seam safety, fill, and panel flow.
- `material_hints`: material zones and sidecar material language.
- `texture_prompt`: per-part prompt fragment used as the local authority above whole-suit summary text.

## Asset cases

### GLB with modeler sidecar and UV

Case id: `glb_with_modeler_sidecar_uv_contract`

Use when a local GLB is present and its `.modeler.json` sidecar can be read. If the sidecar reports `qa_self_report.non_overlapping_uv0` as `pass` or `warn`, `can_generate_mesh_uv_texture` remains true. The prompt may request final mesh-UV atlas generation.

### GLB fallback/unavailable

Case id: `glb_fallback_unavailable_for_final_texture`

Use when the selected asset is a local GLB path but the runtime surface gate cannot validate it, for example missing or corrupt GLB. The prompt contract records the GLB failure and sets `can_generate_mesh_uv_texture: false`. This allows preview/proxy workflows, but final texture lock is blocked.

### mesh JSON seed/proxy

Case id: `mesh_json_seed_proxy_no_authoritative_uv`

Use when `asset_ref` points to `*.mesh.json` or another JSON seed/proxy asset. This is preview geometry, not an authoritative UV0 target. The contract sets `uv0_status: not_applicable` and `can_generate_mesh_uv_texture: false`. Prompt text must say the part has no final mesh-UV authority.

### UV unavailable/no asset

Case id: `uv_unavailable_no_asset_ref`

Use when no asset reference exists. The contract sets `uv0_status: missing` and `can_generate_mesh_uv_texture: false`. Prompt text may still describe a concept surface, but must not imply final UV texture lock.

### Remote GLB

Case id: `glb_without_local_sidecar_uv_unknown`

Use when a GLB cannot be inspected locally, including remote URLs. Runtime does not reject the asset surface gate solely because it is remote. UV status remains `unknown`; adapters should require provider/runtime validation before treating it as a final lock.

## Prompt rules

Provider prompts append a `Web Forge per-part texture contract:` block. That block must include:

- selected variant;
- asset surface case and format;
- shape role and contact intent;
- `uv0_status` and `mesh_uv_allowed`;
- primary motif zone, low-frequency zone, and panel flow;
- material zones and material language.

The whole-suit prompt remains useful for continuity, but the per-part block is the local authority for texture generation on that module.

## Test coverage

Fixed tests:

- missing local GLB produces `glb_fallback_unavailable_for_final_texture` and blocks mesh-UV final texture generation;
- mesh JSON seed/proxy produces `mesh_json_seed_proxy_no_authoritative_uv` and blocks mesh-UV final texture generation;
- explicit UV-unavailable contract is appended to both dry-run prompt and refine prompt;
- existing explicit per-part contract remains projected through runtime package.

## Current capability split

### Can do now

- Attach one inspectable contract per selected armor part without changing the existing Web Forge API shape.
- Preserve `provider_profile: nano_banana` while adding per-part local authority under `surface_design_hints.per_part_texture_contracts`.
- Carry the selected `part`, `variant`, `shape_role`, `uv_availability`, `uv_policy`, `material_hints`, and `texture_prompt` into the runtime package.
- Add a `Web Forge per-part texture contract:` block to provider prompts and refine prompts so dry-run output can be inspected without running the provider.
- Distinguish final mesh-UV texture eligibility from concept/preview surface generation with `can_generate_mesh_uv_texture`.
- Keep mesh JSON seed/proxy and GLB fallback cases visible as concept surface targets while blocking final texture lock.
- Expose the same contract through runtime package fields used by diagnostics and future UI reads.

### Cannot infer from GLB fallback or mesh JSON

- `mesh_json_seed_proxy_no_authoritative_uv` cannot prove UV0 islands, texel density, material slots, seam placement, or non-overlap. It is only a seed/proxy shape.
- `glb_fallback_unavailable_for_final_texture` cannot be treated as a final texture target because the local GLB is missing, corrupt, or otherwise blocked by the runtime surface gate.
- `glb_without_local_sidecar_uv_unknown` can be displayed, but cannot prove final UV lock until provider/runtime validation inspects the actual GLB.
- Prompt text alone cannot visually prove that a motif aligns to a real UV island; it can only describe intent and policy.
- The current Web Forge UI can show surface job readiness, mock surface, and model quality gate state, but it does not yet surface every per-part UV lock reason as a dedicated operator row.

## Acceptance criteria

- Runtime package and texture job payloads keep one contract for every selected/enabled armor part.
- Every contract includes `asset_surface_case`, `asset_format`, `uv0_status`, and `can_generate_mesh_uv_texture`.
- Provider prompts contain the per-part block and must mention selected variant, asset surface case, shape role, `uv0_status`, `mesh_uv_allowed`, UV policy, and material hints.
- Whole-suit prompts are continuity context only; per-part blocks are the local authority for texture generation.
- When `can_generate_mesh_uv_texture: false`, final texture lock is blocked and the part may only receive concept/preview surface treatment.
- `mesh_json_seed_proxy_no_authoritative_uv` and `glb_fallback_unavailable_for_final_texture` must not be collapsed into a generic "planned" state in diagnostics.
- `provider_profile: nano_banana` remains unchanged unless the user explicitly switches provider profile.
- Remote GLB with `uv0_status: unknown` may remain runnable for preview/probe, but acceptance requires a visible "UV unverified" distinction before final lock.

## Prompt granularity

- Whole suit: continuity, palette, silhouette language, shared energy-line vocabulary, and exhibition identity.
- Part block: part-local authority for motif placement, shape role, material zones, and UV policy.
- Variant: exact selected Web Forge variant key and short variant summary, for example `helmet:sleek`.
- Shape role: body-surface role such as head shell, chest frontal shell, back plate, shoulder cap, forearm guard, or shin guard.
- UV availability: exact asset surface case plus `uv0_status` and `mesh_uv_allowed`.
- UV policy: primary motif zone, low-frequency zone, panel flow direction, seam safety, and fill strategy.
- Material hints: base material, accent material, emissive zones, roughness/metalness intent, and provider-facing material language.

## UV lock unavailable display copy

Use these as Web Forge operator-facing copy when the UI consumes `per_part_texture_contracts`.

- Short badge: `UVロック不可`
- mesh JSON detail: `仮メッシュのため最終UVが未確定です。表面生成はコンセプト確認のみで、本番テクスチャ固定はGLB/UV確認後に実行してください。`
- GLB fallback/missing detail: `GLBを検査できないためUVロック不可です。モデル納品またはGLB修復後に表面生成を本番化してください。`
- Remote GLB unknown detail: `リモートGLBのUVは未検査です。表示は可能ですが、最終テクスチャ固定前にUV検査が必要です。`
- Disabled final-lock tooltip: `UV0未確認のため本番テクスチャ固定はできません`
- Surface row: `表面: コンセプト可 / UV固定不可`
- Reason row examples: `理由: mesh_json seed proxy`, `理由: GLB fallback unavailable`, `理由: remote GLB UV unknown`

## UI acceptance notes

- The quick surface action may remain available for preview/probe when the job payload is present, but it must not imply final texture readiness when any selected part has `can_generate_mesh_uv_texture: false`.
- Support diagnostics should show selected part count, UV-lockable part count, and blocked part count.
- A part blocked by mesh JSON or GLB fallback should display concept eligibility separately from final texture lock eligibility.
- Mock surface preview should read as provisional; it should not change `SuitSpec texture_path` or report final lock.
- The operator should be able to inspect the exact `asset_surface_case` for each blocked part without opening provider logs.

## Surface gate and render placement parity

Surface gate, render placement, and texture lock are separate runtime decisions:

- Surface gate answers whether the selected overlay asset can participate in the runtime suit surface.
- Render placement answers where the part should be anchored and clamped for Web and Quest.
- Texture lock answers whether a generated surface may be written as a final mesh-UV texture.

Acceptance rules:

- `render_placements.<part>` must be emitted for every enabled overlay part, even when the part later fails the runtime surface gate.
- `visual_layers.armor_overlay.render_placements.<part>` must match the root `render_placements.<part>` record.
- `render_contract.render_placement_parts` must describe placement coverage, not only visible/surface-gate-passing parts.
- A part that fails surface gate must appear in `runtime_checks.runtime_surface_failures` and `runtime_checks.invalid_overlay_parts`; required failures must block `can_render_runtime_suit`.
- Surface gate failure must not erase placement evidence. Operators still need the placement record to debug Web/Quest alignment and asset intake.
- Web preview must use `coordinate_space: vrm_humanoid_local_y_up_z_front` with `surface_offset_clamped_m`.
- Quest recall must use `quest_coordinate_space: quest_rig_local_y_up_z_back` with `quest_surface_offset_clamped_m`.
- Both Web and Quest clamped offsets must mirror `surface_anchor.offset_clamped_m` and `surface_anchor.quest_rig_offset_clamped_m`.
- `per_part_texture_contracts.<part>.asset_ref` and `render_placements.<part>.asset_ref` must refer to the same selected asset.
- `mesh_json_seed_proxy_no_authoritative_uv` may pass the runtime surface gate as preview geometry, but must still set `can_generate_mesh_uv_texture: false`.
- `glb_fallback_unavailable_for_final_texture` must fail surface gate and final texture lock, while retaining placement for diagnostics.
- `glb_without_local_sidecar_uv_unknown` may pass local surface gate for preview/probe, but remains UV-unverified until a provider/runtime UV validation step records a stronger status.
- Web/Quest parity must not use final texture lock as a renderability signal, and must not use renderability as final texture lock evidence.

Display implication:

- Runtime blocked: `モデル表面Gate不可 / 配置契約あり / Quest表示不可`
- Preview only: `表示可 / UVロック不可 / 本番テクスチャ未固定`
- Remote unverified: `表示可 / UV未検査 / 固定前に検査`
