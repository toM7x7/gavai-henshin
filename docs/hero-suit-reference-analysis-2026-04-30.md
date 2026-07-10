# Hero Suit Surface-Fit Reference Analysis

Date: 2026-04-30

Purpose: reset the Web Forge direction from "GLB parts placed around a VRM" to "a tokusatsu-style bodysuit with body-wrapped armor shells." This document is the design bridge between lore, Web preview QA, and modeler handoff.

Concept sheet: [hero-suit-surface-fit-concept.svg](assets/hero-suit-surface-fit-concept.svg)

## Current Problem

The current preview can pass asset/metadata checks while still failing as a hero suit. The failure mode is not "missing GLB"; it is that the parts read as props floating around a person.

Observed failures:

- Boots read as flat floor objects or forward slabs, not footwear.
- Waist reads as a front bucket/ring, not a pelvis belt loop.
- Back reads thin or detached, not a dorsal shell with scapula/lumbar continuity.
- Base suit is still too close to a single-color body fill. It needs generated paneling and motif lines that agree with armor parts.
- Numeric bbox gates do not catch side-view costume failure.

## Reference Takeaways

Practical costume/foam references converge on the same rule: fit and patterning decide believability before material finish. EVA foam guides emphasize body/dress-form patterning, mockups, heat-shaping, segmentation at joints, and coherent motif rules before final paint.

Relevant references:

- Popverse, "Cosplay: How to texture EVA foam to upgrade your cosplayer game": foam is light and comfortable, but texture/detail must be deliberately added through heat, carving, layering, and paint. <https://www.thepopverse.com/cosplay-texture-foam-eva-armor-plexi>
- Instructables, "Introduction to EVA Foam": body-fit patterning, shoulder-piece construction, and layered foam details are practical precedents for our body-surface-first workflow. <https://www.instructables.com/Introduction-to-EVA-Foam/>
- Kamen Rider official "HENSHIN by KAMEN RIDER" concept: transformation can be reinterpreted through wearable fashion and motif continuity, which supports treating the base suit as a designed garment rather than a blank body fill. <https://www.kamen-rider-official.com/news_articles/1075>
- Community suit-design analysis is not a source of canon, but it usefully frames the visual grammar we need to test: bodysuit visibility, chest/shoulder emphasis, belt identity, helmet silhouette, and high-contrast motif readability.

## Design Rule

The new Web route should treat the generated suit as three layers:

1. **VRM body / fit target**: anatomical reference only.
2. **Base bodysuit surface**: generated texture on the VRM surface. This is the tokusatsu undersuit, not a separate armor part.
3. **Armor shells and toppings**: body-wrapped hard-surface modules that attach to known anatomical zones.

This means the base suit must carry motif lines, color blocks, seam logic, and glow paths. Armor parts should repeat that motif and sit above it with small clearances.

## Acceptance Shifts

The previous acceptance was too close to "file exists and bbox roughly matches." The new acceptance must include costume-readability checks:

- Side view: chest, waist, back, shin, and boots must stay near the corresponding body surface.
- Boots: bottom surface is grounded; toe/heel/ankle cuff/upper shin socket are all visible.
- Waist: front, side, and rear sections form one pelvis loop; it must not be a forward bucket.
- Back: dorsal shell has shoulder blade pads, spine keel, and lumbar clasp; thin plates fail.
- Joints: shoulders, elbows, knees, ankles keep intentional negative space for motion, not accidental gaps.
- Motif: base suit lines and armor accent lines share color, direction, and rhythm.

## Modeler Drawing Requests

Ask for simple, measurable sheets before final sculpt detail:

- Full-body front/side/back at 170cm reference height.
- Side silhouette with floor, center line, and boot contact patch.
- Torso cross-sections at upper chest, lower ribs, waist, and pelvis.
- Back shell sheet showing scapula pads, spine keel, lumbar clasp, and side returns.
- Waist belt loop sheet showing front/side/back wrap and allowed protrusion.
- Boot sheet showing sole plane, toe cap, heel cap, ankle cuff, shin socket, and ground footprint.
- Part-local origin, +X/+Y/+Z, inner surface, outer surface, and contact plane for every GLB.

## Implementation Notes

Web Forge should no longer consume `attachment_offset_target_m` as a placement vector. It is a scalar limit. Placement should use `vrm_attachment.offset_m` / `attachment_offset_m`; target limit should be used for QA.

Immediate implementation decisions:

- Copy full modeler sidecar metadata into preview modules so Web can see `body_follow_profile`, `ground_contact_profile`, `topping_slots`, `variant_key`, `shell_thickness_target_m`, and `clearance_m`.
- Clamp worn placement by part type:
  - back: rear-only depth near torso surface
  - waist: small pelvis-loop protrusion
  - boots: ground-first, very small forward/back depth
  - chest: modest forward shell depth
- Introduce Web QA datasets for boot float, continuity gaps, back thickness, and waist gap.

## Current Implementation Status

2026-04-30 implementation notes:

- Web Forge now separates placement vectors from scalar offset limits. `attachment_offset_target_m` is a QA limit, not a position.
- Preview records receive modeler sidecar metadata, while saved SuitSpec modules stay schema-compatible for Quest recall.
- Boots are grounded before final placement so they do not read as floor props.
- Chest, waist, back, and boots use part-type surface clamps instead of raw bbox centering.
- `back` was regenerated after the first Wave 1++ build exposed an actual GLB depth failure. Back bbox z changed from approximately `0.110m` to `0.135m`, against a target of `0.136m`.
- Verification after the back rebuild: Web GLB smoke `18/0`, armor intake fail `0`, focused pytest `72 passed`.

## Nano Banana Prompt Direction

The texture prompt should not ask for "armor texture on every part" in isolation. It should ask for a unified hero suit material system:

> Bright tokusatsu rescue hero suit, fitted base bodysuit on human form, coherent panel lines flowing from helmet to chest to boots, hard armor shells with matching trim, luminous cyan/green accent channels, clean toy-like production finish, no battle damage, no medieval plate, no loose floating props.

Negative constraints:

- no disconnected box props
- no oversized bucket waist
- no flat shoe slabs
- no thin backpack plate
- no random texture per part

## Current Priority Order

1. Web preview placement and QA: make side view catch failure.
2. Base suit generated texture: use VRM surface as the tokusatsu undersuit.
3. Boots and waist: ground/contact and pelvis loop first.
4. Back: dorsal shell thickness and lumbar connection.
5. Modeler P1 handoff: replace provisional primitives with real sculpted shells.
6. Topping library: add variations after the base silhouette reads correctly.
