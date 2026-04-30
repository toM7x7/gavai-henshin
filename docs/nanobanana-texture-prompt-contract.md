# Nanobanana Texture Prompt Contract

Updated: 2026-04-30

## Purpose

This document is the source of truth for the Nano Banana only texture generation route.
It connects Web Forge inputs, modeler metadata, generated texture outputs, SuitManifest linkage, and Quest recall asset pointers.

The goal is not to paint isolated parts.
The goal is to generate one bright tokusatsu hero suit that Web can preview as a T-pose armor stand and Quest can recall as the same equipped suit.

Canonical contract names:

- texture provider: `nano_banana`
- texture contract: `nanobanana-texture-prompt.v1`
- visual layer contract: `base-suit-overlay.v1`
- base layer: `base_suit_surface`
- overlay layer: `armor_overlay_parts`
- generation unit: `unified_design`

## Non-Negotiable Visual Rules

### Base Suit

`base_suit_surface` is a completed body suit texture mapped onto the VRM surface.
It is not an underlayer placeholder.
It is not a plain single-color undersuit.
It must be readable as the finished body-conforming hero suit in the gaps between armor parts.

Required base suit qualities:

- body-following rubber, fabric, or synthetic suit texture
- panel seams that flow from neck to torso, arms, hips, legs, and boots
- fine geometric linework that is visible but not noisy
- deliberate color blocking using the suit palette
- glow guide lines that can connect into overlay emissive zones
- joint-area continuity at neck, shoulders, elbows, wrists, hips, knees, and ankles

### Armor Overlay

`armor_overlay_parts` are hard GLB armor overlays mounted on top of the VRM body surface.
They must receive and continue the base suit motif.
They must not look like unrelated sci-fi decorations placed over a plain body.

Required overlay qualities:

- hard-surface silhouette for helmet, chest, back, shoulders, waist, forearms, shins, boots, and selected parts
- bevels, trims, ribs, panel edges, and cores that align with `base_motif_link`
- primary/accent/emissive color grammar shared with the base suit
- material zones that can route to `base_surface`, `accent`, `emissive`, and `trim`
- clear distinction between soft body-conforming surface and hard armor shell

### Unified Design

`unified_design` is generated first.
The prompt must define the whole hero before splitting work into base suit and armor textures.

The split order is:

1. Decide the whole-suit visual grammar.
2. Assign low-frequency continuous motifs to `base_suit_surface`.
3. Assign hard silhouette, trims, cores, and topping anchors to `armor_overlay_parts`.
4. Export texture asset pointers back into SuitSpec/SuitManifest for Web and Quest.

## Input Parameters

The Web Forge request and modeler handoff must provide enough context to write a stable prompt.

| Input | Source | Required | Prompt role |
|---|---|---:|---|
| `protect_target` | Web Forge | yes | Defines what the hero protects, such as city, child, shrine, team, archive, memory, or performer. This sets motif symbolism. |
| `temperament` | Web Forge | yes | Defines personality, such as bright, brave, calm, agile, guardian, ceremonial, or tactical. This sets shape and contrast. |
| `height_cm` | Web Forge / body fit | yes | Guides scale language and texture density. Taller suits may use longer vertical lines; shorter suits need stronger silhouette separation. |
| `palette.primary` | Web Forge | yes | Main color family. Must appear on both base suit and overlays. |
| `palette.accent` | Web Forge | yes | Secondary color. Used for trims, motif repeat, and part-to-part continuity. |
| `palette.emissive` | Web Forge | yes | Glow color. Used for guide lines, core marks, masks, and Quest recall effects. |
| `brief` | Web Forge | yes | User-facing flavor text. Convert it into motifs, not literal clutter. |
| `selected_parts` | Web Forge | yes | Canonical overlay modules enabled for generation and manifest linkage. |
| `part_family` | modeler metadata | P0 yes | Groups variants and prompt targets by helmet, chest, shoulder, arm, waist, leg, boot, etc. |
| `variant_key` | modeler metadata | P0 yes | Chooses replacement style within a family, such as `sleek`, `heavy`, `winged`, `tech`, `organic`, or `heroic`. |
| `base_motif_link` | modeler metadata | P0 yes | Names the exact base-suit line, panel, or glow guide that an overlay continues. |
| `topping_slots` | modeler metadata | P0 yes | Names optional add-on locations like `crest`, `visor_trim`, `chest_core`, `shoulder_fin`, `belt_buckle`, or `shin_spike`. |
| `conflicts_with` | modeler metadata | when applicable | Prevents mutually destructive variants or toppings from entering a single prompt. |

Recommended Web-facing Japanese labels:

- 守る対象 -> `protect_target`
- 気質 -> `temperament`
- 身長 -> `height_cm`
- パレット -> `palette`
- 生成メモ -> `brief`
- 選択外装 -> `selected_parts`

## Prompt Structure

Every final prompt must be assembled in this order.

```text
system intent:
  Generate a bright tokusatsu hero suit as one unified design.
  The base suit is a complete VRM body-surface texture, not a plain undersuit.
  Armor overlay parts are hard shells integrated with the base suit motif.

user inputs:
  protect_target: <value>
  temperament: <value>
  height_cm: <value>
  palette: primary=<value>, accent=<value>, emissive=<value>
  brief: <value>
  selected_parts: <canonical module list>

unified_design:
  Define the hero motif, color grammar, material contrast, readable silhouette, and glow logic.

base_suit_surface:
  Body-conforming completed suit texture.
  Include rubber/fabric grain, panel seams, geometric linework, color blocking, and glow guides.
  Explicitly forbid a single-color undersuit.

armor_overlay_parts:
  Hard armor textures for selected canonical modules.
  Continue the base motif through trims, bevels, color panels, and emissive lines.
  Use modeler metadata: part_family, variant_key, base_motif_link, topping_slots, conflicts_with.

output_requirements:
  Produce base suit texture, armor part textures, emissive masks, manifest linkage, and Quest recall asset pointers.

negative:
  dark, gritty, horror, muddy, single-color underwear, plain undersuit, random sci-fi panel noise,
  unrelated armor decorations, gray proxy material, transparent guide boxes, bbox visuals,
  low contrast, dirty realism, post-apocalyptic grime.
```

