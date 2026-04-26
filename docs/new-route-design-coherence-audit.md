# New Route Design Coherence Audit

Date: 2026-04-26

Lore baseline:

```text
Web: Suit Forge -> Quest: Henshin Trial -> Replay: Archive
```

This note tracks the next brush-up lane after the data route is working. The goal is not only to make the mockups prettier. The goal is to make the armor identity, part geometry, UI language, and replay evidence point to the same suit.

## Current Read

The route mechanics are now far enough along to expose visual debt:

- `examples/suitspec.sample.json` is the first canonical suit seed. Its top-level operator identity is now locked to the latest generated identity metadata: `legacy / stoic / clear_white`.
- `viewer/shared/armor-canon.js` contains baseline fit, color, VRM anchor, and part-slot conventions, but the sample `SuitSpec` overrides many values with much smaller or differently offset fit settings.
- `viewer/assets/meshes/*.mesh.json` covers the full 18-part kit, so the base part inventory is complete.
- `texture_path` values in the sample point into `sessions/...`, which is runtime output and ignored by git. That is fine for local proof, but it is not a portable canonical design seed.
- The Quest and dashboard views are still integration harnesses. They prove state and replay, but they should not yet be treated as final visual direction.

## Coherence Risks

### 1. Canonical identity is locked

The sample now keeps the top-level operator profile aligned with the latest generation metadata:

```text
protect_archetype: legacy
temperament_bias: stoic
color_mood: clear_white
palette_family: Rescue ceramic white
```

The active palette follows that family: ceramic off-white shell, cool gray substructure, and blue-white emissive. Stored part prompts remain as generation trace; future texture regeneration should preserve the locked profile.

### 2. Fit values have two competing baselines

`armor-canon.js` has broad baseline scales such as limb parts near `0.9` to `1.04`. The sample `SuitSpec` stores many limb scales near `0.05` to `0.10`, with larger offsets. Examples:

| Part | Main risk |
|---|---|
| `left_thigh` / `right_thigh` | sample scale is far smaller than canon baseline |
| `left_shin` / `right_shin` | sample scale is far smaller than canon baseline |
| `left_forearm` / `right_forearm` | sample scale and offset differ sharply from canon |
| `chest` / `back` | sample is materially smaller and shifted |

This may be intentional if the values belong to different coordinate meanings, but that ambiguity needs to be made explicit. One field should mean authored mesh fit, another should mean viewer/body-fit resolved fit, or the projection step should normalize them.

### 3. Texture references are not portable

The canonical sample refers to generated files under `sessions/S-20260412-YOUB/...`. Those files exist locally, but `sessions/*` is ignored. A fresh checkout may have a valid schema but no visible texture family.

The next design pass should add either:

- committed baseline swatches/placeholder textures under `viewer/assets/`, or
- a clear fallback rule that derives material colors from `palette` and `operator_profile` when textures are missing.

### 4. Debug colors conflict with final suit identity

`PART_COLOR_MAP` uses highly varied per-part debug colors. That is useful for technical inspection, but it does not match the lore direction of a disciplined suit family. The UI should label these as debug colors or switch production display toward the suit palette.

### 5. Quest and dashboard copy still carry harness language

The current Quest page correctly exposes `ROUTE`, `API`, `TRIAL`, and `REPLAY`. The final experience should keep the proof but move visible copy toward the lore lexicon:

```text
FIT AUDIT
MORPHOTYPE LOCKED
BLUEPRINT ISSUED
DEPOSITION
SEAL VERIFIED
REPLAY ARCHIVE
```

## Brush-Up Order

1. Canonical identity lock
   - Done for `VDA-AXIS-OP-00-0001`: `clear_white / stoic / legacy`.
   - Keep future generation metadata, palette, and prompt family aligned with this identity unless a deliberate new suit ID is created.

2. Fit contract split
   - Define whether `module.fit` is authored mesh fit, body-fit result, or runtime override.
   - Add a validator or audit test that reports large drift from `armor-canon.js` unless explicitly marked as calibrated.

3. Portable visual seed
   - Add committed baseline material assets or deterministic palette fallback.
   - Avoid depending on ignored `sessions/...` files for canonical appearance.

4. Part visual pass
   - Check silhouette continuity across helmet, chest, shoulders, forearms, thighs, shins, boots, and hands.
   - Prioritize chest/helmet/shoulders first because they carry identity in Web, Quest, and Replay screenshots.

5. UI language pass
   - Keep the operational dashboard dense, but replace generic harness text with the lore lexicon where it does not reduce clarity.
   - Keep Sakura AI as the real voice/TTS path; mock trigger remains a local smoke-test bypass only.

## Mockup Polish Checklist

Use this as the acceptance gate for the next visual pass.

### Suit Forge

- The screen presents suit establishment, not generic generation.
- Suit ID, approval ID, manifest ID, and updated timestamp are visible in a restrained operational way.
- The visible armor family follows one identity: palette, temperament, silhouette, and motif do not contradict each other.
- Texture or material fallback is portable from a fresh checkout.
- Chest, helmet, and shoulders read as one production family before secondary limbs are judged.

### Body Fit

- Viewer shows inspection states: loaded VRM/body sim, attachment mode, anchor status, and pose quality.
- Gaps and overlaps are inspectable, not hidden by camera framing.
- Left/right pairs remain symmetric unless a specific asymmetry rule is recorded.
- `module.fit` meaning is clear: authored fit, calibrated body-fit result, or runtime override.
- Debug colors are visibly technical aids, not the suit's final identity.

### Quest Trial

- The sensation is armor forming around the wearer, not an object playing in front of them.
- Staging follows body-relative anchors: safe pre-fit distance, ghost silhouette, contraction, deposition, seal.
- HUD/status copy uses the protocol lexicon: `FIT AUDIT`, `MORPHOTYPE`, `BLUEPRINT`, `DEPOSITION`, `SEAL`, `REPLAY`.
- Voice and TTS stay on the Sakura AI path; `mockTrigger=1` remains clearly local smoke only.
- Trial completion leaves a ReplayScript record that the PC dashboard can verify.

## Current Implementation Slice

Current branch:

```text
codex/new-route-canonical-identity-lock
```

This slice consumes the audit's first finding by making the sample identity internally consistent:

- top-level operator profile matches latest generation metadata,
- sample palette and projected manifest palette use the rescue ceramic white family,
- design coherence audit treats `operator_identity_drift` as a regression.

Command:

```powershell
python tools/run_henshin.py design-coherence-audit --output-md tests/.tmp/design-coherence-audit.md
```

After this lock, the next highest-value slice is the fit contract split: make `module.fit` unambiguously mean authored fit, calibrated body-fit result, or runtime override.
