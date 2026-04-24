# UV Texture Generation Bench Log

## Purpose
This log records prompt and generation decisions for UV-bound armor texture work.
The current approved direction is the `c_normal_fold_first` bench variant:

- Use the generated UV guide as Reference A.
- Treat normal-facing color zones and fold/crease lines as engineering constraints.
- Translate guide annotations into armor material, panels, seams, emissives, and wear.
- Do not copy guide colors, wireframe strokes, grid lines, or annotation marks into the final texture.
- Keep the output as a flat 1:1 albedo-like UV texture sheet, not a rendered armor object.

## Current Canonical Prompt Strategy
The working structure is:

1. Decode Reference A as a UV engineering map.
2. Paint by surface direction: front identity, side wrap/construction, rear service logic.
3. Use orange fold/crease lines as plate bends, material breaks, or formed hard-surface transitions.
4. Apply user-specific armor DNA after UV correctness.
5. Apply the design-team constraints as a final critical review.
6. Reject character renders, object renders, backgrounds, labels, logos, and perspective scenes.

## Batch Bench Command
Dry-run prompt generation:

```powershell
python tools\prompt_bench_parts.py --parts all --output-dir sessions\_bench\all-parts\<stamp>
```

Live Nano Banana run for the approved variant:

```powershell
python tools\prompt_bench_parts.py --parts all --live --variant c_normal_fold_first --output-dir sessions\_bench\all-parts\<stamp>
```

Create a full-body preview SuitSpec from a batch summary:

```powershell
python tools\preview_bench_suitspec.py --batch-summary sessions\_bench\all-parts\<stamp>\summary.json --variant c_normal_fold_first --output sessions\S-BENCH-ALL-PARTS\suitspec.json --label "All parts UV texture bench preview"
```

Capture body-fit preview views:

```powershell
node tools\capture_bodyfit_views.mjs --base-url http://127.0.0.1:8010 --suitspec sessions/S-BENCH-ALL-PARTS/suitspec.json --sim sessions/body-sim.json --vrm viewer/assets/vrm/default.vrm --attach vrm --output-dir sessions/S-BENCH-ALL-PARTS/bodyfit-preview --preview-only
```

## Review Rubric
- `uv_layout_obedience`: image remains a flat UV atlas bound to Reference A.
- `normal_fold_obedience`: fold/crease and normal-facing zones influence panel breaks.
- `part_identity`: each part expresses its mechanical role without becoming a standalone render.
- `side_rear_logic`: side and rear zones carry construction/service logic, not filler.
- `user_identity`: palette, motif, and finish remain coherent across all modules.
- `artifact_rejection`: no body, no scene, no labels, no logos, no guide annotation leakage.

## Handoff To Model-Shape Work
Only after UV texture fit is acceptable across all parts, move into model-side improvement:

- Compare front/side/back/three-quarter captures for each generated texture.
- Identify where texture detail lands on unexpected model faces.
- Record parts whose model volume, seam placement, UV island proportions, or body-fit scale obstruct the prompt's intended design logic.
- Improve mesh shape/size after confirming the texture generation method is stable.

## 2026-04-19 All-Parts Live Bench
Command:

```powershell
python tools\prompt_bench_parts.py --parts all --live --variant c_normal_fold_first --timeout 150 --output-dir sessions\_bench\all-parts\latest-live-normal-fold
```

Result:

- Output summary: `sessions/_bench/all-parts/latest-live-normal-fold/summary.json`
- Parts generated: 18 / 18
- Provider/model: `gemini` / `gemini-2.5-flash-image`
- Total live generation time: about 224.0 sec
- Average part time: about 12.4 sec
- Slowest part: about 17.5 sec
- Average prompt length: about 3842 chars

Preview:

```powershell
python tools\preview_bench_suitspec.py --batch-summary sessions\_bench\all-parts\latest-live-normal-fold\summary.json --variant c_normal_fold_first --output sessions\S-BENCH-ALL-PARTS\suitspec.json --label "All parts UV texture bench preview"
node tools\capture_bodyfit_views.mjs --base-url http://127.0.0.1:8010 --suitspec sessions/S-BENCH-ALL-PARTS/suitspec.json --sim sessions/body-sim.json --vrm viewer/assets/vrm/default.vrm --attach vrm --output-dir sessions/S-BENCH-ALL-PARTS/bodyfit-preview --preview-only
```