## Output Contract

Texture generation produces assets and linkage data.
The suit is not final until both are present.

| Output | Required | Consumer | Notes |
|---|---:|---|---|
| `base_suit_texture` | yes | Web Forge, Quest | Texture for the VRM body surface. Must be a complete body suit design. |
| `armor_part_textures` | yes for selected parts | Web Forge, Quest | Per-module or atlas texture pointers for selected canonical GLB overlays. |
| `emissive_mask` | yes | Web Forge, Quest effects | Mask or texture channel that identifies glow lines, cores, visors, and power guides. |
| `material_zone_map` | yes | renderer, QA | Maps generated images to `base_surface`, `accent`, `emissive`, and `trim`. |
| `manifest_linkage` | yes | SuitManifest projection | Writes texture pointers into the manifest parts/layers that Quest recalls. |
| `quest_recall_asset_pointers` | yes | `GET /v1/quest/recall/{recallCode}` | Runtime-ready pointers for base suit surface, overlay textures, emissive masks, and selected part modules. |
| `generation_summary` | yes | Web Forge UI, operator QA | Reports provider, status counts, generated-now count, fallback reuse count, and final writeability. |

Recommended shape:

```json
{
  "texture_contract_version": "nanobanana-texture-prompt.v1",
  "provider_profile": "nano_banana",
  "visual_layers": {
    "base_suit_surface": {
      "texture_path": "generated/base_suit/albedo.png",
      "emissive_mask_path": "generated/base_suit/emissive.png",
      "material_zone_map_path": "generated/base_suit/zones.json"
    },
    "armor_overlay_parts": [
      {
        "module": "chest",
        "texture_path": "generated/armor/chest/albedo.png",
        "emissive_mask_path": "generated/armor/chest/emissive.png",
        "base_motif_link": "chest_v_glow_line",
        "variant_key": "heroic",
        "topping_slots": ["chest_core", "rib_trim"]
      }
    ]
  },
  "manifest_linkage": {
    "writes_suitspec": true,
    "writes_manifest": true,
    "quest_recall_asset_pointers_ready": true
  }
}
```

The exact file paths may differ by storage backend.
The contract requirement is that Web preview and Quest recall can load the same generated surface assets from the saved SuitSpec/SuitManifest lineage.

## Web Forge Connection

Web Forge is the input and preview surface.
It must:

1. Collect `protect_target`, `temperament`, `height_cm`, `palette`, `brief`, and `selected_parts`.
2. Attach modeler metadata for selected modules when available.
3. Build the `unified_design` prompt before requesting per-layer output.
4. Save the generation summary and asset pointers with the generated suit.
5. Preview both `base_suit_surface` and `armor_overlay_parts`.
6. Keep `final_texture_ready=false` until Nano Banana generated assets are written, even if fallback assets are shown temporarily.

Web must not present fallback/cache/proxy textures as final Nano Banana output.

## Modeler Handoff Connection

Modeler metadata keeps prompts stable across variants and toppings.
For P0 modules, handoff data must include:

- `part_family`
- `variant_key`
- `base_motif_link`
- two or more `topping_slots`
- `conflicts_with` when a variant or topping would collide

Modeler preview images should show where `base_motif_link` enters the overlay.
For example, a chest V-line from the base suit can enter the chest plate edge, continue into `chest_core`, and echo at the waist buckle.

## Quest Recall Connection

Quest does not generate textures.
Quest recalls prepared suit data.

`GET /v1/quest/recall/{recallCode}` must expose asset pointers that let the runtime load:

- base VRM asset
- `base_suit_surface.texture_path`
- selected overlay GLB module asset refs
- selected overlay texture paths
- emissive masks or channels
- material zone maps when needed by the renderer

If asynchronous Nano Banana generation finishes after initial suit issue, Quest recall should project the latest saved texture pointers into the returned manifest.
This prevents a suit from being recallable but visually reverting to the baseline VRM or placeholder armor.

Quest import validity:

- valid: base VRM + generated base suit texture + required overlay modules + overlay textures
- provisional: base VRM + overlay modules + planned texture job, with `final_texture_ready=false`
- invalid as final: base VRM only
- invalid as final: plain single-color base suit plus unrelated overlay textures

## Negative Prompt Contract

Always include negative prompt coverage for:

- dark
- gritty
- horror
- muddy
- single-color underwear
- plain undersuit
- random sci-fi panel noise
- unrelated armor decorations
- gray proxy material
- transparent guide boxes
- bbox visuals
- low contrast
- dirty realism
- post-apocalyptic grime
- exposed unfinished skin where suit texture should exist

The route is allowed to be dramatic, but not grim.
It should read as bright, inspectable, exhibition-ready hero gear.

## QA Checklist

Before setting `final_texture_ready=true`, verify:

- The base suit is not single-color and not underwear-like.
- Base suit lines continue across neck, torso, arms, hips, legs, and boots.
- Overlay trims and emissive zones continue named `base_motif_link` motifs.
- Selected parts have texture pointers or explicit planned status.
- Emissive mask exists for glow guides, visor/core marks, or equivalent effect zones.
- Quest recall returns the same asset pointers Web Forge preview saved.
- Fallback/cache/proxy assets are not counted as final generated output.

This checklist is separate from mesh fit.
Mesh fit can pass while texture unity still fails.
