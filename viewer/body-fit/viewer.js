import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { TransformControls } from "three/addons/controls/TransformControls.js";
import { loadVrmScene, VRM_RUNTIME_TARGETS } from "./vrm-loader.js?v=20260304a";
import {
  LIVE_POSE_OPTIONS,
  LiveCameraPipeline,
  createDefaultLiveState,
  createPoseLandmarkerPipelineModule,
  createPoseSegmentsPipelineModule,
  estimateLiveBodyScale,
  extractPoseJointsWorld,
} from "./body-fit-live.js?v=20260412a";
import {
  createBoneInferenceSnapshot,
  inferCanonicalJointsFromBoneResolver,
} from "../shared/bone-inference.js?v=20260412a";
import {
  createBodyTrackingFrameFromInference,
} from "../shared/body-tracking-frame.js?v=20260418a";
import {
  FIT_CONTACT_PAIRS,
  VRM_BONE_ALIASES,
  effectiveVrmAnchorFor,
  getModuleVisualConfig,
  normalizeAttachmentSlot,
  normalizeBoneName,
  normalizeVec3,
  partColor,
} from "../shared/armor-canon.js";
import {
  applyAutoFitResultToSuitSpec,
  evaluateArmorFitToVrm,
  fitArmorToVrm,
  formatAutoFitSummary,
} from "../shared/auto-fit-engine.js?v=20260412g";
import { createWearableTemplateGeometry } from "../shared/wearable-template.js?v=20260412d";
import { renderBindingFor } from "../shared/vrm-fit-policy.js?v=20260412c";
import {
  buildSurfaceFirstSnapshot,
  createSurfacePointLayer,
  createSurfaceFirstDemoRig,
  disposeSurfaceFirstDemoRig,
  reprojectSurfaceFirstSnapshot,
  summarizeSurfaceFirstSnapshot,
} from "../shared/surface-first-system.js?v=20260412d";

const DEFAULT_SUITSPEC = "examples/suitspec.sample.json";
const DEFAULT_SIM = "sessions/body-sim.json";
const DEFAULT_DEPOSITION_DURATION = 2.8;

const DEPOSITION_PROFILES = {
  uplift: { label: "高揚", shellColor: 0xffca57, highlightColor: 0xfff4b7, glowColor: 0xfff0d8, auraOpacity: 0.28, ringSpeed: 1.35, shellCount: 620, glowCount: 260, shellSize: 0.072, glowSize: 0.13 },
  drive: { label: "闘志", shellColor: 0xff5a4a, highlightColor: 0xffb08d, glowColor: 0xffd7d0, auraOpacity: 0.26, ringSpeed: 1.55, shellCount: 640, glowCount: 280, shellSize: 0.075, glowSize: 0.14 },
  grief: { label: "哀傷", shellColor: 0x4da6ff, highlightColor: 0xa9ddff, glowColor: 0xd9f1ff, auraOpacity: 0.2, ringSpeed: 0.9, shellCount: 560, glowCount: 240, shellSize: 0.068, glowSize: 0.12 },
  tension: { label: "緊張", shellColor: 0x8e63ff, highlightColor: 0xd1c2ff, glowColor: 0xf3efff, auraOpacity: 0.22, ringSpeed: 1.1, shellCount: 700, glowCount: 220, shellSize: 0.062, glowSize: 0.11 },
  guard: { label: "守護", shellColor: 0x4fd7a4, highlightColor: 0xbff5df, glowColor: 0xe5fff5, auraOpacity: 0.25, ringSpeed: 1.0, shellCount: 600, glowCount: 260, shellSize: 0.07, glowSize: 0.13 },
  embrace: { label: "受容", shellColor: 0xff6fbd, highlightColor: 0xffc7ea, glowColor: 0xffeef8, auraOpacity: 0.24, ringSpeed: 0.95, shellCount: 580, glowCount: 280, shellSize: 0.074, glowSize: 0.135 },
};

const PANEL = {
  suitspecPath: document.getElementById("suitspecPath"),
  simPath: document.getElementById("simPath"),
  btnLoad: document.getElementById("btnLoad"),
  btnPlay: document.getElementById("btnPlay"),
  btnPrev: document.getElementById("btnPrev"),
  btnNext: document.getElementById("btnNext"),
  btnUiSimple: document.getElementById("btnUiSimple"),
  btnUiDetail: document.getElementById("btnUiDetail"),
  uiModeHint: document.getElementById("uiModeHint"),
  btnTexture: document.getElementById("btnTexture"),
  btnGeometry: document.getElementById("btnGeometry"),
  btnTheme: document.getElementById("btnTheme"),
  btnCamFront: document.getElementById("btnCamFront"),
  btnCamSide: document.getElementById("btnCamSide"),
  btnCamBack: document.getElementById("btnCamBack"),
  btnCamTop: document.getElementById("btnCamTop"),
  btnCamPov: document.getElementById("btnCamPov"),
  btnFit: document.getElementById("btnFit"),
  frameSlider: document.getElementById("frameSlider"),
  speedSlider: document.getElementById("speedSlider"),
  reliefSlider: document.getElementById("reliefSlider"),
  vrmPath: document.getElementById("vrmPath"),
  btnVrmLoad: document.getElementById("btnVrmLoad"),
  btnVrmClear: document.getElementById("btnVrmClear"),
  btnVrmToggle: document.getElementById("btnVrmToggle"),
  btnVrmAttach: document.getElementById("btnVrmAttach"),
  btnArmorToggle: document.getElementById("btnArmorToggle"),
  btnVrmIdleToggle: document.getElementById("btnVrmIdleToggle"),
  btnVrmFocus: document.getElementById("btnVrmFocus"),
  btnVrmTPose: document.getElementById("btnVrmTPose"),
  btnVrmAutoFit: document.getElementById("btnVrmAutoFit"),
  btnVrmAutoFitSave: document.getElementById("btnVrmAutoFitSave"),
  vrmIdleAmount: document.getElementById("vrmIdleAmount"),
  vrmIdleSpeed: document.getElementById("vrmIdleSpeed"),
  vrmStatus: document.getElementById("vrmStatus"),
  btnDepositionPlay: document.getElementById("btnDepositionPlay"),
  btnDepositionReset: document.getElementById("btnDepositionReset"),
  depositionProfile: document.getElementById("depositionProfile"),
  depositionDuration: document.getElementById("depositionDuration"),
  depositionStatus: document.getElementById("depositionStatus"),
  btnSurfaceFirstRefresh: document.getElementById("btnSurfaceFirstRefresh"),
  btnSurfaceFirstGraph: document.getElementById("btnSurfaceFirstGraph"),
  btnSurfaceFirstShell: document.getElementById("btnSurfaceFirstShell"),
  btnSurfaceFirstMounts: document.getElementById("btnSurfaceFirstMounts"),
  surfacePointDensity: document.getElementById("surfacePointDensity"),
  surfaceShellOffset: document.getElementById("surfaceShellOffset"),
  surfaceStatus: document.getElementById("surfaceStatus"),
  btnLiveStart: document.getElementById("btnLiveStart"),
  btnLiveStop: document.getElementById("btnLiveStop"),
  liveViewMode: document.getElementById("liveViewMode"),
  liveStatus: document.getElementById("liveStatus"),
  liveCheckInput: document.getElementById("liveCheckInput"),
  liveCheckPose: document.getElementById("liveCheckPose"),
  liveCheckFrame: document.getElementById("liveCheckFrame"),
  liveCheckSurface: document.getElementById("liveCheckSurface"),
  liveVideo: document.getElementById("liveVideo"),
  fitPart: document.getElementById("fitPart"),
  fitScaleX: document.getElementById("fitScaleX"),
  fitScaleY: document.getElementById("fitScaleY"),
  fitScaleZ: document.getElementById("fitScaleZ"),
  fitOffsetY: document.getElementById("fitOffsetY"),
  fitZOffset: document.getElementById("fitZOffset"),
  fitNudgeStep: document.getElementById("fitNudgeStep"),
  fitNudgeControls: document.getElementById("fitNudgeControls"),
  fitAssistSummary: document.getElementById("fitAssistSummary"),
  fitAssistCurrent: document.getElementById("fitAssistCurrent"),
  fitAssistList: document.getElementById("fitAssistList"),
  btnFitRefreshCheck: document.getElementById("btnFitRefreshCheck"),
  btnFitPrevIssue: document.getElementById("btnFitPrevIssue"),
  btnFitNextIssue: document.getElementById("btnFitNextIssue"),
  btnFitFocusPart: document.getElementById("btnFitFocusPart"),
  btnGizmoToggle: document.getElementById("btnGizmoToggle"),
  btnGizmoMove: document.getElementById("btnGizmoMove"),
  btnGizmoScale: document.getElementById("btnGizmoScale"),
  btnGizmoSpace: document.getElementById("btnGizmoSpace"),
  fitGizmoHint: document.getElementById("fitGizmoHint"),
  vrmEditPart: document.getElementById("vrmEditPart"),
  vrmEditBone: document.getElementById("vrmEditBone"),
  vrmEditOffsetX: document.getElementById("vrmEditOffsetX"),
  vrmEditOffsetY: document.getElementById("vrmEditOffsetY"),
  vrmEditOffsetZ: document.getElementById("vrmEditOffsetZ"),
  vrmEditRotX: document.getElementById("vrmEditRotX"),
  vrmEditRotY: document.getElementById("vrmEditRotY"),
  vrmEditRotZ: document.getElementById("vrmEditRotZ"),
  vrmEditScaleX: document.getElementById("vrmEditScaleX"),
  vrmEditScaleY: document.getElementById("vrmEditScaleY"),
  vrmEditScaleZ: document.getElementById("vrmEditScaleZ"),
  btnVrmEditLoad: document.getElementById("btnVrmEditLoad"),
  btnVrmEditApply: document.getElementById("btnVrmEditApply"),
  btnVrmEditReset: document.getElementById("btnVrmEditReset"),
  vrmEditHint: document.getElementById("vrmEditHint"),
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
/* legacy label overrides retained only to avoid merge churn

DEPOSITION_PROFILES.uplift.label = "高揚";
DEPOSITION_PROFILES.drive.label = "闘志";
DEPOSITION_PROFILES.grief.label = "哀傷";
DEPOSITION_PROFILES.tension.label = "緊張";
DEPOSITION_PROFILES.guard.label = "守護";
DEPOSITION_PROFILES.embrace.label = "受容";

*/
DEPOSITION_PROFILES.uplift.label = "高揚";
DEPOSITION_PROFILES.drive.label = "闘志";
DEPOSITION_PROFILES.grief.label = "哀傷";
DEPOSITION_PROFILES.tension.label = "緊張";
DEPOSITION_PROFILES.guard.label = "守護";
DEPOSITION_PROFILES.embrace.label = "受容";

const FIT_FIELD_LABELS = {
  fitScaleX: "横幅",
  fitScaleY: "高さ",
  fitScaleZ: "奥行",
  fitOffsetY: "上下位置",
  fitZOffset: "前後位置",
};

const textureLoader = new THREE.TextureLoader();
const meshGeometryCache = new Map();
const textureAssetCache = new Map();
const textureSamplerCache = new WeakMap();
const geometryUvCache = new WeakMap();
const DEFAULT_VRM_PATH = "viewer/assets/vrm/default.vrm";
const GEOMETRY_MODES = Object.freeze({
  TEMPLATE: "template",
  ASSET: "asset",
});

const VRM_PART_BONE_FALLBACKS = {
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
};

const VRM_ATTACH_MODES = {
  BODY: "body",
  HYBRID: "hybrid",
  VRM: "vrm",
};

const UI_LEVELS = {
  SIMPLE: "simple",
  DETAIL: "detail",
};

const VRM_ATTACH_MODE_LABELS = {
  [VRM_ATTACH_MODES.BODY]: "BodySim",
  [VRM_ATTACH_MODES.HYBRID]: "ハイブリッド",
  [VRM_ATTACH_MODES.VRM]: "VRM",
};

VRM_ATTACH_MODE_LABELS[VRM_ATTACH_MODES.BODY] = "BodySim基準";
VRM_ATTACH_MODE_LABELS[VRM_ATTACH_MODES.HYBRID] = "ハイブリッド";

const UI_MODE_HINTS = {
  [UI_LEVELS.SIMPLE]: "まずは VRM を読み込み、「自動フィット」で装着結果を確認します。通常はこのモードだけで足ります。",
  [UI_LEVELS.DETAIL]: "部位ごとのフィット調整、VRMアンカー調整、Surface-first デモ、ライブ入力まで扱うモードです。",
};

function jaOnOff(enabled) {
  return enabled ? "ON" : "OFF";
}

function jaYesNo(enabled) {
  return enabled ? "あり" : "なし";
}

function formatUiModeHint(level) {
  return UI_MODE_HINTS[level] || UI_MODE_HINTS[UI_LEVELS.SIMPLE];
}

function formatAutoFitSummaryJa(summary) {
  if (!summary) return "未評価";
  const fitScore = Number(summary.fitScore || 0).toFixed(1);
  const missing = Array.isArray(summary.missingAnchors) ? summary.missingAnchors.length : 0;
  const surface = Array.isArray(summary.surfaceViolations) ? summary.surfaceViolations.length : 0;
  const hero = Array.isArray(summary.heroOverflow) ? summary.heroOverflow.length : 0;
  const symmetry = Array.isArray(summary.symmetryDelta)
    ? summary.symmetryDelta.filter((entry) => entry && entry.ok === false).length
    : 0;
  const seam = Array.isArray(summary.seamContinuity)
    ? summary.seamContinuity.filter((entry) => entry && entry.ok === false).length
    : 0;
  const render = Array.isArray(summary.renderDeviation)
    ? summary.renderDeviation.filter((entry) => entry && entry.ok === false).length
    : 0;
  const textureNg = summary.texturesVisible === false ? 1 : 0;
  const state = summary.canSave ? "保存可" : "要調整";
  return `${state} | Fit ${fitScore} | アンカー ${missing} | 表面 ${surface} | ヒーロー ${hero} | 左右差 ${symmetry} | 継ぎ目 ${seam} | 表示 ${render} | テクスチャ ${textureNg}`;
}

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
  left_hand: {
    position_x: 0.08,
    position_y: -0.66,
    position_z: 0.22,
    rotation_z: 0.18,
    scale_x: 0.2,
    scale_y: 0.24,
    scale_z: 0.2,
  },
  right_hand: {
    position_x: 1.02,
    position_y: -0.66,
    position_z: 0.22,
    rotation_z: -0.18,
    scale_x: 0.2,
    scale_y: 0.24,
    scale_z: 0.2,
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
  left_foot: {
    position_x: 0.42,
    position_y: -1.56,
    position_z: 0.3,
    rotation_z: 0,
    scale_x: 0.22,
    scale_y: 0.26,
    scale_z: 0.42,
  },
  right_foot: {
    position_x: 0.68,
    position_y: -1.56,
    position_z: 0.3,
    rotation_z: 0,
    scale_x: 0.22,
    scale_y: 0.26,
    scale_z: 0.42,
  },
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
    name: "right_hand",
    startJoint: "right_wrist",
    endJoint: "right_middle_proximal",
    radiusFactor: 0.18,
    radiusMin: 0.04,
    radiusMax: 0.16,
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
    name: "left_hand",
    startJoint: "left_wrist",
    endJoint: "left_middle_proximal",
    radiusFactor: 0.18,
    radiusMin: 0.04,
    radiusMax: 0.16,
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
    name: "right_foot",
    startJoint: "right_ankle",
    endJoint: "right_toes",
    radiusFactor: 0.16,
    radiusMin: 0.04,
    radiusMax: 0.12,
    z: 0.28,
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
    name: "left_foot",
    startJoint: "left_ankle",
    endJoint: "left_toes",
    radiusFactor: 0.16,
    radiusMin: 0.04,
    radiusMax: 0.12,
    z: 0.28,
    smoothGain: 18.0,
  },
  {
    name: "chest_core",
    startJoint: "hips_center",
    endJoint: "shoulders_center",
    radiusFactor: 0.38,
    radiusMin: 0.05,
    radiusMax: 0.35,
    z: 0.22,
    smoothGain: 18.0,
  },
];

const VRM_LIVE_BONE_SPECS = [
  {
    bone: "spine",
    childBone: "chest",
    startJoint: "hips_center",
    endJoint: "shoulders_center",
    smoothGain: 8,
  },
  {
    bone: "chest",
    childBone: "neck",
    startJoint: "hips_center",
    endJoint: "shoulders_center",
    smoothGain: 10,
  },
  {
    bone: "leftUpperArm",
    childBone: "leftLowerArm",
    startJoint: "left_shoulder",
    endJoint: "left_elbow",
    smoothGain: 16,
  },
  {
    bone: "leftLowerArm",
    childBone: "leftHand",
    startJoint: "left_elbow",
    endJoint: "left_wrist",
    smoothGain: 16,
  },
  {
    bone: "rightUpperArm",
    childBone: "rightLowerArm",
    startJoint: "right_shoulder",
    endJoint: "right_elbow",
    smoothGain: 16,
  },
  {
    bone: "rightLowerArm",
    childBone: "rightHand",
    startJoint: "right_elbow",
    endJoint: "right_wrist",
    smoothGain: 16,
  },
  {
    bone: "leftUpperLeg",
    childBone: "leftLowerLeg",
    startJoint: "left_hip",
    endJoint: "left_knee",
    smoothGain: 14,
  },
  {
    bone: "leftLowerLeg",
    childBone: "leftFoot",
    startJoint: "left_knee",
    endJoint: "left_ankle",
    smoothGain: 14,
  },
  {
    bone: "rightUpperLeg",
    childBone: "rightLowerLeg",
    startJoint: "right_hip",
    endJoint: "right_knee",
    smoothGain: 14,
  },
  {
    bone: "rightLowerLeg",
    childBone: "rightFoot",
    startJoint: "right_knee",
    endJoint: "right_ankle",
    smoothGain: 14,
  },
  {
    bone: "neck",
    childBone: "head",
    startJoint: "shoulders_center",
    endJoint: "nose",
    smoothGain: 8,
  },
];

const VRM_TPOSE_BONE_CHAINS = [
  { bone: "leftUpperArm", childBone: "leftLowerArm", target: [-1, 0, 0], strength: 1.0 },
  { bone: "leftLowerArm", childBone: "leftHand", target: [-1, 0, 0], strength: 1.0 },
  { bone: "rightUpperArm", childBone: "rightLowerArm", target: [1, 0, 0], strength: 1.0 },
  { bone: "rightLowerArm", childBone: "rightHand", target: [1, 0, 0], strength: 1.0 },
  { bone: "leftUpperLeg", childBone: "leftLowerLeg", target: [0, -1, 0], strength: 0.8 },
  { bone: "leftLowerLeg", childBone: "leftFoot", target: [0, -1, 0], strength: 0.8 },
  { bone: "rightUpperLeg", childBone: "rightLowerLeg", target: [0, -1, 0], strength: 0.8 },
  { bone: "rightLowerLeg", childBone: "rightFoot", target: [0, -1, 0], strength: 0.8 },
  { bone: "spine", childBone: "chest", target: [0, 1, 0], strength: 0.6 },
  { bone: "chest", childBone: "neck", target: [0, 1, 0], strength: 0.6 },
  { bone: "neck", childBone: "head", target: [0, 1, 0], strength: 0.5 },
];

const VRM_AUTO_CALIBRATE_PARTS = Object.freeze([
  "chest",
  "back",
  "waist",
  "left_shoulder",
  "right_shoulder",
  "left_upperarm",
  "right_upperarm",
  "left_forearm",
  "right_forearm",
  "left_hand",
  "right_hand",
  "left_thigh",
  "right_thigh",
  "left_shin",
  "right_shin",
  "left_boot",
  "right_boot",
]);

function toNumberOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeVrmAttachMode(mode) {
  const v = String(mode || "")
    .trim()
    .toLowerCase();
  if (v === VRM_ATTACH_MODES.BODY || v === VRM_ATTACH_MODES.HYBRID || v === VRM_ATTACH_MODES.VRM) {
    return v;
  }
  return VRM_ATTACH_MODES.HYBRID;
}

function nextVrmAttachMode(currentMode) {
  const mode = normalizeVrmAttachMode(currentMode);
  if (mode === VRM_ATTACH_MODES.BODY) return VRM_ATTACH_MODES.HYBRID;
  if (mode === VRM_ATTACH_MODES.HYBRID) return VRM_ATTACH_MODES.VRM;
  return VRM_ATTACH_MODES.BODY;
}

function normalizeGeometryMode(mode) {
  return String(mode || "").trim().toLowerCase() === GEOMETRY_MODES.ASSET
    ? GEOMETRY_MODES.ASSET
    : GEOMETRY_MODES.TEMPLATE;
}

function countFitOverrides(suitspec) {
  const modules = suitspec?.modules || {};
  return Object.values(modules).filter((module) => module && typeof module.fit === "object").length;
}

function round3(value) {
  return Math.round(Number(value || 0) * 1000) / 1000;
}

function roundMetricMap(metrics) {
  if (!metrics || typeof metrics !== "object") return null;
  return Object.fromEntries(
    Object.entries(metrics).map(([key, value]) => [key, round3(value)])
  );
}

