import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const DEFAULT_SUITSPEC = "examples/suitspec.sample.json";
const DEFAULT_SIM = "sessions/body-sim.json";

const PANEL = {
  suitspecPath: document.getElementById("suitspecPath"),
  simPath: document.getElementById("simPath"),
  btnLoad: document.getElementById("btnLoad"),
  btnPlay: document.getElementById("btnPlay"),
  btnPrev: document.getElementById("btnPrev"),
  btnNext: document.getElementById("btnNext"),
  btnTexture: document.getElementById("btnTexture"),
  btnTheme: document.getElementById("btnTheme"),
  btnCamFront: document.getElementById("btnCamFront"),
  btnCamSide: document.getElementById("btnCamSide"),
  btnCamTop: document.getElementById("btnCamTop"),
  btnFit: document.getElementById("btnFit"),
  frameSlider: document.getElementById("frameSlider"),
  speedSlider: document.getElementById("speedSlider"),
  reliefSlider: document.getElementById("reliefSlider"),
  vrmPath: document.getElementById("vrmPath"),
  btnVrmLoad: document.getElementById("btnVrmLoad"),
  btnVrmClear: document.getElementById("btnVrmClear"),
  btnVrmToggle: document.getElementById("btnVrmToggle"),
  btnVrmAttach: document.getElementById("btnVrmAttach"),
  vrmStatus: document.getElementById("vrmStatus"),
  btnLiveStart: document.getElementById("btnLiveStart"),
  btnLiveStop: document.getElementById("btnLiveStop"),
  liveStatus: document.getElementById("liveStatus"),
  liveVideo: document.getElementById("liveVideo"),
  fitPart: document.getElementById("fitPart"),
  fitScaleX: document.getElementById("fitScaleX"),
  fitScaleY: document.getElementById("fitScaleY"),
  fitScaleZ: document.getElementById("fitScaleZ"),
  fitOffsetY: document.getElementById("fitOffsetY"),
  fitZOffset: document.getElementById("fitZOffset"),
  btnFitSuggestCurrent: document.getElementById("btnFitSuggestCurrent"),
  btnFitApplyCurrent: document.getElementById("btnFitApplyCurrent"),
  btnFitResetCurrent: document.getElementById("btnFitResetCurrent"),
  btnFitSaveSuitspec: document.getElementById("btnFitSaveSuitspec"),
  btnBridgeToggle: document.getElementById("btnBridgeToggle"),
  bridgeThickness: document.getElementById("bridgeThickness"),
  status: document.getElementById("status"),
  meta: document.getElementById("meta"),
  legendText: document.getElementById("legendText"),
};

const textureLoader = new THREE.TextureLoader();
const meshGeometryCache = new Map();
const DEFAULT_VRM_PATH = "viewer/assets/vrm/default.vrm";
let gltfLoaderModulePromise = null;
let threeVrmModulePromise = null;
const THREE_VERSION = "0.180.0";
const THREE_VRM_VERSION = "3.4.4";

const MODULE_VIS = {
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
};

const VRM_ANCHOR_BASELINES = {
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
};

const VRM_BONE_ALIASES = {
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
};

const DEFAULT_SEGMENT_POSE = {
  chest_core: {
    position_x: 0.55,
    position_y: -0.25,
    position_z: 0.22,
    rotation_z: 0,
    scale_x: 1,
    scale_y: 1,
    scale_z: 1,
  },
  left_upperarm: {
    position_x: 0.22,
    position_y: -0.02,
    position_z: 0.22,
    rotation_z: 0.2,
    scale_x: 0.9,
    scale_y: 0.95,
    scale_z: 0.9,
  },
  right_upperarm: {
    position_x: 0.88,
    position_y: -0.02,
    position_z: 0.22,
    rotation_z: -0.2,
    scale_x: 0.9,
    scale_y: 0.95,
    scale_z: 0.9,
  },
  left_forearm: {
    position_x: 0.16,
    position_y: -0.42,
    position_z: 0.22,
    rotation_z: 0.18,
    scale_x: 0.88,
    scale_y: 0.95,
    scale_z: 0.88,
  },
  right_forearm: {
    position_x: 0.94,
    position_y: -0.42,
    position_z: 0.22,
    rotation_z: -0.18,
    scale_x: 0.88,
    scale_y: 0.95,
    scale_z: 0.88,
  },
  left_thigh: {
    position_x: 0.42,
    position_y: -0.72,
    position_z: 0.22,
    rotation_z: 0.04,
    scale_x: 0.95,
    scale_y: 1.05,
    scale_z: 0.95,
  },
  right_thigh: {
    position_x: 0.68,
    position_y: -0.72,
    position_z: 0.22,
    rotation_z: -0.04,
    scale_x: 0.95,
    scale_y: 1.05,
    scale_z: 0.95,
  },
  left_shin: {
    position_x: 0.42,
    position_y: -1.18,
    position_z: 0.22,
    rotation_z: 0.02,
    scale_x: 0.92,
    scale_y: 1.05,
    scale_z: 0.92,
  },
  right_shin: {
    position_x: 0.68,
    position_y: -1.18,
    position_z: 0.22,
    rotation_z: -0.02,
    scale_x: 0.92,
    scale_y: 1.05,
    scale_z: 0.92,
  },
};

const PART_COLOR_MAP = {
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
};

const FIT_CONTACT_PAIRS = [
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
];

const POSE_IDX = {
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
};

const LIVE_SEGMENT_SPECS = [
  {
    name: "right_upperarm",
    startJoint: "right_shoulder",
    endJoint: "right_elbow",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "right_forearm",
    startJoint: "right_elbow",
    endJoint: "right_wrist",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "left_upperarm",
    startJoint: "left_shoulder",
    endJoint: "left_elbow",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "left_forearm",
    startJoint: "left_elbow",
    endJoint: "left_wrist",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "right_thigh",
    startJoint: "right_hip",
    endJoint: "right_knee",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "right_shin",
    startJoint: "right_knee",
    endJoint: "right_ankle",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "left_thigh",
    startJoint: "left_hip",
    endJoint: "left_knee",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "left_shin",
    startJoint: "left_knee",
    endJoint: "left_ankle",
    radiusFactor: 0.22,
    radiusMin: 0.05,
    radiusMax: 0.22,
    z: 0.22,
    smoothGain: 18.0,
  },
  {
    name: "chest_core",
    startJoint: "left_shoulder",
    endJoint: "right_hip",
    radiusFactor: 0.38,
    radiusMin: 0.05,
    radiusMax: 0.35,
    z: 0.22,
    smoothGain: 18.0,
  },
];

function toNumberOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeVec3(input, fallback) {
  const fb = Array.isArray(fallback) && fallback.length >= 3 ? fallback : [1, 1, 1];
  if (Array.isArray(input) && input.length >= 3) {
    return [
      toNumberOr(input[0], fb[0]),
      toNumberOr(input[1], fb[1]),
      toNumberOr(input[2], fb[2]),
    ];
  }
  if (input && typeof input === "object") {
    return [
      toNumberOr(input.x, fb[0]),
      toNumberOr(input.y, fb[1]),
      toNumberOr(input.z, fb[2]),
    ];
  }
  return [...fb];
}

function normalizeBoneName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function normalizeVrmAnchor(rawAnchor, fallback) {
  const base = fallback || {
    bone: "chest",
    offset: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: [1, 1, 1],
  };
  const anchor = rawAnchor && typeof rawAnchor === "object" ? rawAnchor : {};
  return {
    bone: String(anchor.bone ?? base.bone ?? "chest"),
    offset: normalizeVec3(anchor.offset, base.offset),
    rotation: normalizeVec3(anchor.rotation, base.rotation),
    scale: normalizeVec3(anchor.scale, base.scale).map((v) => Math.max(0.01, Number(v || 1))),
  };
}

function baseVrmAnchorFor(partName) {
  return normalizeVrmAnchor(VRM_ANCHOR_BASELINES[partName], null);
}

function effectiveVrmAnchorFor(partName, module) {
  return normalizeVrmAnchor(module?.vrm_anchor, baseVrmAnchorFor(partName));
}

function defaultModuleVisualConfig(name) {
  const base = MODULE_VIS[name];
  if (!base) {
    return {
      shape: "box",
      source: "chest_core",
      attach: "center",
      offsetY: 0,
      zOffset: 0,
      scale: [0.2, 0.2, 0.2],
      follow: [1, 1, 1],
      minScale: [0.2, 0.2, 0.2],
    };
  }
  return {
    ...base,
    scale: normalizeVec3(base.scale, [1, 1, 1]),
    follow: normalizeVec3(base.follow, [1, 1, 1]),
    minScale: normalizeVec3(base.minScale, [0.2, 0.2, 0.2]),
  };
}

