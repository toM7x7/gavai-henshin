# Armor Build Wave 2 Results

Date: 2026-05-01

## Current Status

Wave 2 is now integrated as a runtime and authoring contract, not yet as fully built variant GLB deliverables.

The local repository now has:

- `viewer/assets/armor-parts/variant_catalog.json`: 18 modules, 38 variants, 55 topping slots.
- Strict catalog validation passing with `--strict-mirror-of --strict-recommended-slots`.
- Blender-free variant/topping pipeline validation and dry-run planning.
- Nanobanana prompt linkage from Web Forge into generation jobs and part generation prompts.
- Wave 2 sidecar metadata synced into the committed 18 canonical `.modeler.json` files.
- Web Forge UI contract for variant, topping, conflict, and visual-density status.

Actual variant/topping GLB builds were not run in this environment because `blender` is not available on PATH. The generated directory contract is ready for Blender/modeler output.

## Implemented Contract

### Variant Catalog

`viewer/assets/armor-parts/variant_catalog.json`

- 18 canonical armor modules.
- 38 total variant entries.
- 55 topping slots.
- Right-side modules now declare `mirror_of`.
- Boot variant recommended slots now reference existing catalog slots.
- Strict validator now returns `status=pass`.

### Variant/Topping Pipeline

`tools/blender/armor_variant_specs.py`

`tools/blender/run_variant_pipeline.py`

- Import-safe outside Blender.
- Validates catalog/spec consistency.
- Produces dry-run output paths for:
  - `viewer/assets/armor-parts/<module>/variants/<variant_slug>/<module>__<variant_slug>.glb`
  - `viewer/assets/armor-parts/<module>/toppings/<slot>/<key>/<module>__<slot>__<key>.glb`
- Real GLB/.blend building remains gated on Blender runtime availability.

### Sidecar Metadata

`tools/blender/armor_part_specs.py`

`tools/blender/armor_builder_core.py`

`tools/sync_armor_sidecar_metadata.py`

The committed canonical sidecars now include:

- `variant_key`
- `part_family`
- `base_motif_link`
- `topping_slots`
- `conflicts_with`
- `texture_zone_notes`
- `attachment_offset_target_m`

This prevents Web Forge from showing only shape/fit data while losing design intent, Nanobanana hints, and modeler-facing constraints.

### Nanobanana Linkage

`src/henshin/new_route_api.py`

`src/henshin/part_generation.py`

`src/henshin/dashboard_server.py`

Web Forge now sends these fields into the generation job payload:

- `texture_prompt_contract`
- `variant_prompt_summary`
- `surface_design_hints`

`part_generation.py` folds them into the effective generation brief so the texture prompt does not collapse back to a plain single-color undersuit.

## Verification

Commands run:

```powershell
python -m pytest -q
python -m pytest tests\test_armor_part_variant_catalog.py tests\test_armor_part_specs.py tests\test_validate_variant_catalog.py tests\test_variant_topping_intake.py tests\test_dashboard_server.py tests\test_new_route_api.py -q
node --check viewer\armor-forge\forge.js
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
python tools\blender\run_variant_pipeline.py validate
python tools\blender\run_variant_pipeline.py dry-run --kind all
python tools\sync_armor_sidecar_metadata.py --check --report-json
python tools\validate_armor_parts_intake.py
python tools\smoke_web_glb_load.py
```

Results:

- Full test suite: `219 passed, 86 subtests passed`.
- Wave 2 focused tests: `72 passed, 18 subtests passed`.
- Variant catalog strict validation: pass.
- Variant pipeline validation: pass.
- Sidecar metadata sync check: pass, 0 changed after sync.
- Web GLB smoke: `previewGlbParts=18 previewFallbackParts=0`.

Remaining warnings are geometry tolerance warnings, not contract failures:

- chest z depth: -12.7 percent from target.
- waist x width: -10.1 percent from target.
- left/right upperarm x width: -11.5 percent from target.
- left/right shin x width: -12.0 percent from target.

These should be handled as Wave 2.1 model-shape refinement, not as API/catalog blockers.

## Next Work

1. Run the variant/topping build path inside Blender and produce the first P0 GLB variants.
2. Add closeup renderers for variant and topping deliverables.
3. Let Web Forge select concrete variant keys and topping slots, not only display the catalog.
4. Feed selected variant/topping choices into Nanobanana texture generation as final prompt constraints.
5. Ask the modeler to focus on the remaining geometry warnings and on richer face/body panel density.
