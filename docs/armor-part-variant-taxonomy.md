# Armor Part Variant Taxonomy

This document defines a static taxonomy for future fine-grained armor parts,
micro details, toppings, and variant selection. The machine-readable source is:

```text
viewer/assets/armor-parts/variant_catalog.json
```

The catalog is intentionally read-only design data. It does not change the
current Web Forge runtime, GLB loading path, or modeler sidecar format by
itself.

## Goals

- Keep the canonical 18 armor parts as the parent contract.
- Let generation and Web preview tooling reason about smaller optional details.
- Reserve stable slot identifiers before adding multiple GLB variants.
- Make each slot bounded by count, anchor, size, material zone, and examples.
- Support mirrored left/right parts without merging them into one runtime ID.

## Canonical Parent Parts

The parent part IDs remain:

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

Each catalog entry lives under `modules.<part_id>`. A right-side part may
declare mirror-related variants later, but it still owns explicit right-side slot
records so tools can address it without implicit mirroring logic.

## Slot Shape

Each slot has this shape:

```json
{
  "topping_slot": "visor_trim",
  "slot_kind": "detail",
  "allowed_count": { "min": 0, "max": 1 },
  "anchor_hint": {
    "body_anchor": "head",
    "parent_surface": "front_upper",
    "placement": "horizontal band across eye line"
  },
  "max_bbox_m": { "x": 0.25, "y": 0.075, "z": 0.04 },
  "material_zone": "lens",
  "variant_examples": [
    "single slit visor",
    "dual eye lens",
    "wraparound tactical visor"
  ]
}
```

Field meanings:

- `topping_slot`: Stable semantic key for the local slot. It must match P0
  required slot names where the acceptance spec defines them.
- `slot_kind`: One of `micro`, `detail`, or `topping`.
- `allowed_count`: Inclusive min/max count for generated children in the slot.
- `anchor_hint`: Semantic placement hint, not a final transform.
- `max_bbox_m`: Maximum local envelope in meters for a single child item.
- `material_zone`: Preferred material or texture zone name.
- `variant_examples`: Three promptable examples for generation or modeler briefs.

## Slot Kinds

`micro` is for small repeated trim, pads, slats, tread pieces, and socket lips.
These should not dominate the silhouette.

`detail` is for visible but bounded subparts such as a face plate, chest core,
rear core, cuff, toe cap, heel, or palm emitter.

`topping` is for optional silhouette accents such as crests, fins, short vanes,
spikes, wrist modules, and compact add-ons. Toppings must obey their max bbox
and should not become full wings, weapons, or loose floating props.

## Required Coverage By Family

The current catalog reserves slots for:

- Helmet: face plate, visor, crest.
- Chest: chest core, rib trim, collar guard.
- Back: spine ridge, rear core, rear vane.
- Waist: belt buckle, side clip, hip skirt.
- Shoulders: shoulder fin, edge trim.
- Upper arms: bicep band, outer plate.
- Forearms: forearm cuff, wrist module.
- Hands: knuckle, palm emitter.
- Thighs: outer guard, knee socket trim.
- Shins: shin spike, ankle cuff.
- Boots: toe, heel, sole, ankle socket.

## Future Integration Notes

Generation can treat the catalog as a capability list:

1. Pick a parent part from `canonical_parts`.
2. Read `modules[part].topping_slots`.
3. Filter by requested `slot_kind`, `material_zone`, or `slot_key`.
4. Generate zero or more child details within `allowed_count`.
5. Keep each generated child inside `max_bbox_m`.
6. Attach generated children using `anchor_hint` plus the parent sidecar
   transform.

Web preview can use the same data to display unavailable slots, count selected
toppings, and preflight whether a requested child part can fit inside the parent
without inventing runtime-specific naming.

Modeler sidecars can later refer to these slots with a compact field such as:

```json
{
  "topping_slots": [
    {
      "topping_slot": "toe_fin",
      "variant_key": "left_boot:sleek"
    }
  ]
}
```

That future sidecar shape is only an example. The current catalog deliberately
does not require runtime support.
