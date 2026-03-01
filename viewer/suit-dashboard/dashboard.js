import * as THREE from "../body-fit/vendor/three/build/three.module.js";
import { OrbitControls } from "../body-fit/vendor/three/examples/jsm/controls/OrbitControls.js";

const UI = {
  suitPath: document.getElementById("suitPath"),
  fallbackDir: document.getElementById("fallbackDir"),
  textureMode: document.getElementById("textureMode"),
  uvRefine: document.getElementById("uvRefine"),
  simPath: document.getElementById("simPath"),
  preferFallback: document.getElementById("preferFallback"),
  updateSuitspec: document.getElementById("updateSuitspec"),
  promptPart: document.getElementById("promptPart"),
  promptPreview: document.getElementById("promptPreview"),
  partChecks: document.getElementById("partChecks"),
  fitPart: document.getElementById("fitPart"),
  fitSource: document.getElementById("fitSource"),
  fitAttach: document.getElementById("fitAttach"),
  fitOffsetY: document.getElementById("fitOffsetY"),
  fitZOffset: document.getElementById("fitZOffset"),
  fitScaleX: document.getElementById("fitScaleX"),
  fitScaleY: document.getElementById("fitScaleY"),
  fitScaleZ: document.getElementById("fitScaleZ"),
  fitFollowX: document.getElementById("fitFollowX"),
  fitFollowY: document.getElementById("fitFollowY"),
  fitFollowZ: document.getElementById("fitFollowZ"),
  fitMinScaleX: document.getElementById("fitMinScaleX"),
  fitMinScaleY: document.getElementById("fitMinScaleY"),
  fitMinScaleZ: document.getElementById("fitMinScaleZ"),
  btnFitLoad: document.getElementById("btnFitLoad"),
  btnFitApply: document.getElementById("btnFitApply"),
  btnFitReset: document.getElementById("btnFitReset"),
  btnFitSave: document.getElementById("btnFitSave"),
  fitPreview: document.getElementById("fitPreview"),
  vrmPart: document.getElementById("vrmPart"),
  vrmSlot: document.getElementById("vrmSlot"),
  vrmBone: document.getElementById("vrmBone"),
  vrmOffsetX: document.getElementById("vrmOffsetX"),
  vrmOffsetY: document.getElementById("vrmOffsetY"),
  vrmOffsetZ: document.getElementById("vrmOffsetZ"),
  vrmRotX: document.getElementById("vrmRotX"),
  vrmRotY: document.getElementById("vrmRotY"),
  vrmRotZ: document.getElementById("vrmRotZ"),
  vrmScaleX: document.getElementById("vrmScaleX"),
  vrmScaleY: document.getElementById("vrmScaleY"),
  vrmScaleZ: document.getElementById("vrmScaleZ"),
  btnVrmLoad: document.getElementById("btnVrmLoad"),
  btnVrmApply: document.getElementById("btnVrmApply"),
  btnVrmReset: document.getElementById("btnVrmReset"),
  btnVrmSave: document.getElementById("btnVrmSave"),
  vrmAnchorVisible: document.getElementById("vrmAnchorVisible"),
  vrmPreview: document.getElementById("vrmPreview"),
  vrmModelPath: document.getElementById("vrmModelPath"),
  btnVrmModelLoad: document.getElementById("btnVrmModelLoad"),
  btnVrmModelClear: document.getElementById("btnVrmModelClear"),
  vrmModelStatus: document.getElementById("vrmModelStatus"),
  reliefSlider: document.getElementById("reliefSlider"),
  status: document.getElementById("status"),
  cards: document.getElementById("cards"),
  btnRefreshSuits: document.getElementById("btnRefreshSuits"),
  btnLoadSuit: document.getElementById("btnLoadSuit"),
  btnGenerate: document.getElementById("btnGenerate"),
  btnOpenBodyFit: document.getElementById("btnOpenBodyFit"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  panelParts: document.getElementById("panelParts"),
  panelBody: document.getElementById("panelBody"),
  bodyFrontCanvas: document.getElementById("bodyFrontCanvas"),
  bodyFrontMeta: document.getElementById("bodyFrontMeta"),
  bodyTunePart: document.getElementById("bodyTunePart"),
  bodyTuneScaleX: document.getElementById("bodyTuneScaleX"),
  bodyTuneScaleY: document.getElementById("bodyTuneScaleY"),
  bodyTuneScaleZ: document.getElementById("bodyTuneScaleZ"),
  bodyTuneOffsetY: document.getElementById("bodyTuneOffsetY"),
  bodyTuneZOffset: document.getElementById("bodyTuneZOffset"),
  btnBodyTuneApply: document.getElementById("btnBodyTuneApply"),
  btnBodyTuneToFit: document.getElementById("btnBodyTuneToFit"),
};

const textureLoader = new THREE.TextureLoader();
const meshGeometryCache = new Map();

const previewCards = [];
let currentSuitPath = "";
let currentSuit = null;
let lastSummary = null;
let isSyncingTuneControls = false;

const BODY_FRONT_LAYOUT = {
  helmet: { pos: [0.0, 1.30, 0.08], scale: [0.66, 0.66, 0.66] },
  chest: { pos: [0.0, 0.72, 0.14], scale: [1.18, 1.22, 1.08] },
  back: { pos: [0.0, 0.72, -0.14], scale: [1.08, 1.18, 1.05] },
  waist: { pos: [0.0, 0.22, 0.06], scale: [1.0, 1.02, 1.02] },
  left_shoulder: { pos: [-0.55, 0.98, 0.02], scale: [0.68, 0.68, 0.68] },
  right_shoulder: { pos: [0.55, 0.98, 0.02], scale: [0.68, 0.68, 0.68] },
  left_upperarm: { pos: [-0.72, 0.66, 0.01], scale: [0.78, 0.96, 0.78] },
  right_upperarm: { pos: [0.72, 0.66, 0.01], scale: [0.78, 0.96, 0.78] },
  left_forearm: { pos: [-0.76, 0.22, 0.03], scale: [0.80, 1.02, 0.80] },
  right_forearm: { pos: [0.76, 0.22, 0.03], scale: [0.80, 1.02, 0.80] },
  left_hand: { pos: [-0.78, -0.24, 0.08], scale: [0.74, 0.74, 0.74] },
  right_hand: { pos: [0.78, -0.24, 0.08], scale: [0.74, 0.74, 0.74] },
  left_thigh: { pos: [-0.28, -0.42, 0.03], scale: [0.90, 1.18, 0.90] },
  right_thigh: { pos: [0.28, -0.42, 0.03], scale: [0.90, 1.18, 0.90] },
  left_shin: { pos: [-0.28, -1.02, 0.05], scale: [0.88, 1.20, 0.88] },
  right_shin: { pos: [0.28, -1.02, 0.05], scale: [0.88, 1.20, 0.88] },
  left_boot: { pos: [-0.28, -1.62, 0.20], scale: [0.92, 0.95, 1.18] },
  right_boot: { pos: [0.28, -1.62, 0.20], scale: [0.92, 0.95, 1.18] },
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

const FIT_BASELINES = {
  helmet: {
    source: "chest_core",
    attach: "start",
    offsetY: 0.2,
    zOffset: 0.02,
    scale: [0.3, 0.32, 0.3],
    follow: [0.34, 0.42, 0.34],
    minScale: [0.22, 0.24, 0.22],
  },
  chest: {
    source: "chest_core",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.72, 0.78, 0.66],
    follow: [0.72, 0.78, 0.72],
    minScale: [0.48, 0.56, 0.46],
  },
  back: {
    source: "chest_core",
    attach: "center",
    offsetY: -0.02,
    zOffset: -0.1,
    scale: [0.68, 0.74, 0.6],
    follow: [0.68, 0.76, 0.68],
    minScale: [0.46, 0.54, 0.42],
  },
  waist: {
    source: "chest_core",
    attach: "end",
    offsetY: -0.08,
    zOffset: 0.0,
    scale: [0.52, 0.38, 0.46],
    follow: [0.62, 0.7, 0.62],
    minScale: [0.34, 0.28, 0.3],
  },
  left_shoulder: {
    source: "left_upperarm",
    attach: "start",
    offsetY: 0.08,
    zOffset: 0.0,
    scale: [0.24, 0.24, 0.24],
    follow: [0.56, 0.5, 0.56],
    minScale: [0.16, 0.16, 0.16],
  },
  right_shoulder: {
    source: "right_upperarm",
    attach: "start",
    offsetY: 0.08,
    zOffset: 0.0,
    scale: [0.24, 0.24, 0.24],
    follow: [0.56, 0.5, 0.56],
    minScale: [0.16, 0.16, 0.16],
  },
  left_upperarm: {
    source: "left_upperarm",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.94, 1.0, 0.94],
    follow: [0.88, 0.94, 0.88],
    minScale: [0.52, 0.56, 0.52],
  },
  right_upperarm: {
    source: "right_upperarm",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.94, 1.0, 0.94],
    follow: [0.88, 0.94, 0.88],
    minScale: [0.52, 0.56, 0.52],
  },
  left_forearm: {
    source: "left_forearm",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.9, 1.02, 0.9],
    follow: [0.9, 0.96, 0.9],
    minScale: [0.48, 0.56, 0.48],
  },
  right_forearm: {
    source: "right_forearm",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.9, 1.02, 0.9],
    follow: [0.9, 0.96, 0.9],
    minScale: [0.48, 0.56, 0.48],
  },
  left_hand: {
    source: "left_forearm",
    attach: "end",
    offsetY: -0.08,
    zOffset: 0.03,
    scale: [0.2, 0.2, 0.2],
    follow: [0.38, 0.34, 0.38],
    minScale: [0.14, 0.14, 0.14],
  },
  right_hand: {
    source: "right_forearm",
    attach: "end",
    offsetY: -0.08,
    zOffset: 0.03,
    scale: [0.2, 0.2, 0.2],
    follow: [0.38, 0.34, 0.38],
    minScale: [0.14, 0.14, 0.14],
  },
  left_thigh: {
    source: "left_thigh",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [1.0, 1.04, 1.0],
    follow: [0.94, 0.96, 0.94],
    minScale: [0.56, 0.66, 0.56],
  },
  right_thigh: {
    source: "right_thigh",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [1.0, 1.04, 1.0],
    follow: [0.94, 0.96, 0.94],
    minScale: [0.56, 0.66, 0.56],
  },
  left_shin: {
    source: "left_shin",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.96, 1.04, 0.96],
    follow: [0.92, 0.96, 0.92],
    minScale: [0.52, 0.64, 0.52],
  },
  right_shin: {
    source: "right_shin",
    attach: "center",
    offsetY: 0.0,
    zOffset: 0.0,
    scale: [0.96, 1.04, 0.96],
    follow: [0.92, 0.96, 0.92],
    minScale: [0.52, 0.64, 0.52],
  },
  left_boot: {
    source: "left_shin",
    attach: "end",
    offsetY: -0.14,
    zOffset: 0.08,
    scale: [0.28, 0.22, 0.4],
    follow: [0.58, 0.52, 0.62],
    minScale: [0.2, 0.16, 0.24],
  },
  right_boot: {
    source: "right_shin",
    attach: "end",
    offsetY: -0.14,
    zOffset: 0.08,
    scale: [0.28, 0.22, 0.4],
    follow: [0.58, 0.52, 0.62],
    minScale: [0.2, 0.16, 0.24],
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

const VRM_HUMANOID_BONES = [
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
];

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

const ATTACHMENT_SLOT_ALIASES = {
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
};

const DEFAULT_VRM_CANDIDATES = [
  "viewer/assets/vrm/default.vrm",
  "viewer/assets/vrm/default.glb",
  "viewer/assets/vrm/default.gltf",
];

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

let gltfLoaderModulePromise = null;

function setStatus(text, isError = false) {
  UI.status.textContent = text;
  UI.status.style.color = isError ? "#9c1b2f" : "#17335f";
}

function normPath(path) {
  let p = String(path || "").replace(/\\/g, "/").trim();
  if (!p) return p;
  if (/^https?:\/\//i.test(p)) return p;
  if (p.startsWith("/")) return p;
  if (p.startsWith("./")) p = p.slice(2);
  return `/${p}`;
}

function normalizeBoneName(name) {
  return String(name || "")
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

async function pathExists(path) {
  const url = normPath(path);
  if (!url) return false;
  try {
    const res = await fetch(url, { method: "HEAD" });
    if (res.ok) return true;
  } catch {
    // fall through
  }
  try {
    const res = await fetch(url, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

async function discoverDefaultVrmPath() {
  for (const candidate of DEFAULT_VRM_CANDIDATES) {
    if (await pathExists(candidate)) {
      return candidate;
    }
  }
  return "";
}

function setVrmModelStatus(text) {
  if (!UI.vrmModelStatus) return;
  UI.vrmModelStatus.textContent = text;
}

async function getGLTFLoaderClass() {
  if (!gltfLoaderModulePromise) {
    gltfLoaderModulePromise = import("../body-fit/vendor/three/examples/jsm/loaders/GLTFLoader.js").catch(() =>
      import("https://cdn.jsdelivr.net/npm/three@0.173.0/examples/jsm/loaders/GLTFLoader.js/+esm")
    );
  }
  const mod = await gltfLoaderModulePromise;
  if (!mod?.GLTFLoader) {
    throw new Error("GLTFLoader not available.");
  }
  return mod.GLTFLoader;
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
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
  const score = clamp(1 - gapPenalty * 0.65 - penetrationPenalty * 0.35, 0, 1);
  return score;
}

function numOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function vec3Or(input, fallback) {
  const fb = Array.isArray(fallback) && fallback.length >= 3 ? fallback : [1, 1, 1];
  if (Array.isArray(input) && input.length >= 3) {
    return [numOr(input[0], fb[0]), numOr(input[1], fb[1]), numOr(input[2], fb[2])];
  }
  if (input && typeof input === "object") {
    return [numOr(input.x, fb[0]), numOr(input.y, fb[1]), numOr(input.z, fb[2])];
  }
  return [...fb];
}

function normalizeFit(rawFit, fallback) {
  const base = fallback || {
    source: "chest_core",
    attach: "center",
    offsetY: 0,
    zOffset: 0,
    scale: [1, 1, 1],
    follow: [1, 1, 1],
    minScale: [0.2, 0.2, 0.2],
  };
  const fit = rawFit && typeof rawFit === "object" ? rawFit : {};
  const attach = String(fit.attach ?? base.attach ?? "center").toLowerCase();
  const safeAttach = attach === "start" || attach === "end" ? attach : "center";
  return {
    source: String(fit.source ?? base.source ?? "chest_core"),
    attach: safeAttach,
    offsetY: numOr(fit.offsetY, numOr(base.offsetY, 0)),
    zOffset: numOr(fit.zOffset, numOr(base.zOffset, 0)),
    scale: vec3Or(fit.scale, base.scale ?? [1, 1, 1]),
    follow: vec3Or(fit.follow, base.follow ?? [1, 1, 1]),
    minScale: vec3Or(fit.minScale, base.minScale ?? [0.2, 0.2, 0.2]),
  };
}

function baseFitFor(partName) {
  return normalizeFit(FIT_BASELINES[partName], null);
}

function effectiveFitFor(partName, module) {
  const base = baseFitFor(partName);
  const override = module?.fit;
  return normalizeFit(override, base);
}

function partColor(partName) {
  return PART_COLOR_MAP[partName] || 0x6ea3e6;
}

function normalizeVrmAnchor(rawAnchor, fallback) {
  const base = fallback || {
    bone: "chest",
    offset: [0, 0, 0],
    rotation: [0, 0, 0],
    scale: [1, 1, 1],
  };
  const anchor = rawAnchor && typeof rawAnchor === "object" ? rawAnchor : {};
  const bone = String(anchor.bone ?? base.bone ?? "chest").trim() || "chest";
  const offset = vec3Or(anchor.offset, base.offset ?? [0, 0, 0]);
  const rotation = vec3Or(anchor.rotation, base.rotation ?? [0, 0, 0]);
  const scale = vec3Or(anchor.scale, base.scale ?? [1, 1, 1]).map((v) => Math.max(0.01, v));
  return { bone, offset, rotation, scale };
}

function normalizeAttachmentSlot(partName, module) {
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

function baseVrmAnchorFor(slotName) {
  return normalizeVrmAnchor(VRM_ANCHOR_BASELINES[slotName], null);
}

function effectiveVrmAnchorFor(partName, module) {
  const slot = normalizeAttachmentSlot(partName, module);
  const base = baseVrmAnchorFor(slot);
  return normalizeVrmAnchor(module?.vrm_anchor, base);
}

function bodyFrontTransformFor(partName, module) {
  const layout = BODY_FRONT_LAYOUT[partName] || { pos: [0, 0, 0], scale: [1, 1, 1] };
  const fit = effectiveFitFor(partName, module);
  return {
    position: [layout.pos[0], layout.pos[1] + fit.offsetY, layout.pos[2] + fit.zOffset],
    scale: [
      Math.max(layout.scale[0] * fit.scale[0], 0.02),
      Math.max(layout.scale[1] * fit.scale[1], 0.02),
      Math.max(layout.scale[2] * fit.scale[2], 0.02),
    ],
  };
}

function ensureSelectValue(select, value) {
  const normalized = String(value || "").trim();
  if (!normalized) return;
  const hasOption = Array.from(select.options).some((op) => op.value === normalized);
  if (!hasOption) {
    const option = document.createElement("option");
    option.value = normalized;
    option.textContent = normalized;
    select.appendChild(option);
  }
  select.value = normalized;
}

function populateVrmBoneOptions() {
  if (!UI.vrmBone) return;
  UI.vrmBone.innerHTML = "";
  for (const bone of VRM_HUMANOID_BONES) {
    const op = document.createElement("option");
    op.value = bone;
    op.textContent = bone;
    UI.vrmBone.appendChild(op);
  }
}

function readEnabledModules(suitspec) {
  const modules = suitspec?.modules || {};
  return Object.entries(modules).filter(([, mod]) => mod && mod.enabled);
}

function resolveMeshAssetPath(partName, module) {
  const ref = String(module?.asset_ref || "").replace(/\\/g, "/").trim();
  if (ref.toLowerCase().endsWith(".mesh.json")) return ref;
  return `viewer/assets/meshes/${partName}.mesh.json`;
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh format.");
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

async function loadMeshGeometryFromAsset(assetPath) {
  const key = normPath(assetPath);
  if (meshGeometryCache.has(key)) {
    return meshGeometryCache.get(key).clone();
  }
  const res = await fetch(key);
  if (!res.ok) {
    throw new Error(`mesh load failed: ${key} (${res.status})`);
  }
  const payload = await res.json();
  const geometry = meshGeometryFromPayload(payload);
  meshGeometryCache.set(key, geometry);
  return geometry.clone();
}

function restoreBase(mesh) {
  const pos = mesh.geometry.attributes.position;
  const base = mesh.userData.basePositions;
  if (!pos || !base || base.length !== pos.array.length) return;
  for (let i = 0; i < pos.count; i++) {
    pos.setXYZ(i, base[i * 3], base[i * 3 + 1], base[i * 3 + 2]);
  }
  pos.needsUpdate = true;
  mesh.geometry.computeVertexNormals();
}

function applyRelief(mesh, texture, amplitude) {
  const image = texture?.image;
  if (!image || amplitude <= 0) {
    restoreBase(mesh);
    return;
  }

  const geo = mesh.geometry;
  const pos = geo.attributes.position;
  const norm = geo.attributes.normal;
  const uv = geo.attributes.uv;
  const base = mesh.userData.basePositions;
  if (!pos || !norm || !uv || !base || base.length !== pos.array.length) return;

  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.drawImage(image, 0, 0, size, size);
  const data = ctx.getImageData(0, 0, size, size).data;

  for (let i = 0; i < pos.count; i++) {
    const u = clamp(uv.getX(i), 0, 1);
    const v = clamp(uv.getY(i), 0, 1);
    const x = Math.floor(u * (size - 1));
    const y = Math.floor((1 - v) * (size - 1));
    const idx = (y * size + x) * 4;

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
    const invLen = 1 / (Math.hypot(nx, ny, nz) || 1);

    pos.setXYZ(
      i,
      base[i * 3] + nx * invLen * disp,
      base[i * 3 + 1] + ny * invLen * disp,
      base[i * 3 + 2] + nz * invLen * disp
    );
  }
  pos.needsUpdate = true;
  geo.computeVertexNormals();
}

function loadTexture(path) {
  if (!path) return Promise.resolve(null);
  return new Promise((resolve) => {
    textureLoader.load(
      normPath(path),
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        tex.anisotropy = 4;
        resolve(tex);
      },
      undefined,
      () => resolve(null)
    );
  });
}

function fitCameraToObject(camera, controls, object3d, distanceFactor = 2.35) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) return;
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 0.05);
  const fov = (camera.fov * Math.PI) / 180;
  const distance = (radius / Math.sin(fov / 2)) * distanceFactor;
  camera.position.set(sphere.center.x, sphere.center.y + radius * 0.15, sphere.center.z + distance);
  controls.target.copy(sphere.center);
  controls.update();
}

function prepareCanvas(canvas) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(2, Math.floor((canvas.clientWidth || 320) * dpr));
  const h = Math.max(2, Math.floor((canvas.clientHeight || 210) * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  return { w, h };
}

function computeUvAreaRatio(geometry) {
  const uv = geometry?.getAttribute("uv");
  if (!uv || uv.count < 3) return 0;

  let area = 0;
  if (geometry.index) {
    const idx = geometry.index.array;
    for (let i = 0; i < idx.length; i += 3) {
      const a = idx[i];
      const b = idx[i + 1];
      const c = idx[i + 2];
      const ax = uv.getX(a);
      const ay = uv.getY(a);
      const bx = uv.getX(b);
      const by = uv.getY(b);
      const cx = uv.getX(c);
      const cy = uv.getY(c);
      area += Math.abs((ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)) * 0.5);
    }
  } else {
    for (let i = 0; i < uv.count; i += 3) {
      const ax = uv.getX(i);
      const ay = uv.getY(i);
      const bx = uv.getX(i + 1);
      const by = uv.getY(i + 1);
      const cx = uv.getX(i + 2);
      const cy = uv.getY(i + 2);
      area += Math.abs((ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)) * 0.5);
    }
  }
  return clamp(area, 0, 1);
}

function analyzeTextureCoverage(image) {
  if (!image) {
    return { fillRatio: 0, borderFillRatio: 0 };
  }

  const size = 256;
  const edge = Math.max(2, Math.floor(size * 0.04));
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return { fillRatio: 0, borderFillRatio: 0 };

  ctx.drawImage(image, 0, 0, size, size);
  const data = ctx.getImageData(0, 0, size, size).data;

  let ink = 0;
  let borderInk = 0;
  let borderTotal = 0;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const r = data[i + 0];
      const g = data[i + 1];
      const b = data[i + 2];
      const lum = (r + g + b) / 3;
      const sat = Math.max(r, g, b) - Math.min(r, g, b);
      const isInk = lum < 245 || sat > 22;
      if (isInk) ink += 1;

      const isBorder = x < edge || x >= size - edge || y < edge || y >= size - edge;
      if (isBorder) {
        borderTotal += 1;
        if (isInk) borderInk += 1;
      }
    }
  }

  const total = size * size;
  return {
    fillRatio: ink / total,
    borderFillRatio: borderTotal ? borderInk / borderTotal : 0,
  };
}

function drawUvWire(ctx, geometry, width, height) {
  const uv = geometry?.getAttribute("uv");
  if (!uv || uv.count < 3) return;

  ctx.strokeStyle = "rgba(14, 52, 112, 0.72)";
  ctx.lineWidth = 1;

  const drawTri = (a, b, c) => {
    const ax = uv.getX(a) * width;
    const ay = (1 - uv.getY(a)) * height;
    const bx = uv.getX(b) * width;
    const by = (1 - uv.getY(b)) * height;
    const cx = uv.getX(c) * width;
    const cy = (1 - uv.getY(c)) * height;

    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(bx, by);
    ctx.lineTo(cx, cy);
    ctx.closePath();
    ctx.stroke();
  };

  if (geometry.index) {
    const idx = geometry.index.array;
    for (let i = 0; i < idx.length; i += 3) {
      drawTri(idx[i], idx[i + 1], idx[i + 2]);
    }
  } else {
    for (let i = 0; i < uv.count; i += 3) {
      drawTri(i, i + 1, i + 2);
    }
  }
}

class PartCardPreview {
  constructor({ meshCanvas, uvCanvas, statsNode, partName, module }) {
    this.meshCanvas = meshCanvas;
    this.uvCanvas = uvCanvas;
    this.statsNode = statsNode;
    this.partName = partName;
    this.module = module || {};
    this.texturePath = this.module.texture_path || null;
    this.assetPath = resolveMeshAssetPath(this.partName, this.module);
    this.texture = null;
    this.textureImage = null;

    this.renderer = new THREE.WebGLRenderer({ canvas: meshCanvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(44, 1, 0.01, 50);
    this.camera.position.set(0, 0.2, 2.2);

    this.controls = new OrbitControls(this.camera, meshCanvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.5;
    this.controls.target.set(0, 0, 0);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.78));
    const dir = new THREE.DirectionalLight(0xffffff, 0.86);
    dir.position.set(1.2, 1.8, 1.4);
    this.scene.add(dir);

    const geometry = new THREE.SphereGeometry(0.5, 24, 16).toNonIndexed();
    const material = new THREE.MeshStandardMaterial({
      color: 0xe6eefb,
      metalness: 0.68,
      roughness: 0.3,
      side: THREE.DoubleSide,
    });

    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);
    this.scene.add(this.mesh);

    this.wire = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry, 18),
      new THREE.LineBasicMaterial({ color: 0x355e99, transparent: true, opacity: 0.32 })
    );
    this.scene.add(this.wire);

    this.tick = this.tick.bind(this);
    requestAnimationFrame(this.tick);

    this.loadAssetGeometry().then(() => this.updateUvDebug());
    this.loadTextureAndRelief(Number(UI.reliefSlider.value || "0.05"));
  }

  async loadAssetGeometry() {
    try {
      const geometry = await loadMeshGeometryFromAsset(this.assetPath);
      this.mesh.geometry.dispose();
      this.mesh.geometry = geometry;
      this.mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);
      this.wire.geometry.dispose();
      this.wire.geometry = new THREE.EdgesGeometry(geometry, 18);
      fitCameraToObject(this.camera, this.controls, this.mesh, 2.15);
    } catch (error) {
      console.warn(`asset mesh fallback for ${this.partName}`, error);
    }
  }

  async loadTextureAndRelief(amplitude) {
    if (!this.texturePath) {
      restoreBase(this.mesh);
      this.mesh.material.map = null;
      this.mesh.material.color.setHex(0xdfe8f8);
      this.mesh.material.needsUpdate = true;
      this.texture = null;
      this.textureImage = null;
      this.updateUvDebug();
      return;
    }

    const tex = await loadTexture(this.texturePath);
    this.texture = tex;
    this.textureImage = tex?.image || null;

    if (tex) {
      this.mesh.material.map = tex;
      this.mesh.material.color.setHex(0xe7f0ff);
      this.mesh.material.needsUpdate = true;
      applyRelief(this.mesh, tex, amplitude);
    } else {
      this.mesh.material.map = null;
      this.mesh.material.color.setHex(0xdfe8f8);
      this.mesh.material.needsUpdate = true;
      restoreBase(this.mesh);
    }

    this.updateUvDebug();
  }

  updateRelief(amplitude) {
    applyRelief(this.mesh, this.texture, amplitude);
  }

  updateUvDebug() {
    const { w, h } = prepareCanvas(this.uvCanvas);
    const ctx = this.uvCanvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, h);

    if (this.textureImage) {
      ctx.drawImage(this.textureImage, 0, 0, w, h);
    } else {
      ctx.fillStyle = "#f5f8ff";
      for (let y = 0; y < h; y += 24) {
        for (let x = 0; x < w; x += 24) {
          if (((x + y) / 24) % 2 === 0) {
            ctx.fillRect(x, y, 24, 24);
          }
        }
      }
    }

    drawUvWire(ctx, this.mesh.geometry, w, h);

    const uvAreaRatio = computeUvAreaRatio(this.mesh.geometry);
    const coverage = analyzeTextureCoverage(this.textureImage);
    const fitScore = clamp(1 - Math.abs(coverage.fillRatio - uvAreaRatio), 0, 1);

    const text = [
      `UV占有: ${(uvAreaRatio * 100).toFixed(1)}%`,
      `テクスチャ充填: ${(coverage.fillRatio * 100).toFixed(1)}%`,
      `外周充填: ${(coverage.borderFillRatio * 100).toFixed(1)}%`,
      `一致度: ${(fitScore * 100).toFixed(1)}%`,
    ].join(" | ");

    this.statsNode.textContent = text;
    this.statsNode.style.color = fitScore < 0.7 ? "#9c1b2f" : "#35567f";
  }

  tick() {
    const w = this.meshCanvas.clientWidth || 320;
    const h = this.meshCanvas.clientHeight || 210;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.tick);
  }
}