function getModuleVisualConfig(name, module) {
  const merged = defaultModuleVisualConfig(name);
  const fit = module?.fit;
  if (!fit || typeof fit !== "object") return merged;

  if (typeof fit.shape === "string" && fit.shape.trim()) {
    merged.shape = fit.shape.trim();
  }
  if (typeof fit.source === "string" && fit.source.trim()) {
    merged.source = fit.source.trim();
  }
  if (typeof fit.attach === "string") {
    const attach = fit.attach.trim().toLowerCase();
    if (attach === "start" || attach === "center" || attach === "end") {
      merged.attach = attach;
    }
  }
  merged.offsetY = toNumberOr(fit.offsetY, toNumberOr(merged.offsetY, 0));
  merged.zOffset = toNumberOr(fit.zOffset, toNumberOr(merged.zOffset, 0));
  merged.scale = normalizeVec3(fit.scale, merged.scale);
  merged.follow = normalizeVec3(fit.follow, merged.follow);
  merged.minScale = normalizeVec3(fit.minScale, merged.minScale);
  return merged;
}

function countFitOverrides(suitspec) {
  const modules = suitspec?.modules || {};
  return Object.values(modules).filter((module) => module && typeof module.fit === "object").length;
}

function round3(value) {
  return Math.round(Number(value || 0) * 1000) / 1000;
}

function aabbGapAndPenetration(a, b) {
  const gapX = Math.max(0, Math.max(a.min.x - b.max.x, b.min.x - a.max.x));
  const gapY = Math.max(0, Math.max(a.min.y - b.max.y, b.min.y - a.max.y));
  const gapZ = Math.max(0, Math.max(a.min.z - b.max.z, b.min.z - a.max.z));
  const gap = Math.hypot(gapX, gapY, gapZ);

  const overlapX = Math.min(a.max.x, b.max.x) - Math.max(a.min.x, b.min.x);
  const overlapY = Math.min(a.max.y, b.max.y) - Math.max(a.min.y, b.min.y);
  const overlapZ = Math.min(a.max.z, b.max.z) - Math.max(a.min.z, b.min.z);
  const penetration =
    overlapX > 0 && overlapY > 0 && overlapZ > 0 ? Math.min(overlapX, overlapY, overlapZ) : 0;
  return { gap, penetration };
}

function fitPairScore(gap, penetration) {
  const gapPenalty = clamp(gap / 0.09, 0, 1);
  const penetrationPenalty = clamp(penetration / 0.05, 0, 1);
  return clamp(1 - gapPenalty * 0.65 - penetrationPenalty * 0.35, 0, 1);
}

function supportPointOnBoxFace(box, towardPoint) {
  const center = box.getCenter(new THREE.Vector3());
  const dir = new THREE.Vector3().subVectors(towardPoint, center);
  const ax = Math.abs(dir.x);
  const ay = Math.abs(dir.y);
  const az = Math.abs(dir.z);
  if (ax >= ay && ax >= az) {
    return new THREE.Vector3(dir.x >= 0 ? box.max.x : box.min.x, center.y, center.z);
  }
  if (ay >= ax && ay >= az) {
    return new THREE.Vector3(center.x, dir.y >= 0 ? box.max.y : box.min.y, center.z);
  }
  return new THREE.Vector3(center.x, center.y, dir.z >= 0 ? box.max.z : box.min.z);
}

function normToWorld(x01, y01, mirror = true) {
  const xNorm = mirror ? 1 - x01 : x01;
  const x = xNorm * 2 - 1;
  const y = -(y01 * 2 - 1);
  return { x, y };
}

function extractPoseJointsWorld(landmarks) {
  const pick = (index) => landmarks?.[index] || null;
  const joints = {};

  const lShoulder = pick(POSE_IDX.LEFT_SHOULDER);
  const rShoulder = pick(POSE_IDX.RIGHT_SHOULDER);
  const lElbow = pick(POSE_IDX.LEFT_ELBOW);
  const rElbow = pick(POSE_IDX.RIGHT_ELBOW);
  const lWrist = pick(POSE_IDX.LEFT_WRIST);
  const rWrist = pick(POSE_IDX.RIGHT_WRIST);
  const lHip = pick(POSE_IDX.LEFT_HIP);
  const rHip = pick(POSE_IDX.RIGHT_HIP);
  const lKnee = pick(POSE_IDX.LEFT_KNEE);
  const rKnee = pick(POSE_IDX.RIGHT_KNEE);
  const lAnkle = pick(POSE_IDX.LEFT_ANKLE);
  const rAnkle = pick(POSE_IDX.RIGHT_ANKLE);

  if (lShoulder) joints.left_shoulder = normToWorld(lShoulder.x, lShoulder.y, true);
  if (rShoulder) joints.right_shoulder = normToWorld(rShoulder.x, rShoulder.y, true);
  if (lElbow) joints.left_elbow = normToWorld(lElbow.x, lElbow.y, true);
  if (rElbow) joints.right_elbow = normToWorld(rElbow.x, rElbow.y, true);
  if (lWrist) joints.left_wrist = normToWorld(lWrist.x, lWrist.y, true);
  if (rWrist) joints.right_wrist = normToWorld(rWrist.x, rWrist.y, true);
  if (lHip) joints.left_hip = normToWorld(lHip.x, lHip.y, true);
  if (rHip) joints.right_hip = normToWorld(rHip.x, rHip.y, true);
  if (lKnee) joints.left_knee = normToWorld(lKnee.x, lKnee.y, true);
  if (rKnee) joints.right_knee = normToWorld(rKnee.x, rKnee.y, true);
  if (lAnkle) joints.left_ankle = normToWorld(lAnkle.x, lAnkle.y, true);
  if (rAnkle) joints.right_ankle = normToWorld(rAnkle.x, rAnkle.y, true);
  return joints;
}

class BodyFitViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
    this.camera.position.set(0, 0.2, 2.8);

    this.controls = new OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 0, 0.2);
    this.controls.maxDistance = 5.0;
    this.controls.minDistance = 1.0;

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.bridgeGroup = new THREE.Group();
    this.root.add(this.bridgeGroup);
    this.vrmGroup = new THREE.Group();
    this.scene.add(this.vrmGroup);

    this.grid = new THREE.GridHelper(3.2, 32, 0x9ab4dc, 0xd6e1f2);
    this.grid.position.y = -1.0;
    this.grid.rotation.x = Math.PI / 2;
    this.scene.add(this.grid);

    this.floor = new THREE.Mesh(
      new THREE.CircleGeometry(1.65, 80),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.94 })
    );
    this.floor.position.set(0, -1.0, -0.15);
    this.scene.add(this.floor);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(2, 3, 4);
    this.scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xeaf2ff, 0.7);
    fillLight.position.set(-2, 1, 2);
    this.scene.add(fillLight);
    this.scene.add(new THREE.HemisphereLight(0xd8e8ff, 0xaac7eb, 0.7));

    this.meshes = new Map();
    this.frames = [];
    this.frameIndex = 0;
    this.playing = false;
    this.playbackAccumSec = 0;
    this.speed = 1.0;
    this.useTextures = true;
    this.reliefStrength = Number(PANEL.reliefSlider?.value || "0.05");
    if (!Number.isFinite(this.reliefStrength)) this.reliefStrength = 0.05;
    this.bridgeEnabled = true;
    this.bridgeThickness = clamp(Number(PANEL.bridgeThickness?.value || 0.1), 0.03, 0.22);
    this.bridgeVisibleCount = 0;
    this.bridgeMeshes = new Map();
    this.darkTheme = false;
    this.modelCenter = new THREE.Vector3(0, 0, 0.2);
    this.modelRadius = 0.85;
    this.loadedSuitspecPath = "";
    this.loadedSimPath = "";
    this.fitStats = {
      pairCount: 0,
      meanGap: 0,
      meanPenetration: 0,
      score: 0,
      pairs: [],
      weakest: [],
    };
    this.live = {
      active: false,
      video: null,
      stream: null,
      landmarker: null,
      lastVideoTime: -1,
      lastNowMs: performance.now(),
      fps: 0,
    };
    this.liveFollowers = new Map();
    this.vrm = {
      model: null,
      skeleton: null,
      instance: null,
      boneMap: new Map(),
      path: "",
      visible: true,
      attachArmor: true,
      boneCount: 0,
      error: "",
    };

    this.lastTime = performance.now();
    this.updateBridgeButton();
    this.updateVrmButton();
    this.updateVrmAttachButton();
    this.updateVrmStatus("VRM: not loaded");
    this.resize();
    window.addEventListener("resize", () => this.resize());
    requestAnimationFrame((t) => this.tick(t));
  }

  resize() {
    const w = this.canvas.clientWidth || window.innerWidth;
    const h = this.canvas.clientHeight || window.innerHeight;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
  }

  setStatus(text, isError = false) {
    PANEL.status.textContent = text;
    PANEL.status.classList.toggle("error", Boolean(isError));
  }

  setMeta(meta) {
    PANEL.meta.textContent = JSON.stringify(meta, null, 2);
  }

  updateMetaPanel() {
    const sim = this.sim || {};
    this.setMeta({
      suitspec: this.loadedSuitspecPath || PANEL.suitspecPath.value,
      sim: this.loadedSimPath || PANEL.simPath.value,
      modules: this.meshes.size,
      fit_overrides: countFitOverrides(this.suitspec),
      frames: this.frames.length,
      segments: Array.isArray(sim.segments) ? sim.segments.length : 0,
      equip_frame: sim.equip_frame ?? -1,
      equipped: sim.equipped ?? false,
      textures: this.useTextures,
      theme: this.darkTheme ? "dark" : "bright",
      fit_score: round3((this.fitStats?.score || 0) * 100),
      fit_pair_count: this.fitStats?.pairCount || 0,
      fit_mean_gap: round3(this.fitStats?.meanGap || 0),
      fit_mean_penetration: round3(this.fitStats?.meanPenetration || 0),
      fit_weak_pairs: (this.fitStats?.weakest || []).map((w) => ({
        pair: w.pair,
        score: round3(w.score * 100),
        gap: round3(w.gap),
        penetration: round3(w.penetration),
      })),
      bridge_enabled: this.bridgeEnabled,
      bridge_thickness: round3(this.bridgeThickness),
      bridge_visible_count: this.bridgeVisibleCount,
      vrm_path: this.vrm.path || null,
      vrm_bones_visible: this.vrm.visible,
      vrm_attach_armor: this.vrm.attachArmor,
      vrm_bone_count: this.vrm.boneCount || 0,
      vrm_error: this.vrm.error || null,
      three_revision: THREE.REVISION,
      three_target: THREE_VERSION,
      three_vrm_target: THREE_VRM_VERSION,
      live_active: this.live?.active || false,
      live_fps: round3(this.live?.fps || 0),
    });
  }

  updateLiveStatus(text, isError = false) {
    if (!PANEL.liveStatus) return;
    PANEL.liveStatus.textContent = text;
    PANEL.liveStatus.style.color = isError ? "#b41f2f" : "#264b7f";
  }

  updateBridgeButton() {
    if (PANEL.btnBridgeToggle) {
      PANEL.btnBridgeToggle.textContent = `Bridges: ${this.bridgeEnabled ? "On" : "Off"}`;
    }
  }

  updateVrmButton() {
    if (PANEL.btnVrmToggle) {
      PANEL.btnVrmToggle.textContent = `VRM Bones: ${this.vrm.visible ? "On" : "Off"}`;
    }
  }

  updateVrmAttachButton() {
    if (PANEL.btnVrmAttach) {
      PANEL.btnVrmAttach.textContent = `Attach: ${this.vrm.attachArmor ? "VRM" : "BodySim"}`;
    }
  }

  updateVrmStatus(text, isError = false) {
    if (!PANEL.vrmStatus) return;
    PANEL.vrmStatus.textContent = text;
    PANEL.vrmStatus.style.color = isError ? "#b41f2f" : "#264b7f";
  }

  setVrmVisible(enabled) {
    this.vrm.visible = Boolean(enabled);
    if (this.vrm.skeleton) this.vrm.skeleton.visible = this.vrm.visible;
    this.updateVrmButton();
    this.updateMetaPanel();
    this.setLegend();
  }

  setVrmAttachArmor(enabled) {
    this.vrm.attachArmor = Boolean(enabled);
    this.updateVrmAttachButton();
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    this.updateMetaPanel();
    this.setLegend();
  }

  clearVrmModel() {
    if (this.vrm.skeleton) {
      this.vrmGroup.remove(this.vrm.skeleton);
      const mat = this.vrm.skeleton.material;
      this.vrm.skeleton.geometry?.dispose?.();
      if (Array.isArray(mat)) {
        for (const m of mat) m?.dispose?.();
      } else {
        mat?.dispose?.();
      }
    }
    if (this.vrm.model) {
      this.vrmGroup.remove(this.vrm.model);
      this.vrm.model.traverse((obj) => {
        if (!obj.isMesh) return;
        obj.geometry?.dispose?.();
        const material = obj.material;
        if (Array.isArray(material)) {
          for (const m of material) m?.dispose?.();
        } else {
          material?.dispose?.();
        }
      });
    }
    this.vrm.model = null;
    this.vrm.skeleton = null;
    this.vrm.instance = null;
    this.vrm.boneMap = new Map();
    this.vrm.path = "";
    this.vrm.boneCount = 0;
    this.vrm.error = "";
    this.updateVrmStatus("VRM: cleared");
    this.updateMetaPanel();
    this.updateVrmAttachButton();
    this.setLegend();
  }

  countModelBones(model) {
    let count = 0;
    model.traverse((obj) => {
      if (obj.isBone) count += 1;
    });
    return count;
  }

  buildBoneMap(model) {
    const map = new Map();
    model.traverse((obj) => {
      if (!obj.isBone) return;
      const key = normalizeBoneName(obj.name);
      if (key && !map.has(key)) {
        map.set(key, obj);
      }
    });
    return map;
  }

  resolveVrmBone(boneName) {
    const humanoid = this.vrm.instance?.humanoid;
    if (humanoid && typeof humanoid.getNormalizedBoneNode === "function") {
      const node = humanoid.getNormalizedBoneNode(boneName);
      if (node) return node;
    }
    const aliases = VRM_BONE_ALIASES[boneName] || [boneName];
    for (const alias of aliases) {
      const key = normalizeBoneName(alias);
      const bone = this.vrm.boneMap?.get(key);
      if (bone) return bone;
    }
    return null;
  }

  applyArmorToVrmBones() {
    if (!this.vrm.attachArmor || !this.vrm.model) return;
    const modules = this.suitspec?.modules || {};
    for (const [partName, rec] of this.meshes.entries()) {
      if (!rec?.group?.visible) continue;
      const module = modules[partName];
      const anchor = effectiveVrmAnchorFor(partName, module);
      const bone = this.resolveVrmBone(anchor.bone);
      if (!bone) continue;

      const bonePos = bone.getWorldPosition(new THREE.Vector3());
      const boneQuat = bone.getWorldQuaternion(new THREE.Quaternion());
      const offset = new THREE.Vector3(anchor.offset[0], anchor.offset[1], anchor.offset[2]).applyQuaternion(
        boneQuat
      );
      const anchorPos = bonePos.add(offset);
      const localRot = new THREE.Quaternion().setFromEuler(
        new THREE.Euler(
          THREE.MathUtils.degToRad(anchor.rotation[0]),
          THREE.MathUtils.degToRad(anchor.rotation[1]),
          THREE.MathUtils.degToRad(anchor.rotation[2]),
          "XYZ"
        )
      );
      rec.group.position.copy(anchorPos);
      rec.group.quaternion.copy(boneQuat).multiply(localRot);
      rec.group.scale.multiply(new THREE.Vector3(anchor.scale[0], anchor.scale[1], anchor.scale[2]));
    }
  }

  alignVrmModelToArmor(model) {
    model.updateMatrixWorld(true);
    const modelBox = new THREE.Box3().setFromObject(model);
    if (modelBox.isEmpty()) return;

    const armorBox = new THREE.Box3().setFromObject(this.root);
    const sourceHeight = Math.max(modelBox.max.y - modelBox.min.y, 0.001);
    let targetHeight = 2.9;
    let targetMinY = -1.6;
    let targetCenterXZ = new THREE.Vector2(0, 0);

    if (!armorBox.isEmpty()) {
      targetHeight = Math.max(armorBox.max.y - armorBox.min.y, 0.5);
      targetMinY = armorBox.min.y;
      const center = armorBox.getCenter(new THREE.Vector3());
      targetCenterXZ = new THREE.Vector2(center.x, center.z);
    }

    const scale = clamp(targetHeight / sourceHeight, 0.2, 5.0);
    model.scale.setScalar(scale);
    model.updateMatrixWorld(true);

    const scaledBox = new THREE.Box3().setFromObject(model);
    const scaledCenter = scaledBox.getCenter(new THREE.Vector3());
    const shiftX = targetCenterXZ.x - scaledCenter.x;
    const shiftY = targetMinY - scaledBox.min.y;
    const shiftZ = targetCenterXZ.y - scaledCenter.z;
    model.position.add(new THREE.Vector3(shiftX, shiftY, shiftZ));
    model.updateMatrixWorld(true);
  }

  async loadVrmModel(path, { silent = false } = {}) {
    const rawPath = String(path || "").trim();
    if (!rawPath) {
      this.clearVrmModel();
      if (!silent) this.setStatus("VRM path is empty.");
      return;
    }

    const exists = await pathExists(rawPath);
    if (!exists) {
      this.vrm.error = `VRM file not found: ${rawPath}`;
      this.updateVrmStatus(this.vrm.error, true);
      this.updateMetaPanel();
      if (!silent) this.setStatus(this.vrm.error, true);
      return;
    }

    this.updateVrmStatus(`VRM loading: ${rawPath}`);
    const GLTFLoader = await getGLTFLoaderClass();
    let ThreeVrm = null;
    try {
      ThreeVrm = await getThreeVrmModule();
    } catch {
      ThreeVrm = null;
    }
    const loader = new GLTFLoader();
    if (ThreeVrm?.VRMLoaderPlugin) {
      loader.register((parser) => new ThreeVrm.VRMLoaderPlugin(parser));
    }
    const gltf = await new Promise((resolve, reject) => {
      loader.load(
        normalizePath(rawPath),
        resolve,
        (progress) => {
          if (!progress?.total) return;
          const ratio = clamp(progress.loaded / progress.total, 0, 1);
          const pct = Math.round(ratio * 100);
          this.updateVrmStatus(`VRM loading: ${rawPath} (${pct}%)`);
        },
        reject
      );
    });

    const vrmInstance = gltf.userData?.vrm || null;
    const model = vrmInstance?.scene || gltf.scene || gltf.scenes?.[0];
    if (!model) {
      throw new Error(`Invalid VRM/GLTF scene: ${rawPath}`);
    }
    if (vrmInstance && ThreeVrm?.VRMUtils?.rotateVRM0) {
      // Official recommendation for VRM 0.0 to align axes with newer conventions.
      try {
        ThreeVrm.VRMUtils.rotateVRM0(vrmInstance);
      } catch {
        // Non-fatal: continue rendering even if rotateVRM0 fails for this model.
      }
    }

    this.clearVrmModel();
    this.alignVrmModelToArmor(model);
    model.traverse((obj) => {
      if (!obj.isMesh) return;
      const srcMat = Array.isArray(obj.material) ? obj.material[0] : obj.material;
      const mat = new THREE.MeshStandardMaterial({
        color: srcMat?.color?.getHex?.() || 0x1a1f29,
        metalness: 0.08,
        roughness: 0.82,
        transparent: true,
        opacity: 0.18,
        side: THREE.DoubleSide,
        depthWrite: false,
      });
      obj.material = mat;
      obj.renderOrder = 0;
    });
    this.vrmGroup.add(model);

    const skeleton = new THREE.SkeletonHelper(model);
    skeleton.material.depthTest = false;
    skeleton.material.transparent = true;
    skeleton.material.opacity = 0.95;
    skeleton.material.color.setHex(0x2d6de6);
    skeleton.visible = this.vrm.visible;
    skeleton.renderOrder = 5;
    this.vrmGroup.add(skeleton);

    this.vrm.model = model;
    this.vrm.skeleton = skeleton;
    this.vrm.instance = vrmInstance;
    this.vrm.boneMap = this.buildBoneMap(model);
    this.vrm.path = rawPath;
    this.vrm.boneCount = this.countModelBones(model);
    this.vrm.error = "";
    this.updateVrmButton();
    this.updateVrmAttachButton();
    const vrmSource = vrmInstance ? "three-vrm" : "gltf-fallback";
    this.updateVrmStatus(`VRM loaded: ${rawPath} (bones=${this.vrm.boneCount}, source=${vrmSource})`);
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    this.updateMetaPanel();
    this.setLegend();
    if (!silent) this.setStatus(`Loaded VRM: ${rawPath}`);
  }

  setBridgeEnabled(enabled) {
    this.bridgeEnabled = Boolean(enabled);
    this.updateBridgeButton();
    this.updateBridges();
    this.updateMetaPanel();
    this.setLegend();
  }

  clearBridges() {
    for (const mesh of this.bridgeMeshes.values()) {
      this.bridgeGroup.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
    this.bridgeMeshes.clear();
    this.bridgeVisibleCount = 0;
  }

  ensureBridgeMesh(key) {
    const cached = this.bridgeMeshes.get(key);
    if (cached) return cached;
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(1, 1, 1, 24, 1, false),
      new THREE.MeshStandardMaterial({
        color: 0x8db4f7,
        transparent: true,
        opacity: 0.72,
        roughness: 0.52,
        metalness: 0.1,
      })
    );
    mesh.visible = false;
    mesh.renderOrder = 2;
    this.bridgeGroup.add(mesh);
    this.bridgeMeshes.set(key, mesh);
    return mesh;
  }

  updateBridges() {
    if (!this.bridgeEnabled) {
      this.bridgeVisibleCount = 0;
      for (const mesh of this.bridgeMeshes.values()) mesh.visible = false;
      return;
    }
    const pairScoreMap = new Map((this.fitStats?.pairs || []).map((p) => [p.pair, p.score]));
    const up = new THREE.Vector3(0, 1, 0);
    const scoreGood = new THREE.Color(0x84b6ff);
    const scoreBad = new THREE.Color(0xff9a8c);
    let visibleCount = 0;

    for (const [aName, bName] of FIT_CONTACT_PAIRS) {
      const key = `${aName}-${bName}`;
      const mesh = this.ensureBridgeMesh(key);
      const recA = this.meshes.get(aName);
      const recB = this.meshes.get(bName);
      if (!recA || !recB || !recA.group.visible || !recB.group.visible) {
        mesh.visible = false;
        continue;
      }

      const boxA = new THREE.Box3().setFromObject(recA.group);
      const boxB = new THREE.Box3().setFromObject(recB.group);
      if (boxA.isEmpty() || boxB.isEmpty()) {
        mesh.visible = false;
        continue;
      }

      const centerA = boxA.getCenter(new THREE.Vector3());
      const centerB = boxB.getCenter(new THREE.Vector3());
      const anchorA = supportPointOnBoxFace(boxA, centerB);
      const anchorB = supportPointOnBoxFace(boxB, centerA);
      const axis = new THREE.Vector3().subVectors(anchorB, anchorA);
      const distance = axis.length();
      if (!Number.isFinite(distance) || distance < 0.003) {
        mesh.visible = false;
        continue;
      }

      axis.normalize();
      const score = clamp(pairScoreMap.get(key) ?? 0.9, 0, 1);
      const radius = clamp(this.bridgeThickness * (1 + (1 - score) * 0.45), 0.02, 0.3);
      const color = scoreBad.clone().lerp(scoreGood, score);

      mesh.visible = true;
      mesh.position.copy(anchorA).lerp(anchorB, 0.5);
      mesh.quaternion.setFromUnitVectors(up, axis);
      mesh.scale.set(radius, distance, radius);
      mesh.material.color.copy(color);
      mesh.material.opacity = clamp(0.58 + (1 - score) * 0.25, 0.45, 0.9);
      visibleCount += 1;
    }
    this.bridgeVisibleCount = visibleCount;
  }

  resetLiveFollowers() {
    this.liveFollowers.clear();
    for (const spec of LIVE_SEGMENT_SPECS) {
      const fallback = DEFAULT_SEGMENT_POSE[spec.name] || {
        position_x: 0,
        position_y: 0,
        position_z: spec.z,
        rotation_z: 0,
        scale_x: 1,
        scale_y: 1,
        scale_z: 1,
      };
      this.liveFollowers.set(spec.name, { ...fallback });
    }
  }

  buildLiveSegmentsFromLandmarks(landmarks, dtSec) {
    const joints = extractPoseJointsWorld(landmarks);
    const segments = {};

    for (const spec of LIVE_SEGMENT_SPECS) {
      const prev = this.liveFollowers.get(spec.name) || DEFAULT_SEGMENT_POSE[spec.name];
      const start = joints[spec.startJoint];
      const end = joints[spec.endJoint];
      if (!start || !end) {
        segments[spec.name] = { ...prev };
        continue;
      }

      const dx = end.x - start.x;
      const dy = end.y - start.y;
      const length = Math.hypot(dx, dy);
      const midpointX = (start.x + end.x) * 0.5;
      const midpointY = (start.y + end.y) * 0.5;
      const angle = Math.atan2(dy, dx);
      const rotationZ = angle - Math.PI / 2;
      const radius = clamp(length * spec.radiusFactor, spec.radiusMin, spec.radiusMax);
      const lerp = clamp(dtSec * spec.smoothGain, 0, 1);

      const next = {
        position_x: prev.position_x + (midpointX - prev.position_x) * lerp,
        position_y: prev.position_y + (midpointY - prev.position_y) * lerp,
        position_z: spec.z,
        rotation_z: prev.rotation_z + (rotationZ - prev.rotation_z) * lerp,
        scale_x: prev.scale_x + (radius - prev.scale_x) * lerp,
        scale_y: prev.scale_y + (length - prev.scale_y) * lerp,
        scale_z: prev.scale_z + (radius - prev.scale_z) * lerp,
      };
      this.liveFollowers.set(spec.name, next);
      segments[spec.name] = next;
    }
    return segments;
  }

  applySegments(segments, frame = null) {
    const segs = withFallbackSegments(segments || {});
    for (const [name, rec] of this.meshes.entries()) {
      const t = resolveTransform(name, rec.config, segs);
      if (!t) {
        rec.group.visible = false;
        continue;
      }
      rec.group.visible = true;
      rec.group.position.set(t.position_x, t.position_y, t.position_z);
      rec.group.rotation.set(0, 0, t.rotation_z);
      rec.group.scale.set(t.scale_x, t.scale_y, t.scale_z);
    }
    const sphere = this.computeVisibleBounds();
    if (sphere) {
      this.modelCenter.copy(sphere.center);
      this.modelRadius = Math.max(sphere.radius, 0.35);
    }
    if (this.vrm.model && !this.playing && !this.live.active) {
      this.alignVrmModelToArmor(this.vrm.model);
    }
    this.applyArmorToVrmBones();
    this.fitStats = this.calculateFitStats();
    this.updateBridges();
    this.updateMetaPanel();
    this.setLegend(frame);
  }

  async startLiveWebcam() {
    if (this.live.active) {
      this.updateLiveStatus("Live: already active");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      this.updateLiveStatus("Live: camera API unavailable", true);
      this.setStatus("WebCam unavailable in this browser/context", true);
      return;
    }

    try {
      this.setStatus("Starting webcam + pose model...");
      this.updateLiveStatus("Live: loading model...");

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 540 } },
        audio: false,
      });
      const video = PANEL.liveVideo || document.createElement("video");
      video.srcObject = stream;
      await video.play();

      const visionTasks = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14");
      const vision = await visionTasks.FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
      );
      const modelAssetPath =
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";
      const landmarker = await visionTasks.PoseLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath },
        runningMode: "VIDEO",
        numPoses: 1,
      });

      this.live = {
        active: true,
        video,
        stream,
        landmarker,
        lastVideoTime: -1,
        lastNowMs: performance.now(),
        fps: 0,
      };
      this.resetLiveFollowers();
      this.playing = false;
      PANEL.btnPlay.textContent = "Play";
      this.updateLiveStatus("Live: webcam active");
      this.setStatus("Live webcam started");
      this.updateMetaPanel();
    } catch (err) {
      this.stopLive({ silent: true });
      const detail = String(err?.message || err || "unknown");
      this.updateLiveStatus("Live: start failed", true);
      this.setStatus(`Live start failed: ${detail}`, true);
    }
  }

  stopLive({ silent = false } = {}) {
    const live = this.live;
    try {
      live.landmarker?.close?.();
    } catch {
      // ignore
    }
    if (live.stream) {
      for (const track of live.stream.getTracks()) {
        track.stop();
      }
    }
    if (live.video) {
      live.video.pause?.();
      live.video.srcObject = null;
    }

    this.live = {
      active: false,
      video: null,
      stream: null,
      landmarker: null,
      lastVideoTime: -1,
      lastNowMs: performance.now(),
      fps: 0,
    };
    this.updateLiveStatus("Live: inactive");
    this.updateMetaPanel();
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    if (!silent) {
      this.setStatus("Live webcam stopped");
    }
  }

  updateLivePose(nowMs) {
    if (!this.live.active || !this.live.landmarker || !this.live.video) return;
    const video = this.live.video;
    if (video.readyState < 2) return;
    if (video.currentTime === this.live.lastVideoTime) return;
    this.live.lastVideoTime = video.currentTime;

    let result = null;
    try {
      result = this.live.landmarker.detectForVideo(video, nowMs);
    } catch (err) {
      this.updateLiveStatus("Live: detect error", true);
      this.setStatus(`Live detect failed: ${String(err?.message || err || "unknown")}`, true);
      return;
    }
    const landmarks = result?.landmarks?.[0];
    const dtSec = clamp((nowMs - this.live.lastNowMs) / 1000, 0.001, 0.1);
    this.live.lastNowMs = nowMs;
    this.live.fps = dtSec > 0 ? 1 / dtSec : 0;

    if (!landmarks || landmarks.length === 0) return;
    const liveSegments = this.buildLiveSegmentsFromLandmarks(landmarks, dtSec);
    this.applySegments(liveSegments, null);
  }

  calculateFitStats() {
    this.root.updateMatrixWorld(true);
    const boxes = new Map();
    for (const [name, rec] of this.meshes.entries()) {
      if (!rec.group.visible) continue;
      boxes.set(name, new THREE.Box3().setFromObject(rec.group));
    }

    let totalGap = 0;
    let totalPenetration = 0;
    let totalScore = 0;
    let count = 0;
    const weakPairs = [];

    for (const [aName, bName] of FIT_CONTACT_PAIRS) {
      const a = boxes.get(aName);
      const b = boxes.get(bName);
      if (!a || !b) continue;
      const { gap, penetration } = aabbGapAndPenetration(a, b);
      const score = fitPairScore(gap, penetration);
      totalGap += gap;
      totalPenetration += penetration;
      totalScore += score;
      count += 1;
      weakPairs.push({ a: aName, b: bName, pair: `${aName}-${bName}`, gap, penetration, score });
    }

    if (count === 0) {
      return {
        pairCount: 0,
        meanGap: 0,
        meanPenetration: 0,
        score: 0,
        pairs: [],
        weakest: [],
      };
    }

    weakPairs.sort((x, y) => x.score - y.score);
    return {
      pairCount: count,
      meanGap: totalGap / count,
      meanPenetration: totalPenetration / count,
      score: totalScore / count,
      pairs: weakPairs,
      weakest: weakPairs.slice(0, 3),
    };
  }

  listEditableParts() {
    const modules = this.suitspec?.modules || {};
    return Object.entries(modules)
      .filter(([, module]) => module?.enabled)
      .map(([name]) => name);
  }

  populateFitEditor() {
    if (!PANEL.fitPart) return;
    const prev = PANEL.fitPart.value;
    const parts = this.listEditableParts();
    PANEL.fitPart.innerHTML = "";
    for (const name of parts) {
      const op = document.createElement("option");
      op.value = name;
      op.textContent = name;
      PANEL.fitPart.appendChild(op);
    }
    if (!parts.length) return;
    PANEL.fitPart.value = parts.includes(prev) ? prev : parts[0];
    this.loadFitEditorForPart(PANEL.fitPart.value);
  }

  loadFitEditorForPart(partName) {
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;
    const fit = getModuleVisualConfig(partName, module);
    PANEL.fitScaleX.value = String(round3(fit.scale[0]));
    PANEL.fitScaleY.value = String(round3(fit.scale[1]));
    PANEL.fitScaleZ.value = String(round3(fit.scale[2]));
    PANEL.fitOffsetY.value = String(round3(fit.offsetY));
    PANEL.fitZOffset.value = String(round3(fit.zOffset || 0));
  }

  suggestFitForCurrentPart() {
    const partName = PANEL.fitPart?.value;
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;

    const pairs = (this.fitStats?.pairs || []).filter((p) => p.a === partName || p.b === partName);
    if (!pairs.length) {
      this.setStatus(`Suggest unavailable: no contact pair for ${partName}`, true);
      return;
    }

    const worst = pairs[0];
    const effective = getModuleVisualConfig(partName, module);
    const gap = Number(worst.gap || 0);
    const penetration = Number(worst.penetration || 0);

    const scaleAllFactor = clamp(1 + clamp(gap * 1.9, 0, 0.16) - clamp(penetration * 2.1, 0, 0.18), 0.82, 1.22);
    const scaleYFactor = clamp(1 + clamp((gap - penetration) * 2.0, -0.16, 0.16), 0.82, 1.22);
    const towardSign = worst.b === partName ? 1 : -1;
    const offsetAdjust = clamp((gap - penetration) * 0.28, -0.035, 0.035) * towardSign;

    const nextScale = [
      round3(effective.scale[0] * scaleAllFactor),
      round3(effective.scale[1] * scaleYFactor),
      round3(effective.scale[2] * scaleAllFactor),
    ];
    const nextOffsetY = round3(effective.offsetY + offsetAdjust);

    PANEL.fitScaleX.value = String(nextScale[0]);
    PANEL.fitScaleY.value = String(nextScale[1]);
    PANEL.fitScaleZ.value = String(nextScale[2]);
    PANEL.fitOffsetY.value = String(nextOffsetY);

    this.applyFitEditorToCurrentPart({ silent: true });
    this.setStatus(
      `Suggest applied: ${partName} <- ${worst.pair} (score ${(worst.score * 100).toFixed(1)}, gap ${gap.toFixed(
        3
      )}, pen ${penetration.toFixed(3)})`
    );
  }

  applyFitEditorToCurrentPart({ silent = false } = {}) {
    const partName = PANEL.fitPart?.value;
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;

    const effective = getModuleVisualConfig(partName, module);
    module.fit = {
      shape: effective.shape,
      source: effective.source,
      attach: effective.attach,
      offsetY: toNumberOr(PANEL.fitOffsetY.value, effective.offsetY),
      zOffset: toNumberOr(PANEL.fitZOffset.value, effective.zOffset || 0),
      scale: normalizeVec3(
        [PANEL.fitScaleX.value, PANEL.fitScaleY.value, PANEL.fitScaleZ.value],
        effective.scale
      ),
      follow: normalizeVec3(effective.follow, [1, 1, 1]),
      minScale: normalizeVec3(effective.minScale, [0.2, 0.2, 0.2]),
    };

    const rec = this.meshes.get(partName);
    if (rec) {
      rec.config = getModuleVisualConfig(partName, module);
    }
    this.applyFrame(this.frameIndex);
    this.updateMetaPanel();
    if (!silent) {
      this.setStatus(`Applied fit: ${partName}`);
    }
  }

  resetFitForCurrentPart() {
    const partName = PANEL.fitPart?.value;
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;
    delete module.fit;
    const rec = this.meshes.get(partName);
    if (rec) {
      rec.config = getModuleVisualConfig(partName, module);
    }
    this.applyFrame(this.frameIndex);
    this.loadFitEditorForPart(partName);
    this.updateMetaPanel();
    this.setStatus(`Reset fit: ${partName}`);
  }

  async saveSuitspecFit() {
    const path = this.loadedSuitspecPath || PANEL.suitspecPath.value;
    if (!path || !this.suitspec) {
      this.setStatus("Save failed: suitspec not loaded", true);
      return;
    }
    try {
      const res = await fetch("/api/suitspec-save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          path,
          suitspec: this.suitspec,
        }),
      });
      let data = null;
      try {
        data = await res.json();
      } catch {
        data = null;
      }
      if (!res.ok || !data?.ok) {
        const msg = data?.error || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      this.updateMetaPanel();
      this.setStatus(`Saved fits to ${data.path || path}`);
    } catch (err) {
      const detail = String(err?.message || err || "unknown");
      if (detail.includes("404")) {
        this.setStatus("Save API not available. Use serve-dashboard on this URL.", true);
        return;
      }
      this.setStatus(`Save failed: ${detail}`, true);
    }
  }

  setLegend(frame = null) {
    const activeFrame = frame || this.frames[this.frameIndex] || null;
    const frameText = this.frames.length ? `${this.frameIndex + 1}/${this.frames.length}` : "0/0";
    const equipped = activeFrame ? Boolean(activeFrame.equipped) : Boolean(this.sim?.equipped);
    const fitScore = ((this.fitStats?.score || 0) * 100).toFixed(1);
    const fitGap = (this.fitStats?.meanGap || 0).toFixed(3);
    const fitPen = (this.fitStats?.meanPenetration || 0).toFixed(3);
    const lines = [
      "表示ガイド: パーツ形状 / テクスチャ / 接続ブリッジ / VRM骨組み",
      `Frame ${frameText} | Equipped: ${equipped ? "YES" : "NO"} | Speed x${this.speed.toFixed(2)}`,
      `Textures: ${this.useTextures ? "ON" : "OFF"} | Relief: ${this.reliefStrength.toFixed(2)} | Theme: ${
        this.darkTheme ? "Dark" : "Bright"
      }`,
      `Bridges: ${this.bridgeEnabled ? "ON" : "OFF"} | Visible: ${this.bridgeVisibleCount} | Thickness: ${this.bridgeThickness.toFixed(
        2
      )}`,
      `VRM: ${this.vrm.path ? "ON" : "OFF"} | Bones: ${this.vrm.boneCount || 0} | Visible: ${
        this.vrm.visible ? "ON" : "OFF"
      } | Attach: ${this.vrm.attachArmor ? "VRM" : "BodySim"}`,
      `FitScore: ${fitScore} | Gap: ${fitGap} | Penetration: ${fitPen}`,
      "Tip: Attach を VRM にすると、各部位をVRM骨に追従表示します。",
    ];
    PANEL.legendText.innerHTML = lines.join("<br>");
  }

  updateCameraRange(distance) {
    const d = Math.max(distance, 1.0);
    this.controls.maxDistance = Math.max(d * 4.5, 4.0);
    this.controls.minDistance = Math.max(d * 0.2, 0.35);
    this.camera.near = Math.max(0.01, d / 120);
    this.camera.far = Math.max(40, d * 22);
    this.camera.updateProjectionMatrix();
  }

  computeVisibleBounds() {
    const box = new THREE.Box3();
    let hasVisible = false;
    for (const rec of this.meshes.values()) {
      if (!rec.group.visible) continue;
      box.expandByObject(rec.group);
      hasVisible = true;
    }
    if (!hasVisible || box.isEmpty()) return null;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    if (!Number.isFinite(sphere.radius) || sphere.radius <= 0) {
      sphere.radius = 0.5;
    }
    return sphere;
  }

  fitCameraToVisible() {
    const sphere = this.computeVisibleBounds();
    if (!sphere) return;
    this.modelCenter.copy(sphere.center);
    this.modelRadius = Math.max(sphere.radius, 0.35);

    const distance = Math.max(this.modelRadius * 2.8, 1.45);
    const viewDir = new THREE.Vector3().subVectors(this.camera.position, this.controls.target);
    if (viewDir.lengthSq() < 0.00001) viewDir.set(0, 0.1, 1);
    viewDir.normalize();

    this.controls.target.copy(this.modelCenter);
    this.camera.position.copy(this.modelCenter).addScaledVector(viewDir, distance);
    this.updateCameraRange(distance);
    this.controls.update();
  }

  setCameraPreset(preset) {
    const center = this.modelCenter.clone();
    const radius = Math.max(this.modelRadius, 0.35);
    const distance = Math.max(radius * 2.8, 1.45);
    const yBias = radius * 0.15;

    switch (preset) {
      case "front":
        this.camera.position.copy(center).add(new THREE.Vector3(0, yBias, distance));
        break;
      case "side":
        this.camera.position.copy(center).add(new THREE.Vector3(distance, radius * 0.08, 0));
        break;
      case "top":
        this.camera.position.copy(center).add(new THREE.Vector3(0.01, distance, 0.01));
        break;
      default:
        this.camera.position.copy(center).add(new THREE.Vector3(0, yBias, distance));
        break;
    }
    this.controls.target.copy(center);
    this.updateCameraRange(distance);
    this.controls.update();
  }

  applyTheme() {
    const gridMaterials = Array.isArray(this.grid.material) ? this.grid.material : [this.grid.material];
    const outlineColor = this.darkTheme ? 0xeaf2ff : 0x0f2342;

    if (this.darkTheme) {
      this.scene.background = new THREE.Color(0xf4f7fc);
      this.floor.material.color.setHex(0xffffff);
      this.floor.material.opacity = 0.95;
      for (const mat of gridMaterials) {
        mat.color.setHex(0xc4d2e8);
      }
      PANEL.btnTheme.textContent = "Theme: Soft";
    } else {
      this.scene.background = new THREE.Color(0xffffff);
      this.floor.material.color.setHex(0xffffff);
      this.floor.material.opacity = 0.94;
      for (const mat of gridMaterials) {
        mat.color.setHex(0xd6e1f2);
      }
      PANEL.btnTheme.textContent = "Theme: White";
    }

    for (const rec of this.meshes.values()) {
      rec.outline.material.color.setHex(outlineColor);
    }
    this.setLegend();
  }

  async load(suitspecPath, simPath) {
    if (this.live.active) {
      this.stopLive({ silent: true });
    }
    this.setStatus("Loading JSON...");
    const [spec, sim] = await Promise.all([this.fetchJson(suitspecPath), this.fetchJson(simPath)]);
    this.suitspec = spec;
    this.sim = sim;
    this.loadedSuitspecPath = suitspecPath;
    this.loadedSimPath = simPath;
    this.frames = Array.isArray(sim.frames) ? sim.frames : [];
    this.frameIndex = 0;
    this.playbackAccumSec = 0;
    await this.buildMeshes();
    PANEL.frameSlider.max = String(Math.max(0, this.frames.length - 1));
    PANEL.frameSlider.value = "0";
    this.applyFrame(0);
    const vrmPath = String(PANEL.vrmPath?.value || "").trim();
    if (vrmPath) {
      try {
        if (this.vrm.model && this.vrm.path === vrmPath) {
          this.alignVrmModelToArmor(this.vrm.model);
          this.updateVrmStatus(`VRM loaded: ${vrmPath} (bones=${this.vrm.boneCount})`);
        } else {
          await this.loadVrmModel(vrmPath, { silent: true });
        }
      } catch (error) {
        const detail = String(error?.message || error || "VRM load failed");
        this.vrm.error = detail;
        this.updateVrmStatus(`VRM load failed: ${detail}`, true);
      }
    } else {
      this.updateVrmStatus("VRM: not loaded");
    }
    this.fitCameraToVisible();
    const hasFrames = this.frames.length > 0;
    this.setStatus(
      hasFrames
        ? `Loaded. frames=${this.frames.length}, parts=${this.meshes.size}`
        : `Loaded, but no frames found in ${normalizePath(simPath)}`,
      !hasFrames
    );
    this.updateMetaPanel();
    this.populateFitEditor();
    this.setLegend(this.frames[0] || null);
  }

  async fetchJson(path) {
    const url = normalizePath(path);
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`Failed to load JSON: ${url} (${res.status})`);
    }
    return res.json();
  }

  clearMeshes() {
    this.clearBridges();
    for (const rec of this.meshes.values()) {
      this.root.remove(rec.group);
      rec.mesh.geometry.dispose();
      rec.mesh.material.dispose();
      rec.outline.geometry.dispose();
      rec.outline.material.dispose();
    }
    this.meshes.clear();
  }

  async buildMeshes() {
    this.clearMeshes();
    const modules = this.suitspec?.modules || {};
    for (const [name, module] of Object.entries(modules)) {
      if (!module?.enabled) continue;
      const config = getModuleVisualConfig(name, module);
      const assetPath = resolveMeshAssetPath(name, module);
      const geometry = await loadModuleGeometry(name, config.shape, assetPath);
      const mesh = createMeshFromGeometry(geometry);
      mesh.material.color.setHex(partColor(name));
      mesh.userData.partName = name;

      const outline = createOutline(mesh, this.darkTheme ? 0xffffff : 0x10223f);
      const group = new THREE.Group();
      group.add(mesh);
      group.add(outline);

      this.root.add(group);
      this.meshes.set(name, {
        partName: name,
        group,
        mesh,
        outline,
        config,
        assetPath,
        texturePath: module.texture_path || null,
        texture: null,
      });
    }
    this.updateTextureMode();
  }

  updateTextureMode(forceRelief = false) {
    PANEL.btnTexture.textContent = this.useTextures ? "Textures: On" : "Textures: Off";
    for (const rec of this.meshes.values()) {
      rec.outline.visible = true;
      rec.outline.material.opacity = this.useTextures ? 0.22 : 0.85;
      if (!this.useTextures) {
        rec.mesh.material.map = null;
        rec.mesh.material.color.setHex(partColor(rec.partName));
        rec.mesh.material.needsUpdate = true;
        restoreBaseGeometry(rec.mesh);
        continue;
      }
      if (!rec.texturePath) continue;
      if (rec.texture) {
        rec.mesh.material.map = rec.texture;
        rec.mesh.material.color.setHex(0xe7f0ff);
        rec.mesh.material.needsUpdate = true;
        if (forceRelief || !rec.reliefApplied) {
          applyReliefFromTexture(rec.mesh, rec.texture, this.reliefStrength);
          rec.reliefApplied = true;
        }
        continue;
      }
      textureLoader.load(
        normalizePath(rec.texturePath),
        (tex) => {
          tex.colorSpace = THREE.SRGBColorSpace;
          tex.wrapS = THREE.RepeatWrapping;
          tex.wrapT = THREE.RepeatWrapping;
          rec.texture = tex;
          rec.reliefApplied = false;
          if (this.useTextures) {
            rec.mesh.material.map = tex;
            rec.mesh.material.color.setHex(0xe7f0ff);
            rec.mesh.material.needsUpdate = true;
            applyReliefFromTexture(rec.mesh, tex, this.reliefStrength);
            rec.reliefApplied = true;
          }
        },
        undefined,
        () => {
          rec.texture = null;
          rec.reliefApplied = false;
        }
      );
    }
    this.setLegend();
  }

  applyFrame(index) {
    if (!this.frames.length) return;
    const safeIndex = Math.max(0, Math.min(this.frames.length - 1, index));
    this.frameIndex = safeIndex;
    PANEL.frameSlider.value = String(safeIndex);
    const frame = this.frames[safeIndex];
    this.applySegments(frame.segments || {}, frame);
  }

  tick(now) {
    const dt = Math.min(0.05, (now - this.lastTime) / 1000);
    this.lastTime = now;
    this.speed = Number(PANEL.speedSlider.value || "1");

    if (this.live.active) {
      this.updateLivePose(now);
    } else if (this.playing && this.frames.length > 0) {
      this.playbackAccumSec += dt * this.speed;
      let frame = this.frames[this.frameIndex];
      let targetDt = Number(frame?.dt_sec || 0.1);
      if (!Number.isFinite(targetDt) || targetDt <= 0) targetDt = 0.1;
      while (this.playbackAccumSec >= targetDt) {
        this.playbackAccumSec -= targetDt;
        const next = (this.frameIndex + 1) % this.frames.length;
        this.applyFrame(next);
        frame = this.frames[this.frameIndex];
        targetDt = Number(frame?.dt_sec || 0.1);
      }
    }

    if (this.vrm.instance && typeof this.vrm.instance.update === "function") {
      this.vrm.instance.update(dt);
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame((t) => this.tick(t));
  }
}

