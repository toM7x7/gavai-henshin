# Armor Parts Intake

External GLB armor parts are staged here.

Expected layout:

```text
viewer/assets/armor-parts/<module>/<module>.glb
viewer/assets/armor-parts/<module>/<module>.modeler.json
viewer/assets/armor-parts/<module>/source/<module>.blend
viewer/assets/armor-parts/<module>/textures/
viewer/assets/armor-parts/<module>/preview/<module>.mesh.json
```

The current runtime still uses `viewer/assets/meshes/*.mesh.json` as the seed/proxy fallback.
See `docs/modeler-armor-brief.md` and `GET /v1/catalog/part-blueprints` before adding final GLB assets.
Texture generation for this route is Nano Banana only; do not prepare provider-specific fal/openai texture assumptions for these parts.
