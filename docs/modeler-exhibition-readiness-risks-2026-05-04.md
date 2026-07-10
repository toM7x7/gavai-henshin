# Modeler Exhibition Readiness Risks - 2026-05-04

Scope: modeler bbox, fidelity, and visual QA readiness for a public demo that will run on a different external exhibition PC.

Premise: the exhibition PC is not the development checkout. Anything needed for the demo must be packaged with repo-relative paths, reproducible validation output, and visual proof that can be inspected without Blender or local worktrees.

## Current Read

- `tools/smoke_web_glb_load.py --report-json` passes technical load: `preview_glb_parts=18`, `preview_fallback_parts=0`, `ok=true`.
- The same smoke has 6 bbox yellow warnings: `chest.z`, `waist.x`, `left_upperarm.x`, `right_upperarm.x`, `left_shin.x`, `right_shin.x`.
- `docs/modeler-fit-micro-adjustments-2026-05-04.md` is the active per-part micro-adjustment list for these warnings, including size deltas, position nudges, and tri-view proof requirements.
- Mirror-pair bbox checks pass for all left/right pairs.
- The 30 three-line variants in the modeler delivery audit are `fidelity_hold`. They should not be activated in the public runtime until their visual identity and per-asset provenance pass.
- The P1 limb three-line order remains an open order for 24 variants. This is not a public-demo dependency unless the demo claims line-complete arms/hands/thighs.

## Must Fix Before Public Demo

These are blockers for the exhibition PC package.

| Risk id | Area | Public-demo risk | Required action | Acceptance |
|---|---|---|---|---|
| EXH-PKG-01 | Package determinism | External PC falls back to proxy mesh or misses local worktree paths. | Build the demo package from the exact runtime asset tree, not `.claude/worktrees` paths. | On the packaged directory, `python tools/smoke_web_glb_load.py --repo-root <package-root> --report-json` returns `ok=true`, `preview_glb_parts=18`, `preview_fallback_parts=0`, and no failures. |
| EXH-PKG-02 | Runtime activation | `fidelity_hold` variants accidentally appear in the public selector. | Keep the 30 held line variants disabled/unselected/unreferenced by public runtime selection. | Public demo starts with accepted canonical/base parts only, unless a variant has a new fidelity-pass packet. |
| EXH-BBOX-01 | `chest.z` | Chest can read too flat in side/3Q and under exhibition lighting. | Reorder/modeler thickens chest depth without breaking chest/waist/arm clearance. | `chest.z` enters the +/-10% pass range: current `0.142398m`, target `0.163200m`, minimum pass `0.146880m`; sidecar and GLB bbox differ by <= `0.002m`; side and 3Q screenshots show chest volume. |
| EXH-BBOX-02 | `waist.x` | Belt can read slightly narrow, making torso/leg connection fragile on wide displays. | Reorder/modeler widens pelvis wrap or explicitly waives after rehearsal imagery. | Preferred: `waist.x` enters pass range: current `0.440351m`, target `0.489600m`, minimum pass `0.440640m`; GLB/sidecar match <= `0.002m`. If waived, include final full-body front/3Q proof and note why the 0.3mm minimum delta is visually harmless. |
| EXH-BBOX-03 | upperarm pair `x` | Upper arms can read like thin bands between shoulder and forearm. | Reorder/modeler widens both upperarm shells symmetrically. | `left_upperarm.x` and `right_upperarm.x` enter pass range: current `0.096304m`, target `0.108800m`, minimum pass `0.097920m`; mirror max delta remains <=3%; elbow/shoulder clearance screenshot included. |
| EXH-BBOX-04 | shin pair `x` | Shins can read too narrow from front, weakening boot-to-leg continuity. | Reorder/modeler widens both shin shells symmetrically. | `left_shin.x` and `right_shin.x` enter pass range: current `0.101728m`, target `0.115600m`, minimum pass `0.104040m`; mirror max delta remains <=3%; front and boot-side closeup included. |
| EXH-QA-01 | Visual proof | Staff cannot diagnose problems on the exhibition PC without source tools. | Package visual QA artifacts with the demo. | `qa/` folder includes smoke JSON, browser/Quest screenshots, public build metadata, and a short operator checklist. |

## Can Remain Hold

These do not block the public demo if they are not activated or advertised as complete.

| Hold id | Scope | Why it can remain hold | Guardrail |
|---|---|---|---|
| HOLD-FID-30 | 30 delivered line variants for helmet/chest/back/waist/shoulder/shin/boot across 3 lines | They are file-valid but still `fidelity_hold`; public demo can use stable canonical/base suit. | Do not expose them in the public runtime. Keep them in reviewer-only folders or hide them behind a non-public flag. |
| HOLD-P1-24 | P1 limb line variants for upperarm/forearm/hand/thigh | They are ordered but not required for a base public suit demo. | Do not claim line-complete arms/hands/thighs in the demo script. |
| HOLD-META-EXPERIMENTAL | Existing non-public variant metadata holds | Metadata-only holds are acceptable if those assets are not selectable at runtime. | Runtime catalog for the exhibition package must not point public selection to held assets. |
| HOLD-FID-EVIDENCE | Missing `source_overlay_front.png` and `boot_closeup_side.png` for held line variants | These are required for fidelity promotion, not for a base canonical public demo. | If any held line is promoted, these images become required before packaging. |

