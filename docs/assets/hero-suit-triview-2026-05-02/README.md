# Hero Suit Triview References - 2026-05-02

This folder stores the generated three-view reference sheets used for modeler handoff.

The images are concept references, not locked production blueprints. The fixed contract is the runtime split: base suit surface, canonical armor modules, variants, toppings, and sidecar metadata. The modeler may improve silhouette, panel cuts, materials, and construction as long as the delivered assets keep the Web/Quest intake contract.

Primary handoff documents:

- `docs/modeler-triview-handoff-2026-05-02.md`
- `docs/modeler-asset-intake-contract-2026-05-02.md`
- `docs/modeler-first-three-lines-order-2026-05-02.md`

Delivery manifest sample:

- `examples/modeler_delivery_manifest.sample.json`

## Sheets

| Sheet | Concepts | File |
|---|---|---|
| 01 | 01-03 | `sheet-01-concepts-01-03.png` |
| 02 | 04-06 | `sheet-02-concepts-04-06.png` |
| 03 | 07-09 | `sheet-03-concepts-07-09.png` |
| 04 | 10-12 | `sheet-04-concepts-10-12.png` |
| 05 | 13-15 | `sheet-05-concepts-13-15.png` |

## Concept List

| ID | Working Name | Motif | Recommended Use |
|---|---|---|---|
| `c01` | Royal Insect Guardian | insect / emerald / agile | helmet, chest, shoulder, back variant direction |
| `c02` | Rescue Knight Sleek | pearl white / cobalt / rescue armor | chest, shoulder, back, boot variant direction |
| `c03` | Memory Ninja Light | charcoal / gold seams / low profile | base suit motif, forearm, shin, back variant direction |
| `c04` | Dragon Scale Rescuer | ivory / crimson / scale ridges | helmet, shoulder, chest, shin variant direction |
| `c05` | Cyber Oath Runner | graphite / magenta cyan circuit | base suit texture, visor, forearm, boot direction |
| `c06` | Orbital Citizen Guardian | white silver / orange / compact back unit | helmet, back, belt, chest core direction |
| `c07` | Flame Oath Form | red white / amber / flame V | chest, shoulder, spine vent direction |
| `c08` | Water Stream Form | teal pearl / flowing shell | base suit, back fin, shin, shoulder direction |
| `c09` | Lightning Vector Form | yellow black / zigzag seams | helmet crest, chest split, boot, shin direction |
| `c10` | Beast Guardian | white violet / clean claw accents | helmet, forearm, boot, chest direction |
| `c11` | Avian Flight Form | sky white navy / wing line | shoulder fin, back, chest motif direction |
| `c12` | Ancient Relic Oath | ivory obsidian / turquoise inscriptions | chest core, belt, trim, texture direction |
| `c13` | Medical Rescue Hero | white mint / coral / sensor visor | public-facing rescue form, belt, chest, helmet |
| `c14` | Prototype Shadow Hero | black blue / amber one-eye / repaired edges | asymmetry study, damaged variant, internal seams |
| `c15` | Final Oath Form | pearl gold cyan / crown visor / dense glow | final-form silhouette, high-end hero variant |

## Fixed Design Language

- Bright tokusatsu hero, not dark military SF.
- Completed base bodysuit, not plain underwear.
- Armor sits on the body surface; do not deliver floating panels.
- Chest, back, and waist should read as a coherent torso system.
- Emissive lines should connect visor, chest core, belt, spine, shins, and boots.
- Organic curves are welcome, but each part also needs precise mechanical bevels and small readable angular cuts.
- The same motif should continue across base suit texture, armor overlay, and topping details.

## Runtime Split

Use the three-view sheets for visual direction, then deliver assets through the existing runtime split:

- `base_suit_surface`: texture / body panel design.
- `armor_overlay_parts`: the canonical 18 GLB modules.
- `variant`: a replacement shape for one canonical module while preserving the slot.
- `topping`: small optional add-on attached to a local slot on a parent module.

Do not change the canonical 18 module names, the current catalog order, or the `base` variant resolution when delivering new work.

## Intake Check

Before a delivered GLB set is activated in Web/Quest, create a delivery manifest and run:

```bash
python tools/validate_modeler_delivery_manifest.py --manifest examples/modeler_delivery_manifest.sample.json
```

The manifest is a staging receipt. It must not activate runtime assets directly.