Body-fit preview result:

- Preview SuitSpec: `sessions/S-BENCH-ALL-PARTS/suitspec.json`
- Preview captures: `sessions/S-BENCH-ALL-PARTS/bodyfit-preview/`
- Fit regression: pass
- Fit score: 91.561
- Textures visible: true
- Missing texture parts: none

Note:

- A separate fit-applied experiment was saved as `sessions/S-BENCH-ALL-PARTS/suitspec.fit-applied.json`.
- Re-running auto-fit from that baked-fit SuitSpec regressed to fit score 87.205 with seam and surface violations.
- Therefore the canonical preview SuitSpec remains texture-only; model size/shape/fit improvements should be handled in the next phase rather than baking the transient auto-fit result into this bench artifact.

## 2026-04-19 AI-Reference Guide And Safe-Subject Iteration

Reason:

- The first all-parts run proved Nano Banana can generate useful armor material language, but many outputs were object renders rather than UV-faithful texture atlases.
- Colored/debug UV guides leaked visible guide colors and construction marks into generated textures.
- Low-contrast guides alone reduced some leakage but allowed `helmet`, `boot`, and similar part names to trigger recognizable object drawings.

Implemented changes:

- Split guide usage into `debug` and `ai_reference` profiles.
- Keep human-readable UV guide images under `sessions/_cache/uv-guides/`.
- Use AI-safe grayscale guide images under `sessions/_cache/uv-guides-ai/`.
- Include guide algorithm version in AI cache filenames so stale guide images cannot silently survive prompt/guide revisions.
- Lower AI guide line contrast in `uv-ai-reference-v3`.
- Update `c_normal_fold_first` prompt strategy to v4:
  - Treat part names as mesh routing keys, not illustration subjects.
  - Use neutral UV subject descriptors such as `LFT-01 left lower terminal contact-shell UV surface group`.
  - Add UV atlas failure guards for full-square coverage, no floating product-shot parts, no readable text/QR, no object silhouettes, and no perspective shading.

Commands:

```powershell
python tools\prompt_bench_parts.py --parts all --output-dir sessions\_bench\all-parts\latest-dry-ai-guide-v4
python tools\prompt_bench_parts.py --parts all --live --variant c_normal_fold_first --timeout 150 --output-dir sessions\_bench\all-parts\latest-live-ai-guide-v4
python tools\preview_bench_suitspec.py --batch-summary sessions\_bench\all-parts\latest-live-ai-guide-v4\summary.json --variant c_normal_fold_first --output sessions\S-BENCH-ALL-PARTS-AI-GUIDE-V4\suitspec.json --label "All parts AI-guide v4 safe-subject UV texture bench preview"
node tools\capture_bodyfit_views.mjs --base-url http://127.0.0.1:8010 --suitspec sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/suitspec.json --sim sessions/body-sim.json --vrm viewer/assets/vrm/default.vrm --attach vrm --output-dir sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/bodyfit-preview --preview-only
```

Result:

- Output summary: `sessions/_bench/all-parts/latest-live-ai-guide-v4/summary.json`
- Parts generated: 18 / 18
- Provider/model: `gemini` / `gemini-2.5-flash-image`
- Total live generation time: about 228.0 sec
- Average part time: about 12.7 sec
- Slowest part: about 15.1 sec
- Fastest part: about 9.4 sec

Preview:

- Preview SuitSpec: `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/suitspec.json`
- Body-fit captures: `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/bodyfit-preview/`
- UV fit review: `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/uv-fit-review/review.md`
- Contact sheets:
  - `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/uv-fit-review/uv-fit-contact-1.png`
  - `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/uv-fit-review/uv-fit-contact-2.png`
  - `sessions/S-BENCH-ALL-PARTS-AI-GUIDE-V4/uv-fit-review/uv-fit-contact-3.png`

Current judgement:

- v4 is better than the colored-guide run and better than the initial AI-guide run for several parts.
- It is still not reliable enough to advance fully into model-shape work as the canonical texture pipeline.
- Main remaining issues are object reconstruction, visible guide leakage, and inconsistent full-canvas atlas coverage.
- Next generation-side experiment should replace visible guide lines with a mask-like topology reference and add automated reject checks before changing mesh shape.

## 2026-04-19 Topology Mask V5 And Quality Gate