function createDefaultGeometry(shape) {
  let geometry;
  switch (shape) {
    case "cylinder":
      geometry = new THREE.CylinderGeometry(0.5, 0.5, 1, 48, 40, true);
      break;
    case "sphere":
      geometry = new THREE.SphereGeometry(0.5, 34, 24);
      break;
    case "box":
    default:
      geometry = new THREE.BoxGeometry(1, 1, 1, 16, 20, 16);
      break;
  }
  if (geometry.index) {
    geometry = geometry.toNonIndexed();
  }
  geometry.computeVertexNormals();
  return geometry;
}

function createMeshFromGeometry(geometry) {
  const material = new THREE.MeshStandardMaterial({
    color: 0x80a9e0,
    metalness: 0.55,
    roughness: 0.45,
    side: THREE.DoubleSide,
  });
  const mesh = new THREE.Mesh(geometry, material);
  const pos = mesh.geometry.attributes.position;
  mesh.userData.basePositions = new Float32Array(pos.array);
  return mesh;
}

function resolveMeshAssetPath(partName, module) {
  const ref = String(module?.asset_ref || "").replace(/\\/g, "/").trim();
  if (ref.toLowerCase().endsWith(".mesh.json")) return ref;
  return `viewer/assets/meshes/${partName}.mesh.json`;
}

