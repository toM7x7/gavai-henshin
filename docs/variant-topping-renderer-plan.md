# Variant/Topping Closeup Renderer Plan

Date: 2026-05-01

Scope: local-code-only design note for modeler follow-up 1,
`render_variant_closeup` and `render_topping_closeup`.

## Current Renderer Pattern

The current Blender review renderer lives in
`tools/blender/render_review.py`.

Relevant public entry points:

- `render_review_for_module(module, repo_root)`: imports one canonical GLB,
  places it at its blueprint bone anchor, and writes standard review PNGs.
- `render_full_suit(repo_root)`: imports all canonical GLBs and writes
  `_masters/full_suit_<view>.png` plus `_masters/full_suit_overlay.png`.
- `render_module_closeup(module, repo_root)`: imports one canonical GLB,
  places it at its blueprint bone anchor, hides `vrm_body` /
  `vrm_body_proxy`, computes the world-space bbox, then renders a temporary
  50mm camera to `preview/<module>_closeup_<view>.png`.
- `render_closeups_all(repo_root)`: calls `render_module_closeup` for every
  module in `_blueprint_snapshot.json`.

The closeup path is the right base for variants and toppings because it already
does the hard parts:

- resolves the preferred VRM-backed or legacy `_masters` blend;
- imports GLB with Blender's glTF importer;
- uses `_bone_world_position(part)` for canonical body placement;
- hides body collections so small parts are not visually buried;
- frames from the imported object's world bbox rather than fixed cameras;
- writes one PNG per view for `front`, `side`, `back`, and `3q`.

## Existing Asset Contracts

Canonical modules currently use:

```text
viewer/assets/armor-parts/<module>/
  <module>.glb
  <module>.modeler.json
  source/<module>.blend
  preview/<module>_front.png
  preview/<module>_side.png
  preview/<module>_back.png
  preview/<module>_3q.png
  preview/<module>_closeup_<view>.png
```

Wave 2 docs reserve these future locations:

```text
viewer/assets/armor-parts/<module>/variants/<variant_key>/
  <module>__<variant_key>.glb
  <module>__<variant_key>.modeler.json
  preview/<module>__<variant_key>_<view>.png
```

```text
viewer/assets/armor-parts/<parent_module>/toppings/<topping_slot>/<topping_key>/
  <parent_module>__<topping_slot>__<topping_key>.glb
  <parent_module>__<topping_slot>__<topping_key>.modeler.json
  preview/<parent_module>__<topping_slot>__<topping_key>_<view>.png
```

`viewer/assets/armor-parts/variant_catalog.json` is design data only today.
It declares `modules.<part>.variants` and `modules.<part>.topping_slots`, but
does not make runtime GLB loading or renderer placement automatic yet.

## Output Naming Rule

Use the same 4-view set as canonical renders:

```text
front
side
back
3q
```

Variant closeup outputs:

```text
viewer/assets/armor-parts/<module>/variants/<variant_key>/preview/
  <module>__<variant_slug>_closeup_front.png
  <module>__<variant_slug>_closeup_side.png
  <module>__<variant_slug>_closeup_back.png
  <module>__<variant_slug>_closeup_3q.png
```

Topping closeup outputs:

```text
viewer/assets/armor-parts/<parent_module>/toppings/<topping_slot>/<topping_key>/preview/
  <parent_module>__<topping_slot>__<topping_slug>_closeup_front.png
  <parent_module>__<topping_slot>__<topping_slug>_closeup_side.png
  <parent_module>__<topping_slot>__<topping_slug>_closeup_back.png
  <parent_module>__<topping_slot>__<topping_slug>_closeup_3q.png
```

Slug normalization:

- Accept catalog-style keys such as `helmet:sleek`, but file paths should use
  only the local key segment: `sleek`.
- Require lowercase snake_case after normalization.
- Reject path separators, empty keys, and `..`.
- Keep canonical module names unchanged.

The existing order sheet lists non-closeup variant/topping preview names
without `_closeup`. Those should remain available later for body-context
review. The closeup renderer should explicitly include `_closeup_` so the
purpose matches canonical `render_module_closeup`.

## Proposed API

Add helper-level implementation to `tools/blender/render_review.py` or to the
future `tools/blender/run_variant_pipeline.py` once that file exists.

```python
def render_variant_closeup(module: str, variant_key: str, repo_root: str) -> dict:
    """Render a replacement module variant as a tight 4-view closeup."""


def render_topping_closeup(
    parent_module: str,
    topping_slot: str,
    topping_key: str,
    repo_root: str,
    *,
    with_parent: bool = True,
) -> dict:
    """Render a topping as a tight 4-view closeup, optionally with parent GLB."""
```

Return shape should mirror `render_module_closeup`:

```python
{
    "module": module,
    "variant_key": variant_key,
    "ok": True,
    "renders": {"front": "...", "side": "...", "back": "...", "3q": "..."},
    "frame_distance": 0.42,
    "bbox_center": (0.0, 0.0, 1.2),
    "bbox_dims": (0.2, 0.1, 0.3),
}
```