class BodyFrontPreview {
  constructor(canvas, metaNode) {
    this.canvas = canvas;
    this.metaNode = metaNode;
    this.records = [];
    this.anchorRecords = new Map();
    this.anchorVisible = true;
    this.vrmRoot = new THREE.Group();
    this.vrmModel = null;
    this.vrmModelPath = "";
    this.vrmBoneMap = new Map();
    this.vrmLoadError = "";

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(38, 1, 0.01, 60);
    this.camera.position.set(0, 0.4, 4.0);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.enablePan = false;
    this.controls.maxPolarAngle = Math.PI * 0.65;
    this.controls.target.set(0, 0.1, 0);

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.anchorGroup = new THREE.Group();
    this.scene.add(this.anchorGroup);
    this.scene.add(this.vrmRoot);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.68));
    const key = new THREE.DirectionalLight(0xffffff, 1.0);
    key.position.set(2.2, 3.0, 3.8);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.56);
    fill.position.set(-2.0, 1.4, 2.0);
    this.scene.add(fill);

    this.tick = this.tick.bind(this);
    requestAnimationFrame(this.tick);
  }

  clear() {
    this.clearAnchors();
    for (const rec of this.records) {
      this.root.remove(rec.group);
      rec.mesh.geometry.dispose();
      rec.mesh.material.dispose();
      rec.wire.geometry.dispose();
      rec.wire.material.dispose();
    }
    this.records = [];
  }

  clearVrmModel() {
    if (this.vrmModel) {
      this.vrmRoot.remove(this.vrmModel);
      this.vrmModel.traverse((obj) => {
        if (!obj.isMesh) return;
        if (obj.geometry) obj.geometry.dispose?.();
        const material = obj.material;
        if (Array.isArray(material)) {
          for (const m of material) m?.dispose?.();
        } else {
          material?.dispose?.();
        }
      });
    }
    this.vrmModel = null;
    this.vrmBoneMap = new Map();
    this.vrmModelPath = "";
    this.vrmLoadError = "";
  }

  buildVrmBoneMap(model) {
    const map = new Map();
    model.traverse((obj) => {
      if (!obj.isBone) return;
      const key = normalizeBoneName(obj.name);
      if (!key) return;
      if (!map.has(key)) map.set(key, obj);
    });
    return map;
  }

  findVrmBone(humanoidBoneName) {
    if (!this.vrmBoneMap || this.vrmBoneMap.size === 0) return null;
    const aliases = VRM_BONE_ALIASES[humanoidBoneName] || [humanoidBoneName];
    for (const alias of aliases) {
      const key = normalizeBoneName(alias);
      const bone = this.vrmBoneMap.get(key);
      if (bone) return bone;
    }
    return null;
  }

  alignVrmModelToScene(model) {
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    if (box.isEmpty()) return;

    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const height = Math.max(size.y, 0.001);
    const targetHeight = 3.0;
    const scale = clamp(targetHeight / height, 0.4, 4.0);
    model.scale.setScalar(scale);
    model.updateMatrixWorld(true);

    const scaledBox = new THREE.Box3().setFromObject(model);
    const scaledCenter = scaledBox.getCenter(new THREE.Vector3());
    const minY = scaledBox.min.y;
    const targetFloorY = -1.74;
    model.position.set(
      model.position.x - scaledCenter.x,
      model.position.y + (targetFloorY - minY),
      model.position.z - scaledCenter.z + 0.02
    );
    model.updateMatrixWorld(true);
  }

  async loadVrmModel(path, { applyBlackMaterial = false } = {}) {
    const rawPath = String(path || "").trim();
    if (!rawPath) {
      this.clearVrmModel();
      this.updateMeta();
      return;
    }

    const exists = await pathExists(rawPath);
    if (!exists) {
      this.vrmLoadError = `VRM file not found: ${rawPath}`;
      throw new Error(this.vrmLoadError);
    }

    const GLTFLoader = await getGLTFLoaderClass();
    const loader = new GLTFLoader();
    const url = normPath(rawPath);
    const gltf = await new Promise((resolve, reject) => {
      loader.load(url, resolve, undefined, reject);
    });

    this.clearVrmModel();
    const model = gltf.scene || gltf.scenes?.[0];
    if (!model) {
      this.vrmLoadError = `Invalid VRM/GLTF scene: ${rawPath}`;
      throw new Error(this.vrmLoadError);
    }

    if (applyBlackMaterial) {
      model.traverse((obj) => {
        if (!obj.isMesh) return;
        obj.material = new THREE.MeshStandardMaterial({
          color: 0x0a0a0a,
          metalness: 0.12,
          roughness: 0.82,
          side: THREE.DoubleSide,
        });
      });
    }

    this.alignVrmModelToScene(model);
    this.vrmRoot.add(model);
    this.vrmModel = model;
    this.vrmModelPath = rawPath;
    this.vrmBoneMap = this.buildVrmBoneMap(model);
    this.vrmLoadError = "";

    this.updateAnchors(currentSuit);
    this.updateMeta();
    fitCameraToObject(this.camera, this.controls, this.root, 2.6);
  }

  clearAnchors() {
    for (const marker of this.anchorRecords.values()) {
      this.anchorGroup.remove(marker.sphere);
      this.anchorGroup.remove(marker.line);
      this.anchorGroup.remove(marker.axes);
      marker.sphere.geometry.dispose();
      marker.sphere.material.dispose();
      marker.line.geometry.dispose();
      marker.line.material.dispose();
      marker.axes.geometry.dispose();
      if (Array.isArray(marker.axes.material)) {
        for (const m of marker.axes.material) m.dispose();
      } else {
        marker.axes.material.dispose();
      }
    }
    this.anchorRecords.clear();
  }

  setAnchorVisible(enabled) {
    this.anchorVisible = Boolean(enabled);
    for (const marker of this.anchorRecords.values()) {
      marker.sphere.visible = this.anchorVisible;
      marker.line.visible = this.anchorVisible;
      marker.axes.visible = this.anchorVisible;
    }
    this.updateMeta();
  }

  ensureAnchorMarker(partName) {
    const cached = this.anchorRecords.get(partName);
    if (cached) return cached;
    const color = partColor(partName);
    const sphere = new THREE.Mesh(
      new THREE.SphereGeometry(0.03, 14, 10),
      new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.34,
        roughness: 0.45,
        metalness: 0.2,
      })
    );
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]),
      new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.82 })
    );
    const axes = new THREE.AxesHelper(0.09);
    sphere.visible = this.anchorVisible;
    line.visible = this.anchorVisible;
    axes.visible = this.anchorVisible;
    this.anchorGroup.add(sphere);
    this.anchorGroup.add(line);
    this.anchorGroup.add(axes);
    const marker = { sphere, line, axes };
    this.anchorRecords.set(partName, marker);
    return marker;
  }

  updateAnchorForPart(partName, module) {
    const rec = this.findRecord(partName);
    const marker = this.ensureAnchorMarker(partName);
    if (!rec || !module) {
      marker.sphere.visible = false;
      marker.line.visible = false;
      marker.axes.visible = false;
      return;
    }

    const anchor = effectiveVrmAnchorFor(partName, module);
    const center = rec.mesh.getWorldPosition(new THREE.Vector3());
    const anchorWorld = new THREE.Vector3();
    const baseQuat = new THREE.Quaternion();
    const vrmBone = this.findVrmBone(anchor.bone);
    if (vrmBone) {
      vrmBone.getWorldPosition(anchorWorld);
      vrmBone.getWorldQuaternion(baseQuat);
      const localOffset = new THREE.Vector3(anchor.offset[0], anchor.offset[1], anchor.offset[2]);
      localOffset.applyQuaternion(baseQuat);
      anchorWorld.add(localOffset);
    } else {
      rec.mesh.getWorldQuaternion(baseQuat);
      anchorWorld.copy(rec.mesh.localToWorld(new THREE.Vector3(anchor.offset[0], anchor.offset[1], anchor.offset[2])));
    }

    marker.sphere.position.copy(anchorWorld);
    marker.line.geometry.setFromPoints([center, anchorWorld]);
    marker.axes.position.copy(anchorWorld);
    const localQuat = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(
        THREE.MathUtils.degToRad(anchor.rotation[0]),
        THREE.MathUtils.degToRad(anchor.rotation[1]),
        THREE.MathUtils.degToRad(anchor.rotation[2]),
        "XYZ"
      )
    );
    marker.axes.quaternion.copy(baseQuat).multiply(localQuat);
    const axisScale = clamp((anchor.scale[0] + anchor.scale[1] + anchor.scale[2]) / 3, 0.2, 3.0);
    marker.axes.scale.setScalar(axisScale);
    marker.sphere.visible = this.anchorVisible;
    marker.line.visible = this.anchorVisible;
    marker.axes.visible = this.anchorVisible;
  }

  updateAnchors(suitspec) {
    const modules = suitspec?.modules || {};
    for (const rec of this.records) {
      this.updateAnchorForPart(rec.partName, modules[rec.partName]);
    }
  }

  applyTransformToRecord(rec, transform) {
    const p = transform?.position || [0, 0, 0];
    const s = transform?.scale || [1, 1, 1];
    rec.mesh.position.set(p[0], p[1], p[2]);
    rec.mesh.scale.set(s[0], s[1], s[2]);
    rec.wire.position.copy(rec.mesh.position);
    rec.wire.scale.copy(rec.mesh.scale);
  }

  findRecord(partName) {
    return this.records.find((rec) => rec.partName === partName) || null;
  }

  refreshPart(partName, module) {
    const rec = this.findRecord(partName);
    if (!rec) return;
    this.applyTransformToRecord(rec, bodyFrontTransformFor(partName, module));
    this.updateAnchorForPart(partName, module);
    this.root.updateMatrixWorld(true);
    this.updateMeta();
    fitCameraToObject(this.camera, this.controls, this.root, 2.6);
  }

  calculateFitStats() {
    this.root.updateMatrixWorld(true);
    const byPart = new Map();
    for (const rec of this.records) {
      const box = new THREE.Box3().setFromObject(rec.mesh);
      byPart.set(rec.partName, box);
    }

    let totalGap = 0;
    let totalPenetration = 0;
    let totalScore = 0;
    let count = 0;
    const weakPairs = [];

    for (const [aName, bName] of FIT_CONTACT_PAIRS) {
      const a = byPart.get(aName);
      const b = byPart.get(bName);
      if (!a || !b) continue;
      const { gap, penetration } = aabbGapAndPenetration(a, b);
      const score = fitPairScore(gap, penetration);
      totalGap += gap;
      totalPenetration += penetration;
      totalScore += score;
      count += 1;
      weakPairs.push({ pair: `${aName}-${bName}`, gap, penetration, score });
    }

    if (count === 0) {
      return {
        pairCount: 0,
        meanGap: 0,
        meanPenetration: 0,
        score: 0,
        weakest: [],
      };
    }

    weakPairs.sort((x, y) => x.score - y.score);
    return {
      pairCount: count,
      meanGap: totalGap / count,
      meanPenetration: totalPenetration / count,
      score: totalScore / count,
      weakest: weakPairs.slice(0, 3),
    };
  }

  updateMeta() {
    const stats = this.calculateFitStats();
    const weakText =
      stats.weakest.length === 0
        ? "-"
        : stats.weakest
            .map(
              (w) =>
                `${w.pair}: score ${(w.score * 100).toFixed(1)} / gap ${w.gap.toFixed(3)} / pen ${w.penetration.toFixed(3)}`
            )
            .join("\n");

    this.metaNode.textContent = [
      `パーツ数: ${this.records.length}`,
      `表示: ボディ前景 + 頂点線`,
      `背景: 白固定`,
      `反映: fit.scale / fit.offsetY / fit.zOffset`,
      `VRMモデル: ${this.vrmModel ? "LOADED" : "NONE"} ${this.vrmModelPath ? `(${this.vrmModelPath})` : ""}`,
      `VRMボーン数: ${this.vrmBoneMap?.size || 0}`,
      `VRMアンカー: ${this.anchorRecords.size} / visible=${this.anchorVisible ? "ON" : "OFF"}`,
      `接続ペア: ${stats.pairCount}`,
      `平均すき間: ${stats.meanGap.toFixed(3)}`,
      `平均食い込み: ${stats.meanPenetration.toFixed(3)}`,
      `フィットスコア: ${(stats.score * 100).toFixed(1)} / 100`,
      `要改善ペア:\n${weakText}`,
      this.vrmLoadError ? `VRM読込エラー: ${this.vrmLoadError}` : "VRM読込エラー: なし",
      `用途: パーツの接続・密度・前景バランス確認`,
    ].join("\n");
  }

  async loadSuit(suitspec) {
    this.clear();

    const modules = readEnabledModules(suitspec);
    const relief = Number(UI.reliefSlider.value || "0.05");

    for (const [name, mod] of modules) {
      const assetPath = resolveMeshAssetPath(name, mod);
      let geometry;
      try {
        geometry = await loadMeshGeometryFromAsset(assetPath);
      } catch {
        geometry = new THREE.BoxGeometry(1, 1, 1, 8, 8, 8).toNonIndexed();
      }

      const material = new THREE.MeshStandardMaterial({
        color: 0xeaf1fb,
        metalness: 0.6,
        roughness: 0.34,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData.basePositions = new Float32Array(geometry.attributes.position.array);

      const wire = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry, 16),
        new THREE.LineBasicMaterial({ color: 0x244c86, transparent: true, opacity: 0.48 })
      );

      const group = new THREE.Group();
      group.add(mesh);
      group.add(wire);
      this.root.add(group);

      const tex = await loadTexture(mod.texture_path || null);
      if (tex) {
        mesh.material.map = tex;
        mesh.material.color.setHex(0xe8f1ff);
        mesh.material.needsUpdate = true;
        applyRelief(mesh, tex, relief);
      }

      const rec = { partName: name, group, mesh, wire, texture: tex };
      this.applyTransformToRecord(rec, bodyFrontTransformFor(name, mod));
      this.records.push(rec);
    }

    this.updateAnchors(suitspec);
    this.setAnchorVisible(Boolean(UI.vrmAnchorVisible?.checked ?? true));
    fitCameraToObject(this.camera, this.controls, this.root, 2.6);
    this.updateMeta();
  }

  updateRelief(amplitude) {
    for (const rec of this.records) {
      applyRelief(rec.mesh, rec.texture, amplitude);
    }
  }

  tick() {
    const w = this.canvas.clientWidth || 720;
    const h = this.canvas.clientHeight || 520;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.tick);
  }
}