function splitFitPairName(pairName) {
  return String(pairName || "")
    .split("-")
    .map((part) => part.trim())
    .filter(Boolean);
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

function meanFinite(values, fallback = 0) {
  const valid = (values || []).filter((v) => Number.isFinite(v) && v > 0);
  if (!valid.length) return fallback;
  return valid.reduce((sum, v) => sum + v, 0) / valid.length;
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
    this.transformControls = new TransformControls(this.camera, this.canvas);
    this.transformControls.visible = false;
    this.transformControls.setMode("translate");
    this.transformControls.setSpace("local");
    this.scene.add(this.transformControls);

    this.root = new THREE.Group();
    this.scene.add(this.root);
    this.bridgeGroup = new THREE.Group();
    this.root.add(this.bridgeGroup);
    this.vrmGroup = new THREE.Group();
    this.scene.add(this.vrmGroup);
    this.surfaceFirstGroup = new THREE.Group();
    this.surfaceFirstGroup.name = "surfaceFirstOverlay";
    this.scene.add(this.surfaceFirstGroup);

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
    this.depositionFx = createDepositionFxRig();
    this.scene.add(this.depositionFx.group);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(2, 3, 4);
    this.scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0xeaf2ff, 0.7);
    fillLight.position.set(-2, 1, 2);
    this.scene.add(fillLight);
    this.scene.add(new THREE.HemisphereLight(0xd8e8ff, 0xaac7eb, 0.7));

    this.meshes = new Map();
    this.renderMeshes = new Map();
    this.frames = [];
    this.frameIndex = 0;
    this.playing = false;
    this.playbackAccumSec = 0;
    this.speed = 1.0;
    this.useTextures = true;
    this.geometryMode = "dual_shell";
    this.showFitShell = false;
    this.uiLevel = UI_LEVELS.SIMPLE;
    this.reliefStrength = Number(PANEL.reliefSlider?.value || "0.05");
    if (!Number.isFinite(this.reliefStrength)) this.reliefStrength = 0.05;
    this.bridgeEnabled = true;
    this.bridgeThickness = clamp(Number(PANEL.bridgeThickness?.value || 0.1), 0.03, 0.22);
    this.bridgeVisibleCount = 0;
    this.bridgeMeshes = new Map();
    this.darkTheme = false;
    this.cameraPreset = "front";
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
    this.autoFitSummary = null;
    this.fitAssistDirty = false;
    this.gizmo = {
      enabled: true,
      mode: "translate",
      space: "local",
      dragging: false,
    };
    this.live = createDefaultLiveState();
    this.livePipeline = new LiveCameraPipeline();
    this.livePipelineActive = false;
    this.livePipelineError = "";
    this.livePipeline.setModules([
      createPoseLandmarkerPipelineModule(this),
      createPoseSegmentsPipelineModule(this),
    ]);
    this.liveFollowers = new Map();
    this.liveJointTrackers = new Map();
    this.lastLiveSegments = null;
    this.lastLiveJoints = null;
    this.liveViewMode = this.normalizeLiveViewMode(PANEL.liveViewMode?.value || "auto");
    this.vrm = {
      model: null,
      skeleton: null,
      instance: null,
      source: null,
      boneMap: new Map(),
      path: "",
      visible: true,
      attachMode: VRM_ATTACH_MODES.HYBRID,
      idleEnabled: false,
      idleAmount: clamp(Number(PANEL.vrmIdleAmount?.value || 0.35), 0, 1),
      idleSpeed: clamp(Number(PANEL.vrmIdleSpeed?.value || 1.0), 0.25, 3),
      idleTimeSec: 0,
      restPosition: new THREE.Vector3(),
      restQuaternion: new THREE.Quaternion(),
      hasRestPose: false,
      boneCount: 0,
      missingAnchorParts: [],
      resolvedAnchors: {},
      liveRig: [],
      liveRigReady: false,
      liveDriven: false,
      bodyInference: null,
      bodyTrackingFrame: null,
      error: "",
    };
    this.armorVisible = true;
    this.deposition = {
      active: false,
      progress: 1,
      durationSec: clamp(Number(PANEL.depositionDuration?.value || DEFAULT_DEPOSITION_DURATION), 1.2, 6.0),
      profileMode: String(PANEL.depositionProfile?.value || "auto"),
      resolvedKey: "guard",
      palette: buildDepositionPalette(DEPOSITION_PROFILES.guard),
      startedAtMs: 0,
    };
    this.surfaceFirst = {
      graphVisible: false,
      shellVisible: false,
      mountsVisible: false,
      forceTrackingSource: "auto",
      density: clamp(Number(PANEL.surfacePointDensity?.value || 72), 24, 240),
      shellOffset: clamp(Number(PANEL.surfaceShellOffset?.value || 0.018), 0.002, 0.08),
      lastRefreshMs: 0,
      refreshIntervalMs: 180,
      rig: null,
      seedSnapshot: null,
      snapshot: null,
      summary: null,
      trackingSource: "vrm",
      error: "",
    };

    this.lastTime = performance.now();
    this.updatePlaybackButton();
    this.updateBridgeButton();
    this.updateArmorButton();
    this.updateGeometryButton();
    this.updateVrmButton();
    this.updateVrmAttachButton();
    this.updateVrmIdleButton();
    this.updateSurfaceFirstButtons();
    this.updateGizmoButtons();
    this.updateUiModeButtons();
    this.updateVrmStatus("VRM: 未読込");
    this.updateDepositionStatus("蒸着: 待機中");
    this.updateSurfaceFirstStatus("Surface-first: VRM 未読込");
    this.updateSurfaceFirstStatus("Surface-first: VRM 未読込");
    this.transformControls.addEventListener("dragging-changed", (event) => {
      this.gizmo.dragging = Boolean(event.value);
      this.controls.enabled = !this.gizmo.dragging;
      if (!this.gizmo.dragging) {
        this.commitGizmoEdit();
      }
    });
    this.transformControls.addEventListener("objectChange", () => {
      if (!this.gizmo.dragging) return;
      this.previewGizmoEdit();
    });
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

  updatePlaybackButton() {
    if (!PANEL.btnPlay) return;
    PANEL.btnPlay.textContent = this.playing ? "停止" : "再生";
    PANEL.btnPlay.classList.toggle("active", this.playing);
  }

  setUiLevel(level) {
    this.uiLevel = level === UI_LEVELS.DETAIL ? UI_LEVELS.DETAIL : UI_LEVELS.SIMPLE;
    document.body.dataset.uiLevel = this.uiLevel;
    this.updateUiModeButtons();
    this.updateMetaPanel();
    this.setLegend();
  }

  updateUiModeButtons() {
    if (PANEL.btnUiSimple) {
      PANEL.btnUiSimple.classList.toggle("active", this.uiLevel === UI_LEVELS.SIMPLE);
    }
    if (PANEL.btnUiDetail) {
      PANEL.btnUiDetail.classList.toggle("active", this.uiLevel === UI_LEVELS.DETAIL);
    }
    if (PANEL.uiModeHint) {
      PANEL.uiModeHint.textContent = formatUiModeHint(this.uiLevel);
    }
  }

  setMeta(meta) {
    PANEL.meta.textContent = JSON.stringify(meta, null, 2);
  }

  updateMetaPanel() {
    const effectiveLiveView = this.getEffectiveLiveMirror() ? "mirror" : "world";
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
      geometry_mode: this.geometryMode,
      fit_shell_overlay: this.showFitShell,
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
      armor_visible: this.armorVisible,
      vrm_path: this.vrm.path || null,
      vrm_source: this.vrm.source || null,
      vrm_humanoid_available: Boolean(this.vrm.instance?.humanoid),
      vrm_bones_visible: this.vrm.visible,
      vrm_attach_mode: this.vrm.attachMode,
      vrm_attach_armor: this.vrm.attachMode !== VRM_ATTACH_MODES.BODY,
      vrm_idle_enabled: this.vrm.idleEnabled,
      vrm_idle_amount: round3(this.vrm.idleAmount),
      vrm_idle_speed: round3(this.vrm.idleSpeed),
      vrm_bone_count: this.vrm.boneCount || 0,
      vrm_body_metrics: roundMetricMap(this.vrm.bodyInference?.metrics),
      vrm_reliable_joints: this.vrm.bodyInference?.reliableJointCount || 0,
      vrm_quality: this.vrm.bodyInference?.qualityLabel || null,
      vrm_quality_score: round3(this.vrm.bodyInference?.qualityScore || 0),
      vrm_fit_readiness: this.vrm.bodyInference?.fitReadiness || null,
      vrm_fit_readiness_score: round3(this.vrm.bodyInference?.fitReadinessScore || 0),
      vrm_shape_profile: this.vrm.bodyInference?.shapeProfile || null,
      vrm_tracking_frame: this.vrm.bodyTrackingFrame
        ? {
            id: this.vrm.bodyTrackingFrame.id,
            source: this.vrm.bodyTrackingFrame.source,
            schema: this.vrm.bodyTrackingFrame.schemaVersion,
          }
        : null,
      vrm_missing_anchor_parts: this.vrm.missingAnchorParts || [],
      vrm_resolved_anchors: this.vrm.resolvedAnchors || {},
      vrm_live_rig_ready: this.vrm.liveRigReady,
      vrm_live_driven: this.vrm.liveDriven,
      vrm_error: this.vrm.error || null,
      three_revision: THREE.REVISION,
      three_target: VRM_RUNTIME_TARGETS.threeVersion,
      three_vrm_target: VRM_RUNTIME_TARGETS.threeVrmVersion,
      live_active: this.live?.active || false,
      live_fps: round3(this.live?.fps || 0),
      live_body_scale_ref: round3(this.live?.bodyScaleRef || 0),
      live_body_metrics: roundMetricMap(this.live?.bodyInference?.metrics),
      live_quality_score: round3(this.live?.bodyInference?.qualityScore || 0),
      live_fit_readiness: this.live?.bodyInference?.fitReadiness || null,
      live_fit_readiness_score: round3(this.live?.bodyInference?.fitReadinessScore || 0),
      live_shape_profile: this.live?.bodyInference?.shapeProfile || null,
      live_tracking_frame: this.live?.bodyTrackingFrame
        ? {
            id: this.live.bodyTrackingFrame.id,
            source: this.live.bodyTrackingFrame.source,
            schema: this.live.bodyTrackingFrame.schemaVersion,
          }
        : null,
      live_pose_model: this.live?.poseModel || null,
      live_pose_quality: this.live?.poseQuality || "idle",
      live_pose_reliable_joints: this.live?.poseReliableJoints || 0,
      live_view_mode: this.liveViewMode,
      live_view_effective: effectiveLiveView,
      live_view_mirrored: this.getEffectiveLiveMirror(),
      camera_preset: this.cameraPreset,
      live_pipeline_active: this.livePipelineActive,
      live_pipeline_modules: this.livePipeline.listModuleNames(),
      live_pipeline_error: this.livePipelineError || null,
      deposition_active: this.deposition.active,
      deposition_progress: round3(this.deposition.progress || 0),
      deposition_duration_sec: round3(this.deposition.durationSec || DEFAULT_DEPOSITION_DURATION),
      deposition_profile_mode: this.deposition.profileMode,
      deposition_profile_resolved: this.deposition.resolvedKey,
      surface_first: this.surfaceFirst.summary
        ? {
            ...this.surfaceFirst.summary,
            error: this.surfaceFirst.error || null,
          }
        : this.surfaceFirst.error
          ? { error: this.surfaceFirst.error }
          : null,
      auto_fit_summary: this.autoFitSummary
        ? {
            fit_score: round3(this.autoFitSummary.fitScore || 0),
            can_save: Boolean(this.autoFitSummary.canSave),
            missing_anchors: this.autoFitSummary.missingAnchors || [],
            reasons: this.autoFitSummary.reasons || [],
            weak_parts: this.autoFitSummary.weakParts || [],
            weak_pairs: this.autoFitSummary.weakPairs || [],
            surface_violations: this.autoFitSummary.surfaceViolations || [],
            hero_overflow: this.autoFitSummary.heroOverflow || [],
            min_scale_locks: this.autoFitSummary.minScaleLocks || [],
            symmetry_delta: this.autoFitSummary.symmetryDelta || [],
            seam_continuity: this.autoFitSummary.seamContinuity || [],
            silhouette_budget: this.autoFitSummary.silhouetteBudget || [],
            render_deviation: this.autoFitSummary.renderDeviation || [],
            textures_visible: this.autoFitSummary.texturesVisible !== false,
          }
        : null,
    });
    this.updateLiveCheckPanel();
  }

  getFitEngineMeshes() {
    return Array.from(this.meshes.values()).map((rec) => ({
      partName: rec.partName,
      group:
        (rec.surfaceFitNodeCount > 0 && rec.surfaceFitProxyGroup?.children?.length
          ? rec.surfaceFitProxyGroup
          : rec.fitProxyGroup) ||
        rec.fitGroup ||
        rec.group,
    }));
  }

  getRenderEngineMeshes() {
    return Array.from(this.meshes.values()).map((rec) => ({
      partName: rec.partName,
      group: rec.renderProxyRoot || rec.renderGroup || rec.group,
    }));
  }

  getVisualRecords() {
    return Array.from(this.meshes.values());
  }

  computeTextureState() {
    const missing = [];
    if (!this.useTextures) {
      return { texturesVisible: false, missing };
    }
    for (const rec of this.meshes.values()) {
      if (!rec.texturePath) continue;
      if (!rec.renderMesh?.visible && !rec.renderGroup?.visible) continue;
      if (!rec.texture || rec.mesh.material.map !== rec.texture) {
        missing.push(rec.partName);
      }
    }
    return { texturesVisible: missing.length === 0, missing };
  }

  decorateWearableSummary(summary) {
    if (!summary) return summary;
    const textureState = this.computeTextureState();
    summary.texturesVisible = textureState.texturesVisible;
    summary.textureMissingParts = textureState.missing;
    if (!textureState.texturesVisible) {
      summary.canSave = false;
      const reason = `Textures missing: ${textureState.missing.join(", ") || "disabled"}`;
      if (!(summary.reasons || []).includes(reason)) {
        summary.reasons = [...(summary.reasons || []), reason];
      }
    }
    return summary;
  }

  getSelectedFitPart() {
    return String(PANEL.fitPart?.value || "");
  }

  buildVrmBoneInferenceSnapshot() {
    if (!this.vrm.model) {
      this.vrm.bodyInference = null;
      return null;
    }
    const snapshot = createBoneInferenceSnapshot({
      joints: inferCanonicalJointsFromBoneResolver((boneName) => this.resolveVrmBone(boneName), {
        preferLimbRoots: true,
      }),
      source: "vrm",
    });
    this.vrm.bodyInference = snapshot;
    this.vrm.bodyTrackingFrame = createBodyTrackingFrameFromInference(snapshot, {
      source: "vrm",
      timestampMs: performance.now(),
      metadata: {
        vrmPath: this.vrm.path || "",
      },
    });
    return snapshot;
  }

  buildLiveBoneInferenceSnapshot(joints) {
    return createBoneInferenceSnapshot({
      joints,
      source: "live",
      options: {
        fallbackBodyScale: toNumberOr(this.live?.bodyScaleRef, 0),
        syntheticTorsoDropRatio: LIVE_POSE_OPTIONS.syntheticTorsoDropRatio,
        syntheticHipWidthRatio: LIVE_POSE_OPTIONS.syntheticHipWidthRatio,
      },
    });
  }

  buildFitAssistItems() {
    const summary = this.autoFitSummary;
    if (!summary) return [];

    const items = new Map();
    const ensureItem = (partName) => {
      const name = String(partName || "").trim();
      if (!name) return null;
      if (!items.has(name)) {
        items.set(name, {
          part: name,
          score: null,
          critical: false,
          pairs: [],
          seams: [],
          surface: [],
          hero: [],
          render: [],
          minScaleAxes: [],
        });
      }
      return items.get(name);
    };

    for (const weak of summary.weakParts || []) {
      const item = ensureItem(weak.part);
      if (!item) continue;
      item.score = Number.isFinite(Number(weak.score)) ? Number(weak.score) : null;
      item.critical = Boolean(weak.critical);
    }

    for (const pair of summary.weakPairs || []) {
      for (const partName of splitFitPairName(pair.pair)) {
        const item = ensureItem(partName);
        if (!item) continue;
        item.pairs.push(String(pair.pair));
      }
    }

    for (const violation of summary.surfaceViolations || []) {
      const item = ensureItem(violation.part);
      if (!item) continue;
      item.surface.push(`${violation.metric}:${violation.kind}`);
    }

    for (const overflow of summary.heroOverflow || []) {
      const item = ensureItem(overflow.part);
      if (!item) continue;
      item.hero.push(String(overflow.metric || "hero"));
    }

    for (const lock of summary.minScaleLocks || []) {
      const item = ensureItem(lock.part);
      if (!item) continue;
      item.minScaleAxes = Array.isArray(lock.axes) ? lock.axes.slice() : [];
    }

    for (const seam of summary.seamContinuity || []) {
      if (seam.ok) continue;
      for (const partName of splitFitPairName(seam.pair)) {
        const item = ensureItem(partName);
        if (!item) continue;
        item.seams.push(`${seam.pair}:${seam.gap}`);
      }
    }

    for (const entry of summary.renderDeviation || []) {
      if (entry.ok) continue;
      const item = ensureItem(entry.part);
      if (!item) continue;
      item.render.push(`render:${Math.max(...(entry.ratio || [0]))}`);
    }

    const severityOf = (item) => {
      let severity = 0;
      severity += item.seams.length * 90;
      severity += item.surface.length * 100;
      severity += item.hero.length * 80;
      severity += item.render.length * 70;
      severity += item.minScaleAxes.length * 12;
      if (item.critical && item.score != null && item.score < 58) severity += 60;
      if (item.score != null) severity += Math.max(0, 100 - item.score);
      return severity;
    };

    return Array.from(items.values()).sort((a, b) => {
      const severityDelta = severityOf(b) - severityOf(a);
      if (severityDelta !== 0) return severityDelta;
      const scoreA = a.score == null ? 999 : a.score;
      const scoreB = b.score == null ? 999 : b.score;
      return scoreA - scoreB;
    });
  }

  renderFitAssistPanel() {
    if (!PANEL.fitAssistSummary || !PANEL.fitAssistCurrent || !PANEL.fitAssistList) return;

    const selectedPart = this.getSelectedFitPart();
    const summary = this.autoFitSummary;
    const items = this.buildFitAssistItems();

    if (!this.vrm.model) {
      PANEL.fitAssistSummary.textContent =
        "1. VRM を読み込む 2. Auto Fit Armor 3. Needs Attention を上から修正 4. Refresh Check 5. Save SuitSpec";
    } else if (!summary) {
      PANEL.fitAssistSummary.textContent =
        "VRM 基準の判定は未実行です。Auto Fit Armor か Refresh Check で最初の診断を作ってください。";
    } else if (this.fitAssistDirty) {
      PANEL.fitAssistSummary.textContent =
        "手動編集後の未評価状態です。今の数値を信じる前に Refresh Check を押してください。";
    } else if (summary.canSave) {
      PANEL.fitAssistSummary.textContent =
        "Ready to save。必要なら気になる部位だけ微調整し、最後に Save SuitSpec を押してください。";
    } else {
      PANEL.fitAssistSummary.textContent = `Needs Attention: ${items.length} parts | ${formatAutoFitSummary(summary)}`;
    }

    const current = items.find((item) => item.part === selectedPart) || null;
    if (!selectedPart) {
      PANEL.fitAssistCurrent.textContent = "Current: -";
    } else if (!current) {
      PANEL.fitAssistCurrent.textContent = `Current: ${selectedPart}\nこの部位は直近の診断では強い問題としては出ていません。`;
    } else {
      const lines = [`Current: ${current.part}`];
      if (current.score != null) {
        lines.push(`score=${current.score.toFixed(1)}${current.critical ? " critical" : ""}`);
      }
      if (current.pairs.length) {
        lines.push(`weak pairs=${current.pairs.slice(0, 3).join(", ")}`);
      }
      if (current.seams.length) {
        lines.push(`seams=${current.seams.slice(0, 3).join(", ")}`);
      }
      if (current.surface.length) {
        lines.push(`surface=${current.surface.slice(0, 3).join(", ")}`);
      }
      if (current.hero.length) {
        lines.push(`hero=${current.hero.slice(0, 3).join(", ")}`);
      }
      if (current.render.length) {
        lines.push(`render=${current.render.slice(0, 3).join(", ")}`);
      }
      if (current.minScaleAxes.length) {
        lines.push(`minScale lock=${current.minScaleAxes.join(", ")}`);
      }
      PANEL.fitAssistCurrent.textContent = lines.join("\n");
    }

    PANEL.fitAssistList.innerHTML = "";
    if (!items.length) {
      const empty = document.createElement("button");
      empty.type = "button";
      empty.className = "fit-assist-item empty";
      empty.disabled = true;
      empty.textContent = summary?.canSave
        ? "Blocking issue はありません。必要なら見た目だけ追い込んで保存してください。"
        : "強い問題を検出できませんでした。Refresh Check で再判定してください。";
      PANEL.fitAssistList.appendChild(empty);
      return;
    }

    for (const item of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fit-assist-item";
      const blocking =
        item.seams.length ||
        item.surface.length ||
        item.hero.length ||
        item.render.length ||
        (item.critical && item.score != null && item.score < 58);
      if (blocking) button.classList.add("blocking");
      if (item.part === selectedPart) button.classList.add("active");

      const title = document.createElement("strong");
      title.textContent =
        item.score != null ? `${item.part} | score ${item.score.toFixed(1)}` : item.part;
      const detail = document.createElement("span");
      const detailParts = [];
      if (item.pairs.length) detailParts.push(`pair ${item.pairs.slice(0, 2).join(", ")}`);
      if (item.seams.length) detailParts.push(`seam ${item.seams.slice(0, 2).join(", ")}`);
      if (item.surface.length) detailParts.push(`surface ${item.surface.slice(0, 2).join(", ")}`);
      if (item.hero.length) detailParts.push(`hero ${item.hero.slice(0, 2).join(", ")}`);
      if (item.render.length) detailParts.push(`render ${item.render.slice(0, 2).join(", ")}`);
      if (item.minScaleAxes.length) detailParts.push(`minScale ${item.minScaleAxes.join(", ")}`);
      detail.textContent = detailParts.join(" | ") || "detail unavailable";
      button.append(title, detail);
      button.onclick = () => this.selectFitPart(item.part, { focusCamera: true });
      PANEL.fitAssistList.appendChild(button);
    }
  }

  updateFitSelectionVisuals() {
    const selectedPart = this.getSelectedFitPart();
    const baseColor = this.darkTheme ? 0xeaf2ff : 0x0f2342;
    const activeColor = this.darkTheme ? 0xffd296 : 0xd46a00;
    for (const [partName, rec] of this.meshes.entries()) {
      const active = partName === selectedPart;
      rec.outline.material.color.setHex(active ? activeColor : baseColor);
      rec.outline.material.opacity = active ? 0.96 : this.useTextures ? 0.22 : 0.85;
      if (rec.fitOutline) {
        rec.fitOutline.material.color.setHex(active ? activeColor : 0x4f89ff);
        rec.fitOutline.material.opacity = this.showFitShell ? (active ? 0.9 : 0.22) : 0;
      }
    }
  }

  syncFitShellOverlay() {
    for (const rec of this.meshes.values()) {
      const useSurfaceOverlay = Boolean(rec.surfaceFitNodeCount > 0);
      if (rec.fitGroup) rec.fitGroup.visible = this.showFitShell && !useSurfaceOverlay;
      if (rec.surfaceFitOverlay) rec.surfaceFitOverlay.visible = this.showFitShell && useSurfaceOverlay && this.armorVisible && rec.group.visible;
      if (rec.fitMesh?.material) {
        rec.fitMesh.material.opacity = this.showFitShell && !useSurfaceOverlay ? 0.12 : 0;
        rec.fitMesh.material.transparent = true;
        rec.fitMesh.material.depthWrite = false;
        rec.fitMesh.material.needsUpdate = true;
      }
      if (rec.fitOutline?.material) {
        rec.fitOutline.material.opacity = this.showFitShell && !useSurfaceOverlay ? 0.22 : 0;
        rec.fitOutline.material.transparent = true;
      }
    }
    this.updateFitSelectionVisuals();
  }

  fitCameraToPart(partName) {
    const rec = this.meshes.get(partName);
    const target = rec?.renderGroup || rec?.group;
    if (!target) return false;
    const box = new THREE.Box3().setFromObject(target);
    if (box.isEmpty()) return false;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const distance = Math.max(sphere.radius * 4.2, 0.55);
    const viewDir = new THREE.Vector3().subVectors(this.camera.position, this.controls.target);
    if (viewDir.lengthSq() < 0.00001) viewDir.set(0, 0.1, 1);
    viewDir.normalize();
    this.controls.target.copy(sphere.center);
    this.camera.position.copy(sphere.center).addScaledVector(viewDir, distance);
    this.updateCameraRange(distance);
    this.controls.update();
    return true;
  }

  selectFitPart(partName, { focusCamera = false } = {}) {
    const target = String(partName || "").trim();
    if (!target) return false;
    const fitOptions = Array.from(PANEL.fitPart?.options || []);
    if (fitOptions.length && !fitOptions.some((option) => option.value === target)) return false;
    if (PANEL.fitPart) PANEL.fitPart.value = target;
    this.loadFitEditorForPart(target);
    if (PANEL.vrmEditPart) {
      const anchorOptions = Array.from(PANEL.vrmEditPart.options || []);
      if (anchorOptions.some((option) => option.value === target)) {
        PANEL.vrmEditPart.value = target;
        this.loadVrmAnchorEditorForPart(target);
      }
    }
    if (focusCamera) {
      this.fitCameraToPart(target);
    }
    this.updateTransformGizmo();
    return true;
  }

  refreshFitAssistCheck() {
    return this.evaluateCurrentFitAgainstVrm({ forceTPose: true, silent: false });
  }

  selectAdjacentFitIssue(direction = 1) {
    const issues = this.buildFitAssistItems();
    const list = issues.length ? issues.map((item) => item.part) : this.listEditableParts();
    if (!list.length) return false;
    const current = this.getSelectedFitPart();
    const currentIndex = list.indexOf(current);
    const index = currentIndex >= 0 ? currentIndex : direction > 0 ? -1 : 1;
    const next = list[(index + direction + list.length) % list.length];
    return this.selectFitPart(next, { focusCamera: true });
  }

  getFitNudgeStep() {
    return clamp(Number(PANEL.fitNudgeStep?.value || 0.01), 0.001, 0.25);
  }

  nudgeCurrentFitField(fieldId, direction) {
    const input = PANEL[fieldId];
    if (!input) return false;
    const current = toNumberOr(input.value, 0);
    const step = this.getFitNudgeStep();
    const min = input.min === "" ? -Infinity : Number(input.min);
    const max = input.max === "" ? Infinity : Number(input.max);
    const next = round3(clamp(current + step * direction, min, max));
    input.value = String(next);
    this.applyFitEditorToCurrentPart({ silent: true });
      this.setStatus(`微調整: ${this.getSelectedFitPart() || "-"} / ${FIT_FIELD_LABELS[fieldId] || fieldId} = ${next}`);
    return true;
  }

  getGizmoEditTargetMode() {
    return normalizeVrmAttachMode(this.vrm.attachMode) === VRM_ATTACH_MODES.BODY ? "fit" : "anchor";
  }

  getCurrentDisplaySegments() {
    if (this.frames.length) {
      return withFallbackSegments(this.frames[this.frameIndex]?.segments || {});
    }
    if (this.vrm.model) {
      return withFallbackSegments(this.buildSegmentsFromCurrentVrmPose());
    }
    return withFallbackSegments({});
  }

  captureFitFromCurrentGroup(partName) {
    const module = this.suitspec?.modules?.[partName];
    const rec = this.meshes.get(partName);
    if (!module || !rec?.group) return null;
    const effective = getModuleVisualConfig(partName, module);
    const segments = this.getCurrentDisplaySegments();
    const base = segments[effective.source];
    if (!base) return null;

    const attach = String(effective.attach || "center");
    let anchor = 0;
    if (attach === "start") anchor = 0.5;
    if (attach === "end") anchor = -0.5;

    const axis = localYAxis(base.rotation_z);
    const deltaX = rec.group.position.x - Number(base.position_x || 0);
    const deltaY = rec.group.position.y - Number(base.position_y || 0);
    const along = deltaX * axis.x + deltaY * axis.y;
    const baseScaleX = Math.max(Number(base.scale_x || 1), 0.2);
    const baseScaleY = Math.max(Number(base.scale_y || 1), 0.2);
    const baseScaleZ = Math.max(Number(base.scale_z || 1), 0.2);
    const fitScaleX = 1 + (baseScaleX - 1) * Number(effective.follow[0] ?? 1);
    const fitScaleY = 1 + (baseScaleY - 1) * Number(effective.follow[1] ?? 1);
    const fitScaleZ = 1 + (baseScaleZ - 1) * Number(effective.follow[2] ?? 1);

    return {
      shape: effective.shape,
      source: effective.source,
      attach: effective.attach,
      offsetY: round3(along / Math.max(baseScaleY, 0.2) - anchor),
      zOffset: round3(rec.group.position.z - Number(base.position_z || 0)),
      scale: [
        round3(clamp(rec.group.scale.x / Math.max(fitScaleX, 0.001), 0.05, 3)),
        round3(clamp(rec.group.scale.y / Math.max(fitScaleY, 0.001), 0.05, 3)),
        round3(clamp(rec.group.scale.z / Math.max(fitScaleZ, 0.001), 0.05, 3)),
      ],
      follow: normalizeVec3(effective.follow, [1, 1, 1]),
      minScale: normalizeVec3(effective.minScale, [0.2, 0.2, 0.2]),
    };
  }

  captureAnchorFromCurrentGroup(partName) {
    const module = this.suitspec?.modules?.[partName];
    const rec = this.meshes.get(partName);
    if (!module || !rec?.group) return null;
    const effective = effectiveVrmAnchorFor(partName, module);
    const bone = this.resolveVrmBoneForPart(partName, module, effective.bone);
    if (!bone) return null;

    const bonePos = bone.getWorldPosition(new THREE.Vector3());
    const boneQuat = bone.getWorldQuaternion(new THREE.Quaternion());
    const invBone = boneQuat.clone().invert();
    const groupPos = rec.group.getWorldPosition(new THREE.Vector3());
    const localOffset = groupPos.sub(bonePos).applyQuaternion(invBone);
    const baseScale = rec.lastTransform
      ? [rec.lastTransform.scale_x, rec.lastTransform.scale_y, rec.lastTransform.scale_z]
      : [1, 1, 1];

    return {
      bone: String(effective.bone || "chest"),
      offset: [round3(localOffset.x), round3(localOffset.y), round3(localOffset.z)],
      rotation: normalizeVec3(effective.rotation, [0, 0, 0]).map((value) => round3(value)),
      scale: [
        round3(Math.max(0.01, rec.group.scale.x / Math.max(Number(baseScale[0] || 1), 0.001))),
        round3(Math.max(0.01, rec.group.scale.y / Math.max(Number(baseScale[1] || 1), 0.001))),
        round3(Math.max(0.01, rec.group.scale.z / Math.max(Number(baseScale[2] || 1), 0.001))),
      ],
    };
  }

  previewGizmoEdit() {
    const partName = this.getSelectedFitPart();
    if (!partName) return false;
    if (this.getGizmoEditTargetMode() === "fit") {
      const fit = this.captureFitFromCurrentGroup(partName);
      if (!fit) return false;
      PANEL.fitScaleX.value = String(fit.scale[0]);
      PANEL.fitScaleY.value = String(fit.scale[1]);
      PANEL.fitScaleZ.value = String(fit.scale[2]);
      PANEL.fitOffsetY.value = String(fit.offsetY);
      PANEL.fitZOffset.value = String(fit.zOffset || 0);
      return true;
    }
    const anchor = this.captureAnchorFromCurrentGroup(partName);
    if (!anchor) return false;
    if (PANEL.vrmEditPart) PANEL.vrmEditPart.value = partName;
    if (PANEL.vrmEditBone) PANEL.vrmEditBone.value = anchor.bone;
    if (PANEL.vrmEditOffsetX) PANEL.vrmEditOffsetX.value = String(anchor.offset[0]);
    if (PANEL.vrmEditOffsetY) PANEL.vrmEditOffsetY.value = String(anchor.offset[1]);
    if (PANEL.vrmEditOffsetZ) PANEL.vrmEditOffsetZ.value = String(anchor.offset[2]);
    if (PANEL.vrmEditScaleX) PANEL.vrmEditScaleX.value = String(anchor.scale[0]);
    if (PANEL.vrmEditScaleY) PANEL.vrmEditScaleY.value = String(anchor.scale[1]);
    if (PANEL.vrmEditScaleZ) PANEL.vrmEditScaleZ.value = String(anchor.scale[2]);
    this.updateVrmAnchorPreview(anchor, normalizeAttachmentSlot(partName, this.suitspec?.modules?.[partName]));
    return true;
  }

  commitGizmoEdit() {
    const partName = this.getSelectedFitPart();
    if (!partName || !this.gizmo.enabled) return false;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return false;

    if (this.getGizmoEditTargetMode() === "fit") {
      const fit = this.captureFitFromCurrentGroup(partName);
      if (!fit) return false;
      module.fit = fit;
      const rec = this.meshes.get(partName);
      if (rec) rec.config = getModuleVisualConfig(partName, module);
      this.fitAssistDirty = true;
      this.applyFrame(this.frameIndex);
      this.loadFitEditorForPart(partName);
      this.setStatus(`ギズモでフィット反映: ${partName}`);
      return true;
    }

    const slot = normalizeAttachmentSlot(partName, module);
    const anchor = this.captureAnchorFromCurrentGroup(partName);
    if (!anchor) return false;
    module.attachment_slot = slot;
    module.vrm_anchor = anchor;
    this.fitAssistDirty = true;
    this.applyFrame(this.frameIndex);
    this.loadVrmAnchorEditorForPart(partName);
    this.setStatus(`ギズモでアンカー反映: ${partName}`);
    return true;
  }

  updateGizmoButtons() {
    if (PANEL.btnGizmoToggle) PANEL.btnGizmoToggle.textContent = `ギズモ: ${jaOnOff(this.gizmo.enabled)}`;
    if (PANEL.btnGizmoMove) PANEL.btnGizmoMove.classList.toggle("active", this.gizmo.mode === "translate");
    if (PANEL.btnGizmoScale) PANEL.btnGizmoScale.classList.toggle("active", this.gizmo.mode === "scale");
    if (PANEL.btnGizmoSpace) PANEL.btnGizmoSpace.textContent = `座標: ${this.gizmo.space === "local" ? "ローカル" : "ワールド"}`;
    if (PANEL.btnGizmoSpace) PANEL.btnGizmoSpace.classList.toggle("active", this.gizmo.space === "world");
    if (PANEL.fitGizmoHint) {
      const target = this.getGizmoEditTargetMode() === "fit" ? "fit" : "anchor";
      const mode = this.gizmo.mode === "translate" ? "Move" : "Scale";
      PANEL.fitGizmoHint.textContent =
        `Selected part に ${mode} gizmo を表示中。Attach=${VRM_ATTACH_MODE_LABELS[normalizeVrmAttachMode(this.vrm.attachMode)] || "Hybrid"} なので ${target} を更新します。`;
    }
  }

  refreshLiveTrackingStatus() {
    if (!this.live?.active) return;
    const model = this.live.poseModel || "-";
    const quality = this.live.poseQuality || "idle";
    const joints = this.live.poseReliableJoints || 0;
    const readiness = this.live?.bodyInference?.fitReadiness || "unknown";
    const viewMode =
      this.liveViewMode === "auto"
        ? `自動/${this.getEffectiveLiveViewLabel() === "mirror" ? "ミラー" : "ワールド"}`
        : this.liveViewMode === "mirror"
          ? "ミラー"
          : "ワールド";
    const isLow = quality === "low" || quality === "missing";
    const text = isLow
      ? `ライブ: 信頼度が低めです (関節 ${joints}, model=${model}, readiness=${readiness}, view=${viewMode})`
      : `ライブ: 動作中 (${quality}, 関節 ${joints}, readiness=${readiness}, model=${model}, view=${viewMode})`;
    this.updateLiveStatus(text, isLow);
  }

  updateTransformGizmo() {
    if (!this.transformControls) return;
    this.updateGizmoButtons();
    const partName = this.getSelectedFitPart();
    const rec = this.meshes.get(partName);
    const canAttach = Boolean(this.gizmo.enabled && rec?.group?.visible);
    this.transformControls.enabled = canAttach;
    this.transformControls.visible = canAttach;
    if (!canAttach) {
      this.transformControls.detach();
      return;
    }

    if (this.transformControls.object !== rec.group) {
      this.transformControls.attach(rec.group);
    }
    const editMode = this.getGizmoEditTargetMode();
    this.transformControls.setMode(this.gizmo.mode);
    const space = editMode === "fit" && this.gizmo.mode === "translate" ? "local" : this.gizmo.space;
    this.transformControls.setSpace(space);
    this.transformControls.showX = !(editMode === "fit" && this.gizmo.mode === "translate");
    this.transformControls.showY = true;
    this.transformControls.showZ = true;
    this.transformControls.size = editMode === "fit" ? 0.72 : 0.82;
  }

  setGizmoEnabled(enabled) {
    this.gizmo.enabled = Boolean(enabled);
    this.updateTransformGizmo();
  }

  setGizmoMode(mode) {
    this.gizmo.mode = mode === "scale" ? "scale" : "translate";
    this.updateTransformGizmo();
  }

  cycleGizmoSpace() {
    this.gizmo.space = this.gizmo.space === "local" ? "world" : "local";
    this.updateTransformGizmo();
  }

  updateLiveStatus(text, isError = false) {
    if (!PANEL.liveStatus) return;
    PANEL.liveStatus.textContent = text;
    PANEL.liveStatus.style.color = isError ? "#b41f2f" : "#264b7f";
    this.updateLiveCheckPanel();
  }

  updateLiveCheckPanel() {
    if (!PANEL.liveCheckInput || !PANEL.liveCheckPose || !PANEL.liveCheckFrame || !PANEL.liveCheckSurface) return;
    const live = this.live || {};
    const frame = live.bodyTrackingFrame || null;
    const inference = frame?.boneInference || live.bodyInference || null;
    const summary = this.surfaceFirst?.summary || null;
    const fps = round3(live.fps || 0);
    const model = live.poseModel || "-";
    const quality = live.poseQuality || inference?.qualityLabel || "idle";
    const joints = live.poseReliableJoints || inference?.reliableJointCount || 0;
    const readiness = inference?.fitReadiness || "未判定";

    PANEL.liveCheckInput.textContent = live.active ? `ON / ${fps} fps / ${model}` : "停止中";
    PANEL.liveCheckPose.textContent = live.active ? `${quality} / joints ${joints} / ${readiness}` : "未取得";
    PANEL.liveCheckFrame.textContent = frame
      ? `${frame.source} / schema ${frame.schemaVersion} / ${frame.id}`
      : "なし";
    if (summary?.error) {
      PANEL.liveCheckSurface.textContent = `error / ${summary.error}`;
    } else if (summary) {
      const source = summary.tracking_frame_source || summary.tracking_source || "-";
      const nodes = summary.stable_node_count ?? summary.sampleCount ?? 0;
      const textureNodes = summary.texture_projected_nodes ?? 0;
      const reproject = summary.live_reprojected ? "ON" : "OFF";
      PANEL.liveCheckSurface.textContent = `${source} / nodes ${nodes} / tex ${textureNodes} / reproject ${reproject}`;
    } else {
      PANEL.liveCheckSurface.textContent = "未接続";
    }
  }

  normalizeLiveViewMode(mode) {
    const value = String(mode || "auto").trim().toLowerCase();
    return value === "mirror" || value === "world" ? value : "auto";
  }

  getEffectiveLiveMirror() {
    if (this.liveViewMode === "mirror") return true;
    if (this.liveViewMode === "world") return false;
    return this.cameraPreset === "front";
  }

  getEffectiveLiveViewLabel() {
    return this.getEffectiveLiveMirror() ? "mirror" : "world";
  }

  updateLiveVideoPresentation() {
    if (!PANEL.liveVideo) return;
    PANEL.liveVideo.classList.toggle("mirrored", this.getEffectiveLiveMirror());
  }

  setLiveViewMode(mode) {
    this.liveViewMode = this.normalizeLiveViewMode(mode);
    if (PANEL.liveViewMode) {
      PANEL.liveViewMode.value = this.liveViewMode;
    }
    this.updateLiveVideoPresentation();
    this.refreshLiveTrackingStatus();
    this.updateMetaPanel();
    this.setLegend();
  }

  refreshLiveTrackingStatus() {
    if (!this.live?.active) return;
    const model = this.live.poseModel || "-";
    const quality = this.live.poseQuality || "idle";
    const joints = this.live.poseReliableJoints || 0;
    const readiness = this.live?.bodyInference?.fitReadiness || "unknown";
    const viewMode =
      this.liveViewMode === "auto"
        ? `auto/${this.getEffectiveLiveViewLabel()}`
        : this.liveViewMode;
    const isLow = quality === "low" || quality === "missing";
    const text = isLow
      ? `Live: low confidence (${joints} joints, model=${model}, readiness=${readiness}, view=${viewMode})`
      : `Live: webcam active (${quality}, joints=${joints}, readiness=${readiness}, model=${model}, view=${viewMode})`;
    this.updateLiveStatus(text, isLow);
  }

  formatLivePipelineError(detail) {
    const raw = String(detail || "unknown");
    if (/notallowederror|permission denied|permission dismissed|securityerror/i.test(raw)) {
      return "Camera permission was denied. Allow camera access and retry.";
    }
    if (/failed to fetch|networkerror|err_network|err_internet|err_connection|err_blocked/i.test(raw)) {
      return `${raw} (pose model download/import failed. Check network, firewall, ad-blocker, or host model files locally)`;
    }
    if (/no live pipeline modules configured/i.test(raw)) {
      return "No live pipeline modules configured.";
    }
    return raw;
  }

  listLivePipelineModules() {
    return this.livePipeline.listModuleNames();
  }

  async startLivePipelineModules() {
    if (!this.listLivePipelineModules().length) {
      throw new Error("No live pipeline modules configured");
    }
    this.livePipelineError = "";
    await this.livePipeline.runStart({
      viewer: this,
      live: this.live,
      video: this.live.video,
    });
    this.livePipelineActive = true;
  }

  stopLivePipelineModules() {
    if (!this.livePipelineActive && !this.live?.landmarker) return;
    try {
      this.livePipeline.runStop({
        viewer: this,
        live: this.live,
        video: this.live.video,
      });
      this.livePipelineError = "";
    } catch (error) {
      this.livePipelineError = String(error?.message || error || "pipeline stop failed");
      console.warn("live pipeline stop warning:", error);
    } finally {
      this.livePipelineActive = false;
    }
  }

  updateLivePipelineModules(nowMs, dtSec, video) {
    const ctx = {
      viewer: this,
      live: this.live,
      video,
      nowMs,
      dtSec,
      poseLandmarks: null,
      liveSegments: null,
    };
    this.livePipeline.runUpdate(ctx);
    return ctx;
  }

  updateBridgeButton() {
    if (PANEL.btnBridgeToggle) {
      PANEL.btnBridgeToggle.textContent = `接続ブリッジ: ${jaOnOff(this.bridgeEnabled)}`;
    }
  }

  updateArmorButton() {
    if (PANEL.btnArmorToggle) {
      PANEL.btnArmorToggle.textContent = `鎧表示: ${jaOnOff(this.armorVisible)}`;
    }
  }

  updateVrmButton() {
    if (PANEL.btnVrmToggle) {
      PANEL.btnVrmToggle.textContent = `骨表示: ${jaOnOff(this.vrm.visible)}`;
    }
  }

  updateVrmIdleButton() {
    if (PANEL.btnVrmIdleToggle) {
      PANEL.btnVrmIdleToggle.textContent = `待機モーション: ${jaOnOff(this.vrm.idleEnabled)}`;
    }
  }

  updateVrmAttachButton() {
    if (PANEL.btnVrmAttach) {
      const mode = normalizeVrmAttachMode(this.vrm.attachMode);
      PANEL.btnVrmAttach.textContent = `装着基準: ${VRM_ATTACH_MODE_LABELS[mode] || "ハイブリッド"}`;
    }
  }

  updateVrmStatus(text, isError = false) {
    if (!PANEL.vrmStatus) return;
    PANEL.vrmStatus.textContent = text;
    PANEL.vrmStatus.style.color = isError ? "#b41f2f" : "#264b7f";
  }

  updateDepositionStatus(text, isError = false) {
    if (!PANEL.depositionStatus) return;
    PANEL.depositionStatus.textContent = text;
    PANEL.depositionStatus.style.color = isError ? "#b41f2f" : "#264b7f";
  }

  updateSurfaceFirstButtons() {
    if (PANEL.btnSurfaceFirstGraph) {
      PANEL.btnSurfaceFirstGraph.textContent = `表面点群: ${jaOnOff(this.surfaceFirst.graphVisible)}`;
      PANEL.btnSurfaceFirstGraph.classList.toggle("active", this.surfaceFirst.graphVisible);
    }
    if (PANEL.btnSurfaceFirstShell) {
      PANEL.btnSurfaceFirstShell.textContent = `密着殻: ${jaOnOff(this.surfaceFirst.shellVisible)}`;
      PANEL.btnSurfaceFirstShell.classList.toggle("active", this.surfaceFirst.shellVisible);
    }
    if (PANEL.btnSurfaceFirstMounts) {
      PANEL.btnSurfaceFirstMounts.textContent = `装着点: ${jaOnOff(this.surfaceFirst.mountsVisible)}`;
      PANEL.btnSurfaceFirstMounts.classList.toggle("active", this.surfaceFirst.mountsVisible);
    }
  }

  updateSurfaceFirstStatus(text, isError = false) {
    if (!PANEL.surfaceStatus) return;
    PANEL.surfaceStatus.textContent = text;
    PANEL.surfaceStatus.style.color = isError ? "#b41f2f" : "#264b7f";
  }

  isSurfaceFirstVisible() {
    return Boolean(this.surfaceFirst.graphVisible || this.surfaceFirst.shellVisible || this.surfaceFirst.mountsVisible);
  }

  needsSurfaceFirstSnapshot() {
    return Boolean(this.showFitShell || this.isSurfaceFirstVisible());
  }

  resolveSurfaceFirstTrackingContext() {
    const forced = String(this.surfaceFirst?.forceTrackingSource || "auto");
    const liveFrame = this.live?.active ? this.live?.bodyTrackingFrame : null;
    const liveInference = liveFrame?.boneInference || (this.live?.active ? this.live?.bodyInference : null);
    if (
      forced !== "vrm" &&
      liveInference &&
      String(liveInference.fitReadiness || "") !== "insufficient"
    ) {
      return {
        source: liveFrame?.source || "webcam",
        label: "webcam",
        bodyInference: liveInference,
        trackingFrame: liveFrame,
        resolveBone: null,
      };
    }
    return {
      source: "vrm",
      label: "vrm",
      bodyInference: this.vrm.bodyInference,
      trackingFrame: this.vrm.bodyTrackingFrame || null,
      resolveBone: (boneName) => this.resolveVrmBone(boneName),
    };
  }

  clearSurfaceFitOverlays() {
    for (const rec of this.meshes.values()) {
      if (rec.surfaceFitOverlay) {
        disposeObjectResources(rec.surfaceFitOverlay);
        rec.surfaceFitOverlay.clear();
        rec.surfaceFitOverlay.visible = false;
      }
      if (rec.surfaceFitProxyGroup) {
        disposeObjectResources(rec.surfaceFitProxyGroup);
        rec.surfaceFitProxyGroup.clear();
      }
      rec.surfaceFitNodeCount = 0;
    }
  }

  projectSurfaceTextureColors(snapshot) {
    if (!snapshot?.nodes?.length) return { texturedParts: [], texturedNodeCount: 0 };
    this.root.updateMatrixWorld(true);
    const texturedParts = new Set();
    let texturedNodeCount = 0;
    for (const node of snapshot.nodes) {
      const partName = classifySurfaceNodeToPart(node, snapshot.proxies);
      node.partName = partName || null;
      if (partName && node.binding && !node.binding.partName) {
        node.binding.partName = partName;
      }
      if (!partName) continue;
      const record = this.meshes.get(partName);
      if (!record) continue;
      const samplePoint = (node.position || node.surfacePoint || new THREE.Vector3()).clone();
      const color = this.useTextures
        ? sampleRecordTextureColorAtWorldPoint(record, samplePoint, partColor(partName))
        : new THREE.Color(partColor(partName));
      node.color = color.clone().lerp(node.color || new THREE.Color(partColor(partName)), this.useTextures ? 0.18 : 0.32);
      if (record.texture) {
        texturedParts.add(partName);
        texturedNodeCount += 1;
      }
    }
    return {
      texturedParts: Array.from(texturedParts.values()),
      texturedNodeCount,
    };
  }

  applySurfaceFitOverlays(snapshot) {
    this.clearSurfaceFitOverlays();
    if (!snapshot?.nodes?.length) return { partCount: 0, nodeCount: 0 };
    this.root.updateMatrixWorld(true);
    const offset = Number(snapshot.shellOffset || this.surfaceFirst.shellOffset || 0.018);
    const buckets = new Map();
    for (const node of snapshot.nodes) {
      const partName = node.partName || classifySurfaceNodeToPart(node, snapshot.proxies);
      const rec = this.meshes.get(partName);
      if (!partName || !rec?.group) continue;
      const worldPoint = (node.position || node.surfacePoint || new THREE.Vector3())
        .clone()
        .addScaledVector(node.normal || new THREE.Vector3(0, 0, 1), offset * 0.5);
      const localPoint = rec.group.worldToLocal(worldPoint.clone());
      const localNormal = (node.normal || new THREE.Vector3(0, 0, 1)).clone().normalize();
      if (!buckets.has(partName)) buckets.set(partName, []);
      buckets.get(partName).push({
        position: localPoint,
        normal: localNormal,
        color: (node.color || new THREE.Color(partColor(partName))).clone(),
      });
    }

    let totalNodes = 0;
    for (const [partName, nodes] of buckets.entries()) {
      const rec = this.meshes.get(partName);
      if (!rec) continue;
      totalNodes += nodes.length;
      rec.surfaceFitNodeCount = nodes.length;

      const overlay = createSurfacePointLayer(nodes, {
        size: 0.02,
        opacity: this.useTextures ? 0.82 : 0.7,
        additive: false,
        renderOrder: 6,
      });
      overlay.name = `${partName}:surfaceFitOverlayPoints`;
      rec.surfaceFitOverlay.add(overlay);
      rec.surfaceFitOverlay.visible = this.showFitShell && this.armorVisible && rec.group.visible;

      const proxy = createSurfacePointLayer(nodes, {
        size: 0.016,
        opacity: 0.001,
        additive: false,
        renderOrder: 1,
      });
      proxy.name = `${partName}:surfaceFitProxyPoints`;
      proxy.material.depthWrite = false;
      proxy.material.depthTest = false;
      rec.surfaceFitProxyGroup.add(proxy);
    }
    return { partCount: buckets.size, nodeCount: totalNodes };
  }

  clearSurfaceFirstDemo() {
    if (this.surfaceFirst.rig?.group) {
      this.surfaceFirstGroup.remove(this.surfaceFirst.rig.group);
      disposeSurfaceFirstDemoRig(this.surfaceFirst.rig);
    }
    this.clearSurfaceFitOverlays();
    this.surfaceFirst.rig = null;
    this.surfaceFirst.seedSnapshot = null;
    this.surfaceFirst.snapshot = null;
    this.surfaceFirst.summary = null;
    this.surfaceFirst.trackingSource = "vrm";
    this.surfaceFirst.error = "";
  }

  refreshSurfaceFirstDemo({ force = false } = {}) {
    this.surfaceFirst.density = clamp(Number(PANEL.surfacePointDensity?.value || this.surfaceFirst.density || 72), 24, 240);
    this.surfaceFirst.shellOffset = clamp(Number(PANEL.surfaceShellOffset?.value || this.surfaceFirst.shellOffset || 0.018), 0.002, 0.08);
    if (!this.vrm.model || !this.vrm.bodyInference) {
      this.clearSurfaceFirstDemo();
      this.updateSurfaceFirstStatus("Surface-first: VRM 未読込");
      this.updateMetaPanel();
      this.setLegend();
      return null;
    }
    if (!force && !this.needsSurfaceFirstSnapshot()) {
      this.updateSurfaceFirstStatus("Surface-first: 非表示");
      this.updateMetaPanel();
      this.setLegend();
      return this.surfaceFirst.summary;
    }
    try {
      const tracking = this.resolveSurfaceFirstTrackingContext();
      const seedSnapshot = buildSurfaceFirstSnapshot({
        vrmModel: this.vrm.model,
        resolveBone: (boneName) => this.resolveVrmBone(boneName),
        bodyInference: this.vrm.bodyInference,
        options: {
          maxSamplesPerMesh: this.surfaceFirst.density,
          shellOffset: this.surfaceFirst.shellOffset,
        },
      });
      const snapshot =
        tracking.source !== "vrm"
          ? reprojectSurfaceFirstSnapshot(seedSnapshot, {
              bodyInference: tracking.bodyInference,
              resolveBone: tracking.resolveBone,
              options: {
                trackingSource: tracking.source,
                maxGraphNodesPerRegion: this.surfaceFirst.density,
              },
            })
          : {
              ...seedSnapshot,
              trackingSource: tracking.source,
            };
      const textureProjection = this.projectSurfaceTextureColors(snapshot);
      this.clearSurfaceFirstDemo();
      this.surfaceFirst.seedSnapshot = seedSnapshot;
      this.surfaceFirst.snapshot = snapshot;
      this.surfaceFirst.trackingSource = tracking.source;
      this.surfaceFirst.rig = createSurfaceFirstDemoRig(snapshot, {
        graphVisible: this.surfaceFirst.graphVisible,
        shellVisible: this.surfaceFirst.shellVisible,
        mountsVisible: this.surfaceFirst.mountsVisible,
        shellOffset: this.surfaceFirst.shellOffset,
      });
      if (this.surfaceFirst.rig?.group) {
        this.surfaceFirstGroup.add(this.surfaceFirst.rig.group);
      }
      const fitOverlay = this.applySurfaceFitOverlays(snapshot);
      const partCounts = {};
      for (const node of snapshot.nodes || []) {
        const partName = node.partName || null;
        if (!partName) continue;
        partCounts[partName] = (partCounts[partName] || 0) + 1;
      }
      this.surfaceFirst.summary = summarizeSurfaceFirstSnapshot(snapshot, {
        graphVisible: this.surfaceFirst.graphVisible,
        shellVisible: this.surfaceFirst.shellVisible,
        mountsVisible: this.surfaceFirst.mountsVisible,
        shellOffset: this.surfaceFirst.shellOffset,
      });
      this.surfaceFirst.summary.quality = this.vrm.bodyInference?.qualityLabel || null;
      this.surfaceFirst.summary.fit_readiness = this.vrm.bodyInference?.fitReadiness || null;
      this.surfaceFirst.summary.texture_projected_parts = textureProjection.texturedParts;
      this.surfaceFirst.summary.texture_projected_nodes = textureProjection.texturedNodeCount;
      this.surfaceFirst.summary.fit_overlay_parts = fitOverlay.partCount;
      this.surfaceFirst.summary.fit_overlay_nodes = fitOverlay.nodeCount;
      this.surfaceFirst.summary.tracking_source = tracking.source;
      this.surfaceFirst.summary.stable_node_count = snapshot.nodes?.filter((node) => Boolean(node.id)).length || 0;
      this.surfaceFirst.summary.first_node_id = snapshot.nodes?.[0]?.id || null;
      this.surfaceFirst.summary.node_id_sample = (snapshot.nodes || []).slice(0, 8).map((node) => node.id);
      this.surfaceFirst.summary.part_counts = partCounts;
      this.surfaceFirst.summary.tracking_frame_id = tracking.trackingFrame?.id || null;
      this.surfaceFirst.summary.tracking_frame_source = tracking.trackingFrame?.source || tracking.source;
      this.surfaceFirst.summary.tracking_frame_schema = tracking.trackingFrame?.schemaVersion || null;
      this.surfaceFirst.summary.tracking_timestamp_ms = round3(tracking.trackingFrame?.timestampMs || 0);
      this.surfaceFirst.summary.live_reprojected = tracking.source !== "vrm";
      this.surfaceFirst.lastRefreshMs = performance.now();
      this.updateSurfaceFirstStatus(
        `Surface-first: ${snapshot.sampleCount} pts / ${snapshot.links.length} links / ${snapshot.mounts.length} mounts / fit ${fitOverlay.partCount} parts / source ${tracking.label}`
      );
      this.updateMetaPanel();
      this.syncFitShellOverlay();
      this.setLegend();
      return this.surfaceFirst.summary;
    } catch (error) {
      this.clearSurfaceFirstDemo();
      this.surfaceFirst.error = error?.message || String(error);
      this.updateSurfaceFirstStatus(`Surface-first: ${this.surfaceFirst.error}`, true);
      this.updateMetaPanel();
      this.setLegend();
      return null;
    }
  }

  setSurfaceFirstLayerVisible(layer, visible) {
    if (layer === "graph") this.surfaceFirst.graphVisible = Boolean(visible);
    if (layer === "shell") this.surfaceFirst.shellVisible = Boolean(visible);
    if (layer === "mounts") this.surfaceFirst.mountsVisible = Boolean(visible);
    if (this.surfaceFirst.rig) {
      if (layer === "graph" && this.surfaceFirst.rig.graphGroup) this.surfaceFirst.rig.graphGroup.visible = this.surfaceFirst.graphVisible;
      if (layer === "shell" && this.surfaceFirst.rig.shellGroup) this.surfaceFirst.rig.shellGroup.visible = this.surfaceFirst.shellVisible;
      if (layer === "mounts" && this.surfaceFirst.rig.mountGroup) this.surfaceFirst.rig.mountGroup.visible = this.surfaceFirst.mountsVisible;
    }
    this.updateSurfaceFirstButtons();
    this.refreshSurfaceFirstDemo({ force: this.needsSurfaceFirstSnapshot() });
  }

  syncSurfaceFirstDemo(now) {
    if (!this.vrm.model || !this.vrm.bodyInference || !this.needsSurfaceFirstSnapshot()) return;
    if (now - this.surfaceFirst.lastRefreshMs < this.surfaceFirst.refreshIntervalMs) return;
    this.refreshSurfaceFirstDemo({ force: true });
  }

  resolveDepositionProfileKey() {
    const mode = String(PANEL.depositionProfile?.value || this.deposition.profileMode || "auto");
    this.deposition.profileMode = mode;
    if (mode !== "auto" && DEPOSITION_PROFILES[mode]) return mode;
    const hue = hueFromHex(this.suitspec?.palette?.primary);
    if (hue == null) return "guard";
    if (hue < 20 || hue >= 345) return "drive";
    if (hue < 70) return "uplift";
    if (hue < 180) return "guard";
    if (hue < 250) return "grief";
    if (hue < 305) return "tension";
    return "embrace";
  }

  playDepositionMock() {
    if (!this.meshes.size) {
      this.setStatus("蒸着を再生する前に SuitSpec を読み込んでください。", true);
      this.updateDepositionStatus("Deposition: no armor loaded", true);
      return;
    }
    this.deposition.durationSec = clamp(
      Number(PANEL.depositionDuration?.value || this.suitspec?.effects?.deposition_seconds || DEFAULT_DEPOSITION_DURATION),
      1.2,
      6.0
    );
    this.deposition.resolvedKey = this.resolveDepositionProfileKey();
    const profile = DEPOSITION_PROFILES[this.deposition.resolvedKey] || DEPOSITION_PROFILES.guard;
    this.deposition.palette = buildDepositionPalette(profile);
    const bounds = this.getDepositionBounds();
    if (!bounds) {
      this.setStatus("蒸着の範囲を取得できませんでした。", true);
      this.updateDepositionStatus("Deposition: bounds unavailable", true);
      return;
    }
    this.prepareDepositionParticles(bounds, profile, this.deposition.palette);
    this.deposition.startedAtMs = performance.now();
    this.deposition.progress = 0;
    this.deposition.active = true;
    this.depositionFx.group.visible = true;
    this.updateDepositionStatus(
      `Deposition: playing ${DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey}`
    );
    this.setStatus(
      this.vrm.model
        ? `Deposition mock started (${DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey})`
        : `Deposition mock started (${DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey}, armor-only)`
    );
    this.updateMetaPanel();
    this.setLegend();
  }

  resetDepositionMock({ silent = false, keepStatus = false } = {}) {
    this.deposition.active = false;
    this.deposition.progress = 1;
    this.depositionFx.group.visible = false;
    this.resetDepositionVisuals();
    if (!keepStatus) {
      this.updateDepositionStatus("Deposition: idle");
    }
    if (!silent) {
    this.setStatus("蒸着演出をリセットしました。");
    }
    this.updateMetaPanel();
    this.setLegend();
  }

  finishDepositionMock() {
    this.deposition.active = false;
    this.deposition.progress = 1;
    this.depositionFx.group.visible = false;
    this.resetDepositionVisuals();
    const label = DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey;
    this.updateDepositionStatus(`Deposition: complete (${label})`);
    this.updateMetaPanel();
    this.setLegend();
  }

  resetDepositionVisuals() {
    if (this.depositionFx?.shellParticles?.points?.material) {
      this.depositionFx.shellParticles.points.material.opacity = 0;
    }
    if (this.depositionFx?.glowParticles?.points?.material) {
      this.depositionFx.glowParticles.points.material.opacity = 0;
    }
    for (const rec of this.meshes.values()) {
      const material = rec.mesh.material;
      material.transparent = false;
      material.opacity = 1;
      material.emissive?.setHex?.(0x000000);
      material.emissiveIntensity = 0;
      material.metalness = 0.55;
      material.roughness = 0.45;
      material.needsUpdate = true;
      rec.outline.visible = true;
      rec.outline.material.opacity = this.useTextures ? 0.22 : 0.85;
      if (rec.lastTransform) {
        rec.group.scale.set(rec.lastTransform.scale_x, rec.lastTransform.scale_y, rec.lastTransform.scale_z);
      }
    }
  }

  getDepositionBounds() {
    this.root.updateMatrixWorld(true);
    if (this.vrm.model) this.vrm.model.updateMatrixWorld(true);
    const box = new THREE.Box3();
    let hasVisible = false;
    if (this.armorVisible) {
      for (const rec of this.meshes.values()) {
        const target = rec.renderGroup?.visible ? rec.renderGroup : rec.group;
        if (!target?.visible) continue;
        box.expandByObject(target);
        hasVisible = true;
      }
    }
    if (this.vrm.model) {
      box.expandByObject(this.vrm.model);
      hasVisible = true;
    }
    if (!hasVisible || box.isEmpty()) return null;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    return {
      box,
      center: sphere.center,
      radius: Math.max(sphere.radius, 0.35),
      minY: box.min.y,
      maxY: box.max.y,
      minZ: box.min.z,
      maxZ: box.max.z,
      height: Math.max(box.max.y - box.min.y, 1.0),
      width: Math.max(box.max.x - box.min.x, 0.5),
    };
  }

  prepareDepositionParticles(bounds, profile, palette = buildDepositionPalette(profile)) {
    const fx = this.depositionFx;
    fx.group.visible = true;
    fx.group.position.set(0, 0, 0);
    seedDepositionParticleSystem(
      fx.shellParticles,
      {
        count: profile.shellCount,
        size: profile.shellSize,
        shellColor: palette.particleShell,
        highlightColor: palette.particleHighlight,
      },
      (i) => this.randomDepositionSource(bounds, this.deposition.resolvedKey, i, "shell"),
      () => this.sampleDepositionTarget(bounds, this.deposition.resolvedKey, "shell")
    );
    seedDepositionParticleSystem(
      fx.glowParticles,
      {
        count: profile.glowCount,
        size: profile.glowSize,
        shellColor: palette.particleHighlight,
        highlightColor: palette.particleGlow,
      },
      (i) => this.randomDepositionSource(bounds, this.deposition.resolvedKey, i, "glow"),
      () => this.sampleDepositionTarget(bounds, this.deposition.resolvedKey, "glow")
    );
  }

  randomDepositionSource(bounds, profileKey, index, kind) {
    const randA = hash01(index * 13.17 + 0.31);
    const randB = hash01(index * 17.13 + 0.73);
    const randC = hash01(index * 19.91 + 0.19);
    let angle = randA * Math.PI * 2;
    let radius = bounds.radius * (kind === "glow" ? 1.02 + randB * 0.38 : 1.18 + randB * 0.82);
    let y = lerp(bounds.minY - bounds.height * 0.08, bounds.maxY + bounds.height * 0.08, randC);

    switch (profileKey) {
      case "uplift":
        y = lerp(bounds.minY - bounds.height * 0.34, bounds.maxY * 0.18, randC);
        break;
      case "drive":
        angle = lerp(-0.42, 0.42, randA) + Math.PI;
        radius = bounds.radius * (1.1 + randB * 0.55);
        break;
      case "grief":
        y = lerp(bounds.maxY + bounds.height * 0.12, bounds.minY + bounds.height * 0.2, randC);
        break;
      case "tension":
        radius = bounds.radius * (1.24 + randB * 0.92);
        break;
      case "guard":
        radius = bounds.radius * (1.3 + randB * 0.5);
        break;
      case "embrace":
        angle = randA * Math.PI * 2;
        radius = bounds.radius * (1.22 + randB * 0.42);
        y = lerp(bounds.minY - bounds.height * 0.02, bounds.maxY + bounds.height * 0.04, randC);
        break;
      default:
        break;
    }

    return {
      x: bounds.center.x + Math.cos(angle) * radius,
      y,
      z: bounds.center.z + Math.sin(angle) * radius,
    };
  }

  sampleDepositionTarget(bounds, profileKey, kind) {
    const armorPoint = this.sampleArmorSurfacePoint();
    if (armorPoint) return armorPoint;

    const angle = hash01(Math.random() * 97.17) * Math.PI * 2;
    const y = lerp(bounds.minY, bounds.maxY, Math.random());
    const radius = kind === "glow" ? bounds.radius * 0.36 : bounds.radius * 0.5;
    return {
      x: bounds.center.x + Math.cos(angle) * radius,
      y,
      z: bounds.center.z + Math.sin(angle) * radius,
    };
  }

  sampleArmorSurfacePoint() {
    const visible = [];
    for (const rec of this.meshes.values()) {
      if (!rec.group.visible) continue;
      const pos = rec.mesh.geometry?.attributes?.position;
      if (!pos || !pos.count) continue;
      visible.push(rec);
    }
    if (!visible.length) return null;
    const rec = visible[Math.floor(Math.random() * visible.length)];
    const pos = rec.mesh.geometry.attributes.position;
    const idx = Math.floor(Math.random() * pos.count);
    const point = new THREE.Vector3(pos.getX(idx), pos.getY(idx), pos.getZ(idx));
    rec.mesh.localToWorld(point);
    return { x: point.x, y: point.y, z: point.z };
  }

  updateDepositionEffect(now, dt) {
    if (!this.deposition.active) return;
    const profile = DEPOSITION_PROFILES[this.deposition.resolvedKey] || DEPOSITION_PROFILES.guard;
    const palette = this.deposition.palette || buildDepositionPalette(profile);
    const bounds = this.getDepositionBounds();
    if (!bounds) return;

    const elapsed = Math.max(0, (now - this.deposition.startedAtMs) / 1000);
    const progress = clamp(elapsed / Math.max(this.deposition.durationSec, 0.1), 0, 1);
    this.deposition.progress = progress;

    this.applyDepositionFxRig(bounds, profile, palette, progress, dt);
    updateDepositionParticleSystem(
      this.depositionFx.shellParticles,
      bounds,
      progress,
      dt,
      this.deposition.resolvedKey,
      profile,
      palette,
      false
    );
    updateDepositionParticleSystem(
      this.depositionFx.glowParticles,
      bounds,
      progress,
      dt,
      this.deposition.resolvedKey,
      profile,
      palette,
      true
    );
    this.applyDepositionToArmor(bounds, profile, palette, progress);

    if (progress >= 1) {
      this.finishDepositionMock();
    }
  }

  applyDepositionFxRig(bounds, profile, palette, progress, dt) {
    const fx = this.depositionFx;
    const radius = Math.max(bounds.radius * 0.72, 0.35);
    const height = Math.max(bounds.height * 1.05, 1.2);
    const pulse = 0.82 + 0.18 * Math.sin(progress * Math.PI * (2.5 + profile.ringSpeed));
    const scanY = -height * 0.48 + progress * height * 0.96;
    const aura = palette.aura;
    const color = palette.ringPrimary;
    const highlight = palette.ringAccent;
    const glow = palette.core;
    const center = bounds.center;

    fx.group.visible = true;
    fx.group.position.set(0, 0, 0);

    fx.aura.material.color.copy(aura);
    fx.aura.material.opacity = profile.auraOpacity * (0.55 + 0.45 * Math.sin(progress * Math.PI));
    fx.aura.scale.set(radius * 1.35 * pulse, height, radius * 1.35 * pulse);
    fx.aura.position.copy(center);

    fx.auraWire.material.color.copy(highlight);
    fx.auraWire.material.opacity = 0.2 + 0.35 * (1 - Math.abs(progress - 0.55) * 1.25);
    fx.auraWire.scale.copy(fx.aura.scale);
    fx.auraWire.position.copy(center);

    fx.ringLower.material.color.copy(color);
    fx.ringLower.material.opacity = 0.4 + 0.32 * (1 - progress);
    fx.ringLower.position.set(center.x, center.y + scanY, center.z);
    fx.ringLower.scale.setScalar(radius * (0.85 + 0.15 * pulse));

    fx.ringUpper.material.color.copy(highlight);
    fx.ringUpper.material.opacity = 0.18 + 0.3 * smoothstep(0.12, 0.72, progress);
    fx.ringUpper.position.set(center.x, center.y + scanY - 0.12 * height, center.z);
    fx.ringUpper.scale.setScalar(radius * (0.65 + 0.2 * (1 - progress)));

    fx.core.material.color.copy(glow);
    fx.core.material.opacity = 0.14 + 0.35 * Math.exp(-Math.pow((progress - 0.58) / 0.22, 2));
    fx.core.scale.setScalar(radius * (0.34 + 0.28 * Math.sin(progress * Math.PI)));
    fx.core.position.copy(center);
  }

  applyDepositionToArmor(bounds, profile, palette, progress) {
    const color = palette.ringPrimary;
    const glow = palette.core;
    const center = bounds.center;

    for (const rec of this.meshes.values()) {
      if (!rec.group.visible) continue;
      const material = rec.mesh.material;
      const phase = computeDepositionPhase(rec.group.position, center, bounds, this.deposition.resolvedKey);
      const reveal = smoothstep(phase - 0.1, phase + 0.16, progress);
      const shimmer = 1 - clamp(Math.abs(progress - phase) / 0.16, 0, 1);
      const shimmerPow = shimmer * shimmer;
      const opacity = clamp(0.02 + reveal * 1.08, 0.02, 1);

      material.transparent = opacity < 0.999 || progress < 1;
      material.opacity = opacity;
      material.metalness = clamp(0.18 + reveal * 0.7, 0.18, 0.9);
      material.roughness = clamp(0.78 - reveal * 0.44, 0.22, 0.78);
      material.emissive.copy(glow).multiplyScalar(0.18 + shimmerPow * 1.85);
      material.emissiveIntensity = 0.22 + shimmerPow * 0.95;
      material.needsUpdate = true;

      if (!this.useTextures) {
        material.color.copy(color).lerp(new THREE.Color(partColor(rec.partName)), 0.25 + reveal * 0.75);
      }

      rec.outline.visible = true;
      rec.outline.material.opacity = clamp(0.08 + shimmerPow * 0.75 + reveal * 0.15, 0.08, 0.95);
      rec.outline.material.color.copy(glow);

      if (rec.lastTransform) {
        const overshoot = 1 + shimmerPow * 0.1;
        rec.group.scale.set(
          rec.lastTransform.scale_x * overshoot,
          rec.lastTransform.scale_y * overshoot,
          rec.lastTransform.scale_z * overshoot
        );
      }
    }
  }

  setVrmVisible(enabled) {
    this.vrm.visible = Boolean(enabled);
    if (this.vrm.skeleton) this.vrm.skeleton.visible = this.vrm.visible;
    this.updateVrmButton();
    this.updateMetaPanel();
    this.setLegend();
  }

  setArmorVisible(enabled) {
    this.armorVisible = Boolean(enabled);
    this.root.visible = this.armorVisible;
    for (const rec of this.meshes.values()) {
      if (rec.renderGroup) rec.renderGroup.visible = this.armorVisible && rec.group.visible;
      if (rec.fitGroup) rec.fitGroup.visible = this.armorVisible && this.showFitShell && rec.group.visible;
    }
    this.syncFitShellOverlay();
    this.updateArmorButton();
    this.updateMetaPanel();
    this.setLegend();
  }

  setVrmIdleEnabled(enabled) {
    this.vrm.idleEnabled = Boolean(enabled);
    this.updateVrmIdleButton();
    if (!this.vrm.idleEnabled) {
      this.applyVrmIdlePose(0, true);
      if (this.frames.length) {
        this.applyFrame(this.frameIndex);
      }
    }
    this.updateMetaPanel();
    this.setLegend();
  }

  fitCameraToVrm() {
    if (!this.vrm.model) return;
    const box = new THREE.Box3().setFromObject(this.vrm.model);
    if (box.isEmpty()) return;
    const sphere = box.getBoundingSphere(new THREE.Sphere());
    const radius = Math.max(sphere.radius, 0.35);
    const distance = Math.max(radius * 2.8, 1.45);
    this.controls.target.copy(sphere.center);
    this.camera.position.copy(sphere.center).add(new THREE.Vector3(0, radius * 0.15, distance));
    this.updateCameraRange(distance);
    this.controls.update();
  }

  setVrmAttachMode(mode) {
    this.vrm.attachMode = normalizeVrmAttachMode(mode);
    this.updateVrmAttachButton();
    this.updateGizmoButtons();
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    this.updateMetaPanel();
    this.updateTransformGizmo();
    this.setLegend();
  }

  cycleVrmAttachMode() {
    this.setVrmAttachMode(nextVrmAttachMode(this.vrm.attachMode));
  }

  clearVrmModel() {
    this.clearSurfaceFirstDemo();
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
    this.vrm.source = null;
    this.vrm.boneCount = 0;
    this.vrm.bodyInference = null;
    this.vrm.bodyTrackingFrame = null;
    this.vrm.idleTimeSec = 0;
    this.vrm.hasRestPose = false;
    this.vrm.missingAnchorParts = [];
    this.vrm.resolvedAnchors = {};
    this.vrm.liveRig = [];
    this.vrm.liveRigReady = false;
    this.vrm.liveDriven = false;
    this.vrm.error = "";
    this.surfaceFirst.forceTrackingSource = "auto";
    this.updateVrmStatus("VRM: cleared");
    this.updateSurfaceFirstStatus("Surface-first: VRM 未読込");
    this.updateMetaPanel();
    this.updateVrmAttachButton();
    this.populateVrmAnchorEditor();
    this.renderFitAssistPanel();
    this.updateTransformGizmo();
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

  resolveVrmBoneForPart(partName, module, primaryBone) {
    const tried = new Set();
    const slot = normalizeAttachmentSlot(partName, module);
    const candidates = [primaryBone, ...(VRM_PART_BONE_FALLBACKS[slot] || [])];
    for (const candidate of candidates) {
      const boneKey = String(candidate || "").trim();
      if (!boneKey) continue;
      const norm = normalizeBoneName(boneKey);
      if (tried.has(norm)) continue;
      tried.add(norm);
      const bone = this.resolveVrmBone(boneKey);
      if (bone) return bone;
    }
    return null;
  }

  buildVrmLiveRig() {
    if (!this.vrm.model) {
      this.vrm.liveRig = [];
      this.vrm.liveRigReady = false;
      this.vrm.liveDriven = false;
      return;
    }
    this.vrm.model.updateMatrixWorld(true);
    const liveRig = [];
    for (const spec of VRM_LIVE_BONE_SPECS) {
      const bone = this.resolveVrmBone(spec.bone);
      if (!bone) continue;

      let restDirWorld = null;
      const childBone = this.resolveVrmBone(spec.childBone);
      if (childBone) {
        const bonePos = bone.getWorldPosition(new THREE.Vector3());
        const childPos = childBone.getWorldPosition(new THREE.Vector3());
        const delta = childPos.sub(bonePos);
        if (delta.lengthSq() > 1e-8) {
          restDirWorld = delta.normalize();
        }
      }

      if (!restDirWorld) {
        restDirWorld = new THREE.Vector3(0, -1, 0).applyQuaternion(
          bone.getWorldQuaternion(new THREE.Quaternion())
        );
      }

      const parentQuat = bone.parent
        ? bone.parent.getWorldQuaternion(new THREE.Quaternion())
        : new THREE.Quaternion();
      const restDirParent = restDirWorld
        .clone()
        .applyQuaternion(parentQuat.clone().invert())
        .normalize();
      liveRig.push({
        spec,
        bone,
        bindQuat: bone.quaternion.clone(),
        restDirParent,
        smoothGain: toNumberOr(spec.smoothGain, 12),
      });
    }
    this.vrm.liveRig = liveRig;
    this.vrm.liveRigReady = liveRig.length > 0;
    this.vrm.liveDriven = false;
  }

  updateVrmFromLiveJoints(joints, dtSec) {
    if (!this.vrm.model || !this.vrm.liveRigReady || !Array.isArray(this.vrm.liveRig)) {
      this.vrm.liveDriven = false;
      return;
    }
    if (!joints || typeof joints !== "object") {
      this.vrm.liveDriven = false;
      return;
    }

    let updates = 0;
    for (const entry of this.vrm.liveRig) {
      const start = joints[entry.spec.startJoint];
      const end = joints[entry.spec.endJoint];
      if (!start || !end) continue;

      const targetWorld = new THREE.Vector3(
        end.x - start.x,
        end.y - start.y,
        toNumberOr(end.z, 0.22) - toNumberOr(start.z, 0.22)
      );
      if (!Number.isFinite(targetWorld.lengthSq()) || targetWorld.lengthSq() < 1e-8) continue;
      targetWorld.normalize();

      const parentQuat = entry.bone.parent
        ? entry.bone.parent.getWorldQuaternion(new THREE.Quaternion())
        : new THREE.Quaternion();
      const targetParent = targetWorld.applyQuaternion(parentQuat.clone().invert()).normalize();
      if (!Number.isFinite(targetParent.x)) continue;

      const deltaQuat = new THREE.Quaternion().setFromUnitVectors(entry.restDirParent, targetParent);
      const desiredQuat = deltaQuat.multiply(entry.bindQuat.clone());
      const alpha = clamp(toNumberOr(dtSec, 0.016) * entry.smoothGain, 0, 1);
      entry.bone.quaternion.slerp(desiredQuat, alpha);
      updates += 1;
    }

    this.vrm.model.updateMatrixWorld(true);
    this.vrm.liveDriven = updates > 0;
  }

  getVrmBoneWorldPosition(name) {
    const bone = this.resolveVrmBone(name);
    if (!bone) return null;
    return bone.getWorldPosition(new THREE.Vector3());
  }

  measurePartWorldSize(group) {
    if (!group) return new THREE.Vector3(0.22, 0.22, 0.22);
    const box = new THREE.Box3().setFromObject(group);
    if (box.isEmpty()) return new THREE.Vector3(0.22, 0.22, 0.22);
    const size = box.getSize(new THREE.Vector3());
    return new THREE.Vector3(
      Math.max(size.x, 0.02),
      Math.max(size.y, 0.02),
      Math.max(size.z, 0.02)
    );
  }

  rotateVrmBoneChainTowardWorldDir(boneName, childBoneName, targetDirArr, strength = 1) {
    const bone = this.resolveVrmBone(boneName);
    const childBone = this.resolveVrmBone(childBoneName);
    if (!bone || !childBone) return false;

    this.vrm.model?.updateMatrixWorld(true);
    const bonePos = bone.getWorldPosition(new THREE.Vector3());
    const childPos = childBone.getWorldPosition(new THREE.Vector3());
    const currentDir = childPos.sub(bonePos);
    if (!Number.isFinite(currentDir.lengthSq()) || currentDir.lengthSq() < 1e-8) return false;
    currentDir.normalize();

    const targetDir = new THREE.Vector3(
      toNumberOr(targetDirArr?.[0], 0),
      toNumberOr(targetDirArr?.[1], 0),
      toNumberOr(targetDirArr?.[2], 0)
    );
    if (!Number.isFinite(targetDir.lengthSq()) || targetDir.lengthSq() < 1e-8) return false;
    targetDir.normalize();

    const deltaWorld = new THREE.Quaternion().setFromUnitVectors(currentDir, targetDir);
    const parentWorldQuat = bone.parent
      ? bone.parent.getWorldQuaternion(new THREE.Quaternion())
      : new THREE.Quaternion();
    const boneWorldQuat = bone.getWorldQuaternion(new THREE.Quaternion());
    const desiredWorldQuat = deltaWorld.multiply(boneWorldQuat);
    const desiredLocalQuat = parentWorldQuat.clone().invert().multiply(desiredWorldQuat);
    bone.quaternion.slerp(desiredLocalQuat, clamp(strength, 0, 1));
    bone.updateMatrixWorld(true);
    return true;
  }

  applyVrmTPose({ silent = false } = {}) {
    if (!this.vrm.model) {
      if (!silent) this.setStatus("Tポーズ適用に失敗しました。VRM が未読込です。", true);
      return false;
    }

    let applied = 0;
    for (const chain of VRM_TPOSE_BONE_CHAINS) {
      const ok = this.rotateVrmBoneChainTowardWorldDir(
        chain.bone,
        chain.childBone,
        chain.target,
        chain.strength
      );
      if (ok) applied += 1;
    }

    this.vrm.model.updateMatrixWorld(true);
    this.buildVrmLiveRig();
    this.vrm.liveDriven = false;
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    } else {
      const vrmPoseSegments = this.buildSegmentsFromCurrentVrmPose();
      this.applySegments(vrmPoseSegments, null);
    }
    this.updateMetaPanel();
    this.setLegend();
    if (!silent) {
      this.setStatus(`VRM に Tポーズを適用しました。(${applied}/${VRM_TPOSE_BONE_CHAINS.length})`);
    }
    return applied > 0;
  }

  estimateVrmBodyMetrics() {
    return this.buildVrmBoneInferenceSnapshot()?.metrics || null;
  }

  estimateAutoFitTargetSize(partName, metrics, fallbackSize) {
    const fb = fallbackSize || new THREE.Vector3(0.22, 0.22, 0.22);
    const target = fb.clone();
    const shoulderWidth = Math.max(metrics.shoulderWidth || 0.44, 0.2);
    const hipWidth = Math.max(metrics.hipWidth || shoulderWidth * 0.75, 0.16);
    const torsoLen = Math.max(metrics.torsoLen || 0.62, 0.2);
    const headLen = Math.max(metrics.headLen || torsoLen * 0.3, 0.12);
    const upperArmLen = Math.max(metrics.upperArmLen || 0.36, 0.12);
    const foreArmLen = Math.max(metrics.foreArmLen || upperArmLen * 0.92, 0.1);
    const thighLen = Math.max(metrics.thighLen || 0.5, 0.14);
    const shinLen = Math.max(metrics.shinLen || thighLen * 0.92, 0.14);
    const handLen = Math.max(metrics.handLen || foreArmLen * 0.34, 0.06);
    const footLen = Math.max(metrics.footLen || shinLen * 0.4, 0.08);

    switch (partName) {
      case "helmet":
        target.set(headLen * 0.9, headLen * 1.0, headLen * 0.92);
        break;
      case "chest":
        target.set(shoulderWidth * 0.88, torsoLen * 0.44, (shoulderWidth + hipWidth) * 0.36);
        break;
      case "back":
        target.set(shoulderWidth * 0.84, torsoLen * 0.42, (shoulderWidth + hipWidth) * 0.32);
        break;
      case "waist":
        target.set(hipWidth * 0.95, torsoLen * 0.24, hipWidth * 0.58);
        break;
      case "left_shoulder":
      case "right_shoulder":
        target.set(upperArmLen * 0.26, upperArmLen * 0.26, upperArmLen * 0.26);
        break;
      case "left_upperarm":
      case "right_upperarm":
        target.set(upperArmLen * 0.22, upperArmLen * 0.94, upperArmLen * 0.22);
        break;
      case "left_forearm":
      case "right_forearm":
        target.set(foreArmLen * 0.2, foreArmLen * 0.98, foreArmLen * 0.2);
        break;
      case "left_hand":
      case "right_hand":
        target.set(handLen * 0.62, handLen * 0.48, handLen * 0.82);
        break;
      case "left_thigh":
      case "right_thigh":
        target.set(thighLen * 0.24, thighLen * 1.0, thighLen * 0.24);
        break;
      case "left_shin":
      case "right_shin":
        target.set(shinLen * 0.2, shinLen * 1.0, shinLen * 0.2);
        break;
      case "left_boot":
      case "right_boot":
        target.set(footLen * 0.44, footLen * 0.28, footLen * 0.95);
        break;
      default:
        break;
    }
    return target;
  }

  autoFitArmorToCurrentVrm({ forceTPose = true, silent = false } = {}) {
    if (!this.vrm.model) {
      if (!silent) this.setStatus("自動フィットに失敗しました。VRM が未読込です。", true);
      return null;
    }
    if (!this.suitspec || this.meshes.size === 0) {
      if (!silent) this.setStatus("自動フィットに失敗しました。SuitSpec または body-fit が未読込です。", true);
      return null;
    }

    try {
      const result = fitArmorToVrm({
        vrmModel: this.vrm.model,
        meshes: this.getFitEngineMeshes(),
        suitspec: this.suitspec,
        options: {
          forceTPose,
          resolveBone: (boneName) => this.resolveVrmBone(boneName),
          refinePasses: 2,
          renderMeshes: this.getRenderEngineMeshes(),
        },
      });
      this.decorateWearableSummary(result.summary);
      result.wearableSummary = result.summary;
      this.applyAutoFitResult(result);
      if (!silent) {
        this.setStatus(formatAutoFitSummaryJa(result.summary), !result.summary?.canSave);
      }
      return result;
    } catch (err) {
      if (!silent) {
        this.setStatus(`自動フィットに失敗しました: ${String(err?.message || err || "unknown")}`, true);
      }
      return null;
    }
  }

  evaluateCurrentFitAgainstVrm({ forceTPose = true, silent = false } = {}) {
    if (!this.vrm.model) {
      if (!silent) this.setStatus("フィット診断に失敗しました。VRM が未読込です。", true);
      return null;
    }
    if (!this.suitspec || this.meshes.size === 0) {
      if (!silent) this.setStatus("フィット診断に失敗しました。SuitSpec または body-fit が未読込です。", true);
      return null;
    }

    try {
      const result = evaluateArmorFitToVrm({
        vrmModel: this.vrm.model,
        meshes: this.getFitEngineMeshes(),
        suitspec: this.suitspec,
        options: {
          forceTPose,
          resolveBone: (boneName) => this.resolveVrmBone(boneName),
          renderMeshes: this.getRenderEngineMeshes(),
        },
      });
      this.autoFitSummary = this.decorateWearableSummary(result.summary || null);
      this.fitAssistDirty = false;
      this.updateMetaPanel();
      this.renderFitAssistPanel();
      this.setLegend();
      if (!silent) {
        this.setStatus(formatAutoFitSummaryJa(result.summary), !result.summary?.canSave);
      }
      return result;
    } catch (err) {
      if (!silent) {
        this.setStatus(`フィット診断に失敗しました: ${String(err?.message || err || "unknown")}`, true);
      }
      return null;
    }
  }

  applyAutoFitResult(result) {
    if (!result || !this.suitspec) return false;
    applyAutoFitResultToSuitSpec(this.suitspec, result);
    for (const [partName, rec] of this.meshes.entries()) {
      const module = this.suitspec.modules?.[partName];
      if (!module) continue;
      rec.config = getModuleVisualConfig(partName, module);
    }
    this.autoFitSummary = result.summary || null;
    this.decorateWearableSummary(this.autoFitSummary);
    this.fitAssistDirty = false;
    this.vrm.model?.updateMatrixWorld(true);
    this.buildVrmLiveRig();
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    } else {
      const vrmPoseSegments = this.buildSegmentsFromCurrentVrmPose();
      this.applySegments(vrmPoseSegments, null);
    }
    this.updateMetaPanel();
    this.populateFitEditor();
    this.renderFitAssistPanel();
    this.setLegend();
    return true;
  }

  async autoFitAndSaveCurrentVrm({ forceTPose = true } = {}) {
    const result = this.autoFitArmorToCurrentVrm({ forceTPose, silent: true });
    if (!result) return false;
    if (!result.summary?.canSave) {
      this.setStatus(formatAutoFitSummaryJa(result.summary), true);
      return false;
    }
    await this.saveSuitspecFit({ requireAutoFitGate: true });
    this.setStatus(`自動フィットして保存しました。${formatAutoFitSummaryJa(result.summary)}`);
    return true;
  }

  calibrateVrmAnchorsFromCurrentPose({
    partNames = null,
    overrideExisting = false,
    silent = false,
  } = {}) {
    if (!this.vrm.model || !this.suitspec || this.meshes.size === 0) {
      if (!silent) this.setStatus("VRMアンカー自動補正をスキップしました。VRM または SuitSpec が不足しています。", true);
      return 0;
    }
    this.vrm.model.updateMatrixWorld(true);
    this.root.updateMatrixWorld(true);

    const modules = this.suitspec.modules || {};
    const targetParts = Array.isArray(partNames) && partNames.length ? new Set(partNames) : null;
    let updated = 0;

    for (const [partName, rec] of this.meshes.entries()) {
      if (!rec?.group?.visible) continue;
      if (targetParts && !targetParts.has(partName)) continue;
      const module = modules[partName];
      if (!module || !module.enabled) continue;
      if (!overrideExisting && module.vrm_anchor && typeof module.vrm_anchor === "object") continue;

      const effective = effectiveVrmAnchorFor(partName, module);
      const bone = this.resolveVrmBoneForPart(partName, module, effective.bone);
      if (!bone) continue;

      const bodyPos = rec.group.getWorldPosition(new THREE.Vector3());
      const bodyQuat = rec.group.getWorldQuaternion(new THREE.Quaternion());
      const bonePos = bone.getWorldPosition(new THREE.Vector3());
      const boneQuat = bone.getWorldQuaternion(new THREE.Quaternion());
      const invBone = boneQuat.clone().invert();

      const localOffset = bodyPos.sub(bonePos).applyQuaternion(invBone);
      const localQuat = invBone.multiply(bodyQuat).normalize();
      const euler = new THREE.Euler().setFromQuaternion(localQuat, "XYZ");
      const rotationDeg = [
        round3(THREE.MathUtils.radToDeg(euler.x)),
        round3(THREE.MathUtils.radToDeg(euler.y)),
        round3(THREE.MathUtils.radToDeg(euler.z)),
      ];

      module.vrm_anchor = {
        bone: String(effective.bone || "chest"),
        offset: [round3(localOffset.x), round3(localOffset.y), round3(localOffset.z)],
        rotation: rotationDeg,
        scale: normalizeVec3(effective.scale, [1, 1, 1]),
      };
      updated += 1;
    }

    if (updated > 0) {
      for (const [partName, rec] of this.meshes.entries()) {
        const module = modules[partName];
        if (!module) continue;
        rec.config = getModuleVisualConfig(partName, module);
      }
      this.populateVrmAnchorEditor();
      this.updateMetaPanel();
      this.setLegend();
    }

    if (!silent) {
      this.setStatus(`VRMアンカーを自動補正しました。${updated}部位を更新。`);
    }
    return updated;
  }

  applyArmorToVrmBones() {
    const attachMode = normalizeVrmAttachMode(this.vrm.attachMode);
    if (attachMode === VRM_ATTACH_MODES.BODY || !this.vrm.model) {
      this.vrm.missingAnchorParts = [];
      this.vrm.resolvedAnchors = {};
      return;
    }
    const modules = this.suitspec?.modules || {};
    const missing = [];
    const resolved = {};
    for (const [partName, rec] of this.meshes.entries()) {
      if (!rec?.group?.visible) continue;
      const module = modules[partName];
      const anchor = effectiveVrmAnchorFor(partName, module);
      const bone = this.resolveVrmBoneForPart(partName, module, anchor.bone);
      if (!bone) {
        missing.push(partName);
        if (attachMode === VRM_ATTACH_MODES.VRM) {
          rec.group.visible = false;
          if (rec.renderGroup) rec.renderGroup.visible = false;
          if (rec.fitGroup) rec.fitGroup.visible = false;
        }
        continue;
      }
      if (attachMode === VRM_ATTACH_MODES.VRM) {
        rec.group.visible = true;
        if (rec.renderGroup) rec.renderGroup.visible = this.armorVisible;
        if (rec.fitGroup) rec.fitGroup.visible = this.showFitShell;
      }
      resolved[partName] = bone.name || anchor.bone;

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
      const baseScale = rec.lastTransform
        ? [
            Number(rec.lastTransform.scale_x || 1),
            Number(rec.lastTransform.scale_y || 1),
            Number(rec.lastTransform.scale_z || 1),
          ]
        : [1, 1, 1];
      rec.group.scale.set(
        Math.max(0.01, baseScale[0] * Number(anchor.scale[0] || 1)),
        Math.max(0.01, baseScale[1] * Number(anchor.scale[1] || 1)),
        Math.max(0.01, baseScale[2] * Number(anchor.scale[2] || 1))
      );
    }
    this.vrm.missingAnchorParts = missing;
    this.vrm.resolvedAnchors = resolved;
    this.syncFitShellOverlay();
  }

  captureVrmRestPose() {
    if (!this.vrm.model) {
      this.vrm.hasRestPose = false;
      return;
    }
    this.vrm.restPosition.copy(this.vrm.model.position);
    this.vrm.restQuaternion.copy(this.vrm.model.quaternion);
    this.vrm.hasRestPose = true;
  }

  applyVrmIdlePose(dtSec, forceRest = false) {
    if (!this.vrm.model || !this.vrm.hasRestPose) return;
    if (forceRest || !this.vrm.idleEnabled) {
      this.vrm.model.position.copy(this.vrm.restPosition);
      this.vrm.model.quaternion.copy(this.vrm.restQuaternion);
      this.vrm.model.updateMatrixWorld(true);
      return;
    }
    const dt = Math.max(0, Number(dtSec || 0));
    this.vrm.idleTimeSec += dt * this.vrm.idleSpeed;
    const t = this.vrm.idleTimeSec;
    const amount = clamp(this.vrm.idleAmount, 0, 1);
    const rise = Math.sin(t * 1.7) * (0.012 * amount);
    const yaw = Math.sin(t * 0.9 + 0.4) * (0.02 * amount);
    const roll = Math.sin(t * 1.2) * (0.028 * amount);
    const offset = new THREE.Vector3(0, rise, 0);
    const qIdle = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, yaw, roll, "XYZ"));
    this.vrm.model.position.copy(this.vrm.restPosition).add(offset);
    this.vrm.model.quaternion.copy(this.vrm.restQuaternion).multiply(qIdle);
    this.vrm.model.updateMatrixWorld(true);
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
    if (this.vrm.model === model) {
      this.captureVrmRestPose();
    }
  }

  async loadVrmModel(path, { silent = false } = {}) {
    const rawPath = String(path || "").trim();
    if (!rawPath) {
      this.clearVrmModel();
      if (!silent) this.setStatus("VRM パスが空です。", true);
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
    const { model, vrmInstance, source } = await loadVrmScene(normalizePath(rawPath), {
      onProgress: (progress) => {
        if (progress?.ratio == null) return;
        const pct = Math.round(clamp(progress.ratio, 0, 1) * 100);
        this.updateVrmStatus(`VRM loading: ${rawPath} (${pct}%)`);
      },
    });
    if (!model) {
      throw new Error(`Invalid VRM/GLTF scene: ${rawPath}`);
    }

    this.clearVrmModel();
    this.alignVrmModelToArmor(model);
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
    this.vrm.source = source;
    this.vrm.boneMap = this.buildBoneMap(model);
    this.vrm.path = rawPath;
    this.vrm.boneCount = this.countModelBones(model);
    this.buildVrmLiveRig();
    this.buildVrmBoneInferenceSnapshot();
    this.refreshSurfaceFirstDemo({ force: this.needsSurfaceFirstSnapshot() });
    this.captureVrmRestPose();
    this.applyVrmIdlePose(0, true);
    this.vrm.error = "";
    this.updateVrmButton();
    this.updateVrmAttachButton();
    this.populateVrmAnchorEditor();
    this.updateVrmStatus(
      `VRM loaded: ${rawPath} (bones=${this.vrm.boneCount}, liveRig=${this.vrm.liveRig.length}, source=${source})`
    );
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    this.updateMetaPanel();
    this.renderFitAssistPanel();
    this.updateTransformGizmo();
    this.setLegend();
    if (!silent) {
      if (source === "gltf-fallback") {
        this.setStatus(`VRM 拡張を読めなかったため GLTF として読み込みました: ${rawPath}`, true);
      } else {
        this.setStatus(`VRM を読み込みました: ${rawPath}`);
      }
    }
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
      const targetA = recA?.renderGroup?.visible ? recA.renderGroup : recA?.group;
      const targetB = recB?.renderGroup?.visible ? recB.renderGroup : recB?.group;
      if (!recA || !recB || !targetA?.visible || !targetB?.visible) {
        mesh.visible = false;
        continue;
      }

      const boxA = new THREE.Box3().setFromObject(targetA);
      const boxB = new THREE.Box3().setFromObject(targetB);
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
    this.liveJointTrackers.clear();
    this.lastLiveSegments = null;
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

  smoothLiveJoints(rawJoints, dtSec) {
    const alpha = clamp(toNumberOr(dtSec, 0.016) * LIVE_POSE_OPTIONS.smoothGain, 0.08, 0.55);
    const maxJump = LIVE_POSE_OPTIONS.maxJointJump;
    const holdFrames = LIVE_POSE_OPTIONS.holdFramesOnMissing;
    const present = new Set();
    const out = {};

    for (const [name, raw] of Object.entries(rawJoints || {})) {
      if (!raw || typeof raw !== "object") continue;
      if (!Number.isFinite(raw.x) || !Number.isFinite(raw.y)) continue;
      present.add(name);
      const next = new THREE.Vector3(
        toNumberOr(raw.x, 0),
        toNumberOr(raw.y, 0),
        toNumberOr(raw.z, 0.22)
      );
      const tracker = this.liveJointTrackers.get(name);
      if (!tracker) {
        this.liveJointTrackers.set(name, { vec: next.clone(), missing: 0 });
        out[name] = { x: next.x, y: next.y, z: next.z };
        continue;
      }

      const prev = tracker.vec;
      const dist = prev.distanceTo(next);
      if (Number.isFinite(dist) && dist > maxJump) {
        const t = maxJump / dist;
        next.copy(prev).lerp(next, clamp(t, 0.1, 1));
      }

      prev.lerp(next, alpha);
      tracker.missing = 0;
      out[name] = { x: prev.x, y: prev.y, z: prev.z };
    }

    for (const [name, tracker] of this.liveJointTrackers.entries()) {
      if (present.has(name)) continue;
      tracker.missing += 1;
      if (tracker.missing <= holdFrames) {
        const v = tracker.vec;
        out[name] = { x: v.x, y: v.y, z: v.z };
      } else {
        this.liveJointTrackers.delete(name);
      }
    }

    return out;
  }

  completeUpperBodyLiveJoints(joints) {
    return this.buildLiveBoneInferenceSnapshot(joints).joints;
  }

  buildSegmentPoseFromEndpoints(spec, start, end, prev, lerp, lengthScale = 1) {
    if (!start || !end) {
      return { ...prev };
    }
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const dz = toNumberOr(end.z, spec.z) - toNumberOr(start.z, spec.z);
    const length = Math.hypot(dx, dy, dz) * lengthScale;
    const midpointX = (start.x + end.x) * 0.5;
    const midpointY = (start.y + end.y) * 0.5;
    const midpointZ = (toNumberOr(start.z, spec.z) + toNumberOr(end.z, spec.z)) * 0.5;
    const angle = Math.atan2(dy, dx);
    const rotationZ = angle - Math.PI / 2;
    const radius = clamp(length * spec.radiusFactor, spec.radiusMin, spec.radiusMax);

    return {
      position_x: prev.position_x + (midpointX - prev.position_x) * lerp,
      position_y: prev.position_y + (midpointY - prev.position_y) * lerp,
      position_z: prev.position_z + (midpointZ - prev.position_z) * lerp,
      rotation_z: prev.rotation_z + (rotationZ - prev.rotation_z) * lerp,
      scale_x: prev.scale_x + (radius - prev.scale_x) * lerp,
      scale_y: prev.scale_y + (length - prev.scale_y) * lerp,
      scale_z: prev.scale_z + (radius - prev.scale_z) * lerp,
    };
  }

  buildSegmentsFromJointMap(joints, { followerMap = null, dtSec = 0.016, lerpOverride = null, lengthScale = 1 } = {}) {
    const segments = {};
    for (const spec of LIVE_SEGMENT_SPECS) {
      const prev =
        (followerMap && followerMap.get(spec.name)) ||
        DEFAULT_SEGMENT_POSE[spec.name] || {
          position_x: 0,
          position_y: 0,
          position_z: spec.z,
          rotation_z: 0,
          scale_x: 1,
          scale_y: 1,
          scale_z: 1,
        };
      const start = joints?.[spec.startJoint] || null;
      const end = joints?.[spec.endJoint] || null;
      const lerp =
        lerpOverride == null ? clamp(dtSec * spec.smoothGain, 0, 1) : clamp(lerpOverride, 0, 1);
      const next = this.buildSegmentPoseFromEndpoints(spec, start, end, prev, lerp, lengthScale);
      if (followerMap) {
        followerMap.set(spec.name, next);
      }
      segments[spec.name] = next;
    }
    return segments;
  }

  buildSegmentsFromCurrentVrmPose() {
    const inference = this.buildVrmBoneInferenceSnapshot();
    return this.buildSegmentsFromJointMap(inference?.joints || {}, {
      followerMap: null,
      lerpOverride: 1,
      lengthScale: 1,
    });
  }

  buildLiveSegmentsFromLandmarks(landmarks, dtSec) {
    const rawJoints = extractPoseJointsWorld(landmarks, {
      ...LIVE_POSE_OPTIONS,
      mirror: this.getEffectiveLiveMirror(),
    });
    const rawInference = this.buildLiveBoneInferenceSnapshot(rawJoints);
    const smoothedJoints = this.smoothLiveJoints(rawJoints, dtSec);
    const smoothedInference = this.buildLiveBoneInferenceSnapshot(smoothedJoints);
    const joints = smoothedInference.joints;
    const reliableJointCount = rawInference.reliableJointCount;
    const hasMeasuredTorsoAnchors = rawInference.hasMeasuredTorsoAnchors;
    const hasSolvedTorsoAnchors = smoothedInference.hasSolvedTorsoAnchors;
    const hasUpperBodyAnchors = rawInference.hasUpperBodyAnchors;
    const fitReadiness = smoothedInference.fitReadiness || "insufficient";
    this.live.poseReliableJoints = reliableJointCount;
    this.live.bodyInference = smoothedInference;
    this.live.bodyTrackingFrame = createBodyTrackingFrameFromInference(smoothedInference, {
      source: "webcam",
      timestampMs: performance.now(),
      metadata: {
        model: this.live.poseModel || null,
        rawQuality: rawInference.qualityLabel || null,
        smoothed: true,
      },
      raw: {
        reliableJointCount,
        hasMeasuredTorsoAnchors,
        hasSolvedTorsoAnchors,
      },
    });
    this.lastLiveJoints = joints;

    const canUseUpperBodyFallback =
      hasUpperBodyAnchors && reliableJointCount >= LIVE_POSE_OPTIONS.minUpperBodyJointCount;
    if (
      ((fitReadiness !== "fit-ready" && fitReadiness !== "upper-body-only") && !canUseUpperBodyFallback) ||
      (!hasSolvedTorsoAnchors && !canUseUpperBodyFallback) ||
      reliableJointCount < LIVE_POSE_OPTIONS.minUpperBodyJointCount
    ) {
      this.live.poseQuality = "low";
      this.vrm.liveDriven = false;
      this.refreshLiveTrackingStatus();
      if (this.lastLiveSegments) {
        return { ...this.lastLiveSegments };
      }
      return {};
    }

    this.live.poseQuality =
      fitReadiness === "upper-body-only"
        ? "upper"
        : smoothedInference.qualityLabel ||
          (hasMeasuredTorsoAnchors ? (reliableJointCount >= 10 ? "good" : "fair") : "upper");
    const bodyScale = estimateLiveBodyScale(joints);
    if (!Number.isFinite(this.live.bodyScaleRef) || this.live.bodyScaleRef <= 0) {
      this.live.bodyScaleRef = bodyScale > 0 ? bodyScale : 1;
    } else if (bodyScale > 0) {
      const ema = clamp(toNumberOr(dtSec, 0.016) * LIVE_POSE_OPTIONS.bodyScaleEmaGain, 0.01, 0.08);
      this.live.bodyScaleRef += (bodyScale - this.live.bodyScaleRef) * ema;
    }
    const bodyScaleCompRaw =
      bodyScale > 0 && this.live.bodyScaleRef > 0 ? this.live.bodyScaleRef / bodyScale : 1;
    const bodyScaleComp = clamp(
      bodyScaleCompRaw,
      LIVE_POSE_OPTIONS.bodyScaleCompRange[0],
      LIVE_POSE_OPTIONS.bodyScaleCompRange[1]
    );
    const segments = this.buildSegmentsFromJointMap(joints, {
      followerMap: this.liveFollowers,
      dtSec,
      lengthScale: bodyScaleComp,
    });

    this.updateVrmFromLiveJoints(joints, dtSec);
    this.lastLiveSegments = { ...segments };
    this.refreshLiveTrackingStatus();
    return segments;
  }

  applySegments(segments, frame = null) {
    const segs = withFallbackSegments(segments || {});
    for (const [name, rec] of this.meshes.entries()) {
      const t = resolveTransform(name, rec.config, segs);
      if (!t) {
        rec.group.visible = false;
        if (rec.renderGroup) rec.renderGroup.visible = false;
        if (rec.fitGroup) rec.fitGroup.visible = false;
        continue;
      }
      rec.lastTransform = { ...t };
      rec.group.visible = true;
      rec.group.position.set(t.position_x, t.position_y, t.position_z);
      rec.group.rotation.set(0, 0, t.rotation_z);
      rec.group.scale.set(t.scale_x, t.scale_y, t.scale_z);
      if (rec.renderGroup) rec.renderGroup.visible = this.armorVisible;
      if (rec.fitGroup) rec.fitGroup.visible = this.showFitShell;
    }
    const sphere = this.computeVisibleBounds();
    if (sphere) {
      this.modelCenter.copy(sphere.center);
      this.modelRadius = Math.max(sphere.radius, 0.35);
    }
    if (this.vrm.model && !this.playing && !this.live.active) {
      this.alignVrmModelToArmor(this.vrm.model);
    }
    if (!this.gizmo.dragging) {
      this.applyArmorToVrmBones();
    }
    this.syncFitShellOverlay();
    this.fitStats = this.calculateFitStats();
    this.updateBridges();
    this.updateMetaPanel();
    this.updateTransformGizmo();
    this.setLegend(frame);
  }

  async startLiveWebcam() {
    if (this.live.active) {
      this.updateLiveStatus("ライブ: すでに起動中");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      this.updateLiveStatus("ライブ: カメラ API を利用できません", true);
      this.setStatus("このブラウザ環境では Webカメラを利用できません。", true);
      return;
    }

    try {
      this.setStatus("Webカメラとライブ推定を開始しています...");
      this.updateLiveStatus("ライブ: Webカメラを起動中...");

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 960 }, height: { ideal: 540 } },
        audio: false,
      });
      const video = PANEL.liveVideo || document.createElement("video");
      this.updateLiveVideoPresentation();
      video.srcObject = stream;
      await video.play();
      this.live = {
        ...createDefaultLiveState(),
        active: true,
        video,
        stream,
      };
      this.updateLiveVideoPresentation();
      this.updateLiveStatus("ライブ: 推定モジュールを開始中...");
      await this.startLivePipelineModules();
      this.resetLiveFollowers();
      this.lastLiveJoints = null;
      this.vrm.liveDriven = false;
      this.playing = false;
      this.updatePlaybackButton();
      this.updateLiveStatus("ライブ: Webカメラ動作中");
      this.setStatus(
        `Live webcam started (${this.listLivePipelineModules().join(", ")}, model=${this.live.poseModel || "-"})`
      );
      this.updateMetaPanel();
    } catch (err) {
      this.stopLive({ silent: true });
      const detail = this.formatLivePipelineError(err?.message || err || "unknown");
      this.livePipelineError = detail;
      this.updateLiveStatus("Live: start failed", true);
      this.setStatus(`ライブ入力の開始に失敗しました: ${detail}`, true);
      this.updateMetaPanel();
    }
  }

  stopLive({ silent = false } = {}) {
    const live = this.live;
    this.stopLivePipelineModules();
    if (live.stream) {
      for (const track of live.stream.getTracks()) {
        track.stop();
      }
    }
    if (live.video) {
      live.video.pause?.();
      live.video.srcObject = null;
    }

    this.live = createDefaultLiveState();
    this.lastLiveJoints = null;
    this.liveJointTrackers.clear();
    this.lastLiveSegments = null;
    this.vrm.liveDriven = false;
    this.updateLiveStatus("ライブ: 停止中");
    this.updateMetaPanel();
    if (this.frames.length) {
      this.applyFrame(this.frameIndex);
    }
    if (!silent) {
      this.setStatus("ライブ入力を停止しました。");
    }
  }

  updateLivePose(nowMs) {
    if (!this.live.active || !this.live.video) return;
    const video = this.live.video;
    if (video.readyState < 2) return;
    if (video.currentTime === this.live.lastVideoTime) return;
    this.live.lastVideoTime = video.currentTime;

    const dtSec = clamp((nowMs - this.live.lastNowMs) / 1000, 0.001, 0.1);
    this.live.lastNowMs = nowMs;
    this.live.fps = dtSec > 0 ? 1 / dtSec : 0;

    try {
      this.updateLivePipelineModules(nowMs, dtSec, video);
      this.livePipelineError = "";
    } catch (err) {
      const detail = this.formatLivePipelineError(err?.message || err || "unknown");
      this.livePipelineError = detail;
      this.updateLiveStatus("Live: pipeline error", true);
      this.setStatus(`Live detect failed: ${detail}`, true);
      this.updateMetaPanel();
    }
  }

  calculateFitStats() {
    this.root.updateMatrixWorld(true);
    const boxes = new Map();
    for (const [name, rec] of this.meshes.entries()) {
      const target = rec.renderGroup?.visible ? rec.renderGroup : rec.group;
      if (!target?.visible) continue;
      boxes.set(name, new THREE.Box3().setFromObject(target));
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
    this.populateVrmAnchorEditor(parts);
    this.renderFitAssistPanel();
  }

  populateVrmAnchorEditor(parts = null) {
    if (!PANEL.vrmEditPart || !PANEL.vrmEditBone) return;
    const editableParts = Array.isArray(parts) ? parts : this.listEditableParts();
    const prevPart = PANEL.vrmEditPart.value;
    PANEL.vrmEditPart.innerHTML = "";
    for (const name of editableParts) {
      const op = document.createElement("option");
      op.value = name;
      op.textContent = name;
      PANEL.vrmEditPart.appendChild(op);
    }

    const bones = this.listVrmBoneOptions();
    const prevBone = PANEL.vrmEditBone.value;
    PANEL.vrmEditBone.innerHTML = "";
    for (const bone of bones) {
      const op = document.createElement("option");
      op.value = bone;
      op.textContent = bone;
      PANEL.vrmEditBone.appendChild(op);
    }

    if (!editableParts.length) return;
    PANEL.vrmEditPart.value = editableParts.includes(prevPart) ? prevPart : editableParts[0];
    if (bones.length) {
      PANEL.vrmEditBone.value = bones.includes(prevBone) ? prevBone : bones[0];
    }
    this.loadVrmAnchorEditorForPart(PANEL.vrmEditPart.value);
  }

  listVrmBoneOptions() {
    const base = Object.keys(VRM_BONE_ALIASES);
    const fromModel = [];
    for (const [, bone] of this.vrm.boneMap || []) {
      if (bone?.name) fromModel.push(String(bone.name));
    }
    const merged = [...base, ...fromModel];
    return Array.from(new Set(merged)).sort((a, b) => a.localeCompare(b));
  }

  updateVrmAnchorPreview(anchor, slotName = null) {
    if (!PANEL.vrmEditHint) return;
    const slotText = slotName ? `slot=${slotName} ` : "";
    PANEL.vrmEditHint.textContent = `${slotText}bone=${anchor.bone} offset=[${anchor.offset
      .map((v) => round3(v))
      .join(", ")}] rot=[${anchor.rotation.map((v) => round3(v)).join(", ")}] scale=[${anchor.scale
      .map((v) => round3(v))
      .join(", ")}]`;
  }

  loadVrmAnchorEditorForPart(partName) {
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;
    const slot = normalizeAttachmentSlot(partName, module);
    const anchor = effectiveVrmAnchorFor(partName, module);
    if (PANEL.vrmEditBone) {
      const exists = Array.from(PANEL.vrmEditBone.options || []).some((op) => op.value === anchor.bone);
      if (!exists) {
        const op = document.createElement("option");
        op.value = anchor.bone;
        op.textContent = anchor.bone;
        PANEL.vrmEditBone.appendChild(op);
      }
      PANEL.vrmEditBone.value = anchor.bone;
    }
    if (PANEL.vrmEditOffsetX) PANEL.vrmEditOffsetX.value = String(round3(anchor.offset[0]));
    if (PANEL.vrmEditOffsetY) PANEL.vrmEditOffsetY.value = String(round3(anchor.offset[1]));
    if (PANEL.vrmEditOffsetZ) PANEL.vrmEditOffsetZ.value = String(round3(anchor.offset[2]));
    if (PANEL.vrmEditRotX) PANEL.vrmEditRotX.value = String(round3(anchor.rotation[0]));
    if (PANEL.vrmEditRotY) PANEL.vrmEditRotY.value = String(round3(anchor.rotation[1]));
    if (PANEL.vrmEditRotZ) PANEL.vrmEditRotZ.value = String(round3(anchor.rotation[2]));
    if (PANEL.vrmEditScaleX) PANEL.vrmEditScaleX.value = String(round3(anchor.scale[0]));
    if (PANEL.vrmEditScaleY) PANEL.vrmEditScaleY.value = String(round3(anchor.scale[1]));
    if (PANEL.vrmEditScaleZ) PANEL.vrmEditScaleZ.value = String(round3(anchor.scale[2]));
    this.updateVrmAnchorPreview(anchor, slot);
  }

  applyVrmAnchorEditorToCurrentPart({ silent = false } = {}) {
    const partName = PANEL.vrmEditPart?.value;
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;

    const effective = effectiveVrmAnchorFor(partName, module);
    const slot = normalizeAttachmentSlot(partName, module);
    module.attachment_slot = slot;
    module.vrm_anchor = {
      bone: String(PANEL.vrmEditBone?.value || effective.bone || "chest"),
      offset: normalizeVec3(
        [PANEL.vrmEditOffsetX?.value, PANEL.vrmEditOffsetY?.value, PANEL.vrmEditOffsetZ?.value],
        effective.offset
      ),
      rotation: normalizeVec3(
        [PANEL.vrmEditRotX?.value, PANEL.vrmEditRotY?.value, PANEL.vrmEditRotZ?.value],
        effective.rotation
      ),
      scale: normalizeVec3(
        [PANEL.vrmEditScaleX?.value, PANEL.vrmEditScaleY?.value, PANEL.vrmEditScaleZ?.value],
        effective.scale
      ).map((v) => Math.max(0.01, Number(v || 1))),
    };

    this.applyFrame(this.frameIndex);
    this.updateMetaPanel();
    this.updateVrmAnchorPreview(module.vrm_anchor, slot);
    if (!silent) {
      this.setStatus(`Applied VRM anchor: ${partName}`);
    }
  }

  resetVrmAnchorForCurrentPart() {
    const partName = PANEL.vrmEditPart?.value;
    if (!partName) return;
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;
    delete module.vrm_anchor;
    this.loadVrmAnchorEditorForPart(partName);
    this.applyFrame(this.frameIndex);
    this.updateMetaPanel();
    this.setStatus(`Reset VRM anchor: ${partName}`);
  }

  loadFitEditorForPart(partName) {
    const modules = this.suitspec?.modules || {};
    const module = modules[partName];
    if (!module) return;
    if (PANEL.fitPart && PANEL.fitPart.value !== partName) {
      PANEL.fitPart.value = partName;
    }
    const fit = getModuleVisualConfig(partName, module);
    PANEL.fitScaleX.value = String(round3(fit.scale[0]));
    PANEL.fitScaleY.value = String(round3(fit.scale[1]));
    PANEL.fitScaleZ.value = String(round3(fit.scale[2]));
    PANEL.fitOffsetY.value = String(round3(fit.offsetY));
    PANEL.fitZOffset.value = String(round3(fit.zOffset || 0));
    this.updateFitSelectionVisuals();
    this.renderFitAssistPanel();
    this.updateTransformGizmo();
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
    this.fitAssistDirty = true;
    this.renderFitAssistPanel();
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
    this.fitAssistDirty = true;
    this.applyFrame(this.frameIndex);
    this.updateMetaPanel();
    this.renderFitAssistPanel();
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
    this.fitAssistDirty = true;
    this.applyFrame(this.frameIndex);
    this.loadFitEditorForPart(partName);
    this.updateMetaPanel();
    this.renderFitAssistPanel();
    this.setStatus(`Reset fit: ${partName}`);
  }

  async saveSuitspecFit({ requireAutoFitGate = false } = {}) {
    const path = this.loadedSuitspecPath || PANEL.suitspecPath.value;
    if (!path || !this.suitspec) {
      this.setStatus("保存に失敗しました。SuitSpec が未読込です。", true);
      return;
    }
    if (!this.vrm.model) {
      this.setStatus("保存に失敗しました。VRM 基準体を読み込んでから保存してください。", true);
      return;
    }
    const evaluation = this.evaluateCurrentFitAgainstVrm({ forceTPose: true, silent: true });
    if (!evaluation) return;
    if (!evaluation.summary?.canSave) {
      this.setStatus(formatAutoFitSummaryJa(evaluation.summary), true);
      return;
    }
    applyAutoFitResultToSuitSpec(this.suitspec, evaluation);
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
      this.setStatus(`SuitSpec を保存しました: ${data.path || path} | ${formatAutoFitSummaryJa(evaluation.summary)}`);
    } catch (err) {
      const detail = String(err?.message || err || "unknown");
      if (detail.includes("404")) {
        this.setStatus("保存 API が見つかりません。serve-dashboard 経由で開いてください。", true);
        return;
      }
      this.setStatus(`保存に失敗しました: ${detail}`, true);
    }
  }

  setLegend(frame = null) {
    const activeFrame = frame || this.frames[this.frameIndex] || null;
    const frameText = this.frames.length ? `${this.frameIndex + 1}/${this.frames.length}` : "0/0";
    const equipped = activeFrame ? Boolean(activeFrame.equipped) : Boolean(this.sim?.equipped);
    const fitScore = ((this.fitStats?.score || 0) * 100).toFixed(1);
    const fitGap = (this.fitStats?.meanGap || 0).toFixed(3);
    const fitPen = (this.fitStats?.meanPenetration || 0).toFixed(3);
    const liveViewText =
      this.liveViewMode === "auto"
        ? `auto=>${this.getEffectiveLiveViewLabel()}`
        : this.getEffectiveLiveViewLabel();
    const depositionLabel = DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey || "auto";
    const lines = [
      "陦ｨ遉ｺ繧ｬ繧､繝・ 繝代・繝・ｽ｢迥ｶ / 繝・け繧ｹ繝√Ε / 謗･邯壹ヶ繝ｪ繝・ず / VRM鬪ｨ邨・∩",
      `Frame ${frameText} | Equipped: ${equipped ? "YES" : "NO"} | Speed x${this.speed.toFixed(2)}`,
      `Textures: ${this.useTextures ? "ON" : "OFF"} | Relief: ${this.reliefStrength.toFixed(2)} | Theme: ${
        this.darkTheme ? "Dark" : "Bright"
      }`,
      `Bridges: ${this.bridgeEnabled ? "ON" : "OFF"} | Visible: ${this.bridgeVisibleCount} | Thickness: ${this.bridgeThickness.toFixed(
        2
      )}`,
      `ArmorVisible: ${this.armorVisible ? "ON" : "OFF"} | VRM Idle: ${this.vrm.idleEnabled ? "ON" : "OFF"} x${this.vrm.idleSpeed.toFixed(
        2
      )}`,
      `AttachMode: ${VRM_ATTACH_MODE_LABELS[normalizeVrmAttachMode(this.vrm.attachMode)] || "Hybrid"}`,
      `VRM: ${this.vrm.path ? "ON" : "OFF"} | Source: ${this.vrm.source || "-"} | Humanoid: ${
        this.vrm.instance?.humanoid ? "YES" : "NO"
      } | Bones: ${this.vrm.boneCount || 0} | Visible: ${this.vrm.visible ? "ON" : "OFF"} | Missing: ${
        (this.vrm.missingAnchorParts || []).length
      } | LiveDrive: ${this.vrm.liveDriven ? "ON" : "OFF"}`,
      `Live: ${this.live.active ? "ON" : "OFF"} | FPS: ${(this.live?.fps || 0).toFixed(
        1
      )} | Pipeline: ${this.livePipelineActive ? "ON" : "OFF"} | Modules: ${
        this.listLivePipelineModules().join(", ") || "-"
      }`,
      `LiveView: ${liveViewText} | CameraPreset: ${this.cameraPreset}`,
      `PoseModel: ${this.live?.poseModel || "-"} | PoseQuality: ${this.live?.poseQuality || "idle"} | ReliableJoints: ${
        this.live?.poseReliableJoints || 0
      } | FitReady: ${this.live?.bodyInference?.fitReadiness || "-"}`,
      `VRM Inference: ${this.vrm.bodyInference?.qualityLabel || "-"} | FitReady: ${
        this.vrm.bodyInference?.fitReadiness || "-"
      }`,
      `SurfaceFirst: ${this.isSurfaceFirstVisible() ? "ON" : "OFF"} | Density: ${this.surfaceFirst.density} | ShellOffset: ${this.surfaceFirst.shellOffset.toFixed(
        3
      )} | SampleCount: ${this.surfaceFirst.summary?.sample_count || 0}`,
      `Deposition: ${this.deposition.active ? "PLAYING" : "IDLE"} | Profile: ${depositionLabel} | Progress: ${(
        (this.deposition.progress || 0) * 100
      ).toFixed(0)}% | Duration: ${this.deposition.durationSec.toFixed(1)}s`,
      `FitScore: ${fitScore} | Gap: ${fitGap} | Penetration: ${fitPen}`,
      `AutoFit: ${formatAutoFitSummary(this.autoFitSummary)}`,
      "Tip: Attach=Hybrid は VRM 骨と BodySim の中間、Attach=VRM は VRM 骨優先です。",
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
      const target = rec.renderGroup?.visible ? rec.renderGroup : rec.group;
      if (!target?.visible) continue;
      box.expandByObject(target);
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
    this.cameraPreset = ["front", "side", "back", "top", "pov"].includes(preset) ? preset : "front";
    const center = this.modelCenter.clone();
    const radius = Math.max(this.modelRadius, 0.35);
    const distance = Math.max(radius * 2.8, 1.45);
    const yBias = radius * 0.15;

    switch (this.cameraPreset) {
      case "front":
        this.camera.position.copy(center).add(new THREE.Vector3(0, yBias, distance));
        break;
      case "side":
        this.camera.position.copy(center).add(new THREE.Vector3(distance, radius * 0.08, 0));
        break;
      case "back":
        this.camera.position.copy(center).add(new THREE.Vector3(0, yBias, -distance));
        break;
      case "top":
        this.camera.position.copy(center).add(new THREE.Vector3(0.01, distance, 0.01));
        break;
      case "pov": {
        const headBone = this.resolveVrmBone("head") || this.resolveVrmBone("neck");
        const headPos =
          this.getVrmBoneWorldPosition("head") ||
          this.getVrmBoneWorldPosition("neck") ||
          center.clone().add(new THREE.Vector3(0, radius * 0.68, 0));
        const headQuat = headBone ? headBone.getWorldQuaternion(new THREE.Quaternion()) : null;
        const forward = new THREE.Vector3(0, 0, 1);
        const up = new THREE.Vector3(0, 1, 0);
        if (headQuat) {
          forward.applyQuaternion(headQuat).normalize();
          up.applyQuaternion(headQuat).normalize();
        }
        const eyePos = headPos
          .clone()
          .addScaledVector(up, Math.max(radius * 0.08, 0.04))
          .addScaledVector(forward, Math.max(radius * 0.04, 0.02));
        const target = headPos.clone().addScaledVector(forward, Math.max(radius * 0.9, 0.75));
        this.camera.position.copy(eyePos);
        this.controls.target.copy(target);
        this.updateCameraRange(Math.max(radius * 1.4, 0.95));
        this.updateLiveVideoPresentation();
        this.updateMetaPanel();
        this.setLegend();
        this.controls.update();
        return;
      }
      default:
        this.camera.position.copy(center).add(new THREE.Vector3(0, yBias, distance));
        break;
    }
    this.controls.target.copy(center);
    this.updateCameraRange(distance);
    this.updateLiveVideoPresentation();
    this.updateMetaPanel();
    this.setLegend();
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
      PANEL.btnTheme.textContent = "表示テーマ: ソフト";
    } else {
      this.scene.background = new THREE.Color(0xffffff);
      this.floor.material.color.setHex(0xffffff);
      this.floor.material.opacity = 0.94;
      for (const mat of gridMaterials) {
        mat.color.setHex(0xd6e1f2);
      }
      PANEL.btnTheme.textContent = "表示テーマ: 明";
    }

    for (const rec of this.meshes.values()) {
      rec.outline.material.color.setHex(outlineColor);
      if (rec.fitOutline?.material) rec.fitOutline.material.color.setHex(0x4f89ff);
    }
    this.updateFitSelectionVisuals();
    if (this.vrm.model && this.vrm.bodyInference && this.needsSurfaceFirstSnapshot()) {
      this.refreshSurfaceFirstDemo({ force: true });
      return;
    }
    this.syncFitShellOverlay();
    this.setLegend();
  }

  async load(suitspecPath, simPath) {
    if (this.live.active) {
      this.stopLive({ silent: true });
    }
    this.setStatus("JSON を読み込み中...");
    const [spec, sim] = await Promise.all([this.fetchJson(suitspecPath), this.fetchJson(simPath)]);
    this.suitspec = spec;
    this.sim = sim;
    this.autoFitSummary = null;
    this.fitAssistDirty = false;
    this.loadedSuitspecPath = suitspecPath;
    this.loadedSimPath = simPath;
    this.frames = Array.isArray(sim.frames) ? sim.frames : [];
    this.frameIndex = 0;
    this.playbackAccumSec = 0;
    const durationFromSpec = Number(spec?.effects?.deposition_seconds);
    if (PANEL.depositionDuration && Number.isFinite(durationFromSpec)) {
      PANEL.depositionDuration.value = String(clamp(durationFromSpec, 1.2, 6.0));
    }
    this.deposition.durationSec = clamp(
      Number(PANEL.depositionDuration?.value || durationFromSpec || DEFAULT_DEPOSITION_DURATION),
      1.2,
      6.0
    );
    this.deposition.resolvedKey = this.resolveDepositionProfileKey();
    this.deposition.palette = buildDepositionPalette(
      DEPOSITION_PROFILES[this.deposition.resolvedKey] || DEPOSITION_PROFILES.guard
    );
    this.updateDepositionStatus(
      `Deposition: ready (${DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey})`
    );
    await this.buildMeshes();
    PANEL.frameSlider.max = String(Math.max(0, this.frames.length - 1));
    PANEL.frameSlider.value = "0";
    this.applyFrame(0);
    const vrmPath = String(PANEL.vrmPath?.value || "").trim();
    if (vrmPath) {
      try {
        if (this.vrm.model && this.vrm.path === vrmPath) {
          this.alignVrmModelToArmor(this.vrm.model);
          this.updateVrmStatus(
            `VRM loaded: ${vrmPath} (bones=${this.vrm.boneCount}, liveRig=${this.vrm.liveRig.length})`
          );
        } else {
          await this.loadVrmModel(vrmPath, { silent: true });
        }
      } catch (error) {
        const detail = String(error?.message || error || "VRM load failed");
        this.vrm.error = detail;
        this.updateVrmStatus(`VRM load failed: ${detail}`, true);
      }
    } else {
      this.updateVrmStatus("VRM: 未読込");
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
    this.resetDepositionMock({ silent: true, keepStatus: true });
    this.clearBridges();
    for (const rec of this.meshes.values()) {
      this.root.remove(rec.group);
      disposeObjectResources(rec.surfaceFitOverlay);
      disposeObjectResources(rec.surfaceFitProxyGroup);
      rec.fitProxyMesh?.geometry?.dispose?.();
      rec.fitProxyMesh?.material?.dispose?.();
      rec.renderProxyMesh?.geometry?.dispose?.();
      rec.renderProxyMesh?.material?.dispose?.();
      rec.fitMesh.geometry.dispose();
      rec.fitMesh.material.dispose();
      rec.fitOutline.geometry.dispose();
      rec.fitOutline.material.dispose();
      rec.mesh.geometry.dispose();
      rec.mesh.material.dispose();
      rec.outline.geometry.dispose();
      rec.outline.material.dispose();
    }
    this.meshes.clear();
    this.renderMeshes.clear();
  }

  async buildMeshes() {
    this.clearMeshes();
    const modules = this.suitspec?.modules || {};
    for (const [name, module] of Object.entries(modules)) {
      if (!module?.enabled) continue;
      const config = getModuleVisualConfig(name, module);
      const assetPath = resolveMeshAssetPath(name, module);
      const fitGeometry = createWearableTemplateGeometry(name, config.shape);
      const renderGeometry = await loadModuleGeometry(name, config.shape, assetPath, GEOMETRY_MODES.ASSET);
      const record = createWearableRecord({
        partName: name,
        fitGeometry,
        renderGeometry,
        config,
        assetPath,
        texturePath: module.texture_path || null,
        darkTheme: this.darkTheme,
      });
      this.root.add(record.group);
      this.meshes.set(name, record);
      this.renderMeshes.set(name, record);
      if (record.texturePath) {
        record.texture = await loadTextureAsset(record.texturePath).catch(() => null);
      }
    }
    this.updateTextureMode();
    this.syncFitShellOverlay();
  }

  updateTextureMode(forceRelief = false) {
    const texturesActive = this.useTextures;
    if (PANEL.btnTexture) {
      PANEL.btnTexture.textContent = this.useTextures ? "テクスチャ: ON" : "テクスチャ: OFF";
      PANEL.btnTexture.classList.toggle("active", texturesActive);
    }
    for (const rec of this.meshes.values()) {
      rec.outline.visible = true;
      rec.outline.material.opacity = texturesActive ? 0.22 : 0.85;
      if (!texturesActive) {
        rec.mesh.material.map = null;
        rec.mesh.material.color.setHex(partColor(rec.partName));
        rec.mesh.material.needsUpdate = true;
        restoreBaseGeometry(rec.mesh);
        continue;
      }
      if (!rec.texturePath) continue;
      if (!rec.texture) continue;
      rec.mesh.material.map = rec.texture;
      rec.mesh.material.color.setHex(0xe7f0ff);
      rec.mesh.material.needsUpdate = true;
      if (forceRelief || !rec.reliefApplied) {
        applyReliefFromTexture(rec.mesh, rec.texture, this.reliefStrength);
        rec.reliefApplied = true;
      }
    }
    this.updateFitSelectionVisuals();
    if (this.vrm.model && this.vrm.bodyInference && this.needsSurfaceFirstSnapshot()) {
      this.refreshSurfaceFirstDemo({ force: true });
      return;
    }
    this.syncFitShellOverlay();
    this.setLegend();
  }

  updateGeometryButton() {
    if (!PANEL.btnGeometry) return;
    PANEL.btnGeometry.textContent = `Fitシェル: ${jaOnOff(this.showFitShell)}`;
    PANEL.btnGeometry.classList.toggle("active", this.showFitShell);
  }

  setGeometryMode(mode) {
    this.showFitShell = Boolean(mode);
    this.updateGeometryButton();
    this.syncFitShellOverlay();
    if (this.vrm.model && this.vrm.bodyInference && this.needsSurfaceFirstSnapshot()) {
      this.refreshSurfaceFirstDemo({ force: true });
    }
    this.updateMetaPanel();
    this.setLegend();
  }

  async rebuildGeometryPresentation() {
    if (!this.suitspec?.modules) {
      this.updateTextureMode();
      this.updateMetaPanel();
      return;
    }
    const currentIndex = this.frameIndex;
    await this.buildMeshes();
    if (this.live.active && this.lastLiveSegments) {
      this.applySegments(this.lastLiveSegments, this.frames[currentIndex] || null);
    } else if (this.frames.length) {
      this.applyFrame(clamp(currentIndex, 0, this.frames.length - 1));
    } else {
      this.applySegments({}, null);
    }
    if (this.vrm.model && normalizeVrmAttachMode(this.vrm.attachMode) !== VRM_ATTACH_MODES.BODY) {
      this.applyArmorToVrmBones();
    }
    this.updateTextureMode(true);
    this.syncFitShellOverlay();
    this.fitCameraToVisible();
    this.updateMetaPanel();
  }

  applyFrame(index) {
    if (!this.frames.length) return;
    const safeIndex = Math.max(0, Math.min(this.frames.length - 1, index));
    this.frameIndex = safeIndex;
    PANEL.frameSlider.value = String(safeIndex);
    const frame = this.frames[safeIndex];
    this.applySegments(frame.segments || {}, frame);
  }

  updateGizmoButtons() {
    if (PANEL.btnGizmoToggle) PANEL.btnGizmoToggle.textContent = `ギズモ: ${jaOnOff(this.gizmo.enabled)}`;
    if (PANEL.btnGizmoMove) PANEL.btnGizmoMove.classList.toggle("active", this.gizmo.mode === "translate");
    if (PANEL.btnGizmoScale) PANEL.btnGizmoScale.classList.toggle("active", this.gizmo.mode === "scale");
    if (PANEL.btnGizmoSpace) {
      PANEL.btnGizmoSpace.textContent = `座標: ${this.gizmo.space === "local" ? "ローカル" : "ワールド"}`;
      PANEL.btnGizmoSpace.classList.toggle("active", this.gizmo.space === "world");
    }
    if (PANEL.fitGizmoHint) {
      const target = this.getGizmoEditTargetMode() === "fit" ? "フィット" : "アンカー";
      const mode = this.gizmo.mode === "translate" ? "移動" : "拡縮";
      const attachMode = VRM_ATTACH_MODE_LABELS[normalizeVrmAttachMode(this.vrm.attachMode)] || "ハイブリッド";
      PANEL.fitGizmoHint.textContent = `選択中の部位を ${mode} ギズモで編集します。装着基準: ${attachMode} / 編集対象: ${target}`;
    }
  }

  renderFitAssistPanel() {
    if (!PANEL.fitAssistSummary || !PANEL.fitAssistCurrent || !PANEL.fitAssistList) return;

    const selectedPart = this.getSelectedFitPart();
    const summary = this.autoFitSummary;
    const items = this.buildFitAssistItems();

    if (!this.vrm.model) {
      PANEL.fitAssistSummary.textContent = "1. VRM読込  2. 自動フィット  3. 必要な部位だけ詳細調整  4. 再チェック  5. 保存";
    } else if (!summary) {
      PANEL.fitAssistSummary.textContent = "まだ診断していません。まず「自動フィット」または「再チェック」を実行してください。";
    } else if (this.fitAssistDirty) {
      PANEL.fitAssistSummary.textContent = "値を変更したので未再評価です。「再チェック」で最新の判定に更新してください。";
    } else if (summary.canSave) {
      PANEL.fitAssistSummary.textContent = "保存可能です。見た目に違和感がなければそのまま SuitSpec を保存できます。";
    } else {
      PANEL.fitAssistSummary.textContent = `要調整: ${items.length}部位 | ${formatAutoFitSummaryJa(summary)}`;
    }

    const current = items.find((item) => item.part === selectedPart) || null;
    if (!selectedPart) {
      PANEL.fitAssistCurrent.textContent = "現在の部位: 未選択";
    } else if (!current) {
      PANEL.fitAssistCurrent.textContent = `現在の部位: ${selectedPart}\nこの部位は大きな問題としては検出されていません。`;
    } else {
      const lines = [`現在の部位: ${current.part}`];
      if (current.score != null) {
        lines.push(`スコア: ${current.score.toFixed(1)}${current.critical ? " / 重要部位" : ""}`);
      }
      if (current.pairs.length) lines.push(`接続ペア: ${current.pairs.slice(0, 3).join(", ")}`);
      if (current.seams.length) lines.push(`継ぎ目: ${current.seams.slice(0, 3).join(", ")}`);
      if (current.surface.length) lines.push(`表面判定: ${current.surface.slice(0, 3).join(", ")}`);
      if (current.hero.length) lines.push(`張り出し: ${current.hero.slice(0, 3).join(", ")}`);
      if (current.render.length) lines.push(`表示殻: ${current.render.slice(0, 3).join(", ")}`);
      if (current.minScaleAxes.length) lines.push(`最小スケール固定: ${current.minScaleAxes.join(", ")}`);
      PANEL.fitAssistCurrent.textContent = lines.join("\n");
    }

    PANEL.fitAssistList.innerHTML = "";
    if (!items.length) {
      const empty = document.createElement("button");
      empty.type = "button";
      empty.className = "fit-assist-item empty";
      empty.disabled = true;
      empty.textContent = summary?.canSave
        ? "大きな問題はありません。必要なら見た目だけ確認して保存してください。"
        : "大きな問題候補は見つかりませんでした。再チェックして最新判定を確認してください。";
      PANEL.fitAssistList.appendChild(empty);
      return;
    }

    for (const item of items) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fit-assist-item";
      const blocking =
        item.seams.length ||
        item.surface.length ||
        item.hero.length ||
        item.render.length ||
        (item.critical && item.score != null && item.score < 58);
      if (blocking) button.classList.add("blocking");
      if (item.part === selectedPart) button.classList.add("active");

      const title = document.createElement("strong");
      title.textContent = item.score != null ? `${item.part} | スコア ${item.score.toFixed(1)}` : item.part;
      const detail = document.createElement("span");
      const detailParts = [];
      if (item.pairs.length) detailParts.push(`接続 ${item.pairs.slice(0, 2).join(", ")}`);
      if (item.seams.length) detailParts.push(`継ぎ目 ${item.seams.slice(0, 2).join(", ")}`);
      if (item.surface.length) detailParts.push(`表面 ${item.surface.slice(0, 2).join(", ")}`);
      if (item.hero.length) detailParts.push(`張り出し ${item.hero.slice(0, 2).join(", ")}`);
      if (item.render.length) detailParts.push(`表示 ${item.render.slice(0, 2).join(", ")}`);
      if (item.minScaleAxes.length) detailParts.push(`最小値 ${item.minScaleAxes.join(", ")}`);
      detail.textContent = detailParts.join(" | ") || "詳細なし";
      button.append(title, detail);
      button.onclick = () => this.selectFitPart(item.part, { focusCamera: true });
      PANEL.fitAssistList.appendChild(button);
    }
  }

  setLegend(frame = null) {
    if (!PANEL.legendText) return;
    const activeFrame = frame || this.frames[this.frameIndex] || null;
    const frameText = this.frames.length ? `${this.frameIndex + 1}/${this.frames.length}` : "0/0";
    const equipped = activeFrame ? Boolean(activeFrame.equipped) : Boolean(this.sim?.equipped);
    const fitScore = ((this.fitStats?.score || 0) * 100).toFixed(1);
    const fitGap = (this.fitStats?.meanGap || 0).toFixed(3);
    const fitPen = (this.fitStats?.meanPenetration || 0).toFixed(3);
    const liveViewText =
      this.liveViewMode === "auto"
        ? `自動 -> ${this.getEffectiveLiveViewLabel() === "mirror" ? "ミラー" : "ワールド"}`
        : this.getEffectiveLiveViewLabel() === "mirror"
          ? "ミラー"
          : "ワールド";
    const depositionLabel = DEPOSITION_PROFILES[this.deposition.resolvedKey]?.label || this.deposition.resolvedKey || "自動";
    const lines = [
      "body-fit の現在状態",
      `フレーム ${frameText} | 装着状態: ${equipped ? "装着済み" : "未装着"} | 再生速度 x${this.speed.toFixed(2)}`,
      `テクスチャ ${jaOnOff(this.useTextures)} | 凹凸 ${this.reliefStrength.toFixed(2)} | 表示テーマ ${this.darkTheme ? "ソフト" : "明"}`,
      `Fitシェル ${jaOnOff(this.showFitShell)} | 接続ブリッジ ${jaOnOff(this.bridgeEnabled)} | 表示数 ${this.bridgeVisibleCount} | 太さ ${this.bridgeThickness.toFixed(2)}`,
      `鎧表示 ${jaOnOff(this.armorVisible)} | 待機モーション ${jaOnOff(this.vrm.idleEnabled)} x${this.vrm.idleSpeed.toFixed(2)} | 装着基準 ${VRM_ATTACH_MODE_LABELS[normalizeVrmAttachMode(this.vrm.attachMode)] || "ハイブリッド"}`,
      `VRM ${this.vrm.path ? "読込済み" : "未読込"} | Source ${this.vrm.source || "-"} | Humanoid ${jaYesNo(Boolean(this.vrm.instance?.humanoid))} | Bones ${this.vrm.boneCount || 0} | 骨表示 ${jaOnOff(this.vrm.visible)}`,
      `ライブ入力 ${jaOnOff(this.live.active)} | FPS ${(this.live?.fps || 0).toFixed(1)} | パイプライン ${jaOnOff(this.livePipelineActive)} | 視点 ${liveViewText}`,
      `姿勢推定 ${this.live?.poseModel || "-"} | 品質 ${this.live?.poseQuality || "idle"} | 信頼関節 ${this.live?.poseReliableJoints || 0} | FitReady ${this.live?.bodyInference?.fitReadiness || "-"}`,
      `VRM推定 ${this.vrm.bodyInference?.qualityLabel || "-"} | FitReady ${this.vrm.bodyInference?.fitReadiness || "-"}`,
      `Surface-first ${jaOnOff(this.isSurfaceFirstVisible())} | 密度 ${this.surfaceFirst.density} | オフセット ${this.surfaceFirst.shellOffset.toFixed(3)} | 点数 ${this.surfaceFirst.summary?.sample_count || 0}`,
      `蒸着 ${this.deposition.active ? "再生中" : "待機中"} | プロファイル ${depositionLabel} | 進捗 ${(((this.deposition.progress || 0) * 100)).toFixed(0)}% | 秒数 ${this.deposition.durationSec.toFixed(1)}`,
      `フィットスコア ${fitScore} | Gap ${fitGap} | Penetration ${fitPen}`,
      `自動フィット判定: ${formatAutoFitSummaryJa(this.autoFitSummary)}`,
      this.uiLevel === UI_LEVELS.SIMPLE
        ? "操作モード: かんたん操作。通常は「VRM読込 -> 自動フィット -> 保存」で進めます。"
        : "操作モード: 詳細操作。部位調整・アンカー調整・PoC機能まで表示しています。",
    ];
    PANEL.legendText.innerHTML = lines.join("<br>");
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
    if (this.vrm.model) {
      this.applyVrmIdlePose(dt, false);
      if (!this.gizmo.dragging && normalizeVrmAttachMode(this.vrm.attachMode) !== VRM_ATTACH_MODES.BODY) {
        this.applyArmorToVrmBones();
      }
    }
    this.updateDepositionEffect(now, dt);
    this.syncSurfaceFirstDemo(now);

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

function computeGeometryBounds(geometry) {
  if (!geometry.boundingBox) geometry.computeBoundingBox();
  if (!geometry.boundingSphere) geometry.computeBoundingSphere();
  const box = geometry.boundingBox?.clone() || new THREE.Box3(new THREE.Vector3(-0.5, -0.5, -0.5), new THREE.Vector3(0.5, 0.5, 0.5));
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  return { box, size, center };
}

function scaledGeometryBox(box, scale) {
  return {
    min: new THREE.Vector3(box.min.x * scale[0], box.min.y * scale[1], box.min.z * scale[2]),
    max: new THREE.Vector3(box.max.x * scale[0], box.max.y * scale[1], box.max.z * scale[2]),
  };
}

function boxRefValue(box, axis, align) {
  if (align === "min") return box.min[axis];
  if (align === "max") return box.max[axis];
  return (box.min[axis] + box.max[axis]) * 0.5;
}

function deriveRenderBinding(partName, fitGeometry, renderGeometry) {
  const fitBounds = computeGeometryBounds(fitGeometry);
  const renderBounds = computeGeometryBounds(renderGeometry);
  const binding = renderBindingFor(partName);
  const scaleBias = normalizeVec3(binding?.scaleBias, [1, 1, 1]);
  const offsetBias = normalizeVec3(binding?.offsetBias, [0, 0, 0]);
  const scale = [
    round3(clamp((fitBounds.size.x / Math.max(renderBounds.size.x, 0.0001)) * scaleBias[0], 0.05, 4)),
    round3(clamp((fitBounds.size.y / Math.max(renderBounds.size.y, 0.0001)) * scaleBias[1], 0.05, 4)),
    round3(clamp((fitBounds.size.z / Math.max(renderBounds.size.z, 0.0001)) * scaleBias[2], 0.05, 4)),
  ];
  const scaledRender = scaledGeometryBox(renderBounds.box, scale);
  const offset = [0, 1, 2].map((index) => {
    const axis = index === 0 ? "x" : index === 1 ? "y" : "z";
    const align =
      axis === "x"
        ? "center"
        : axis === "y"
          ? binding?.alignY || "center"
          : binding?.alignZ || "center";
    return round3(boxRefValue(fitBounds.box, axis, align) - boxRefValue(scaledRender, axis, align) + toNumberOr(offsetBias[index], 0));
  });
  return {
    scale,
    offset,
    alignY: binding?.alignY || "center",
    alignZ: binding?.alignZ || "center",
    maxDeviation: normalizeVec3(binding?.maxDeviation, [0.22, 0.22, 0.22]),
  };
}

function applyRenderBindingToGroup(group, binding) {
  if (!group) return;
  group.position.set(binding.offset[0], binding.offset[1], binding.offset[2]);
  group.scale.set(binding.scale[0], binding.scale[1], binding.scale[2]);
  group.rotation.set(0, 0, 0);
}

function applyRenderBinding(record) {
  const binding = record.renderBinding || { scale: [1, 1, 1], offset: [0, 0, 0] };
  applyRenderBindingToGroup(record.renderGroup, binding);
  applyRenderBindingToGroup(record.renderProxyShell, binding);
}

function wrapUnit(value) {
  const next = Number(value) % 1;
  return next < 0 ? next + 1 : next;
}

function getTextureSampler(texture) {
  if (!texture?.image) return null;
  const cached = textureSamplerCache.get(texture);
  if (cached) return cached;
  const image = texture.image;
  const width = Number(image.width || image.videoWidth || 0);
  const height = Number(image.height || image.videoHeight || 0);
  if (!width || !height) return null;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;
  ctx.drawImage(image, 0, 0, width, height);
  const sampler = { canvas, ctx, width, height, flipY: texture.flipY !== false };
  textureSamplerCache.set(texture, sampler);
  return sampler;
}

function sampleTextureColor(texture, u, v, target = new THREE.Color(0xffffff)) {
  const sampler = getTextureSampler(texture);
  if (!sampler) return null;
  const uu = wrapUnit(u);
  const vv = sampler.flipY ? 1 - wrapUnit(v) : wrapUnit(v);
  const x = clamp(Math.round(uu * Math.max(0, sampler.width - 1)), 0, Math.max(0, sampler.width - 1));
  const y = clamp(Math.round(vv * Math.max(0, sampler.height - 1)), 0, Math.max(0, sampler.height - 1));
  const rgba = sampler.ctx.getImageData(x, y, 1, 1).data;
  target.setRGB(rgba[0] / 255, rgba[1] / 255, rgba[2] / 255);
  return target;
}

function getGeometryUvInfo(geometry) {
  if (!geometry) return null;
  const cached = geometryUvCache.get(geometry);
  if (cached) return cached;
  const position = geometry.getAttribute?.("position");
  const uv = geometry.getAttribute?.("uv");
  if (!position?.count || !uv?.count) return null;
  const info = { position, uv, count: Math.min(position.count, uv.count) };
  geometryUvCache.set(geometry, info);
  return info;
}

function nearestUvForLocalPoint(geometry, localPoint) {
  const info = getGeometryUvInfo(geometry);
  if (!info) return null;
  const { position, uv, count } = info;
  let bestIndex = -1;
  let bestDistance = Infinity;
  for (let index = 0; index < count; index += 1) {
    const dx = position.getX(index) - localPoint.x;
    const dy = position.getY(index) - localPoint.y;
    const dz = position.getZ(index) - localPoint.z;
    const distanceSq = dx * dx + dy * dy + dz * dz;
    if (distanceSq < bestDistance) {
      bestDistance = distanceSq;
      bestIndex = index;
    }
  }
  if (bestIndex < 0) return null;
  return {
    u: uv.getX(bestIndex),
    v: uv.getY(bestIndex),
  };
}

function sampleRecordTextureColorAtWorldPoint(record, worldPoint, fallbackHex = 0xe7f0ff) {
  const color = new THREE.Color(fallbackHex);
  if (!record?.texture || !record?.renderMesh?.geometry || !record.renderMesh.worldToLocal) {
    return color;
  }
  record.renderMesh.updateMatrixWorld(true);
  const localPoint = record.renderMesh.worldToLocal(worldPoint.clone());
  const uv = nearestUvForLocalPoint(record.renderMesh.geometry, localPoint);
  if (!uv) return color;
  return sampleTextureColor(record.texture, uv.u, uv.v, color) || color;
}

function normalizedSegmentT(point, start, end) {
  if (!point || !start || !end) return 0.5;
  const axis = new THREE.Vector3().subVectors(end, start);
  const lengthSq = axis.lengthSq();
  if (lengthSq < 1e-6) return 0.5;
  return clamp(new THREE.Vector3().subVectors(point, start).dot(axis) / lengthSq, 0, 1);
}

function torsoLocalPoint(point, proxy) {
  if (!point || !proxy?.center || !proxy?.axes) return null;
  const delta = point.clone().sub(proxy.center);
  return new THREE.Vector3(
    delta.dot(proxy.axes.x || new THREE.Vector3(1, 0, 0)),
    delta.dot(proxy.axes.y || new THREE.Vector3(0, 1, 0)),
    delta.dot(proxy.axes.z || new THREE.Vector3(0, 0, 1))
  );
}

function classifySurfaceNodeToPart(node, proxies = {}) {
  const binding = node?.binding || null;
  const point = node?.surfacePoint || node?.position || null;
  switch (binding?.region || node?.region) {
    case "head":
      return "helmet";
    case "torso": {
      const yNorm = Number(binding?.obb?.yNorm);
      const zNorm = Number(binding?.obb?.zNorm);
      const torso = proxies.torso;
      const local = (!Number.isFinite(yNorm) || !Number.isFinite(zNorm)) ? torsoLocalPoint(point, torso) : null;
      const half = torso?.halfSize || new THREE.Vector3(0.2, 0.3, 0.12);
      const resolvedYNorm = Number.isFinite(yNorm) ? yNorm : local ? local.y / Math.max(half.y, 0.001) : 0;
      const resolvedZNorm = Number.isFinite(zNorm) ? zNorm : local ? local.z / Math.max(half.z, 0.001) : 0;
      if (resolvedYNorm < -0.22) return "waist";
      if (resolvedZNorm < -0.08) return "back";
      return "chest";
    }
    case "left_upperarm": {
      const segmentT = Number(binding?.capsule?.t);
      const resolvedT = Number.isFinite(segmentT)
        ? segmentT
        : normalizedSegmentT(point, proxies.left_upperarm?.start, proxies.left_upperarm?.end);
      return resolvedT < 0.22 ? "left_shoulder" : "left_upperarm";
    }
    case "right_upperarm": {
      const segmentT = Number(binding?.capsule?.t);
      const resolvedT = Number.isFinite(segmentT)
        ? segmentT
        : normalizedSegmentT(point, proxies.right_upperarm?.start, proxies.right_upperarm?.end);
      return resolvedT < 0.22 ? "right_shoulder" : "right_upperarm";
    }
    case "left_forearm": {
      const segmentT = Number(binding?.capsule?.t);
      const resolvedT = Number.isFinite(segmentT)
        ? segmentT
        : normalizedSegmentT(point, proxies.left_forearm?.start, proxies.left_forearm?.end);
      return resolvedT > 0.8 ? "left_hand" : "left_forearm";
    }
    case "right_forearm": {
      const segmentT = Number(binding?.capsule?.t);
      const resolvedT = Number.isFinite(segmentT)
        ? segmentT
        : normalizedSegmentT(point, proxies.right_forearm?.start, proxies.right_forearm?.end);
      return resolvedT > 0.8 ? "right_hand" : "right_forearm";
    }
    case "left_thigh":
      return "left_thigh";
    case "right_thigh":
      return "right_thigh";
    case "left_shin":
      return "left_shin";
    case "right_shin":
      return "right_shin";
    case "left_foot":
      return "left_boot";
    case "right_foot":
      return "right_boot";
    default:
      return null;
  }
}

function disposeObjectResources(object) {
  object?.traverse?.((entry) => {
    entry.geometry?.dispose?.();
    const material = entry.material;
    if (Array.isArray(material)) {
      material.forEach((item) => item?.dispose?.());
    } else {
      material?.dispose?.();
    }
  });
}

function createWearableRecord({ partName, fitGeometry, renderGeometry, config, assetPath, texturePath, darkTheme }) {
  const fitMesh = createMeshFromGeometry(fitGeometry);
  fitMesh.material.color.setHex(0x76a8ff);
  fitMesh.material.transparent = true;
  fitMesh.material.opacity = 0.12;
  fitMesh.material.depthWrite = false;
  fitMesh.material.metalness = 0.08;
  fitMesh.material.roughness = 0.86;
  fitMesh.userData.partName = `${partName}:fit`;
  const fitOutline = createOutline(fitMesh, 0x4f89ff);
  fitOutline.material.opacity = 0.22;
  const fitGroup = new THREE.Group();
  fitGroup.name = `${partName}:fitShell`;
  fitGroup.add(fitMesh);
  fitGroup.add(fitOutline);
  fitGroup.visible = false;

  const fitProxyMesh = createMeshFromGeometry(fitGeometry.clone());
  fitProxyMesh.material.visible = false;
  const fitProxyGroup = new THREE.Group();
  fitProxyGroup.name = `${partName}:fitProxy`;
  fitProxyGroup.add(fitProxyMesh);

  const surfaceFitOverlay = new THREE.Group();
  surfaceFitOverlay.name = `${partName}:surfaceFitOverlay`;
  surfaceFitOverlay.visible = false;
  const surfaceFitProxyGroup = new THREE.Group();
  surfaceFitProxyGroup.name = `${partName}:surfaceFitProxy`;

  const renderMesh = createMeshFromGeometry(renderGeometry);
  renderMesh.material.color.setHex(partColor(partName));
  renderMesh.userData.partName = partName;
  const renderOutline = createOutline(renderMesh, darkTheme ? 0xffffff : 0x10223f);
  const renderGroup = new THREE.Group();
  renderGroup.name = `${partName}:renderShell`;
  renderGroup.add(renderMesh);
  renderGroup.add(renderOutline);

  const renderProxyMesh = createMeshFromGeometry(renderGeometry.clone());
  renderProxyMesh.material.visible = false;
  const renderProxyShell = new THREE.Group();
  renderProxyShell.name = `${partName}:renderProxyShell`;
  renderProxyShell.add(renderProxyMesh);
  const renderProxyRoot = new THREE.Group();
  renderProxyRoot.name = `${partName}:renderProxy`;
  renderProxyRoot.add(renderProxyShell);

  const group = new THREE.Group();
  group.name = partName;
  group.add(renderGroup);
  group.add(fitGroup);
  group.add(surfaceFitOverlay);

  const record = {
    partName,
    group,
    mesh: renderMesh,
    outline: renderOutline,
    fitMesh,
    fitOutline,
    fitGroup,
    fitProxyMesh,
    fitProxyGroup,
    surfaceFitOverlay,
    surfaceFitProxyGroup,
    renderGroup,
    renderMesh,
    renderOutline,
    renderProxyMesh,
    renderProxyShell,
    renderProxyRoot,
    renderBinding: deriveRenderBinding(partName, fitGeometry, renderGeometry),
    config,
    assetPath,
    geometryMode: "dual_shell",
    texturePath,
    texture: null,
    reliefApplied: false,
    lastTransform: null,
    surfaceFitNodeCount: 0,
  };
  applyRenderBinding(record);
  return record;
}

function resolveMeshAssetPath(partName, module) {
  const ref = String(module?.asset_ref || "").replace(/\\/g, "/").trim();
  if (ref.toLowerCase().endsWith(".mesh.json")) return ref;
  return `viewer/assets/meshes/${partName}.mesh.json`;
}

async function loadModuleGeometry(partName, fallbackShape, assetPath, geometryMode = GEOMETRY_MODES.TEMPLATE) {
  if (normalizeGeometryMode(geometryMode) === GEOMETRY_MODES.TEMPLATE) {
    return createWearableTemplateGeometry(partName, fallbackShape);
  }
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

async function loadTextureAsset(texturePath) {
  const key = normalizePath(texturePath);
  if (!key) return null;
  if (textureAssetCache.has(key)) {
    return textureAssetCache.get(key);
  }
  const pending = new Promise((resolve, reject) => {
    textureLoader.load(
      key,
      (tex) => {
        tex.colorSpace = THREE.SRGBColorSpace;
        tex.wrapS = THREE.RepeatWrapping;
        tex.wrapT = THREE.RepeatWrapping;
        resolve(tex);
      },
      undefined,
      (error) => reject(error || new Error(`Failed to load texture: ${key}`))
    );
  }).catch((error) => {
    textureAssetCache.delete(key);
    throw error;
  });
  textureAssetCache.set(key, pending);
  return pending;
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

function createDepositionFxRig() {
  const group = new THREE.Group();
  group.visible = false;
  const shellTexture = createSoftParticleTexture("#ffffff", 0.95);
  const glowTexture = createSoftParticleTexture("#ffffff", 0.82);

  const auraMaterial = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const aura = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 1, 40, 1, true), auraMaterial);

  const auraWire = new THREE.Mesh(
    new THREE.CylinderGeometry(1.02, 1.02, 1, 24, 1, true),
    new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0,
      wireframe: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );

  const ringLower = new THREE.Mesh(
    new THREE.TorusGeometry(1, 0.045, 10, 72),
    new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  ringLower.rotation.x = Math.PI / 2;

  const ringUpper = new THREE.Mesh(
    new THREE.TorusGeometry(1, 0.025, 10, 72),
    new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  ringUpper.rotation.x = Math.PI / 2;

  const core = new THREE.Mesh(
    new THREE.SphereGeometry(0.26, 24, 18),
    new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );

  group.add(aura);
  group.add(auraWire);
  group.add(ringLower);
  group.add(ringUpper);
  group.add(core);
  const shellParticles = createDepositionParticleSystem(720, 0.072, shellTexture, 0.88, {
    blending: THREE.NormalBlending,
  });
  const glowParticles = createDepositionParticleSystem(320, 0.132, glowTexture, 0.68, {
    blending: THREE.AdditiveBlending,
  });
  group.add(shellParticles.points);
  group.add(glowParticles.points);
  return { group, aura, auraWire, ringLower, ringUpper, core, shellParticles, glowParticles };
}

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function smoothstep(edge0, edge1, value) {
  if (edge0 === edge1) return value < edge0 ? 0 : 1;
  const t = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return t * t * (3 - 2 * t);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function hash01(value) {
  const s = Math.sin(value * 12.9898 + 78.233) * 43758.5453;
  return s - Math.floor(s);
}

function inverseLerp(a, b, value) {
  if (a === b) return 0;
  return clamp((value - a) / (b - a), 0, 1);
}

function hueFromHex(hex) {
  if (typeof hex !== "string" || !hex.trim()) return null;
  const color = new THREE.Color();
  try {
    color.set(hex.trim());
  } catch {
    return null;
  }
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  if (!Number.isFinite(hsl.h)) return null;
  return hsl.h * 360;
}

function computeDepositionPhase(position, center, bounds, profileKey) {
  const heightNorm = inverseLerp(bounds.minY, bounds.maxY, position.y);
  const radial = Math.hypot(position.x - center.x, position.z - center.z);
  const radialNorm = clamp(radial / Math.max(bounds.radius, 0.0001), 0, 1);
  const frontNorm = inverseLerp(bounds.minZ, bounds.maxZ, position.z);

  switch (profileKey) {
    case "uplift":
      return 0.08 + heightNorm * 0.76;
    case "drive":
      return 0.06 + (1 - frontNorm) * 0.44 + heightNorm * 0.3;
    case "grief":
      return 0.12 + (1 - heightNorm) * 0.72;
    case "tension":
      return 0.1 + heightNorm * 0.34 + radialNorm * 0.4 + Math.round(heightNorm * 4) * 0.03;
    case "guard":
      return 0.08 + (1 - radialNorm) * 0.72;
    case "embrace":
      return 0.08 + radialNorm * 0.66 + (1 - heightNorm) * 0.08;
    default:
      return 0.1 + heightNorm * 0.68;
  }
}

function buildDepositionPalette(profile) {
  const ringPrimary = normalizeDepositionColor(new THREE.Color(profile.shellColor), {
    minLightness: 0.52,
    maxLightness: 0.76,
    minSaturation: 0.62,
  });
  const ringAccent = normalizeDepositionColor(
    new THREE.Color(profile.highlightColor).lerp(new THREE.Color(profile.shellColor), 0.08),
    {
      minLightness: 0.72,
      maxLightness: 0.9,
      minSaturation: 0.34,
    }
  );
  const aura = normalizeDepositionColor(ringPrimary.clone().lerp(ringAccent, 0.22), {
    minLightness: 0.58,
    maxLightness: 0.82,
    minSaturation: 0.42,
  });
  const core = normalizeDepositionColor(new THREE.Color(profile.glowColor).lerp(ringAccent, 0.24), {
    minLightness: 0.82,
    maxLightness: 0.96,
    minSaturation: 0.2,
  });
  const particleShell = normalizeDepositionColor(ringPrimary.clone().lerp(ringAccent, 0.36), {
    minLightness: 0.64,
    maxLightness: 0.88,
    minSaturation: 0.5,
  });
  const particleHighlight = normalizeDepositionColor(ringAccent.clone().lerp(core, 0.14), {
    minLightness: 0.76,
    maxLightness: 0.93,
    minSaturation: 0.26,
  });
  const particleGlow = normalizeDepositionColor(core.clone().lerp(ringAccent, 0.2), {
    minLightness: 0.84,
    maxLightness: 0.98,
    minSaturation: 0.16,
  });
  return { ringPrimary, ringAccent, aura, core, particleShell, particleHighlight, particleGlow };
}

function normalizeDepositionColor(color, { minLightness = 0.58, maxLightness = 0.9, minSaturation = 0.35 } = {}) {
  const hsl = { h: 0, s: 0, l: 0 };
  color.getHSL(hsl);
  hsl.s = clamp(Math.max(hsl.s, minSaturation), 0, 1);
  hsl.l = clamp(hsl.l, minLightness, maxLightness);
  return new THREE.Color().setHSL(hsl.h, hsl.s, hsl.l);
}

function createSoftParticleTexture(color = "#ffffff", inner = 0.9) {
  const size = 128;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  const gradient = ctx.createRadialGradient(size / 2, size / 2, size * 0.06, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, color);
  gradient.addColorStop(Math.max(0.2, inner * 0.35), color);
  gradient.addColorStop(inner, "rgba(255,255,255,0.12)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.clearRect(0, 0, size, size);
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.needsUpdate = true;
  return tex;
}

function createDepositionParticleSystem(maxCount, size, map, opacity, { blending = THREE.AdditiveBlending } = {}) {
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(maxCount * 3);
  const colors = new Float32Array(maxCount * 3);
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geometry.setDrawRange(0, 0);
  const material = new THREE.PointsMaterial({
    size,
    map,
    transparent: true,
    opacity,
    depthWrite: false,
    vertexColors: true,
    blending,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(geometry, material);
  points.frustumCulled = false;
  points.renderOrder = 4;
  return {
    points,
    maxCount,
    count: 0,
    positions,
    colors,
    source: new Float32Array(maxCount * 3),
    target: new Float32Array(maxCount * 3),
    phase: new Float32Array(maxCount),
    swirl: new Float32Array(maxCount),
    lift: new Float32Array(maxCount),
    orbit: new Float32Array(maxCount),
    jitter: new Float32Array(maxCount),
  };
}

function seedDepositionParticleSystem(system, config, sourceFn, targetFn) {
  const count = Math.min(system.maxCount, Math.max(0, config.count || system.maxCount));
  system.count = count;
  system.points.geometry.setDrawRange(0, count);
  system.points.material.size = config.size || system.points.material.size;
  const shell = new THREE.Color(config.shellColor || 0xffffff);
  const highlight = new THREE.Color(config.highlightColor || 0xffffff);

  for (let i = 0; i < count; i++) {
    const src = sourceFn(i);
    const dst = targetFn(i);
    const base = i * 3;
    system.positions[base + 0] = src.x;
    system.positions[base + 1] = src.y;
    system.positions[base + 2] = src.z;
    system.source[base + 0] = src.x;
    system.source[base + 1] = src.y;
    system.source[base + 2] = src.z;
    system.target[base + 0] = dst.x;
    system.target[base + 1] = dst.y;
    system.target[base + 2] = dst.z;
    system.phase[i] = hash01(i * 0.73 + 0.91);
    system.swirl[i] = 0.4 + hash01(i * 1.97 + 0.17) * 1.6;
    system.lift[i] = -1 + hash01(i * 2.31 + 0.51) * 2;
    system.orbit[i] = hash01(i * 3.11 + 0.13) * Math.PI * 2;
    system.jitter[i] = 0.55 + hash01(i * 2.71 + 0.87) * 0.85;
    const mix = hash01(i * 1.17 + 0.21);
    const col = shell.clone().lerp(highlight, mix);
    system.colors[base + 0] = col.r;
    system.colors[base + 1] = col.g;
    system.colors[base + 2] = col.b;
  }

  for (let i = count; i < system.maxCount; i++) {
    const base = i * 3;
    system.positions[base + 0] = 9999;
    system.positions[base + 1] = 9999;
    system.positions[base + 2] = 9999;
  }

  system.points.geometry.attributes.position.needsUpdate = true;
  system.points.geometry.attributes.color.needsUpdate = true;
}

function updateDepositionParticleSystem(system, bounds, progress, dt, profileKey, profile, palette, isGlow = false) {
  if (!system || !system.count) return;
  const positions = system.positions;
  const source = system.source;
  const target = system.target;
  const profileColor = isGlow ? palette.particleGlow : palette.particleHighlight;
  const accentColor = isGlow ? palette.particleHighlight : palette.particleShell;
  const width = Math.max(bounds.width, 0.5);
  const height = Math.max(bounds.height, 1.0);

  for (let i = 0; i < system.count; i++) {
    const base = i * 3;
    const phase = system.phase[i];
    const enterWindow = isGlow ? 0.09 : 0.18;
    const reveal = smoothstep(phase - enterWindow, phase + (isGlow ? 0.11 : 0.2), progress);
    const trail = 1 - reveal;
    const sx = source[base + 0];
    const sy = source[base + 1];
    const sz = source[base + 2];
    const tx = target[base + 0];
    const ty = target[base + 1];
    const tz = target[base + 2];
    const angle = system.orbit[i] + progress * Math.PI * (1.5 + system.swirl[i] * 0.45);
    const swirlAmp = (isGlow ? 0.05 : 0.12) * bounds.radius * trail * system.jitter[i];
    const verticalAmp = (isGlow ? 0.04 : 0.09) * height * trail * system.lift[i];
    const profileOffset = depositionProfileVector(profileKey, tx, ty, tz, bounds, trail, i, isGlow);
    positions[base + 0] = lerp(sx, tx, reveal) + Math.cos(angle) * swirlAmp + profileOffset.x;
    positions[base + 1] = lerp(sy, ty, reveal) + Math.sin(progress * Math.PI * 2 + system.orbit[i]) * verticalAmp + profileOffset.y;
    positions[base + 2] = lerp(sz, tz, reveal) + Math.sin(angle) * swirlAmp + profileOffset.z;

    const mix = smoothstep(0.02, 0.88, reveal);
    const col = accentColor.clone().lerp(profileColor, mix);
    system.colors[base + 0] = col.r;
    system.colors[base + 1] = col.g;
    system.colors[base + 2] = col.b;
  }

  system.points.material.opacity = isGlow
    ? 0.1 + 0.6 * Math.sin(progress * Math.PI)
    : 0.12 + 0.78 * (1 - smoothstep(0.82, 1.0, progress));
  system.points.material.size = isGlow
    ? profile.glowSize * (0.9 + 0.55 * Math.sin(progress * Math.PI))
    : profile.shellSize * (0.92 + 0.3 * (1 - progress));
  system.points.geometry.attributes.position.needsUpdate = true;
  system.points.geometry.attributes.color.needsUpdate = true;
}

function depositionProfileVector(profileKey, tx, ty, tz, bounds, trail, index, isGlow) {
  const radial = Math.max(bounds.radius, 0.35);
  const hash = hash01(index * 4.17 + 0.37);
  switch (profileKey) {
    case "uplift":
      return { x: 0, y: trail * heightUnit(bounds) * (isGlow ? 0.04 : 0.12), z: 0 };
    case "drive":
      return { x: 0, y: trail * 0.03, z: -trail * radial * (0.1 + hash * 0.08) };
    case "grief":
      return { x: 0, y: -trail * heightUnit(bounds) * (isGlow ? 0.06 : 0.16), z: 0 };
    case "tension":
      return {
        x: (hash - 0.5) * trail * radial * (isGlow ? 0.05 : 0.09),
        y: 0,
        z: ((hash01(index * 5.31 + 0.19) - 0.5) * trail * radial * (isGlow ? 0.05 : 0.09)),
      };
    case "guard": {
      const dirX = tx - bounds.center.x;
      const dirZ = tz - bounds.center.z;
      const len = Math.hypot(dirX, dirZ) || 1;
      return { x: (dirX / len) * trail * radial * 0.08, y: 0, z: (dirZ / len) * trail * radial * 0.08 };
    }
    case "embrace": {
      const dirX = tx - bounds.center.x;
      const dirZ = tz - bounds.center.z;
      const len = Math.hypot(dirX, dirZ) || 1;
      return { x: -(dirX / len) * trail * radial * 0.07, y: trail * 0.02, z: -(dirZ / len) * trail * radial * 0.07 };
    }
    default:
      return { x: 0, y: 0, z: 0 };
  }
}

function heightUnit(bounds) {
  return Math.max(bounds.height, 1.0);
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
  const webcamCheckMode = params.get("webcamCheck") === "1";
  viewer.geometryMode = "dual_shell";
  viewer.showFitShell = params.get("fitOverlay") === "1" || webcamCheckMode;
  viewer.uiLevel = params.get("ui") === UI_LEVELS.DETAIL || webcamCheckMode ? UI_LEVELS.DETAIL : UI_LEVELS.SIMPLE;
  viewer.setVrmAttachMode(params.get("attach") || VRM_ATTACH_MODES.HYBRID);
  viewer.surfaceFirst.graphVisible = params.has("surfaceGraph") ? params.get("surfaceGraph") === "1" : webcamCheckMode;
  viewer.surfaceFirst.shellVisible = params.has("surfaceShell") ? params.get("surfaceShell") === "1" : webcamCheckMode;
  viewer.surfaceFirst.mountsVisible = params.has("surfaceMounts") ? params.get("surfaceMounts") === "1" : webcamCheckMode;
  viewer.surfaceFirst.forceTrackingSource = params.get("surfaceTracking") || "auto";
  if (params.has("surfaceDensity")) {
    const density = clamp(Number(params.get("surfaceDensity")), 24, 240);
    if (PANEL.surfacePointDensity) PANEL.surfacePointDensity.value = String(density);
    viewer.surfaceFirst.density = density;
  }
  if (params.has("surfaceOffset")) {
    const shellOffset = clamp(Number(params.get("surfaceOffset")), 0.002, 0.08);
    if (PANEL.surfaceShellOffset) PANEL.surfaceShellOffset.value = String(shellOffset);
    viewer.surfaceFirst.shellOffset = shellOffset;
  }
  viewer.updateSurfaceFirstButtons();

  viewer.pendingLoad = Promise.resolve();
  const loadIntoViewer = async (suitspecPath, simPath) => {
    viewer.pendingLoad = Promise.resolve(viewer.pendingLoad)
      .catch(() => null)
      .then(() => viewer.load(suitspecPath, simPath));
    return viewer.pendingLoad;
  };

  PANEL.btnLoad.onclick = async () => {
    try {
      await loadIntoViewer(PANEL.suitspecPath.value, PANEL.simPath.value);
    } catch (err) {
      const details = formatLoadError(err);
      viewer.setStatus(`読込に失敗しました: ${details}`, true);
        viewer.setMeta({
          error: String(details),
          suitspec: PANEL.suitspecPath.value,
          sim: PANEL.simPath.value,
          tip: "python tools/run_henshin.py serve-viewer --port 8000 --root . で viewer を起動し、/viewer/body-fit/ を開いてください。",
        });
    }
  };

  if (PANEL.btnUiSimple) {
    PANEL.btnUiSimple.onclick = () => viewer.setUiLevel(UI_LEVELS.SIMPLE);
  }
  if (PANEL.btnUiDetail) {
    PANEL.btnUiDetail.onclick = () => viewer.setUiLevel(UI_LEVELS.DETAIL);
  }

  PANEL.btnPlay.onclick = () => {
    viewer.playing = !viewer.playing;
    viewer.updatePlaybackButton();
    viewer.setLegend();
  };

  PANEL.btnPrev.onclick = () => viewer.applyFrame(viewer.frameIndex - 1);
  PANEL.btnNext.onclick = () => viewer.applyFrame(viewer.frameIndex + 1);
  PANEL.frameSlider.oninput = () => viewer.applyFrame(Number(PANEL.frameSlider.value));
  PANEL.speedSlider.oninput = () => viewer.setLegend();
  PANEL.btnTexture.onclick = () => {
    viewer.useTextures = !viewer.useTextures;
    viewer.updateTextureMode();
    viewer.updateMetaPanel();
    viewer.setLegend();
  };
  if (PANEL.btnGeometry) {
    PANEL.btnGeometry.onclick = () => {
      viewer.setGeometryMode(!viewer.showFitShell);
    };
  }
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
  if (PANEL.btnCamBack) {
    PANEL.btnCamBack.onclick = () => viewer.setCameraPreset("back");
  }
  PANEL.btnCamTop.onclick = () => viewer.setCameraPreset("top");
  if (PANEL.btnCamPov) {
    PANEL.btnCamPov.onclick = () => viewer.setCameraPreset("pov");
  }
  PANEL.btnFit.onclick = () => viewer.fitCameraToVisible();
  if (PANEL.liveViewMode) {
    PANEL.liveViewMode.onchange = () => viewer.setLiveViewMode(PANEL.liveViewMode.value);
  }
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
    PANEL.btnVrmAttach.onclick = () => viewer.cycleVrmAttachMode();
  }
  if (PANEL.btnArmorToggle) {
    PANEL.btnArmorToggle.onclick = () => viewer.setArmorVisible(!viewer.armorVisible);
  }
  if (PANEL.btnVrmIdleToggle) {
    PANEL.btnVrmIdleToggle.onclick = () => viewer.setVrmIdleEnabled(!viewer.vrm.idleEnabled);
  }
  if (PANEL.btnVrmFocus) {
    PANEL.btnVrmFocus.onclick = () => viewer.fitCameraToVrm();
  }
  if (PANEL.btnVrmTPose) {
    PANEL.btnVrmTPose.onclick = () => viewer.applyVrmTPose();
  }
  if (PANEL.btnVrmAutoFit) {
    PANEL.btnVrmAutoFit.onclick = () => viewer.autoFitArmorToCurrentVrm({ forceTPose: true });
  }
  if (PANEL.btnVrmAutoFitSave) {
    PANEL.btnVrmAutoFitSave.onclick = async () => {
      await viewer.autoFitAndSaveCurrentVrm({ forceTPose: true });
    };
  }
  if (PANEL.btnDepositionPlay) {
    PANEL.btnDepositionPlay.onclick = () => viewer.playDepositionMock();
  }
  if (PANEL.btnDepositionReset) {
    PANEL.btnDepositionReset.onclick = () => viewer.resetDepositionMock();
  }
  if (PANEL.depositionProfile) {
    PANEL.depositionProfile.onchange = () => {
      viewer.deposition.profileMode = PANEL.depositionProfile.value;
      const resolved = viewer.resolveDepositionProfileKey();
      viewer.deposition.resolvedKey = resolved;
      viewer.deposition.palette = buildDepositionPalette(DEPOSITION_PROFILES[resolved] || DEPOSITION_PROFILES.guard);
      viewer.updateDepositionStatus(`Deposition: ready (${DEPOSITION_PROFILES[resolved]?.label || resolved})`);
      viewer.updateMetaPanel();
      viewer.setLegend();
    };
  }
  if (PANEL.btnSurfaceFirstRefresh) {
    PANEL.btnSurfaceFirstRefresh.onclick = () => viewer.refreshSurfaceFirstDemo({ force: true });
  }
  if (PANEL.btnSurfaceFirstGraph) {
    PANEL.btnSurfaceFirstGraph.onclick = () => viewer.setSurfaceFirstLayerVisible("graph", !viewer.surfaceFirst.graphVisible);
  }
  if (PANEL.btnSurfaceFirstShell) {
    PANEL.btnSurfaceFirstShell.onclick = () => viewer.setSurfaceFirstLayerVisible("shell", !viewer.surfaceFirst.shellVisible);
  }
  if (PANEL.btnSurfaceFirstMounts) {
    PANEL.btnSurfaceFirstMounts.onclick = () => viewer.setSurfaceFirstLayerVisible("mounts", !viewer.surfaceFirst.mountsVisible);
  }
  if (PANEL.surfacePointDensity) {
    PANEL.surfacePointDensity.oninput = () => {
      viewer.surfaceFirst.density = clamp(Number(PANEL.surfacePointDensity.value || viewer.surfaceFirst.density), 24, 240);
      viewer.refreshSurfaceFirstDemo({ force: viewer.needsSurfaceFirstSnapshot() });
    };
  }
  if (PANEL.surfaceShellOffset) {
    PANEL.surfaceShellOffset.oninput = () => {
      viewer.surfaceFirst.shellOffset = clamp(Number(PANEL.surfaceShellOffset.value || viewer.surfaceFirst.shellOffset), 0.002, 0.08);
      viewer.refreshSurfaceFirstDemo({ force: viewer.needsSurfaceFirstSnapshot() });
    };
  }
  window.__HENSHIN_BODY_FIT__ = {
    ready: true,
    viewer,
    runFitRegression: async ({
      suitspecPath = PANEL.suitspecPath.value,
      simPath = PANEL.simPath.value,
      vrmPath = PANEL.vrmPath?.value || DEFAULT_VRM_PATH,
      attachMode = VRM_ATTACH_MODES.VRM,
      mode = "auto_fit",
      forceTPose = true,
    } = {}) => {
      if (PANEL.suitspecPath) PANEL.suitspecPath.value = suitspecPath;
      if (PANEL.simPath) PANEL.simPath.value = simPath;
      if (PANEL.vrmPath) PANEL.vrmPath.value = vrmPath;
      viewer.setVrmAttachMode(attachMode);
      await loadIntoViewer(suitspecPath, simPath);
      const result =
        mode === "current"
          ? viewer.evaluateCurrentFitAgainstVrm({ forceTPose, silent: true })
          : viewer.autoFitArmorToCurrentVrm({ forceTPose, silent: true });
      if (!result) {
        return {
          ok: false,
          mode,
          suitspecPath,
          simPath,
          vrmPath,
          error: viewer.autoFitSummary?.reasons?.join(" | ") || "Fit regression failed",
        };
      }
      return {
        ok: Boolean(result.summary?.canSave),
        mode,
        suitspecPath,
        simPath,
        vrmPath,
        summary: result.summary || null,
        wearableSummary: result.wearableSummary || result.summary || null,
        metrics: result.metrics || null,
        fitByPart: result.fitByPart || {},
        anchorByPart: result.anchorByPart || {},
        surfaceModel: result.surfaceModel || null,
      };
    },
    runSurfaceFirstDemo: async ({
      suitspecPath = PANEL.suitspecPath.value,
      simPath = PANEL.simPath.value,
      vrmPath = PANEL.vrmPath?.value || DEFAULT_VRM_PATH,
      graphVisible = true,
      shellVisible = true,
      mountsVisible = true,
      density = viewer.surfaceFirst.density,
      shellOffset = viewer.surfaceFirst.shellOffset,
      trackingSource = "auto",
    } = {}) => {
      if (PANEL.suitspecPath) PANEL.suitspecPath.value = suitspecPath;
      if (PANEL.simPath) PANEL.simPath.value = simPath;
      if (PANEL.vrmPath) PANEL.vrmPath.value = vrmPath;
      if (PANEL.surfacePointDensity) PANEL.surfacePointDensity.value = String(clamp(Number(density), 24, 240));
      if (PANEL.surfaceShellOffset) PANEL.surfaceShellOffset.value = String(clamp(Number(shellOffset), 0.002, 0.08));
      await loadIntoViewer(suitspecPath, simPath);
      if (!viewer.vrm.model || viewer.vrm.path !== vrmPath) {
        await viewer.loadVrmModel(vrmPath, { silent: true });
      }
      viewer.surfaceFirst.graphVisible = Boolean(graphVisible);
      viewer.surfaceFirst.shellVisible = Boolean(shellVisible);
      viewer.surfaceFirst.mountsVisible = Boolean(mountsVisible);
      viewer.surfaceFirst.forceTrackingSource = String(trackingSource || "auto");
      viewer.surfaceFirst.density = clamp(Number(density), 24, 240);
      viewer.surfaceFirst.shellOffset = clamp(Number(shellOffset), 0.002, 0.08);
      if (viewer.surfaceFirst.forceTrackingSource === "live" && !viewer.live?.bodyInference && viewer.vrm.bodyInference) {
        viewer.live.active = true;
        viewer.live.bodyInference = JSON.parse(JSON.stringify(viewer.vrm.bodyInference));
        viewer.live.bodyTrackingFrame = createBodyTrackingFrameFromInference(viewer.live.bodyInference, {
          source: "webcam",
          timestampMs: performance.now(),
          metadata: {
            synthetic: true,
            sourceFrame: viewer.vrm.bodyTrackingFrame?.id || null,
          },
        });
        viewer.live.poseQuality = viewer.live.bodyInference?.qualityLabel || "good";
        viewer.live.poseReliableJoints = viewer.live.bodyInference?.reliableJointCount || 0;
        viewer.lastLiveJoints = viewer.live.bodyInference?.joints || null;
      }
      viewer.updateSurfaceFirstButtons();
      viewer.refreshSurfaceFirstDemo({ force: true });
      return viewer.surfaceFirst.summary;
    },
  };
  if (PANEL.depositionDuration) {
    PANEL.depositionDuration.oninput = () => {
      viewer.deposition.durationSec = clamp(Number(PANEL.depositionDuration.value || DEFAULT_DEPOSITION_DURATION), 1.2, 6.0);
      viewer.updateMetaPanel();
      viewer.setLegend();
    };
  }

  if (PANEL.fitPart) {
    PANEL.fitPart.onchange = () => viewer.loadFitEditorForPart(PANEL.fitPart.value);
  }
  if (PANEL.btnFitRefreshCheck) {
    PANEL.btnFitRefreshCheck.onclick = () => viewer.refreshFitAssistCheck();
  }
  if (PANEL.btnFitPrevIssue) {
    PANEL.btnFitPrevIssue.onclick = () => viewer.selectAdjacentFitIssue(-1);
  }
  if (PANEL.btnFitNextIssue) {
    PANEL.btnFitNextIssue.onclick = () => viewer.selectAdjacentFitIssue(1);
  }
  if (PANEL.btnFitFocusPart) {
    PANEL.btnFitFocusPart.onclick = () => viewer.fitCameraToPart(viewer.getSelectedFitPart());
  }
  if (PANEL.btnGizmoToggle) {
    PANEL.btnGizmoToggle.onclick = () => viewer.setGizmoEnabled(!viewer.gizmo.enabled);
  }
  if (PANEL.btnGizmoMove) {
    PANEL.btnGizmoMove.onclick = () => viewer.setGizmoMode("translate");
  }
  if (PANEL.btnGizmoScale) {
    PANEL.btnGizmoScale.onclick = () => viewer.setGizmoMode("scale");
  }
  if (PANEL.btnGizmoSpace) {
    PANEL.btnGizmoSpace.onclick = () => viewer.cycleGizmoSpace();
  }
  if (PANEL.vrmEditPart) {
    PANEL.vrmEditPart.onchange = () => viewer.loadVrmAnchorEditorForPart(PANEL.vrmEditPart.value);
  }
  if (PANEL.btnVrmEditLoad) {
    PANEL.btnVrmEditLoad.onclick = () => viewer.loadVrmAnchorEditorForPart(PANEL.vrmEditPart?.value || "");
  }
  if (PANEL.btnVrmEditApply) {
    PANEL.btnVrmEditApply.onclick = () => viewer.applyVrmAnchorEditorToCurrentPart();
  }
  if (PANEL.btnVrmEditReset) {
    PANEL.btnVrmEditReset.onclick = () => viewer.resetVrmAnchorForCurrentPart();
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
  if (PANEL.fitNudgeControls) {
    PANEL.fitNudgeControls.onclick = (event) => {
      const button = event.target?.closest?.("[data-fit-nudge]");
      if (!button) return;
      const [fieldId, directionRaw] = String(button.dataset.fitNudge || "").split(":");
      const direction = Number(directionRaw);
      if (!fieldId || !Number.isFinite(direction) || direction === 0) return;
      viewer.nudgeCurrentFitField(fieldId, direction);
    };
  }

  const liveVrmAnchorInputs = [
    PANEL.vrmEditBone,
    PANEL.vrmEditOffsetX,
    PANEL.vrmEditOffsetY,
    PANEL.vrmEditOffsetZ,
    PANEL.vrmEditRotX,
    PANEL.vrmEditRotY,
    PANEL.vrmEditRotZ,
    PANEL.vrmEditScaleX,
    PANEL.vrmEditScaleY,
    PANEL.vrmEditScaleZ,
  ];
  for (const input of liveVrmAnchorInputs) {
    if (!input) continue;
    input.oninput = () => viewer.applyVrmAnchorEditorToCurrentPart({ silent: true });
  }

  if (PANEL.vrmIdleAmount) {
    PANEL.vrmIdleAmount.oninput = () => {
      viewer.vrm.idleAmount = clamp(Number(PANEL.vrmIdleAmount.value || 0.35), 0, 1);
      viewer.updateMetaPanel();
      viewer.setLegend();
    };
  }
  if (PANEL.vrmIdleSpeed) {
    PANEL.vrmIdleSpeed.oninput = () => {
      viewer.vrm.idleSpeed = clamp(Number(PANEL.vrmIdleSpeed.value || 1), 0.25, 3);
      viewer.updateMetaPanel();
      viewer.setLegend();
    };
  }

  viewer.applyTheme();
  viewer.updateBridgeButton();
  viewer.updateArmorButton();
  viewer.updateGeometryButton();
  viewer.updateVrmButton();
  viewer.updateVrmAttachButton();
  viewer.updateVrmIdleButton();
  viewer.updateSurfaceFirstButtons();
  viewer.setCameraPreset("front");
  viewer.setUiLevel(viewer.uiLevel);
  viewer.setLiveViewMode(PANEL.liveViewMode?.value || "auto");
  viewer.setLegend();
  viewer.updateLiveStatus("ライブ: 停止中");
  window.addEventListener("beforeunload", () => viewer.stopLive({ silent: true }));
  void loadIntoViewer(PANEL.suitspecPath.value, PANEL.simPath.value).catch((err) => {
    const details = formatLoadError(err);
    viewer.setStatus(`読込に失敗しました: ${details}`, true);
    viewer.setMeta({
      error: String(details),
      suitspec: PANEL.suitspecPath.value,
      sim: PANEL.simPath.value,
      tip: "python tools/run_henshin.py serve-viewer --port 8000 --root . で viewer を起動し、/viewer/body-fit/ を開いてください。",
    });
  });
}

function formatLoadError(error) {
  const raw = String(error?.message || error || "Unknown error");
  if (!raw.includes("Failed to load JSON")) return raw;
  if (raw.includes("(404)")) {
    return `${raw} / examples/... や sessions/... のパスを確認してください。`;
  }
  return `${raw} / ローカルHTTPサーバーで viewer を配信しているか確認してください。`;
}

init();