async function loadModuleGeometry(partName, fallbackShape, assetPath) {
  try {
    return await loadMeshGeometryFromAsset(assetPath);
  } catch (error) {
    console.warn(`mesh asset load failed for ${partName}:`, error);
    return createDefaultGeometry(fallbackShape);
  }
}

async function loadMeshGeometryFromAsset(assetPath) {
  const key = normalizePath(assetPath);
  if (meshGeometryCache.has(key)) {
    return meshGeometryCache.get(key).clone();
  }

  const res = await fetch(key);
  if (!res.ok) {
    throw new Error(`Failed to load mesh asset: ${key} (${res.status})`);
  }
  const payload = await res.json();
  const geometry = meshGeometryFromPayload(payload);
  meshGeometryCache.set(key, geometry);
  return geometry.clone();
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh asset format.");
  }

  const positions = new Float32Array(payload.positions || []);
  const normals = new Float32Array(payload.normals || []);
  const uv = new Float32Array(payload.uv || []);
  const indices = Array.isArray(payload.indices) ? payload.indices : [];

  if (positions.length < 9 || positions.length % 3 !== 0) {
    throw new Error("Invalid mesh positions.");
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  if (uv.length === (positions.length / 3) * 2) {
    geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  }
  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  }
  if (indices.length > 0) {
    geometry.setIndex(indices);
  }
  if (geometry.index) {
    const expanded = geometry.toNonIndexed();
    expanded.computeVertexNormals();
    return expanded;
  }
  if (!geometry.getAttribute("normal")) {
    geometry.computeVertexNormals();
  }
  return geometry;
}