const bodyFrontPreview = new BodyFrontPreview(UI.bodyFrontCanvas, UI.bodyFrontMeta);

async function loadVrmModelFromInput({ silent = false } = {}) {
  const path = String(UI.vrmModelPath?.value || "").trim();
  if (!path) {
    bodyFrontPreview.clearVrmModel();
    bodyFrontPreview.updateAnchors(currentSuit);
    bodyFrontPreview.updateMeta();
    setVrmModelStatus("VRM: 未読込");
    if (!silent) setStatus("VRMモデルを解除しました。");
    return;
  }
  try {
    setVrmModelStatus(`VRM読込中: ${path}`);
    await bodyFrontPreview.loadVrmModel(path, { applyBlackMaterial: false });
    const bones = bodyFrontPreview.vrmBoneMap?.size || 0;
    setVrmModelStatus(`VRM: 読込済み\npath: ${path}\nbones: ${bones}`);
    if (!silent) setStatus(`VRMモデルを読込しました: ${path}`);
  } catch (err) {
    const msg = String(err?.message || err || "VRM load failed");
    setVrmModelStatus(`VRM: 読込失敗\npath: ${path}\nerror: ${msg}`);
    setStatus(`VRM読込失敗: ${msg}`, true);
  }
}

function clearVrmModelFromInput({ silent = false } = {}) {
  bodyFrontPreview.clearVrmModel();
  bodyFrontPreview.updateAnchors(currentSuit);
  bodyFrontPreview.updateMeta();
  setVrmModelStatus("VRM: 未読込");
  if (!silent) setStatus("VRMモデルを解除しました。");
}

