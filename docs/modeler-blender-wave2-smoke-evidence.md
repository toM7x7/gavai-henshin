# Wave 2 Blender CLI Smoke Evidence

Generated: 2026-05-01 (worktree `jovial-cohen-4bf60f`)

This document captures the artifacts produced by running the Wave 2 modeler
guide (`docs/modeler-blender-wave2-operation-guide.md`) end-to-end against the
worktree using the new CLI subcommands of
`tools/blender/run_variant_pipeline.py`.

## 1. Pre-flight (no Blender)

```text
$ python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots
[PASS] viewer\assets\armor-parts\variant_catalog.json
validated 18 module(s)

$ python tools\blender\run_variant_pipeline.py validate
ok=True variants=38 slots=55 errors=0 warnings=55

$ python tools\blender\run_variant_pipeline.py dry-run --kind all
ok=True planned_variants=24 planned_toppings=16
```

(`warnings=55` are slot_transform-inferred notices for catalog slots that lack
an explicit `slot_transform` field — non-blocking.)

## 2. Step 1 — One Variant Smoke (`helmet:sleek`)

```powershell
$BLENDER = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- `
    build-variant --module helmet --variant-key helmet:sleek
```

Result excerpt:
```json
{
  "ok": true,
  "paths": {
    "glb":     "viewer\\assets\\armor-parts\\helmet\\variants\\sleek\\helmet__sleek.glb",
    "blend":   "viewer\\assets\\armor-parts\\helmet\\variants\\sleek\\source\\helmet__sleek.blend",
    "sidecar": "viewer\\assets\\armor-parts\\helmet\\variants\\sleek\\helmet__sleek.modeler.json",
    "preview_mesh": "viewer\\assets\\armor-parts\\helmet\\variants\\sleek\\preview\\helmet__sleek.mesh.json"
  },
  "triangles": 480,
  "errors": []
}
```

All four expected artifacts are on disk under `helmet/variants/sleek/`.

## 3. Step 2 — One Topping Smoke (`helmet/crest/base`)

```powershell
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- `
    build-topping --parent-module helmet --topping-slot crest --topping-key base
```

Result excerpt:
```json
{
  "ok": true,
  "paths": {
    "glb":     "viewer\\assets\\armor-parts\\helmet\\toppings\\crest\\base\\helmet__crest__base.glb",
    "blend":   "viewer\\assets\\armor-parts\\helmet\\toppings\\crest\\base\\source\\helmet__crest__base.blend",
    "sidecar": "viewer\\assets\\armor-parts\\helmet\\toppings\\crest\\base\\helmet__crest__base.modeler.json",
    "preview_mesh": "viewer\\assets\\armor-parts\\helmet\\toppings\\crest\\base\\preview\\helmet__crest__base.mesh.json"
  },
  "triangles": 108,
  "errors": []
}
```

All four expected artifacts are on disk under `helmet/toppings/crest/base/`.

## 4. Step 5 — Full P0 Batch (`build-p0 --kind all --topping-key base`)

Filesystem after the run:
```text
$ find viewer/assets/armor-parts -path "*/variants/*/*.glb" | wc -l
54
$ find viewer/assets/armor-parts -path "*/toppings/*/*/*.glb" | wc -l
32
```

(54 variant GLBs and 32 topping GLBs — covers the new catalog plus carry-over
from the earlier session's variant set.)

## 5. Step 6 — Post-Build Checks

```text
$ python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots
[PASS] viewer\assets\armor-parts\variant_catalog.json   18/18

$ python tools\blender\run_variant_pipeline.py validate
ok=True  variants=38  slots=55  errors=0  warnings=55

$ python tools\validate_armor_parts_intake.py
INTAKE: status=warn  reasons=0  warnings=6

$ python tools\smoke_web_glb_load.py
previewGlbParts=18  previewFallbackParts=0

$ python -m pytest tests\test_armor_part_variant_catalog.py \
                   tests\test_validate_variant_catalog.py \
                   tests\test_variant_topping_intake.py -q
15 passed in 0.11s
```

The only intake `warnings` are the known Wave 2.1 shape-refinement notes
(`upperarm x`, `shin x`) flagged as acceptable in the operation guide.

## 6. Canonical sidecar Wave 2 metadata refresh

After the canonical 18 modules were rebuilt with the synced
`run_module_pipeline.py`, every committed sidecar now carries the Wave 2
fields:
- `conflicts_with: []`
- `texture_zone_notes: { ... }` (`base_surface`, `accent`, `emissive`, `trim`)
- `topping_slots[]` with `parent_module`, `slot_transform.{anchor,rotation_deg}`,
  `max_bbox_m.{x,y,z}`, `conflicts_with`

This is what unblocks `test_committed_modeler_sidecars_include_wave2_metadata`,
bringing the pytest suite from 14/15 to **15/15**.

## 7. Runtime contract preserved

Smoke verifier reports `previewGlbParts=18 previewFallbackParts=0` after the
rebuild — every canonical module still resolves to a `.glb` (no fallback to
`.mesh.json`). Module IDs and required sidecar fields listed in the operation
guide's "Runtime Contract To Preserve" section are intact.

## 8. Next handoff

Per the modeler operation guide, when the modeler returns the JSON outputs
from the two smoke commands plus generated directory listing and the Step 6
screenshots, the engineering side will wire the Web Forge UI to the freshly
delivered variant/topping pointers. The ground for that is already in place:

- `armor_glb_asset_ref(module, repo_root)` in `src/henshin/forge.py` resolves
  `<module>.glb` for each canonical module (variant pointers go through the
  same path once SuitSpec gains a `module.variant_key` field).
- `tools/smoke_web_glb_load.py` already reports per-module pass/fail and would
  add `selected_variant_key` and `topping_slot` columns once the SuitSpec
  surface exposes them.

## 9. Auxiliary artifact

A small wrapper `tools/blender/_run_canonical_build.py` was added so the
canonical 18-module rebuild can be invoked via:
```powershell
& $BLENDER --background --python tools\blender\_run_canonical_build.py
```
Useful when reapplying the Wave 2 sidecar fields after a builder update.
