# Modeler Blender Operation Guide - Wave 2

Date: 2026-05-01

This guide is for the modeler who can run Blender locally and operate the generated armor assets.

## Goal

Produce Wave 2 variant and topping GLB deliverables from the current catalog while preserving the runtime contract used by Web Forge and Quest.

The current code side is ready for:

- Canonical armor parts: 18 modules.
- Variant catalog: 38 variants.
- Topping slots: 55 slots.
- P0 build target: helmet, chest, back, waist, left/right shoulder, left/right shin.
- Runtime output: glTF 2.0 `.glb` plus `.modeler.json`, `.blend`, and preview mesh JSON.

## Repository

Work in:

```powershell
C:\dev\codex\gavai-henshin
```

Before Blender work, run these checks from PowerShell:

```powershell
cd C:\dev\codex\gavai-henshin
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
python tools\blender\run_variant_pipeline.py validate
python tools\blender\run_variant_pipeline.py dry-run --kind all
```

Expected:

- `validate_variant_catalog.py`: `status` is `pass`.
- `run_variant_pipeline.py validate`: `ok` is `true`.
- `dry-run`: lists planned variant/topping output paths.

## Blender Path

If `blender` is not on PATH, use the full path. Typical Windows examples:

```powershell
$BLENDER = "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
```

or:

```powershell
$BLENDER = "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
```

Check:

```powershell
& $BLENDER --version
```

## Important Blender Invocation Rule

Use `--background --python <script> -- <command args>`.

The second `--` is important. It separates Blender's own arguments from the armor pipeline arguments.

## Step 1 - One Variant Smoke Test

Build one helmet variant first:

```powershell
cd C:\dev\codex\gavai-henshin
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- build-variant --module helmet --variant-key helmet:sleek
```

Expected output:

```text
"ok": true
```

Expected files:

```text
viewer/assets/armor-parts/helmet/variants/sleek/helmet__sleek.glb
viewer/assets/armor-parts/helmet/variants/sleek/helmet__sleek.modeler.json
viewer/assets/armor-parts/helmet/variants/sleek/source/helmet__sleek.blend
viewer/assets/armor-parts/helmet/variants/sleek/preview/helmet__sleek.mesh.json
```

If this fails, stop and send the JSON error plus traceback back to the engineering side.

## Step 2 - One Topping Smoke Test

Build one helmet topping:

```powershell
cd C:\dev\codex\gavai-henshin
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- build-topping --parent-module helmet --topping-slot crest --topping-key base
```

Expected files:

```text
viewer/assets/armor-parts/helmet/toppings/crest/base/helmet__crest__base.glb
viewer/assets/armor-parts/helmet/toppings/crest/base/helmet__crest__base.modeler.json
viewer/assets/armor-parts/helmet/toppings/crest/base/source/helmet__crest__base.blend
viewer/assets/armor-parts/helmet/toppings/crest/base/preview/helmet__crest__base.mesh.json
```

## Step 3 - P0 Variant Batch

After both smoke tests pass:

```powershell
cd C:\dev\codex\gavai-henshin
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- build-p0 --kind variants
```

Expected P0 variant count:

- 8 P0 modules.
- 3 variants each.
- 24 variant outputs.

P0 modules:

```text
helmet
chest
back
waist
left_shoulder
right_shoulder
left_shin
right_shin
```

## Step 4 - P0 Topping Batch

Then build P0 topping assets:

```powershell
cd C:\dev\codex\gavai-henshin
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- build-p0 --kind toppings --topping-key base
```

Expected P0 topping count:

- 31 topping slots.
- One `base` topping per slot.

## Step 5 - Full P0 Batch Alternative

If the smoke tests are clean and you want one command:

```powershell
cd C:\dev\codex\gavai-henshin
& $BLENDER --background --python tools\blender\run_variant_pipeline.py -- build-p0 --kind all --topping-key base
```

## Step 6 - Post-Build Checks

After generating assets, run:

```powershell
cd C:\dev\codex\gavai-henshin
python tools\validate_variant_catalog.py --strict-mirror-of --strict-recommended-slots --report-json
python tools\blender\run_variant_pipeline.py validate
python tools\validate_armor_parts_intake.py
python tools\smoke_web_glb_load.py
python -m pytest tests\test_armor_part_variant_catalog.py tests\test_validate_variant_catalog.py tests\test_variant_topping_intake.py -q
```

Expected:

- Catalog validation remains `pass`.
- Intake has no `reasons`.
- Web GLB smoke still reports `previewGlbParts=18 previewFallbackParts=0`.
- Tests pass.

Geometry warnings are acceptable for now if they are the known Wave 2.1 shape refinement warnings:

```text
chest z depth
waist x width
left/right upperarm x width
left/right shin x width
```

Do not block on those unless a new fail/reason appears.

## Visual Review Tasks

Open the generated `.blend` files or import the generated `.glb` files and check:

- Helmet variants are not a plain smooth mask. They need visible face panels, visor structure, cheek/jaw separation, and crest/line continuity.
- Chest/back/waist read as worn armor, not floating boards.
- Shoulder and shin variants preserve left/right symmetry.
- Toppings are small add-on shapes, not replacements for the parent armor.
- Parts should leave enough body silhouette readable, but should not feel sparse or empty.
- The base suit motif should be readable as a continuous hero suit underneath.

## Runtime Contract To Preserve

Do not rename these module IDs:

```text
helmet
chest
back
waist
left_shoulder
right_shoulder
left_upperarm
right_upperarm
left_forearm
right_forearm
left_hand
right_hand
left_thigh
right_thigh
left_shin
right_shin
left_boot
right_boot
```

Do not remove these sidecar fields:

```text
contract_version
asset_kind
module / parent_module
variant_key / topping_slot / topping_key
base_motif_link
topping_slots
conflicts_with
texture_zone_notes
bbox_m
triangle_count
material_zones
coordinate_frame
```

For canonical parts, also preserve:

```text
vrm_attachment
attachment_offset_target_m
qa_self_report
```

## Handoff Back To Engineering

Please send back:

1. The command you ran.
2. The final JSON output from the command.
3. A list of generated directories.
4. Screenshots of:
   - helmet variant front/side
   - chest + back on body
   - full P0 suit front/side/back
5. Any manual Blender edits made after generation.

## Current Known Limitation

The pipeline creates procedural Wave 2 assets. It is good for contract validation and first playable previews.

For final visual quality, the modeler should still improve:

- richer face/helmet segmentation
- less plain body paneling
- stronger chest/back wrap volume
- better boot/shin silhouette
- coherent motif flow between base suit texture and armor panels

Those improvements should be fed back as updated GLB/Blend assets while preserving the filenames and sidecar contract above.