function renderPartChecks(parts) {
  UI.partChecks.innerHTML = "";
  for (const [name] of parts) {
    const label = document.createElement("label");
    const checked = document.createElement("input");
    checked.type = "checkbox";
    checked.value = name;
    checked.checked = true;
    label.appendChild(checked);
    label.append(` ${name}`);
    UI.partChecks.appendChild(label);
  }
}

function renderFitPartSelector(parts) {
  const prev = UI.fitPart.value;
  UI.fitPart.innerHTML = "";

  for (const [name] of parts) {
    const op = document.createElement("option");
    op.value = name;
    op.textContent = name;
    UI.fitPart.appendChild(op);
  }

  if (!parts.length) {
    UI.fitPreview.textContent = "fit対象パーツなし";
    return;
  }

  UI.fitPart.value = parts.some(([name]) => name === prev) ? prev : parts[0][0];
  loadFitEditor(UI.fitPart.value);
}

function renderVrmPartSelector(parts) {
  const prev = UI.vrmPart.value;
  UI.vrmPart.innerHTML = "";
  for (const [name] of parts) {
    const op = document.createElement("option");
    op.value = name;
    op.textContent = name;
    UI.vrmPart.appendChild(op);
  }

  if (!parts.length) {
    UI.vrmPreview.textContent = "vrm_anchor対象パーツなし";
    return;
  }

  UI.vrmPart.value = parts.some(([name]) => name === prev) ? prev : parts[0][0];
  loadVrmEditor(UI.vrmPart.value);
}

