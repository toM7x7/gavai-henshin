# Wave 1 Auto-Rebuild Results

Generated: 2026-04-30 (worktree `jovial-cohen-4bf60f`)

## Headline metrics — before vs after

## Codex acceptance note

Wave 1+ is accepted as a mechanical asset-pipeline baseline, not as final hero-suit art.
The numeric gates now line up with the modeler response: intake pass, full-suit renders present, closeups present, and bbox deltas within the stated envelope.
Visual review still reads as procedural white proxy armor in several places, especially torso/shoulder/limb silhouette.
Next visual work should therefore focus on authored hero-suit silhouette, final materials, and Nanobanana texture integration rather than only bbox compliance.

| Metric | Baseline (prior session) | After Wave 1 overhaul |
|---|---:|---:|
| Intake validator | warn (18 backup files) | **pass** (0 reasons / 0 warnings) |
| Fit-handoff status | warn | warn (no axis exceeds 15% tol) |
| Modules with bbox bad-axis (>±15%) | **11 / 18** | **0 / 18** |
| Worst single-axis delta | back z **-50%** | back z **+6%** (max abs = 8.9%) |
| Mean abs bbox delta across all 54 axes | ~17% | **3.7%** |
| Median abs bbox delta | ~13% | **3.2%** |
| Total triangles (all 18 modules) | 12,052 | **6,484** (cleaner topology) |
| Material zones present | accent=18, base=18, emis=3, trim=13 | accent=18, base=18, emis=10, trim=10 |

