# Armor Build Wave 1 Results

Updated: 2026-04-30

## Purpose

This file records the local acceptance check for the modeler Wave 1 completion response.

## Local Inventory

- `viewer/assets/armor-parts` contains 18 armor module directories: `back`, `chest`, `helmet`, `left_boot`, `left_forearm`, `left_hand`, `left_shin`, `left_shoulder`, `left_thigh`, `left_upperarm`, `right_boot`, `right_forearm`, `right_hand`, `right_shin`, `right_shoulder`, `right_thigh`, `right_upperarm`, `waist`.
- Each module has `<module>.glb`, `<module>.modeler.json`, `source/<module>.blend`, `preview/<module>.mesh.json`, and 4 preview PNGs.
- No `*.blend1` files were found under `viewer/assets/armor-parts`.
- `_masters` exists and contains `review_master.blend`.

## Claimed vs Local

| Modeler response item | Local status | Note |
|---|---|---|
| 18 modules | Present | All expected runtime modules are present. |
| intake pass | Confirmed | `tools/validate_armor_parts_intake.py` returned `status=pass`. |
| bbox within +/-9% | Not confirmed | Fit audit still returns `status=warn`; several sidecar bbox deltas exceed 9%. |
| `docs/armor-build-wave1-results.md` | Missing at audit start | Created by this acceptance audit. |
| `docs/armor-part-fit-modeler-requests.before.md` | Missing | Not found in `docs`. |
| `_masters/full_suit_*.png` | Missing | `_masters` has `review_master.blend` only. |
| per-part preview PNGs | Present | 4 PNGs per module: front/back/side/3q. |

## Tool Results

```bash
python tools/validate_armor_parts_intake.py
# ok=true, status=pass, part_count=18, missing_parts=[]

python tools/audit_armor_part_fit_handoff.py --format json
# ok=true, status=warn, part_count=18, total_triangles=12052
# material_zone_counts: accent=18, base_surface=18, emissive=3, trim=13
```

## Next Acceptance Gate

- Require full-suit preview images under `viewer/assets/armor-parts/_masters/full_suit_*.png`.
- Require a before snapshot when overwriting modeler request docs: `docs/armor-part-fit-modeler-requests.before.md`.
- Treat `validate_armor_parts_intake.py` as package/schema intake only; use fit audit deltas and preview images before accepting bbox claims.