function setFitEditorValues(fit) {
  ensureSelectValue(UI.fitSource, fit.source);
  ensureSelectValue(UI.fitAttach, fit.attach);
  UI.fitOffsetY.value = String(fit.offsetY);
  UI.fitZOffset.value = String(fit.zOffset);
  UI.fitScaleX.value = String(fit.scale[0]);
  UI.fitScaleY.value = String(fit.scale[1]);
  UI.fitScaleZ.value = String(fit.scale[2]);
  UI.fitFollowX.value = String(fit.follow[0]);
  UI.fitFollowY.value = String(fit.follow[1]);
  UI.fitFollowZ.value = String(fit.follow[2]);
  UI.fitMinScaleX.value = String(fit.minScale[0]);
  UI.fitMinScaleY.value = String(fit.minScale[1]);
  UI.fitMinScaleZ.value = String(fit.minScale[2]);
}

function setVrmEditorValues(slot, anchor) {
  if (UI.vrmSlot) {
    UI.vrmSlot.value = String(slot || "");
  }
  ensureSelectValue(UI.vrmBone, anchor.bone);
  UI.vrmOffsetX.value = String(anchor.offset[0]);
  UI.vrmOffsetY.value = String(anchor.offset[1]);
  UI.vrmOffsetZ.value = String(anchor.offset[2]);
  UI.vrmRotX.value = String(anchor.rotation[0]);
  UI.vrmRotY.value = String(anchor.rotation[1]);
  UI.vrmRotZ.value = String(anchor.rotation[2]);
  UI.vrmScaleX.value = String(anchor.scale[0]);
  UI.vrmScaleY.value = String(anchor.scale[1]);
  UI.vrmScaleZ.value = String(anchor.scale[2]);
}

