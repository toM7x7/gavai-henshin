// Single source of truth for armor-part fit, color, and VRM anchor conventions.

export const MODULE_VIS = Object.freeze({
  helmet: {
    shape: "sphere",
    source: "chest_core",
    attach: "start",
    offsetY: 0.2,
    scale: [0.3, 0.32, 0.3],
    follow: [0.34, 0.42, 0.34],
    minScale: [0.22, 0.24, 0.22],
    zOffset: 0.02,
  },
  chest: {
    shape: "box",
    source: "chest_core",
    attach: "center",
    offsetY: 0.0,
    scale: [0.72, 0.78, 0.66],
    follow: [0.72, 0.78, 0.72],
    minScale: [0.48, 0.56, 0.46],
  },
  back: {
    shape: "box",
    source: "chest_core",
    attach: "center",
    offsetY: -0.02,
    scale: [0.68, 0.74, 0.6],
    follow: [0.68, 0.76, 0.68],
    minScale: [0.46, 0.54, 0.42],
    zOffset: -0.1,
  },
  waist: {
    shape: "box",
    source: "chest_core",
    attach: "end",
    offsetY: -0.08,
    scale: [0.52, 0.38, 0.46],
    follow: [0.62, 0.7, 0.62],
    minScale: [0.34, 0.28, 0.3],
  },
  left_shoulder: {
    shape: "sphere",
    source: "left_upperarm",
    attach: "start",
    offsetY: 0.08,
    scale: [0.24, 0.24, 0.24],
    follow: [0.56, 0.5, 0.56],
    minScale: [0.16, 0.16, 0.16],
  },
  right_shoulder: {
    shape: "sphere",
    source: "right_upperarm",
    attach: "start",
    offsetY: 0.08,
    scale: [0.24, 0.24, 0.24],
    follow: [0.56, 0.5, 0.56],
    minScale: [0.16, 0.16, 0.16],
  },
  left_upperarm: {
    shape: "cylinder",
    source: "left_upperarm",
    attach: "center",
    offsetY: 0.0,
    scale: [0.94, 1.0, 0.94],
    follow: [0.88, 0.94, 0.88],
    minScale: [0.52, 0.56, 0.52],
  },
  right_upperarm: {
    shape: "cylinder",
    source: "right_upperarm",
    attach: "center",
    offsetY: 0.0,
    scale: [0.94, 1.0, 0.94],
    follow: [0.88, 0.94, 0.88],
    minScale: [0.52, 0.56, 0.52],
  },
  left_forearm: {
    shape: "cylinder",
    source: "left_forearm",
    attach: "center",
    offsetY: 0.0,
    scale: [0.9, 1.02, 0.9],
    follow: [0.9, 0.96, 0.9],
    minScale: [0.48, 0.56, 0.48],
  },
  right_forearm: {
    shape: "cylinder",
    source: "right_forearm",
    attach: "center",
    offsetY: 0.0,
    scale: [0.9, 1.02, 0.9],
    follow: [0.9, 0.96, 0.9],
    minScale: [0.48, 0.56, 0.48],
  },
  left_hand: {
    shape: "sphere",
    source: "left_forearm",
    attach: "end",
    offsetY: -0.08,
    scale: [0.2, 0.2, 0.2],
    follow: [0.38, 0.34, 0.38],
    minScale: [0.14, 0.14, 0.14],
    zOffset: 0.03,
  },
  right_hand: {
    shape: "sphere",
    source: "right_forearm",
    attach: "end",
    offsetY: -0.08,
    scale: [0.2, 0.2, 0.2],
    follow: [0.38, 0.34, 0.38],
    minScale: [0.14, 0.14, 0.14],
    zOffset: 0.03,
  },
  left_thigh: {
    shape: "cylinder",
    source: "left_thigh",
    attach: "center",
    offsetY: 0.0,
    scale: [1.0, 1.04, 1.0],
    follow: [0.94, 0.96, 0.94],
    minScale: [0.56, 0.66, 0.56],
  },
  right_thigh: {
    shape: "cylinder",
    source: "right_thigh",
    attach: "center",
    offsetY: 0.0,
    scale: [1.0, 1.04, 1.0],
    follow: [0.94, 0.96, 0.94],
    minScale: [0.56, 0.66, 0.56],
  },
  left_shin: {
    shape: "cylinder",
    source: "left_shin",
    attach: "center",
    offsetY: 0.0,
    scale: [0.96, 1.04, 0.96],
    follow: [0.92, 0.96, 0.92],
    minScale: [0.52, 0.64, 0.52],
  },
  right_shin: {
    shape: "cylinder",
    source: "right_shin",
    attach: "center",
    offsetY: 0.0,
    scale: [0.96, 1.04, 0.96],
    follow: [0.92, 0.96, 0.92],
    minScale: [0.52, 0.64, 0.52],
  },
  left_boot: {
    shape: "box",
    source: "left_shin",
    attach: "end",
    offsetY: -0.14,
    scale: [0.28, 0.22, 0.4],
    follow: [0.58, 0.52, 0.62],
    minScale: [0.2, 0.16, 0.24],
    zOffset: 0.08,
  },
  right_boot: {
    shape: "box",
    source: "right_shin",
    attach: "end",
    offsetY: -0.14,
    scale: [0.28, 0.22, 0.4],
    follow: [0.58, 0.52, 0.62],
    minScale: [0.2, 0.16, 0.24],
    zOffset: 0.08,
  },
});