function createOutline(mesh, color) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 18);
  const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.85 });
  return new THREE.LineSegments(edges, mat);
}

function partColor(name) {
  return PART_COLOR_MAP[name] || 0x7eb6ff;
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function restoreBaseGeometry(mesh) {
  const geo = mesh.geometry;
  const pos = geo.attributes.position;
  const base = mesh.userData.basePositions;
  if (!pos || !base || base.length !== pos.array.length) return;

  for (let i = 0; i < pos.count; i++) {
    pos.setXYZ(i, base[i * 3 + 0], base[i * 3 + 1], base[i * 3 + 2]);
  }
  pos.needsUpdate = true;
  geo.computeVertexNormals();
}

function applyReliefFromTexture(mesh, tex, amplitude) {
  const image = tex?.image;
  if (!image || amplitude <= 0) {
    restoreBaseGeometry(mesh);
    return;
  }

  const geo = mesh.geometry;
  const pos = geo.attributes.position;
  const norm = geo.attributes.normal;
  const uv = geo.attributes.uv;
  const base = mesh.userData.basePositions;
  if (!pos || !norm || !uv || !base || base.length !== pos.array.length) return;

  const W = 256;
  const H = 256;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(image, 0, 0, W, H);
  const data = ctx.getImageData(0, 0, W, H).data;

  for (let i = 0; i < pos.count; i++) {
    const u = clamp(uv.getX(i), 0, 1);
    const v = clamp(uv.getY(i), 0, 1);
    const x = Math.floor(u * (W - 1));
    const y = Math.floor((1 - v) * (H - 1));
    const idx = (y * W + x) * 4;

    const r = data[idx + 0];
    const g = data[idx + 1];
    const b = data[idx + 2];

    const lum = (r + g + b) / (3 * 255);
    const minCh = Math.min(r, g, b) / 255;
    const maxCh = Math.max(r, g, b) / 255;
    const satLike = maxCh - minCh;
    const mask = clamp((0.95 - minCh) * 8 + satLike * 2, 0, 1);

    const disp = (lum - 0.5) * amplitude * mask;
    const nx = norm.getX(i);
    const ny = norm.getY(i);
    const nz = norm.getZ(i);
    const nLen = Math.hypot(nx, ny, nz) || 1;

    pos.setXYZ(
      i,
      base[i * 3 + 0] + (nx / nLen) * disp,
      base[i * 3 + 1] + (ny / nLen) * disp,
      base[i * 3 + 2] + (nz / nLen) * disp
    );
  }

  pos.needsUpdate = true;
  geo.computeVertexNormals();
}

function normalizePath(path) {
  let p = String(path || "").replace(/\\/g, "/").trim();
  if (!p) return p;
  if (/^https?:\/\//i.test(p)) return p;
  if (p.startsWith("/")) return p;
  if (p.startsWith("./")) p = p.slice(2);
  return `/${p}`;
}

async function pathExists(path) {
  const url = normalizePath(path);
  if (!url) return false;
  try {
    const head = await fetch(url, { method: "HEAD" });
    if (head.ok) return true;
  } catch {
    // Some local servers may not support HEAD.
  }
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}

async function getGLTFLoaderClass() {
  if (!gltfLoaderModulePromise) {
    gltfLoaderModulePromise = importFirstSuccessful([
      () => import("three/addons/loaders/GLTFLoader.js"),
      () =>
        import(`https://cdn.jsdelivr.net/npm/three@${THREE_VERSION}/examples/jsm/loaders/GLTFLoader.js`),
      () =>
        import(`https://unpkg.com/three@${THREE_VERSION}/examples/jsm/loaders/GLTFLoader.js?module`),
    ]);
  }
  const mod = await gltfLoaderModulePromise;
  if (!mod?.GLTFLoader) {
    throw new Error("GLTFLoader is not available.");
  }
  return mod.GLTFLoader;
}

async function getThreeVrmModule() {
  if (!threeVrmModulePromise) {
    threeVrmModulePromise = importFirstSuccessful([
      () => import("@pixiv/three-vrm"),
      () =>
        import(
          `https://cdn.jsdelivr.net/npm/@pixiv/three-vrm@${THREE_VRM_VERSION}/lib/three-vrm.module.min.js`
        ),
      () =>
        import(
          `https://unpkg.com/@pixiv/three-vrm@${THREE_VRM_VERSION}/lib/three-vrm.module.min.js?module`
        ),
    ]);
  }
  return threeVrmModulePromise;
}

async function importFirstSuccessful(loaders) {
  let lastError = null;
  for (const load of loaders) {
    try {
      return await load();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("Module import failed.");
}

function withFallbackSegments(segments) {
  const merged = {};
  for (const [name, pose] of Object.entries(DEFAULT_SEGMENT_POSE)) {
    merged[name] = pose;
  }
  for (const [name, pose] of Object.entries(segments || {})) {
    merged[name] = pose;
  }
  return merged;
}

function resolveTransform(name, config, segments) {
  const source = config.source;
  const base = segments[source] || null;
  if (!base) return null;

  const offset = Number(config.offsetY || 0);
  const attach = String(config.attach || "center");
  let anchor = 0;
  if (attach === "start") anchor = 0.5;
  if (attach === "end") anchor = -0.5;

  const axis = localYAxis(base.rotation_z);
  const along = base.scale_y * (anchor + offset);
  const x = base.position_x + axis.x * along;
  const y = base.position_y + axis.y * along;
  const z = base.position_z + Number(config.zOffset || 0);

  const scale = config.scale || [1, 1, 1];
  const follow = config.follow || [1, 1, 1];
  const minScale = config.minScale || [0.24, 0.24, 0.24];

  const baseScaleX = Math.max(Number(base.scale_x || 1), 0.2);
  const baseScaleY = Math.max(Number(base.scale_y || 1), 0.2);
  const baseScaleZ = Math.max(Number(base.scale_z || 1), 0.2);

  const fitScaleX = 1 + (baseScaleX - 1) * Number(follow[0] ?? 1);
  const fitScaleY = 1 + (baseScaleY - 1) * Number(follow[1] ?? 1);
  const fitScaleZ = 1 + (baseScaleZ - 1) * Number(follow[2] ?? 1);

  return {
    position_x: x,
    position_y: y,
    position_z: z,
    rotation_z: base.rotation_z,
    scale_x: Math.max(fitScaleX * scale[0], Number(minScale[0] ?? 0.2)),
    scale_y: Math.max(fitScaleY * scale[1], Number(minScale[1] ?? 0.2)),
    scale_z: Math.max(fitScaleZ * scale[2], Number(minScale[2] ?? 0.2)),
  };
}

function localYAxis(rotationZ) {
  return { x: -Math.sin(rotationZ), y: Math.cos(rotationZ) };
}

function init() {
  const params = new URLSearchParams(window.location.search);
  PANEL.suitspecPath.value = params.get("suitspec") || DEFAULT_SUITSPEC;
  PANEL.simPath.value = params.get("sim") || DEFAULT_SIM;
  if (PANEL.vrmPath) {
    PANEL.vrmPath.value = params.get("vrm") || DEFAULT_VRM_PATH;
  }

  const viewer = new BodyFitViewer(document.getElementById("canvas"));

  PANEL.btnLoad.onclick = async () => {
    try {
      await viewer.load(PANEL.suitspecPath.value, PANEL.simPath.value);
    } catch (err) {
      const details = formatLoadError(err);
      viewer.setStatus(`Load failed: ${details}`, true);
      viewer.setMeta({
        error: String(details),
        suitspec: PANEL.suitspecPath.value,
        sim: PANEL.simPath.value,
        tip: "python -m henshin serve-dashboard --port 8010 で起動し、URLは /viewer/body-fit/ を開いてください。",
      });
    }
  };

  PANEL.btnPlay.onclick = () => {
    viewer.playing = !viewer.playing;
    PANEL.btnPlay.textContent = viewer.playing ? "Pause" : "Play";
    viewer.setLegend();
  };

  PANEL.btnPrev.onclick = () => viewer.applyFrame(viewer.frameIndex - 1);
  PANEL.btnNext.onclick = () => viewer.applyFrame(viewer.frameIndex + 1);
  PANEL.frameSlider.oninput = () => viewer.applyFrame(Number(PANEL.frameSlider.value));
  PANEL.speedSlider.oninput = () => viewer.setLegend();
  PANEL.btnTexture.onclick = () => {
    viewer.useTextures = !viewer.useTextures;
    viewer.updateTextureMode();
  };
  if (PANEL.reliefSlider) {
    PANEL.reliefSlider.oninput = () => {
      viewer.reliefStrength = Number(PANEL.reliefSlider.value || "0");
      if (!Number.isFinite(viewer.reliefStrength)) viewer.reliefStrength = 0;
      viewer.updateTextureMode(true);
    };
  }
  PANEL.btnTheme.onclick = () => {
    viewer.darkTheme = !viewer.darkTheme;
    viewer.applyTheme();
  };
  PANEL.btnCamFront.onclick = () => viewer.setCameraPreset("front");
  PANEL.btnCamSide.onclick = () => viewer.setCameraPreset("side");
  PANEL.btnCamTop.onclick = () => viewer.setCameraPreset("top");
  PANEL.btnFit.onclick = () => viewer.fitCameraToVisible();
  if (PANEL.btnLiveStart) {
    PANEL.btnLiveStart.onclick = () => viewer.startLiveWebcam();
  }
  if (PANEL.btnLiveStop) {
    PANEL.btnLiveStop.onclick = () => viewer.stopLive();
  }
  if (PANEL.btnVrmLoad) {
    PANEL.btnVrmLoad.onclick = async () => {
      try {
        await viewer.loadVrmModel(PANEL.vrmPath?.value || "");
      } catch (error) {
        const detail = String(error?.message || error || "VRM load failed");
        viewer.vrm.error = detail;
        viewer.updateVrmStatus(`VRM load failed: ${detail}`, true);
        viewer.updateMetaPanel();
        viewer.setLegend();
      }
    };
  }
  if (PANEL.btnVrmClear) {
    PANEL.btnVrmClear.onclick = () => viewer.clearVrmModel();
  }
  if (PANEL.btnVrmToggle) {
    PANEL.btnVrmToggle.onclick = () => viewer.setVrmVisible(!viewer.vrm.visible);
  }
  if (PANEL.btnVrmAttach) {
    PANEL.btnVrmAttach.onclick = () => viewer.setVrmAttachArmor(!viewer.vrm.attachArmor);
  }

  if (PANEL.fitPart) {
    PANEL.fitPart.onchange = () => viewer.loadFitEditorForPart(PANEL.fitPart.value);
  }
  if (PANEL.btnFitSuggestCurrent) {
    PANEL.btnFitSuggestCurrent.onclick = () => viewer.suggestFitForCurrentPart();
  }
  if (PANEL.btnFitApplyCurrent) {
    PANEL.btnFitApplyCurrent.onclick = () => viewer.applyFitEditorToCurrentPart();
  }
  if (PANEL.btnFitResetCurrent) {
    PANEL.btnFitResetCurrent.onclick = () => viewer.resetFitForCurrentPart();
  }
  if (PANEL.btnFitSaveSuitspec) {
    PANEL.btnFitSaveSuitspec.onclick = () => viewer.saveSuitspecFit();
  }
  if (PANEL.btnBridgeToggle) {
    PANEL.btnBridgeToggle.onclick = () => viewer.setBridgeEnabled(!viewer.bridgeEnabled);
  }
  if (PANEL.bridgeThickness) {
    PANEL.bridgeThickness.oninput = () => {
      viewer.bridgeThickness = clamp(Number(PANEL.bridgeThickness.value || 0.1), 0.03, 0.22);
      viewer.updateBridges();
      viewer.updateMetaPanel();
      viewer.setLegend();
    };
  }
  const liveFitInputs = [
    PANEL.fitScaleX,
    PANEL.fitScaleY,
    PANEL.fitScaleZ,
    PANEL.fitOffsetY,
    PANEL.fitZOffset,
  ];
  for (const input of liveFitInputs) {
    if (!input) continue;
    input.oninput = () => viewer.applyFitEditorToCurrentPart({ silent: true });
  }

  viewer.applyTheme();
  viewer.updateBridgeButton();
  viewer.updateVrmButton();
  viewer.updateVrmAttachButton();
  viewer.setCameraPreset("front");
  viewer.setLegend();
  viewer.updateLiveStatus("Live: inactive");
  window.addEventListener("beforeunload", () => viewer.stopLive({ silent: true }));
  PANEL.btnLoad.click();
}

function formatLoadError(error) {
  const raw = String(error?.message || error || "Unknown error");
  if (!raw.includes("Failed to load JSON")) return raw;
  if (raw.includes("(404)")) {
    return `${raw} / examples/... や sessions/... の相対パスを確認してください。`;
  }
  return `${raw} / ローカルHTTPサーバー起動中か確認してください。`;
}

init();


