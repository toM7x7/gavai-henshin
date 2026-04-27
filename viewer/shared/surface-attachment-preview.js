const SURFACE_ATTACHMENT_STATUS_KEYS = Object.freeze([
  "matched_mount",
  "proxy_region_only",
  "missing_surface_region",
  "missing_vrm_anchor",
  "not_enabled",
]);

const SURFACE_ATTACHMENT_RULES = Object.freeze({
  helmet: { expectedRegion: "head", mountName: "head_crown" },
  chest: { expectedRegion: "torso", mountName: "chest_front" },
  back: { expectedRegion: "torso", mountName: "upper_back" },
  waist: { expectedRegion: "torso", mountName: "waist_front" },
  left_shoulder: { expectedRegion: "left_upperarm", mountName: "left_shoulder_mount" },
  right_shoulder: { expectedRegion: "right_upperarm", mountName: "right_shoulder_mount" },
  left_upperarm: { expectedRegion: "left_upperarm" },
  right_upperarm: { expectedRegion: "right_upperarm" },
  left_forearm: { expectedRegion: "left_forearm", mountName: "left_forearm_mount" },
  right_forearm: { expectedRegion: "right_forearm", mountName: "right_forearm_mount" },
  left_hand: { expectedRegion: "left_forearm" },
  right_hand: { expectedRegion: "right_forearm" },
  left_thigh: { expectedRegion: "left_thigh" },
  right_thigh: { expectedRegion: "right_thigh" },
  left_shin: { expectedRegion: "left_shin", mountName: "left_shin_mount" },
  right_shin: { expectedRegion: "right_shin", mountName: "right_shin_mount" },
  left_boot: { expectedRegion: "left_foot", mountName: "left_boot_mount" },
  right_boot: { expectedRegion: "right_foot", mountName: "right_boot_mount" },
});

function statusCounter() {
  return Object.fromEntries(SURFACE_ATTACHMENT_STATUS_KEYS.map((key) => [key, 0]));
}

function buildMountIndex(snapshot) {
  const index = new Map();
  for (const mount of snapshot?.mounts || []) {
    if (!mount?.name) continue;
    index.set(String(mount.name), mount);
  }
  return index;
}

function buildRegionSet(snapshot) {
  const regions = new Set();
  for (const region of Object.keys(snapshot?.regionCounts || {})) {
    regions.add(String(region));
  }
  for (const node of snapshot?.nodes || []) {
    if (node?.region) regions.add(String(node.region));
  }
  for (const mount of snapshot?.mounts || []) {
    if (mount?.region) regions.add(String(mount.region));
  }
  return regions;
}

function isEnabledModule(module) {
  return module?.enabled !== false && module?.disabled !== true;
}

function pickStatus({ enabled, anchorBone, expectedRegion, regionSet, mount, rule }) {
  if (!enabled) return "not_enabled";
  if (!anchorBone) return "missing_vrm_anchor";
  if (!expectedRegion || !regionSet.has(expectedRegion)) return "missing_surface_region";
  if (rule?.mountName && mount?.region === expectedRegion) return "matched_mount";
  return "proxy_region_only";
}

export function buildSurfaceAttachmentPreview({
  suitspec,
  snapshot,
  trackingSource = "vrm",
  normalizeAttachmentSlot,
  effectiveVrmAnchorFor,
} = {}) {
  const modules = suitspec?.modules && typeof suitspec.modules === "object" ? suitspec.modules : {};
  const mountIndex = buildMountIndex(snapshot);
  const regionSet = buildRegionSet(snapshot);
  const bindings = [];
  const statusCounts = statusCounter();
  const missingParts = [];
  const notes = [];

  const normalizeSlot =
    typeof normalizeAttachmentSlot === "function"
      ? normalizeAttachmentSlot
      : (partName, module) => String(module?.attachment_slot || partName || "");
  const resolveAnchor =
    typeof effectiveVrmAnchorFor === "function" ? effectiveVrmAnchorFor : () => ({ bone: null });

  for (const [part, module] of Object.entries(modules)) {
    const enabled = isEnabledModule(module);
    const attachmentSlot = String(normalizeSlot(part, module) || part);
    const anchor = resolveAnchor(part, module) || {};
    const anchorBone = typeof anchor.bone === "string" && anchor.bone.trim() ? anchor.bone.trim() : null;
    const rule = SURFACE_ATTACHMENT_RULES[attachmentSlot] || null;
    const expectedRegion = rule?.expectedRegion || null;
    const mountName = rule?.mountName || null;
    const mount = mountName ? mountIndex.get(mountName) || null : null;
    const status = pickStatus({
      enabled,
      anchorBone,
      expectedRegion,
      regionSet,
      mount,
      rule,
    });
    statusCounts[status] += 1;

    const binding = {
      part,
      attachment_slot: attachmentSlot,
      anchor_bone: anchorBone,
      expected_region: expectedRegion,
      mount_name: mountName,
      mount_region: mount?.region || null,
      status,
    };
    bindings.push(binding);
    if (status !== "matched_mount" && status !== "proxy_region_only" && status !== "not_enabled") {
      missingParts.push(part);
    }
  }

  if (!regionSet.size) {
    notes.push("surface_snapshot_has_no_regions");
  }
  if (!(snapshot?.mounts || []).length) {
    notes.push("surface_snapshot_has_no_mounts");
  }

  const enabledPartCount = bindings.filter((binding) => binding.status !== "not_enabled").length;
  return {
    schema_version: "surface_attachment_preview.v0",
    mode: "telemetry_only",
    source: "body-fit.surface_first",
    applies_to_quest: false,
    tracking_source: String(trackingSource || "vrm"),
    part_count: bindings.length,
    enabled_part_count: enabledPartCount,
    evaluated_part_count: enabledPartCount,
    status_counts: statusCounts,
    bindings,
    missing_parts: missingParts,
    notes,
  };
}