export const VRM_ANCHOR_BASELINES = Object.freeze({
  helmet: { bone: "head", offset: [0, 0.08, 0.12], rotation: [0, 0, 0], scale: [1, 1, 1] },
  chest: { bone: "upperChest", offset: [0, 0.03, 0.1], rotation: [0, 0, 0], scale: [1, 1, 1] },
  back: { bone: "upperChest", offset: [0, 0.01, -0.1], rotation: [0, 180, 0], scale: [1, 1, 1] },
  waist: { bone: "hips", offset: [0, 0.0, 0.06], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_shoulder: { bone: "leftShoulder", offset: [0.02, 0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_shoulder: { bone: "rightShoulder", offset: [-0.02, 0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_upperarm: { bone: "leftUpperArm", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_upperarm: { bone: "rightUpperArm", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_forearm: { bone: "leftLowerArm", offset: [0, -0.01, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_forearm: { bone: "rightLowerArm", offset: [0, -0.01, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_hand: { bone: "leftHand", offset: [0, 0, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_hand: { bone: "rightHand", offset: [0, 0, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_thigh: { bone: "leftUpperLeg", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_thigh: { bone: "rightUpperLeg", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_shin: { bone: "leftLowerLeg", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_shin: { bone: "rightLowerLeg", offset: [0, -0.02, 0.02], rotation: [0, 0, 0], scale: [1, 1, 1] },
  left_boot: { bone: "leftFoot", offset: [0, -0.01, 0.08], rotation: [0, 0, 0], scale: [1, 1, 1] },
  right_boot: { bone: "rightFoot", offset: [0, -0.01, 0.08], rotation: [0, 0, 0], scale: [1, 1, 1] },
});

export const VRM_BONE_ALIASES = Object.freeze({
  hips: ["hips", "j_bip_c_hips", "pelvis"],
  spine: ["spine", "j_bip_c_spine", "spine1"],
  chest: ["chest", "j_bip_c_chest", "spine2"],
  upperChest: ["upperchest", "upper_chest", "j_bip_c_upperchest", "spine3"],
  neck: ["neck", "j_bip_c_neck"],
  head: ["head", "j_bip_c_head"],
  leftShoulder: ["leftshoulder", "j_bip_l_shoulder", "l_shoulder", "shoulder_l"],
  rightShoulder: ["rightshoulder", "j_bip_r_shoulder", "r_shoulder", "shoulder_r"],
  leftUpperArm: ["leftupperarm", "j_bip_l_upperarm", "l_upperarm", "upperarm_l"],
  rightUpperArm: ["rightupperarm", "j_bip_r_upperarm", "r_upperarm", "upperarm_r"],
  leftLowerArm: ["leftlowerarm", "j_bip_l_lowerarm", "l_forearm", "lowerarm_l"],
  rightLowerArm: ["rightlowerarm", "j_bip_r_lowerarm", "r_forearm", "lowerarm_r"],
  leftHand: ["lefthand", "j_bip_l_hand", "l_hand", "hand_l"],
  rightHand: ["righthand", "j_bip_r_hand", "r_hand", "hand_r"],
  leftUpperLeg: ["leftupperleg", "j_bip_l_upperleg", "l_thigh", "upleg_l"],
  rightUpperLeg: ["rightupperleg", "j_bip_r_upperleg", "r_thigh", "upleg_r"],
  leftLowerLeg: ["leftlowerleg", "j_bip_l_lowerleg", "l_shin", "leg_l"],
  rightLowerLeg: ["rightlowerleg", "j_bip_r_lowerleg", "r_shin", "leg_r"],
  leftFoot: ["leftfoot", "j_bip_l_foot", "l_foot", "foot_l"],
  rightFoot: ["rightfoot", "j_bip_r_foot", "r_foot", "foot_r"],
});

export const VRM_PART_BONE_FALLBACKS = Object.freeze({
  helmet: ["head", "neck", "upperChest", "chest"],
  chest: ["upperChest", "chest", "spine", "hips"],
  back: ["upperChest", "chest", "spine"],
  waist: ["hips", "spine"],
  left_shoulder: ["leftShoulder", "leftUpperArm", "upperChest", "chest"],
  right_shoulder: ["rightShoulder", "rightUpperArm", "upperChest", "chest"],
  left_upperarm: ["leftUpperArm", "leftShoulder", "leftLowerArm"],
  right_upperarm: ["rightUpperArm", "rightShoulder", "rightLowerArm"],
  left_forearm: ["leftLowerArm", "leftUpperArm", "leftHand"],
  right_forearm: ["rightLowerArm", "rightUpperArm", "rightHand"],
  left_hand: ["leftHand", "leftLowerArm"],
  right_hand: ["rightHand", "rightLowerArm"],
  left_thigh: ["leftUpperLeg", "hips", "leftLowerLeg"],
  right_thigh: ["rightUpperLeg", "hips", "rightLowerLeg"],
  left_shin: ["leftLowerLeg", "leftUpperLeg", "leftFoot"],
  right_shin: ["rightLowerLeg", "rightUpperLeg", "rightFoot"],
  left_boot: ["leftFoot", "leftLowerLeg"],
  right_boot: ["rightFoot", "rightLowerLeg"],
});

export const ATTACHMENT_SLOT_ALIASES = Object.freeze({
  helm: "helmet",
  torso: "chest",
  chest_core: "chest",
  shoulder_l: "left_shoulder",
  shoulder_r: "right_shoulder",
  upperarm_l: "left_upperarm",
  upperarm_r: "right_upperarm",
  forearm_l: "left_forearm",
  forearm_r: "right_forearm",
  hand_l: "left_hand",
  hand_r: "right_hand",
  thigh_l: "left_thigh",
  thigh_r: "right_thigh",
  shin_l: "left_shin",
  shin_r: "right_shin",
  boot_l: "left_boot",
  boot_r: "right_boot",
});

export const PART_COLOR_MAP = Object.freeze({
  helmet: 0xffcd4f,
  chest: 0x4fa8ff,
  back: 0x4f88e8,
  waist: 0x62c9ff,
  left_shoulder: 0xff8f6a,
  right_shoulder: 0xff6a8f,
  left_upperarm: 0x9a8cff,
  right_upperarm: 0x7f99ff,
  left_forearm: 0x63d5ff,
  right_forearm: 0x5deec3,
  left_hand: 0xd4ff73,
  right_hand: 0xb2ff73,
  left_thigh: 0xff8ec8,
  right_thigh: 0xff82ab,
  left_shin: 0x7cd7ff,
  right_shin: 0x63c6ff,
  left_boot: 0xffe48a,
  right_boot: 0xffd36f,
});

export const FIT_CONTACT_PAIRS = Object.freeze([
  ["helmet", "chest"],
  ["chest", "waist"],
  ["chest", "back"],
  ["left_shoulder", "left_upperarm"],
  ["right_shoulder", "right_upperarm"],
  ["left_upperarm", "left_forearm"],
  ["right_upperarm", "right_forearm"],
  ["left_forearm", "left_hand"],
  ["right_forearm", "right_hand"],
  ["waist", "left_thigh"],
  ["waist", "right_thigh"],
  ["left_thigh", "left_shin"],
  ["right_thigh", "right_shin"],
  ["left_shin", "left_boot"],
  ["right_shin", "right_boot"],
]);

export const VRM_HUMANOID_BONES = Object.freeze([
  "hips",
  "spine",
  "chest",
  "upperChest",
  "neck",
  "head",
  "leftShoulder",
  "rightShoulder",
  "leftUpperArm",
  "rightUpperArm",
  "leftLowerArm",
  "rightLowerArm",
  "leftHand",
  "rightHand",
  "leftUpperLeg",
  "rightUpperLeg",
  "leftLowerLeg",
  "rightLowerLeg",
  "leftFoot",
  "rightFoot",
]);

function numberOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function normalizeVec3(input, fallback) {
  const fb = Array.isArray(fallback) && fallback.length >= 3 ? fallback : [1, 1, 1];
  if (Array.isArray(input) && input.length >= 3) {
    return [numberOr(input[0], fb[0]), numberOr(input[1], fb[1]), numberOr(input[2], fb[2])];
  }
  if (input && typeof input === "object") {
    return [numberOr(input.x, fb[0]), numberOr(input.y, fb[1]), numberOr(input.z, fb[2])];
  }
  return [...fb];
}

export function normalizeBoneName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

export function normalizeFit(rawFit, fallback) {
  const base = fallback || {
    shape: "box",
    source: "chest_core",
    attach: "center",
    offsetY: 0,
    zOffset: 0,
    scale: [0.2, 0.2, 0.2],
    follow: [1, 1, 1],
    minScale: [0.2, 0.2, 0.2],
  };
  const fit = rawFit && typeof rawFit === "object" ? rawFit : {};
  const attach = String(fit.attach ?? base.attach ?? "center").trim().toLowerCase();
  return {
    shape: typeof fit.shape === "string" && fit.shape.trim() ? fit.shape.trim() : String(base.shape ?? "box"),
    source:
      typeof fit.source === "string" && fit.source.trim() ? fit.source.trim() : String(base.source ?? "chest_core"),
    attach: attach === "start" || attach === "end" ? attach : "center",
    offsetY: numberOr(fit.offsetY, numberOr(base.offsetY, 0)),
    zOffset: numberOr(fit.zOffset, numberOr(base.zOffset, 0)),
    scale: normalizeVec3(fit.scale, base.scale ?? [0.2, 0.2, 0.2]),
    follow: normalizeVec3(fit.follow, base.follow ?? [1, 1, 1]),
    minScale: normalizeVec3(fit.minScale, base.minScale ?? [0.2, 0.2, 0.2]),
  };
}

export function baseFitFor(partName) {
  return normalizeFit(MODULE_VIS[partName], null);
}

export const defaultModuleVisualConfig = baseFitFor;

export function effectiveFitFor(partName, module) {
  return normalizeFit(module?.fit, baseFitFor(partName));
}

export const getModuleVisualConfig = effectiveFitFor;

export function normalizeVrmAnchor(rawAnchor, fallback) {
  const base = fallback || {
    bone: "chest",
    offset: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: [1, 1, 1],
  };
  const anchor = rawAnchor && typeof rawAnchor === "object" ? rawAnchor : {};
  const bone = String(anchor.bone ?? base.bone ?? "chest").trim() || "chest";
  return {
    bone,
    offset: normalizeVec3(anchor.offset, base.offset),
    rotation: normalizeVec3(anchor.rotation, base.rotation),
    scale: normalizeVec3(anchor.scale, base.scale).map((v) => Math.max(0.01, numberOr(v, 1))),
  };
}

export function normalizeAttachmentSlot(partName, module) {
  const fallback = String(partName || "").trim();
  const raw = String(module?.attachment_slot || fallback)
    .trim()
    .toLowerCase();
  if (!raw) return fallback;
  if (VRM_ANCHOR_BASELINES[raw]) return raw;
  const alias = ATTACHMENT_SLOT_ALIASES[raw];
  if (alias && VRM_ANCHOR_BASELINES[alias]) return alias;
  const collapsed = raw.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (VRM_ANCHOR_BASELINES[collapsed]) return collapsed;
  const collapsedAlias = ATTACHMENT_SLOT_ALIASES[collapsed];
  if (collapsedAlias && VRM_ANCHOR_BASELINES[collapsedAlias]) return collapsedAlias;
  return fallback;
}

export function baseVrmAnchorFor(slotName) {
  const key = String(slotName || "").trim();
  return normalizeVrmAnchor(VRM_ANCHOR_BASELINES[key], null);
}

export function effectiveVrmAnchorFor(partName, module) {
  const slot = normalizeAttachmentSlot(partName, module);
  return normalizeVrmAnchor(module?.vrm_anchor, baseVrmAnchorFor(slot));
}

export function partColor(partName) {
  return PART_COLOR_MAP[partName] || 0x7eb6ff;
}
