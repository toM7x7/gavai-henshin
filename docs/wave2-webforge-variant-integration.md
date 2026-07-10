# Wave 2 Web Forge Variant Integration

Date: 2026-05-01

Scope: progress note for Web Forge integration after the Wave 2 modeler
deliverables were brought onto the main line. This is coordination only; no
runtime implementation decision is made here.

## Current Position

Wave 2 should now be treated as asset-delivered, not only contract-ready.

- Modeler output present in the local tree: 54 variant GLBs and 32 topping GLBs.
- Smoke evidence exists for `helmet:sleek`, `helmet / crest / base`,
  `chest + back`, and the full P0 suit views.
- The catalog and sidecar contract from `docs/armor-build-wave2-results.md`
  remains the integration baseline: 18 canonical modules, variant keys,
  topping slots, conflict metadata, prompt hints, and Web Forge status fields.
- Web Forge integration is therefore at the handoff boundary: assets exist, but
  user-facing selection, preview routing, prompt finalization, and QA evidence
  still need to prove that those assets are actually being used.

The important distinction is:

- Canonical armor load is already proven by `previewGlbParts=18` and
  `previewFallbackParts=0`.
- Variant/topping inventory is present, but Web Forge must still prove selected
  variant and topping GLB paths replace or augment the canonical view as
  intended.

## Confirmation Points

Use these as the short review frame for the next Web Forge pass.

1. Inventory
   - Confirm 54 variant GLBs are discoverable under
     `viewer/assets/armor-parts/<module>/variants/<asset_key>/`.
   - Confirm 32 topping GLBs are discoverable under
     `viewer/assets/armor-parts/<parent>/toppings/<slot>/<key>/`.
   - Confirm each delivered GLB has the matching `.modeler.json` sidecar.

2. Identity
   - Confirm UI and manifests keep catalog keys such as `helmet:sleek`.
   - Confirm filesystem slugs use only the asset segment such as `sleek`.
   - Confirm canonical module IDs remain stable; variants do not create new
     attachment slots.

3. Preview
   - Confirm a selected variant uses its variant GLB instead of the canonical
     module GLB.
   - Confirm a selected topping appears as an add-on and can be toggled without
     hiding or replacing the parent module.
   - Confirm front, side, back, and 3Q views are enough to catch silhouette,
     clipping, and density issues.

4. Metadata
   - Confirm Web Forge surfaces selected variant key, selected topping count,
     conflicts, and readiness flags.
   - Confirm prompt fields preserve `base_motif_link`, `texture_zone_notes`,
     `variant_prompt_summary`, and `surface_design_hints`.
   - Confirm conflict warnings are visible before final texture generation or
     Quest recall handoff.

5. Visual QA
   - Check that chest/back/waist read as outer armor shell, not flat decals.
   - Check shoulders, upper arms, shins, and boots keep enough body volume.
   - Check toppings remain readable when turned off and on.
   - Track the known Wave 2.1 geometry warnings separately from Web Forge
     integration blockers.

## Ask The Modeler Next

Request modeler work only where the asset or visual contract is still the
source of truth.

- Provide closeup render coverage for representative variants and toppings,
  using the existing smoke views as the first acceptance examples.
- Add or verify sidecar evidence for every delivered variant/topping:
  bbox, triangle count, material zones, coordinate frame, and slot data where
  available.
- Prioritize geometry refinement for the known tolerance warnings:
  chest z depth, waist x width, upperarm x width, and shin x width.
- Clarify any topping slot where placement is still inferred rather than backed
  by a final local transform.
- Nominate a small P0 visual-review set for Web Forge smoke:
  `helmet:sleek`, one chest variant, one back variant, one waist topping, and
  one left/right mirrored limb pair.

## Engineer First

Engineering should prove consumption before asking for more art volume.

- Add Web Forge verification that selected variant keys resolve to delivered
  GLB paths.
- Add Web Forge verification that selected toppings resolve to delivered GLB
  paths and do not replace the parent module.
- Extend the smoke checklist from canonical-only GLB loading to selected
  variant/topping loading.
- Keep manifest IDs anchored to canonical modules while recording selected
  `variant_key` and topping selections as metadata.
- Gate Nanobanana final prompt generation on selected variant/topping metadata
  being present and conflict-free.

## What To Look At

For a user review, start with these artifacts in this order.

1. `docs/modeler-handoff-2026-05-01.md`
   - Confirms the modeler-side smoke commands, 54/32 deliverable counts, and
     rendered evidence paths.

2. `docs/_smoke_renders/`
   - Use these images for fast visual sanity: helmet, chest/back, and full P0
     suit views.

3. `viewer/assets/armor-parts/_masters/full_suit_front.png`
   `viewer/assets/armor-parts/_masters/full_suit_side.png`
   `viewer/assets/armor-parts/_masters/full_suit_back.png`
   `viewer/assets/armor-parts/_masters/full_suit_3q.png`
   - Confirm the full suit reads as armor mass and not just body texture.

4. `viewer/assets/armor-parts/helmet/variants/sleek/`
   - Use as the first variant path sanity check.

5. `viewer/assets/armor-parts/helmet/toppings/crest/base/`
   - Use as the first topping path sanity check.

6. Web Forge preview once the engineering pass is ready
   - Confirm selected variant/topping status, visible conflict state, and
     fallback-free GLB preview.

## Decision Summary

The next milestone is not "make more variants." It is "prove that Web Forge can
select, show, report, and pass through one representative variant/topping set
without breaking canonical armor loading." Once that is true, modeler time
should go into closeup evidence, slot transform certainty, and Wave 2.1 shape
refinement.