function renderBodyTuneSelector(parts) {
  const prev = UI.bodyTunePart.value;
  UI.bodyTunePart.innerHTML = "";
  for (const [name] of parts) {
    const op = document.createElement("option");
    op.value = name;
    op.textContent = name;
    UI.bodyTunePart.appendChild(op);
  }
  if (!parts.length) return;
  UI.bodyTunePart.value = parts.some(([name]) => name === prev) ? prev : parts[0][0];
  loadBodyTuneEditor(UI.bodyTunePart.value);
}

function setBodyTuneValues(fit) {
  isSyncingTuneControls = true;
  UI.bodyTuneScaleX.value = String(fit.scale[0]);
  UI.bodyTuneScaleY.value = String(fit.scale[1]);
  UI.bodyTuneScaleZ.value = String(fit.scale[2]);
  UI.bodyTuneOffsetY.value = String(fit.offsetY);
  UI.bodyTuneZOffset.value = String(fit.zOffset);
  isSyncingTuneControls = false;
}

function loadBodyTuneEditor(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) return;
  const fit = effectiveFitFor(partName, currentSuit.modules[partName]);
  setBodyTuneValues(fit);
}

function readBodyTuneFit(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) return null;
  const module = currentSuit.modules[partName];
  const base = effectiveFitFor(partName, module);
  return normalizeFit(
    {
      ...base,
      scale: [UI.bodyTuneScaleX.value, UI.bodyTuneScaleY.value, UI.bodyTuneScaleZ.value],
      offsetY: UI.bodyTuneOffsetY.value,
      zOffset: UI.bodyTuneZOffset.value,
    },
    baseFitFor(partName)
  );
}

function applyBodyTuneToSuit({ syncFitEditor = true, silent = false } = {}) {
  const partName = UI.bodyTunePart.value;
  if (!partName || !currentSuit?.modules?.[partName]) return false;
  const fit = readBodyTuneFit(partName);
  if (!fit) return false;
  currentSuit.modules[partName].fit = fit;
  bodyFrontPreview.refreshPart(partName, currentSuit.modules[partName]);
  if (syncFitEditor) {
    UI.fitPart.value = partName;
    setFitEditorValues(fit);
    renderFitPreview(partName);
  }
  if (!silent) {
    setStatus(`全身プレビュー調整を適用: ${partName}`);
  }
  return true;
}

function renderFitPreview(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) {
    UI.fitPreview.textContent = "fit未設定";
    return;
  }
  const module = currentSuit.modules[partName];
  const base = baseFitFor(partName);
  const effective = effectiveFitFor(partName, module);
  UI.fitPreview.textContent = JSON.stringify(
    {
      part: partName,
      base_fit: base,
      override_fit: module.fit || null,
      effective_fit: effective,
    },
    null,
    2
  );
}

function renderVrmPreview(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) {
    UI.vrmPreview.textContent = "vrm_anchor未設定";
    return;
  }
  const module = currentSuit.modules[partName];
  const slot = normalizeAttachmentSlot(partName, module);
  const base = baseVrmAnchorFor(slot);
  const effective = effectiveVrmAnchorFor(partName, module);
  UI.vrmPreview.textContent = JSON.stringify(
    {
      part: partName,
      attachment_slot: slot,
      base_anchor: base,
      override_anchor: module.vrm_anchor || null,
      effective_anchor: effective,
    },
    null,
    2
  );
}

function loadFitEditor(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) {
    UI.fitPreview.textContent = "fit未設定";
    return;
  }
  const module = currentSuit.modules[partName];
  const effective = effectiveFitFor(partName, module);
  setFitEditorValues(effective);
  if (UI.bodyTunePart.value !== partName) {
    UI.bodyTunePart.value = partName;
  }
  if (UI.vrmPart.value !== partName) {
    UI.vrmPart.value = partName;
  }
  setBodyTuneValues(effective);
  renderFitPreview(partName);
  renderVrmPreview(partName);
}

