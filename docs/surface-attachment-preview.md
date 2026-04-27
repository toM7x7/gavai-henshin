# Surface Attachment Preview

This contract supports the `Webでスーツ成立 -> Questで変身試験 -> Replayで体験を残す` route without making Quest depend on unfinished placement math.

`viewer/body-fit` emits `surface_first.surface_attachment_preview` in the meta summary. The preview answers a narrow question: which SuitSpec part resolves to which attachment slot, VRM anchor bone, expected body-surface region, and optional mount name.

It is telemetry only. It deliberately does not expose `position`, `normal`, `offset`, `scale`, or `fit`. Those values are still owned by the fit/authoring lane. Quest must not treat this preview as a placement contract yet.

```ts
type SurfaceAttachmentPreview = {
  schema_version: "surface_attachment_preview.v0";
  mode: "telemetry_only";
  source: "body-fit.surface_first";
  applies_to_quest: false;
  tracking_source: string;
  part_count: number;
  enabled_part_count: number;
  evaluated_part_count: number;
  status_counts: Record<
    | "matched_mount"
    | "proxy_region_only"
    | "missing_surface_region"
    | "missing_vrm_anchor"
    | "not_enabled",
    number
  >;
  bindings: Array<{
    part: string;
    attachment_slot: string;
    anchor_bone: string | null;
    expected_region: string | null;
    mount_name: string | null;
    mount_region: string | null;
    status: string;
  }>;
  missing_parts: string[];
  notes: string[];
};
```

Status meanings:

- `matched_mount`: the part has a known surface mount for the expected body region.
- `proxy_region_only`: the part has a usable body-surface region but no dedicated mount yet.
- `missing_surface_region`: the part cannot be mapped to a current surface region.
- `missing_vrm_anchor`: the part has no usable VRM anchor bone.
- `not_enabled`: the SuitSpec module is disabled.

This gives the armor-stand preview a measurable fit surface before full asset rebuilding. The next step is to connect this telemetry to the dashboard as a human-readable fit/UV warning panel, then let Quest import by suit number once pairing/auth boundaries are in place.