Reason:

- The AI-reference guide still contained visible construction geometry that Nano Banana could copy.
- A pure prompt instruction was not enough to stop object-sheet outputs.
- We needed a mechanical reject layer so failed generations do not look like successful pipeline runs.

Implemented changes:

- Added `topology_mask` guide profile.
- The production and prompt-bench UV reference path now uses `topology_mask` rather than `ai_reference`.
- `topology_mask` v3 is an almost-uniform UV occupancy mask:
  - no centerline,
  - no motif box,
  - no fold lines,
  - no boundary lines,
  - no colored semantic legend,
  - no high-contrast triangle wire.
- Added `texture_quality.evaluate_texture_output()`.
- Live prompt bench records `quality_gate` per generated variant.
- `run_generate_parts()` records `quality_gate` per generated part and exposes `quality_rejected_count`.

Quality checks:

- `large_unpainted_background`
- `object_silhouette_on_background`
- `construction_orange_guide_leak`
- `diagonal_guide_line_leak`
- `text_or_qr_like_microcontrast`
- `plain_background_frame`

Command:

```powershell
python tools\prompt_bench_parts.py --parts all --live --variant c_normal_fold_first --timeout 150 --output-dir sessions\_bench\all-parts\latest-live-topology-mask-v5
python tools\preview_bench_suitspec.py --batch-summary sessions\_bench\all-parts\latest-live-topology-mask-v5\summary.json --variant c_normal_fold_first --output sessions\S-BENCH-ALL-PARTS-TOPOLOGY-MASK-V5\suitspec.json --label "All parts topology-mask v5 UV texture bench preview"
node tools\capture_bodyfit_views.mjs --base-url http://127.0.0.1:8010 --suitspec sessions/S-BENCH-ALL-PARTS-TOPOLOGY-MASK-V5/suitspec.json --sim sessions/body-sim.json --vrm viewer/assets/vrm/default.vrm --attach vrm --output-dir sessions/S-BENCH-ALL-PARTS-TOPOLOGY-MASK-V5/bodyfit-preview --preview-only
```

Result:

- Output summary: `sessions/_bench/all-parts/latest-live-topology-mask-v5/summary.json`
- Parts generated: 18 / 18
- Provider/model: `gemini` / `gemini-2.5-flash-image`
- Total live generation time: about 215.6 sec
- Average part time: about 12.0 sec
- Quality gate result: 12 reject, 6 warn, 0 pass
- Review: `sessions/S-BENCH-ALL-PARTS-TOPOLOGY-MASK-V5/uv-fit-review/review.md`

Current judgement:

- The mask reference reduced direct guide-copy problems.
- The automated reject layer works and catches the main bad outputs.
- The generation model still strongly prefers armor object concept sheets over true UV texture atlases.
- The next step should not be model-shape work yet. The next generation-side step should be deterministic atlas composition: synthesize the UV atlas structure locally, ask the image model only for material/style patches, then composite those patches into the atlas under masks.

## 2026-04-19 Armor Design Team V2

Reason:

- The prompt stack needed a stricter in-world team model, not just longer art direction.
- The team must separate permanent user armor DNA from current emotional modulation.
- The UV quality failures showed that atlas discipline needs its own review role and hard reject language.

Implemented changes:

- Upgraded `armor_design_team` to v2.
- Expanded the deterministic design team from 5 roles to 10 roles:
  - lore architect,
  - operator oath keeper,
  - armor smith,
  - dock chief,
  - atlas compositor,
  - UV engineer,
  - material director,
  - transformation choreographer,
  - model inspector,
  - reject gatekeeper.
- Added `review_sequence` so prompt/debug output exposes the order of team sign-off.
- Added `hard_rejects` so prompts and summaries carry machine-like failure boundaries:
  - object concept sheets,
  - visible guide artifacts,
  - blank canvas regions,
  - perspective renders,
  - front-only decoration,
  - emotion overriding permanent user DNA.
- Prompt bench compaction now keeps the team operating rule and hard rejects.

Current judgement:

- This is a prompt governance layer, not a new runtime multi-agent pipeline.
- It makes the generation contract clearer: lore > user armor DNA > UV topology > current emotion > request detail.
- Next generation-side step remains deterministic atlas composition, but now the prompt and summary have a named team structure to evaluate against.