function loadVrmEditor(partName) {
  if (!partName || !currentSuit?.modules?.[partName]) {
    UI.vrmPreview.textContent = "vrm_anchor未設定";
    return;
  }
  const module = currentSuit.modules[partName];
  const slot = normalizeAttachmentSlot(partName, module);
  const effective = effectiveVrmAnchorFor(partName, module);
  setVrmEditorValues(slot, effective);
  renderVrmPreview(partName);
}

function readFitEditor(partName) {
  const base = baseFitFor(partName);
  return normalizeFit(
    {
      source: UI.fitSource.value,
      attach: UI.fitAttach.value,
      offsetY: UI.fitOffsetY.value,
      zOffset: UI.fitZOffset.value,
      scale: [UI.fitScaleX.value, UI.fitScaleY.value, UI.fitScaleZ.value],
      follow: [UI.fitFollowX.value, UI.fitFollowY.value, UI.fitFollowZ.value],
      minScale: [UI.fitMinScaleX.value, UI.fitMinScaleY.value, UI.fitMinScaleZ.value],
    },
    base
  );
}

function readVrmEditor(partName) {
  const module = currentSuit?.modules?.[partName] || {};
  const slot = normalizeAttachmentSlot(partName, {
    attachment_slot: UI.vrmSlot?.value || module.attachment_slot || partName,
  });
  const base = baseVrmAnchorFor(slot);
  const anchor = normalizeVrmAnchor(
    {
      bone: UI.vrmBone.value,
      offset: [UI.vrmOffsetX.value, UI.vrmOffsetY.value, UI.vrmOffsetZ.value],
      rotation: [UI.vrmRotX.value, UI.vrmRotY.value, UI.vrmRotZ.value],
      scale: [UI.vrmScaleX.value, UI.vrmScaleY.value, UI.vrmScaleZ.value],
    },
    base
  );
  return { slot, anchor };
}

function applyFitEditorToSuit() {
  const partName = UI.fitPart.value;
  if (!partName || !currentSuit?.modules?.[partName]) {
    setStatus("fit適用対象の部位がありません。", true);
    return false;
  }
  const fit = readFitEditor(partName);
  currentSuit.modules[partName].fit = fit;
  bodyFrontPreview.refreshPart(partName, currentSuit.modules[partName]);
  if (UI.bodyTunePart.value !== partName) {
    UI.bodyTunePart.value = partName;
  }
  setBodyTuneValues(fit);
  renderFitPreview(partName);
  setStatus(`fitを適用しました: ${partName}`);
  return true;
}

function resetFitForPart() {
  const partName = UI.fitPart.value;
  if (!partName || !currentSuit?.modules?.[partName]) {
    setStatus("fit解除対象の部位がありません。", true);
    return;
  }
  delete currentSuit.modules[partName].fit;
  loadFitEditor(partName);
  bodyFrontPreview.refreshPart(partName, currentSuit.modules[partName]);
  setStatus(`fitを解除しました: ${partName}`);
}

function applyVrmEditorToSuit({ silent = false } = {}) {
  const partName = UI.vrmPart.value;
  if (!partName || !currentSuit?.modules?.[partName]) {
    setStatus("vrm_anchor適用対象の部位がありません。", true);
    return false;
  }
  const { slot, anchor } = readVrmEditor(partName);
  currentSuit.modules[partName].attachment_slot = slot;
  currentSuit.modules[partName].vrm_anchor = anchor;
  bodyFrontPreview.refreshPart(partName, currentSuit.modules[partName]);
  renderVrmPreview(partName);
  if (!silent) {
    setStatus(`vrm_anchorを適用しました: ${partName} (slot=${slot})`);
  }
  return true;
}

function resetVrmAnchorForPart() {
  const partName = UI.vrmPart.value;
  if (!partName || !currentSuit?.modules?.[partName]) {
    setStatus("vrm_anchor解除対象の部位がありません。", true);
    return;
  }
  delete currentSuit.modules[partName].vrm_anchor;
  delete currentSuit.modules[partName].attachment_slot;
  loadVrmEditor(partName);
  bodyFrontPreview.refreshPart(partName, currentSuit.modules[partName]);
  setStatus(`vrm_anchorを解除しました: ${partName}`);
}

async function saveCurrentSuit() {
  if (!currentSuitPath || !currentSuit) {
    throw new Error("保存対象の SuitSpec がありません。");
  }
  const res = await fetch("/api/suitspec-save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: currentSuitPath,
      suitspec: currentSuit,
    }),
  });
  const data = await res.json();
  if (!data.ok) {
    throw new Error(data.error || "SuitSpec保存に失敗しました。");
  }
  return data;
}

function selectedParts() {
  return Array.from(UI.partChecks.querySelectorAll("input[type='checkbox']:checked")).map((el) => el.value);
}

function renderPromptSelector(parts, suitspec) {
  UI.promptPart.innerHTML = "";
  for (const [name] of parts) {
    const op = document.createElement("option");
    op.value = name;
    op.textContent = name;
    UI.promptPart.appendChild(op);
  }
  if (parts.length === 0) {
    UI.promptPreview.textContent = "対象パーツなし";
    return;
  }
  const selected = UI.promptPart.value || parts[0][0];
  UI.promptPart.value = selected;
  updatePromptPreview(selected, suitspec);
}

function updatePromptPreview(part, suitspec) {
  if (!part) {
    UI.promptPreview.textContent = "プロンプト未選択";
    return;
  }

  const gen = suitspec?.generation || {};
  const specPrompt = gen?.part_prompts?.[part] || "(SuitSpec内に未保存)";
  const runtimePrompt = lastSummary?.prompts?.[part] || null;
  const refinePrompt = lastSummary?.refine_prompts?.[part] || null;

  const lines = [
    `[part] ${part}`,
    "",
    "[suitspec.prompt]",
    specPrompt,
  ];
  if (runtimePrompt) {
    lines.push("", "[last generation prompt]", runtimePrompt);
  }
  if (refinePrompt) {
    lines.push("", "[last refine prompt]", refinePrompt);
  }
  UI.promptPreview.textContent = lines.join("\n");
}

function clearPreviews() {
  previewCards.splice(0, previewCards.length);
  UI.cards.innerHTML = "";
}

function switchCardView(card, view) {
  const panes = card.querySelectorAll(".view-pane");
  const buttons = card.querySelectorAll(".view-btn");
  panes.forEach((pane) => pane.classList.toggle("active", pane.dataset.view === view));
  buttons.forEach((btn) => btn.classList.toggle("active", btn.dataset.view === view));
}