Baseline = the table in `docs/armor-part-fit-modeler-requests.before.md` (snapshot of the previous session's GLBs against the new audit tool that was synced into the worktree from main).

## What was actually changed

### New / re-engineered tools
- `tools/blender/armor_builder_core.py` — added two procedural primitives:
  - `body_wrap_arc(chord_x, height_y, depth_z, arc_deg, front_bulge, segments, y_taper_top, y_taper_bottom, bevel_m)` — curved shell that wraps around the body cylinder (chord along x, vertical along y, arc opens toward +z). Has real thickness (inner + outer skin + caps). Used by chest, back, waist, shoulders, all limbs, hand and boot ankle.
  - `solid_shell` — thicker variant of `shell_quad` (kept for back-compat).
  Also fixed a long-standing 2x bug in `_scale_cube`: `bmesh.ops.create_cube(size=1.0)` already emits vertices at ±0.5, so multiplying by `sx*0.5` was producing AABBs HALF the requested size. Every existing rounded_box / wedge / trim_ridge panel previously came out half-sized in Blender — that was the root cause of the chronic z-axis deficits in the prior baseline. Fix is one line.
- `tools/blender/armor_part_specs.py` — overhaul of all 11 left/center module spec functions:
  - Torso (chest, back, waist) now use a primary `body_wrap_arc` curving around the ribcage / lumbar / pelvis. Back rotates 180° about Y so apex faces -Z.
  - Shoulder uses a 180° pauldron cap arc plus an insertion lip trim_ridge angled toward chest/back.
  - Limbs (upperarm, forearm, thigh, shin) use two `body_wrap_arc` segments split vertically, preserving elbow/knee/wrist articulation.
  - Hand has a knuckle wrap arc + bump for z-extent + wrist cuff + emissive line.
  - Boot has toe + heel rounded-box caps + ankle wrap arc + flat sole + instep emissive.
  - Helmet kept as bevelled rounded_box dome + visor band emissive + crest fin + ear vents + jaw trim.
  - Each spec function now starts with a `# target_envelope_m: ...` comment for fast comparison.
- `tools/blender/render_review.py` (+270 lines) — new public functions:
  - `render_full_suit(repo_root)` → loads master, attaches all 18 GLBs at their bone positions, renders four review angles + an overlay hero shot under `viewer/assets/armor-parts/_masters/full_suit_*.png`.
  - `render_module_closeup(module, repo_root)` → tight per-module camera at distance ≈ `max(dims)*4` aimed at the bbox center; writes `..._closeup_<view>.png`.
  - `render_closeups_all(repo_root)` → wraps the above for every module.
- `tools/check_armor_part_specs.py` + `tests/test_armor_part_specs.py` — static design-time spec checker (no Blender). Runs a per-primitive AABB heuristic, warns/fails on envelope overflow, missing zones, broken mirror references, > 3 zones. Catches design mistakes before a Blender round-trip.
- `tools/audit_armor_part_fit_handoff.py` and `tools/validate_armor_parts_intake.py` synced from main into the worktree so the same audit + intake gates the upstream brief uses are available locally.
- `tools/blender/run_module_pipeline.py` — `save_blend` adapter now toggles `save_version=0` and `compress=True` so no `.blend1` backup files get committed.

### Files unchanged (kept in line with prior session's contracts)
- `src/henshin/forge.py` (registry override `armor_glb_asset_ref`)
- `src/henshin/modeler_sidecar.py`
- viewer JS/HTML loaders
- `tools/blender/armor_builder_core.py` mirror_module (bmesh.ops.reverse_faces fix from prior session retained)

## Per-module bbox delta (final audit)

| module | bone anchor | x | y | z |
|---|---|---:|---:|---:|
| helmet | head | -4% | +3% | -6% |
| chest | upperChest | -8% | -8% | -2% |
| back | upperChest | -9% | +0% | +6% |
| waist | hips | -8% | -4% | +1% |
| left_shoulder | leftShoulder | -7% | -4% | +3% |
| right_shoulder | rightShoulder | -7% | -4% | +3% |
| left_upperarm | leftUpperArm | -8% | -3% | +1% |
| right_upperarm | rightUpperArm | -8% | -3% | +1% |
| left_forearm | leftLowerArm | -2% | -8% | -0% |
| right_forearm | rightLowerArm | -2% | -8% | -0% |
| left_hand | leftHand | -0% | -4% | +3% |
| right_hand | rightHand | -0% | -4% | +3% |
| left_thigh | leftUpperLeg | -3% | -5% | -4% |
| right_thigh | rightUpperLeg | -3% | -5% | -4% |
| left_shin | leftLowerLeg | -7% | +0% | -2% |
| right_shin | rightLowerLeg | -7% | +0% | -2% |
| left_boot | leftFoot | -6% | +1% | +2% |
| right_boot | rightFoot | -6% | +1% | +2% |

All modules under the audit's 15% tolerance on every axis. Mirror pairs are byte-exact mirrors via `bmesh.ops.reverse_faces` so left/right delta is 0%.

## Wave 1 visual checks

Compare `viewer/assets/armor-parts/_masters/full_suit_*.png` against `_masters/full_suit_*.png` in the prior session:
- Chest is now a curved wrap with a cyan emissive V down the sternum, no longer a flat slab.
- Back wraps the spine and lumbar regions instead of floating as a thin tile.
- Waist is a 200° belt around the hips with a cyan accent buckle.
- Shoulders cap the deltoid spheres with insertion lips reading toward the chest.
- Forearms / upperarms split as front+back shell halves with the inner suit visible at the side gap.
- Boots cap the toe and heel and wrap the ankle.
- Helmet is a bevelled dome with visor band, crest fin and side vents.

Per-module closeups under `viewer/assets/armor-parts/<module>/preview/<module>_closeup_<view>.png` give a tight frame for the modeler to grade silhouette without the full body proxy occluding small parts.

## Sub-agent dispatch log

Wave 1 was driven by 3 parallel sub-agents launched from the orchestrator:
- **Agent J** — designed the `body_wrap_arc` primitive, overhauled all 11 left/center spec functions, and updated the static AABB predictor to match. Handled the largest single edit.
- **Agent K** — added `render_full_suit`, `render_module_closeup`, `render_closeups_all` to `tools/blender/render_review.py` (+270 lines).
- **Agent L** — built `tools/check_armor_part_specs.py` + pytest suite as an independent static checker. Surfaced the spec-design mistakes Agent J then closed.

The orchestrator (this session) handled: tool sync, .blend1 cleanup, the `_scale_cube` 2x fix, central_v / spine_plate trim, hand `base_surface` zone, build/render orchestration, audit comparisons, doc regeneration.

## How to re-run end-to-end

Inside Blender (with the MCP add-on connected, executed via `execute_blender_code`):
```python
import os, sys
REPO = r"C:/dev/codex/gavai-henshin/.claude/worktrees/jovial-cohen-4bf60f"
for k in list(sys.modules):
    if "armor_" in k or "render_review" in k or "run_module_pipeline" in k:
        del sys.modules[k]
exec(open(os.path.join(REPO, "tools/blender/run_module_pipeline.py")).read(), globals())
build_all(REPO)
exec(open(os.path.join(REPO, "tools/blender/render_review.py")).read(), globals())
render_full_suit(REPO)
render_closeups_all(REPO)
```

Outside Blender:
```bash
cd <worktree>
PYTHONPATH=src python tools/check_armor_part_specs.py
PYTHONPATH=src python tools/validate_armor_parts_intake.py
PYTHONPATH=src python tools/audit_armor_part_fit_handoff.py --format markdown --output docs/armor-part-fit-modeler-requests.md
PYTHONPATH=src python -m pytest tests/test_armor_part_specs.py tests/test_validate_armor_part.py tests/test_modeler_sidecar.py -q
```

## Wave 1+ follow-up after `docs/modeler-context-and-actions-2026-04-30.md`

The modeler-facing context doc flagged 4 items as "未確認/不足". Status:

| Item | Status | Evidence |
|---|---|---|
| `audit_armor_part_fit_handoff.py --format json` returning warn instead of pass | **By design** | Audit emits `warn` whenever any module has visual-priority guidance OR sidecar QA warns. All visual_priority_wave1 entries always emit guidance, so a non-empty handoff list always produces `warn`. The substantive fit metrics (bbox delta) all pass: max abs delta 8.9% / mean 3.7%. |
| "bbox ±9% claim not verified locally" | **Verified locally** | `tools/audit_armor_part_fit_handoff.py --format json` against the worktree shows max abs axis delta 8.9% across 54 axes. Detail per module recorded above. |
| `_masters/full_suit_*.png` not yet stored | **Stored** | `viewer/assets/armor-parts/_masters/full_suit_{front,side,back,3q,overlay}.png` produced by `render_full_suit(repo_root)` and written into the worktree branch `claude/jovial-cohen-4bf60f`. |
| `armor-part-fit-modeler-requests.before.md` not yet stored | **Stored** | Wrote `docs/armor-part-fit-modeler-requests.before.md` as a verbatim snapshot of the audit table BEFORE this session's redesign, for diff-against the new `armor-part-fit-modeler-requests.md`. |

### Web Forge load smoke test

`tools/smoke_web_glb_load.py` simulates the Web Forge loader path offline (no Blender, no browser) by:
- resolving `armor_glb_asset_ref(module, '.')` for every blueprint module
- validating each `.glb` header via `validate_glb_header` and each sidecar via `validate_modeler_sidecar`
- cross-checking `vrm_attachment.primary_bone` against `ARMOR_SLOT_SPECS[...].body_anchor`
- composing `bone_world_position + offset_m` against an embedded 170cm reference rig

```
$ PYTHONPATH=src python tools/smoke_web_glb_load.py
previewGlbParts=18 previewFallbackParts=0
exit=0
```

Brief target was `previewGlbParts=12 / previewFallbackParts=0`; current state is **18 / 0**, exceeding Wave 1.

### pytest status

```
$ pytest tests/test_smoke_web_glb_load.py tests/test_armor_part_specs.py \
        tests/test_modeler_sidecar.py tests/test_validate_armor_part.py -q
16 passed in 0.27s
```

Coverage:
- `test_smoke_web_glb_load.py` — pass/fail/fallback paths for the smoke verifier
- `test_armor_part_specs.py` — every blueprint module has a PART_SPECS entry, mirror_of resolves, no static envelope failure
- `test_modeler_sidecar.py` — sidecar present + missing cases
- `test_validate_armor_part.py` — bbox / mirror / sidecar / synthetic-GLB gates

### Closeup-render upgrade

`render_module_closeup` now hides the `vrm_body_proxy` collection during render and tightens the camera to `max(bbox_dim) * 2.2` with a 50mm lens, producing per-module shots that fill the frame with the armor only. This addresses the brief's call for closeup review without body-proxy distraction. New closeups overwritten at `viewer/assets/armor-parts/<module>/preview/<module>_closeup_<view>.png`.

### Real VRM body in render path (deferred)

Agent M added `ensure_vrm_master_blend(repo_root)` to import `viewer/assets/vrm/default.vrm` into `review_master_vrm.blend` so renders show the actual hero body. Blender 5.1's stock glTF importer hits a known upstream bug (`'Context' object has no attribute 'object'`) when reading this particular VRM, so the function falls back to the legacy `review_master.blend` body proxy. Tracking under follow-ups; upgrading the Blender VRM addon (e.g. installing `VRM_Addon_for_Blender`) lifts the fallback. The closeup framing fix that hides the body collection still applies regardless, so the per-module review images are unaffected.

## Known follow-ups (intentionally out of Wave 1 scope)

- **Materials are placeholder palette colours**, not Nano Banana textures. Texture authoring is the next stage per `docs/modeler-armor-brief.md`.
- **Static checker reports 3 warns** on `helmet / left_boot / left_shin` because they declare 4 material zones; the orchestrator merges trim→accent at material-assignment time so the GLB ends up with 3 slots. This is by design but the warn is informational.
- **Body proxy used in renders is a rough cylinder/sphere stand-in**, not a real VRM. Final Web Forge integration uses the actual `viewer/assets/vrm/default.vrm` per `docs/armor-runtime-pipeline.md`.
- **Render lighting is a 3-point area light setup** for silhouette legibility; the production Web preview will swap for the final scene lighting.
- **z-axis on helmet still slightly under target (-6%)** because the dome bevel of 0.020m chamfers the corners. Acceptable for Wave 1 review; if needed, raise dome size_z by 6%.
