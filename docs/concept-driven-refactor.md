# Concept-Driven Refactor Notes

Updated: 2026-03-07

## Why this refactor exists

This repository is not just a simulation toolchain. It is a concept-driven transformation pipeline:

- `Lore / Protocol`: why the system exists
- `SuitSpec / Morphotype`: what is allowed to exist
- `Viewer / Dashboard / Live input`: how the suit is experienced and adjusted

The code had started drifting in one important place: armor-part canon was duplicated across multiple viewer surfaces.

## New rule

Armor-part fit defaults, color identity, and VRM anchor baselines must have one browser-side source of truth:

- `viewer/shared/armor-canon.js`

This file now owns:

- armor-part visual fit baselines
- VRM anchor defaults
- VRM bone alias resolution tables
- attachment-slot aliases
- part color mapping
- fit-contact pairs used for gap/penetration checks

## Architectural intent

### 1. Canon layer

`viewer/shared/armor-canon.js`

This is the browser-side canon for "what a suit part means".
If `chest`, `left_upperarm`, or `right_boot` behave differently between tools, the fix should start here.

### 2. Experience layer

- `viewer/body-fit/viewer.js`
- `viewer/suit-dashboard/dashboard.js`

These files should focus on interaction and rendering, not on redefining suit canon.

### 3. Runtime layer

- live webcam pose tracking
- VRM loading and anchor application
- future mocopi bridge
- future 8thwall evaluation path

This layer should consume canon, not invent it.

### 4. Contract layer

- `schemas/`
- `src/henshin/`

This layer remains the authoritative source for repository outputs and protocol flow.

## What changed in this pass

1. Shared armor canon was extracted for browser tools.
2. `body-fit` and `suit-dashboard` now consume shared part/anchor definitions.
3. `viewer/body-fit/body-fit-live.js` now owns the live pose pipeline primitives that had been buried inside `viewer.js`.
4. Viewer behavior is easier to reason about because both tools are now reading the same baseline semantics.

## Why this matters for the current body-fit/live work

The current workstream depends on stable answers to these questions:

- where does each armor part belong on the body
- which bone should own it in VRM mode
- what size/offset is considered the baseline before live adjustments

If those answers differ across tools, tracking and fitting bugs become ambiguous.
This refactor reduces that ambiguity before resuming live-pipeline iteration.

## Next recommended seams

1. Continue extracting `body-fit` UI/editor wiring from rendering/runtime logic.
2. Move Python-side module inventory (`forge.py`) toward the same explicit canon model.
3. Separate VRM runtime concerns from general body-fit rendering concerns.