## Waiver Protocol

A waiver is a demo-only exception. It does not convert a held or warning asset into an accepted asset, and it expires after the public demo package it names.

Allowed waiver cases:

- Minor bbox yellow warnings may be waived only when smoke has no failures, no GLB fallback, sidecar/GLB bbox match stays within `0.002m`, mirror-pair checks still pass, and rehearsal screenshots show no public-facing visual defect.
- A `fidelity_hold` variant may be waived only for reviewer/operator visibility. It must not be exposed as an accepted public runtime option.
- Missing fidelity evidence may be waived only when the asset is not promoted to runtime and the public script does not claim that line/part as complete.

Never waive:

- GLB fallback, missing public assets, invalid sidecars, failed mirror checks, or runtime selector references to hidden/held variants.
- Quest hand/controller, elbow, hip, knee, boot, or waist defects that block the visitor flow.
- Any asset path that depends on a dev-only checkout or `.claude/worktrees`.

Required sign-off:

| Role | Signs off on | Required before |
|---|---|---|
| Modeler lane owner | Visual acceptability of the bbox/fidelity exception and exact asset ids affected. | Package freeze |
| Exhibition PC lane owner | The waiver evidence was captured from the packaged external-PC build path. | External-PC rehearsal |
| Quest lane owner | Any waiver that may affect headset motion, controller clearance, recall, or transformation read. | Public headset rehearsal |
| Schedule-PM / demo owner | Final go/no-go decision and public script limitations. | Door-open checklist |

Required waiver record:

```text
waiver_id:
risk_id:
asset_ids:
demo_package_id_or_hash:
reason:
evidence_files:
runtime_visibility: public | hidden | operator-only
expires_after:
signed_off_by:
```

Evidence package:

- `smoke_web_glb_load_external_pc.json` and text summary from the packaged root.
- Front/side/back/3Q screenshots from the packaged Web build.
- Quest screenshot or headset note when the waiver touches motion, hand/controller clearance, or recall.
- Diff or manifest proving waived assets are separated from accepted runtime assets.
- A one-line operator script note if the public demo must avoid claiming the waived feature.

Visible separation from accepted assets:

- Accepted assets remain in the public runtime selector/catalog path.
- Waived-for-demo assets must be marked `waived_for_demo` or kept in `operator-only`/reviewer notes, not renamed to `pass`.
- `fidelity_hold` stays `fidelity_hold`; add a separate waiver record instead of changing status.
- The QA package must include a `waivers/` folder or `qa/exhibition-readiness.md` section listing each waiver id, risk id, and visibility.

## 30 Variant Fidelity Promotion Tasks

The 30 held variants should be treated as a reviewer track, not an exhibition runtime track.

| Task | Applies to | Acceptance before runtime promotion |
|---|---|---|
| FID-01 | All 30 held variants | Add per-asset sidecar top-level `source_concept_ids`, `line_id`, `design_intent`, and `fidelity_notes`. Catalog fallback is not enough for replay/debug provenance. |
| FID-02 | `line_rescue_knight` | Make white/cyan rescue identity readable in full-body front/side/back/3Q: blue visor, cyan chest core, compact back, grounded boots. |
| FID-03 | `line_royal_insect` | Make green/white/gold guardian identity readable without relying on tiny texture-only detail: compound visor, short crest/antenna, emerald V chest, close-body shell. |
| FID-04 | `line_final_oath` | Make final-form density visibly exceed c01/c02: crown visor, large cyan core, denser gold trim, glow continuity into legs/boots. |
| FID-05 | Review evidence | Provide per-line `source_overlay_front.png`, `boot_closeup_side.png`, full front/side/back/3Q, helmet closeup, torso closeup, and side/back proof for any variant promoted to runtime. |

## External PC QA Package

Package these artifacts alongside the demo build so exhibition staff can validate the machine without opening Blender.

Recommended layout:

```text
qa/
  exhibition-readiness.md
  smoke_web_glb_load_external_pc.json
  smoke_web_glb_load_external_pc.txt
  browser_console_external_pc.log
  build_manifest.json
  asset_file_manifest.txt
  screenshots/
    web_forge_default_front.png
    web_forge_default_side.png
    web_forge_default_back.png
    web_forge_default_3q.png
    web_forge_mobile_or_small_window.png
    quest_recall_default_front.png
    quest_recall_default_side.png
  modeler_review/
    canonical_full_front.png
    canonical_full_side.png
    canonical_full_back.png
    canonical_full_3q.png
    bbox_warning_chest_side_3q.png
    bbox_warning_upperarm_pair.png
    bbox_warning_shin_pair_boot_closeup.png
```

Minimum commands to run from the packaged root on the exhibition PC:

```powershell
python tools\smoke_web_glb_load.py --repo-root . --report-json > qa\smoke_web_glb_load_external_pc.json
python tools\smoke_web_glb_load.py --repo-root . > qa\smoke_web_glb_load_external_pc.txt
```

Expected public-demo gate:

- No GLB fallback.
- No smoke failures.
- `bbox_warning_count=0`, or waiver records exist under the protocol above with attached rehearsal proof.
- No public runtime selector entry points to `fidelity_hold` assets.
- QA screenshots show the actual packaged build, not development worktree renders.
