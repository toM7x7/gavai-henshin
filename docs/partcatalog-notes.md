# PartCatalog Seed Notes

Updated: 2026-04-24

## Source Findings

- Canonical modules come from `viewer/shared/armor-canon.js`: 18 module keys from `helmet` through `right_boot`.
- Canonical sockets currently equal the module keys. Slot aliases such as `helm`, `torso`, `shoulder_l`, and `boot_r` normalize into those sockets.
- Canonical anchors are `VRM_ANCHOR_BASELINES`; `examples/suitspec.sample.json` contains tuned runtime overrides and is not used as the seed baseline.
- Current mesh assets are `viewer/assets/meshes/*.mesh.json`, format `mesh.v1`, with `positions`, `normals`, `uv`, and `indices`.
- No GLB or OBJ armor-part assets were found under `viewer/assets`; PartCatalog v0.1 allows those kinds for the next asset route but the seed is mesh-json only.
- Current material reality is a single surface slot: `SuitSpec.modules.<module>.texture_path` becomes `MeshStandardMaterial.map`, with `PART_COLOR_MAP` fallback color.

## Seed Choices

- `examples/partcatalog.seed.json` stores one active catalog part for each current module.
- `fit` and `vrm_anchor` values are copied from `armor-canon.js` baselines.
- Asset metrics are measured from the checked-in mesh JSON payloads.
- `surface_base` is the only material slot until assets expose named material IDs or multi-map texture sets.

## Open Risks

- Viewer normalization is not uniform: the Quest demo normalizes mesh geometry while dashboard/body-fit paths can use raw mesh scale plus fit transforms.
- The catalog has no stable runtime resolver yet; parent integration must decide whether SuitManifest stores `part_id`, `module`, or both.
- The UV texture pipeline is still not fully reliable; the seed records mesh UV availability but does not guarantee generated atlas quality.
- Future GLB/OBJ assets need explicit material IDs before this schema can safely model multiple material slots.