For toppings, include:

```python
{
    "parent_module": parent_module,
    "topping_slot": topping_slot,
    "topping_key": topping_key,
    "with_parent": True,
    ...
}
```

## Implementation Shape

Do not duplicate `render_module_closeup`. Extract its generic body into a
private helper:

```python
def _render_imported_closeup(
    repo_root: str,
    imports: list[dict],
    primary_label: str,
    out_dir: str,
    filename_stem: str,
) -> dict:
    ...
```

Where each import item is:

```python
{
    "glb": glb_path,
    "part": blueprint_part,
    "placement": "bone" | "parent_local" | "origin",
    "label": "helmet__sleek",
    "frame_subject": True,
}
```

The helper should:

1. Resolve/open master blend.
2. Strip previous `armor_` imports.
3. Import all GLBs.
4. Place canonical/variant objects with `_bone_world_position(part)`.
5. For toppings with `with_parent=True`, import parent first, then import
   topping. Until sidecar local-slot transforms exist, place topping at the
   same parent bone position and frame the union bbox. This is visually useful
   for modeler review but must return a warning.
6. Move imports into `armor_active`.
7. Compute bbox from either the primary object or the union of
   `frame_subject=True` objects.
8. Hide body collections.
9. Render `_VIEWS` with the same 50mm temporary camera and `max_dim * 2.2`
   distance used by `render_module_closeup`.
10. Restore body visibility and remove temporary camera/target.

`render_module_closeup` can then become a thin canonical wrapper over the same
helper, but that refactor should be done in a branch where no other worker is
editing renderer internals.

## Variant Placement

A variant is a replacement for the canonical module. Therefore:

- Use the canonical module's blueprint part from `_blueprint_snapshot.json`.
- Use `_bone_world_position(part)` exactly like `render_module_closeup`.
- Import only the variant GLB, not the canonical parent.
- Frame the variant object's own bbox.

Path resolver:

```python
def _variant_glb_path(repo_root, module, variant_key):
    slug = _asset_key_slug(variant_key)
    return os.path.join(
        repo_root, "viewer", "assets", "armor-parts", module,
        "variants", slug, f"{module}__{slug}.glb",
    )
```

## Topping Placement

A topping is an add-on mounted on a named local slot of its parent module.
The current local code does not yet contain a concrete transform contract for
slot placement. `variant_catalog.json` has semantic `anchor_hint` and
`max_bbox_m`, not final matrices.

Recommended phase split:

- Phase 1 closeup: render topping with parent at the parent bone position,
  frame the union bbox, and return warning
  `topping_slot_transform_missing`.
- Phase 2 closeup: when sidecars include a local slot transform, apply:
  `parent_world_matrix @ slot_local_matrix @ topping_local_offset`.
- Phase 3 review: add body-context standard previews without `_closeup_`.

For phase 1, `with_parent=True` should be the default. A topping-only closeup is
allowed via `with_parent=False`, but it is less useful because it cannot prove
that the add-on reads as mounted rather than floating.

Path resolver:

```python
def _topping_glb_path(repo_root, parent_module, topping_slot, topping_key):
    slot = _asset_key_slug(topping_slot)
    slug = _asset_key_slug(topping_key)
    return os.path.join(
        repo_root, "viewer", "assets", "armor-parts", parent_module,
        "toppings", slot, slug,
        f"{parent_module}__{slot}__{slug}.glb",
    )
```

## Validation

Before rendering:

- Check master blend exists through `_resolve_master_blend`.
- Check GLB exists and return `{ok: False, error: "glb missing: ..."}` if not.
- Check `module` / `parent_module` exists in `_blueprint_snapshot.json`.
- Check slugs are lowercase snake_case after normalization.
- For toppings, check `topping_slot` exists in
  `variant_catalog.json` when the catalog is present. Treat a missing catalog
  as a warning, not a hard failure.

After rendering:

- Ensure `renders` has four keys: `front`, `side`, `back`, `3q`.
- Ensure every rendered path is under the asset directory for that variant or
  topping.
- Include warnings for provisional placement:
  `["topping_slot_transform_missing"]`.

## Why No Code Change In This Pass

The requested optional edit target, `tools/blender/run_variant_pipeline.py`,
does not exist in the current worktree. The existing implementation target is
actually `tools/blender/render_review.py`, but the request warned that
renderer-adjacent files may be touched by other workers. To avoid reverting or
colliding with parallel work, this pass records the exact implementation plan
and leaves Python files untouched.

Small implementation point once ownership is clear:

1. Add `_asset_key_slug`, `_variant_glb_path`, `_topping_glb_path`.
2. Extract `_render_imported_closeup` from `render_module_closeup`.
3. Rewire `render_module_closeup` to call the helper.
4. Add `render_variant_closeup` as the first new wrapper.
5. Add `render_topping_closeup` with phase-1 parent/union-bbox placement and
   explicit transform warning.