function renderPartCards(suitspec) {
  clearPreviews();
  const parts = readEnabledModules(suitspec);

  for (const [name, mod] of parts) {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <div class="card-head">
        <h3>${name}</h3>
        <small>${mod.texture_path ? "texture ok" : "texture missing"}</small>
      </div>
      <div class="view-tabs">
        <button class="view-btn active" data-view="mesh">3D</button>
        <button class="view-btn" data-view="uv">UV</button>
      </div>
      <canvas class="part-canvas view-pane active" data-view="mesh"></canvas>
      <canvas class="uv-canvas view-pane" data-view="uv"></canvas>
      <div class="uv-stats">UV解析待機中...</div>
      <div class="card-meta">${mod.texture_path || "(texture_path 未設定)"}</div>
    `;
    UI.cards.appendChild(card);

    const preview = new PartCardPreview({
      meshCanvas: card.querySelector(".part-canvas"),
      uvCanvas: card.querySelector(".uv-canvas"),
      statsNode: card.querySelector(".uv-stats"),
      partName: name,
      module: mod,
    });
    previewCards.push(preview);

    for (const btn of card.querySelectorAll(".view-btn")) {
      btn.onclick = () => {
        switchCardView(card, btn.dataset.view);
        if (btn.dataset.view === "uv") {
          preview.updateUvDebug();
        }
      };
    }
  }
}

function activateTab(tab) {
  const isParts = tab === "parts";
  UI.panelParts.classList.toggle("active", isParts);
  UI.panelBody.classList.toggle("active", !isParts);
  for (const btn of UI.tabButtons) {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  }
}

async function loadSuitList() {
  const res = await fetch("/api/suitspecs");
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "SuitSpec一覧の取得に失敗しました。");

  const options = data.items || [];
  UI.suitPath.innerHTML = "";
  for (const item of options) {
    const op = document.createElement("option");
    op.value = item;
    op.textContent = item;
    UI.suitPath.appendChild(op);
  }

  if (options.length === 0) {
    setStatus("SuitSpec が見つかりません。", true);
    return;
  }

  if (!currentSuitPath || !options.includes(currentSuitPath)) {
    currentSuitPath = options[0];
    UI.suitPath.value = currentSuitPath;
  }
}

async function loadSuit(path) {
  const res = await fetch(`/api/suitspec?path=${encodeURIComponent(path)}`);
  const data = await res.json();
  if (!data.ok) throw new Error(data.error || "SuitSpec読込に失敗しました。");

  currentSuitPath = path;
  currentSuit = data.suitspec;

  const enabled = readEnabledModules(currentSuit);
  renderPartChecks(enabled);
  renderFitPartSelector(enabled);
  renderVrmPartSelector(enabled);
  renderBodyTuneSelector(enabled);
  renderPromptSelector(enabled, currentSuit);
  renderPartCards(currentSuit);
  await bodyFrontPreview.loadSuit(currentSuit);
  const vrmPath = String(UI.vrmModelPath?.value || "").trim();
  if (vrmPath) {
    const shouldReload =
      !bodyFrontPreview.vrmModel ||
      bodyFrontPreview.vrmModelPath !== vrmPath ||
      bodyFrontPreview.vrmLoadError;
    if (shouldReload) {
      await loadVrmModelFromInput({ silent: true });
    } else {
      bodyFrontPreview.updateAnchors(currentSuit);
      bodyFrontPreview.updateMeta();
    }
  } else {
    setVrmModelStatus("VRM: 未読込");
  }

  setStatus(`読込完了: ${path}\n有効パーツ: ${enabled.length}`);
}

async function runGenerate() {
  if (!currentSuitPath) {
    setStatus("先に SuitSpec を読み込んでください。", true);
    return;
  }

  const body = {
    suitspec: currentSuitPath,
    parts: selectedParts(),
    texture_mode: UI.textureMode.value,
    uv_refine: UI.uvRefine.checked,
    fallback_dir: UI.fallbackDir.value.trim() || null,
    prefer_fallback: UI.preferFallback.checked,
    update_suitspec: UI.updateSuitspec.checked,
  };

  setStatus("生成中...");

  const res = await fetch("/api/generate-parts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (!data.ok) {
    setStatus(`生成失敗\n${data.stderr || data.error || "unknown"}`, true);
    return;
  }

  const parsed = data.parsed || {};
  lastSummary = null;
  if (parsed.summary_path) {
    try {
      const summaryRes = await fetch(normPath(parsed.summary_path));
      if (summaryRes.ok) {
        lastSummary = await summaryRes.json();
      }
    } catch {
      // best effort
    }
  }
  setStatus(
    [
      `生成完了`,
      `session_id=${parsed.session_id || "-"}`,
      `generated=${parsed.generated_count || 0}`,
      `errors=${parsed.error_count || 0}`,
      `fallback=${parsed.fallback_used_count || 0}`,
      `mode=${UI.textureMode.value}`,
      `uv_refine=${UI.uvRefine.checked}`,
    ].join("\n")
  );

  await loadSuit(currentSuitPath);
}

function openBodyFit() {
  const suit = encodeURIComponent(currentSuitPath || UI.suitPath.value);
  const sim = encodeURIComponent(UI.simPath.value.trim() || "sessions/body-sim.json");
  const attach = encodeURIComponent("hybrid");
  const t = Date.now();
  window.open(`/viewer/body-fit/?suitspec=${suit}&sim=${sim}&attach=${attach}&t=${t}`, "_blank");
}

function bindEvents() {
  UI.btnRefreshSuits.onclick = async () => {
    try {
      await loadSuitList();
      setStatus("SuitSpec一覧を更新しました。");
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnLoadSuit.onclick = async () => {
    try {
      await loadSuit(UI.suitPath.value);
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnGenerate.onclick = async () => {
    try {
      await runGenerate();
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnOpenBodyFit.onclick = openBodyFit;

  UI.fitPart.onchange = () => {
    loadFitEditor(UI.fitPart.value);
  };

  UI.vrmPart.onchange = () => {
    loadVrmEditor(UI.vrmPart.value);
  };

  UI.btnFitLoad.onclick = () => {
    loadFitEditor(UI.fitPart.value);
    setStatus(`fitを読込しました: ${UI.fitPart.value}`);
  };

  UI.btnFitApply.onclick = () => {
    applyFitEditorToSuit();
  };

  UI.btnFitReset.onclick = () => {
    resetFitForPart();
  };

  UI.btnFitSave.onclick = async () => {
    try {
      if (!applyFitEditorToSuit()) return;
      await saveCurrentSuit();
      setStatus(`fitを保存しました: ${currentSuitPath}`);
      await loadSuit(currentSuitPath);
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  UI.btnVrmLoad.onclick = () => {
    loadVrmEditor(UI.vrmPart.value);
    setStatus(`vrm_anchorを読込しました: ${UI.vrmPart.value}`);
  };

  UI.btnVrmApply.onclick = () => {
    applyVrmEditorToSuit();
  };

  UI.btnVrmReset.onclick = () => {
    resetVrmAnchorForPart();
  };

  UI.btnVrmSave.onclick = async () => {
    try {
      if (!applyVrmEditorToSuit()) return;
      await saveCurrentSuit();
      setStatus(`vrm_anchorを保存しました: ${currentSuitPath}`);
      await loadSuit(currentSuitPath);
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  if (UI.btnVrmModelLoad) {
    UI.btnVrmModelLoad.onclick = async () => {
      await loadVrmModelFromInput();
    };
  }

  if (UI.btnVrmModelClear) {
    UI.btnVrmModelClear.onclick = () => {
      clearVrmModelFromInput();
    };
  }

  UI.bodyTunePart.onchange = () => {
    const part = UI.bodyTunePart.value;
    UI.fitPart.value = part;
    UI.vrmPart.value = part;
    loadFitEditor(part);
  };

  const onBodyTuneInput = () => {
    if (isSyncingTuneControls) return;
    applyBodyTuneToSuit({ syncFitEditor: true, silent: true });
  };

  UI.bodyTuneScaleX.oninput = onBodyTuneInput;
  UI.bodyTuneScaleY.oninput = onBodyTuneInput;
  UI.bodyTuneScaleZ.oninput = onBodyTuneInput;
  UI.bodyTuneOffsetY.oninput = onBodyTuneInput;
  UI.bodyTuneZOffset.oninput = onBodyTuneInput;

  UI.btnBodyTuneApply.onclick = () => {
    applyBodyTuneToSuit({ syncFitEditor: true, silent: false });
  };

  UI.btnBodyTuneToFit.onclick = () => {
    const part = UI.bodyTunePart.value;
    if (!part) return;
    UI.fitPart.value = part;
    loadFitEditor(part);
    setStatus(`Fit編集欄へ同期しました: ${part}`);
  };

  if (UI.vrmAnchorVisible) {
    UI.vrmAnchorVisible.onchange = () => {
      bodyFrontPreview.setAnchorVisible(UI.vrmAnchorVisible.checked);
    };
  }

  const onVrmEditorInput = () => {
    if (!UI.vrmPart.value || !currentSuit?.modules?.[UI.vrmPart.value]) return;
    applyVrmEditorToSuit({ silent: true });
  };
  const vrmInputs = [
    UI.vrmSlot,
    UI.vrmBone,
    UI.vrmOffsetX,
    UI.vrmOffsetY,
    UI.vrmOffsetZ,
    UI.vrmRotX,
    UI.vrmRotY,
    UI.vrmRotZ,
    UI.vrmScaleX,
    UI.vrmScaleY,
    UI.vrmScaleZ,
  ];
  for (const input of vrmInputs) {
    if (!input) continue;
    input.oninput = onVrmEditorInput;
    input.onchange = onVrmEditorInput;
  }

  UI.reliefSlider.oninput = () => {
    const amp = Number(UI.reliefSlider.value || "0.05");
    for (const preview of previewCards) {
      preview.updateRelief(amp);
    }
    bodyFrontPreview.updateRelief(amp);
  };

  UI.promptPart.onchange = () => {
    updatePromptPreview(UI.promptPart.value, currentSuit);
  };

  for (const btn of UI.tabButtons) {
    btn.onclick = () => activateTab(btn.dataset.tab || "parts");
  }
}

async function init() {
  populateVrmBoneOptions();
  bindEvents();
  activateTab("parts");

  try {
    const detected = await discoverDefaultVrmPath();
    if (detected && UI.vrmModelPath) {
      UI.vrmModelPath.value = detected;
      setVrmModelStatus(`VRM: 既定ファイル検出\npath: ${detected}`);
    } else {
      const fallback = String(UI.vrmModelPath?.value || DEFAULT_VRM_CANDIDATES[0]);
      setVrmModelStatus(`VRM: 未検出\n候補: ${fallback}\n配置後に「VRM読込」を押してください。`);
    }
  } catch {
    setVrmModelStatus("VRM: 自動検出でエラー（手動読込を利用してください）");
  }

  try {
    await loadSuitList();
    await loadSuit(UI.suitPath.value);
  } catch (err) {
    setStatus(String(err), true);
  }
}

init();
