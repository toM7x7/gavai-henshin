import {
  ReferenceSpaceType,
  SessionMode,
  VisibilityState,
  World,
} from "@iwsdk/core";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import {
  clampSurfaceOffsetForPart,
  wearableSurfaceFitPolicyForPart,
} from "../shared/armor-canon.js";
import {
  EXHIBITION_OPERATOR_COPY,
  operatorStateColorGuide,
  operatorStateLabel,
} from "../shared/exhibition-copy.js";
import {
  clampedQuestOffsetArrayFromPlacement as sharedClampedQuestOffsetArrayFromPlacement,
  questOffsetArrayFromPlacement as sharedQuestOffsetArrayFromPlacement,
  resolveRuntimeOffset,
  resolveRuntimePlacementMode,
  resolveRuntimeRotation,
  resolveRuntimeTargetSize,
  vectorArrayFromRuntimeRecord as sharedVectorArrayFromRuntimeRecord,
  webPreviewOffsetArrayFromPlacement as sharedWebPreviewOffsetArrayFromPlacement,
  webPreviewSurfaceOffsetArrayFromPlacement as sharedWebPreviewSurfaceOffsetArrayFromPlacement,
} from "../shared/runtime-placement-resolver.js";

const DEFAULT_REPLAY = "/sessions/S-IW-DEMO/artifacts/iwsdk-deposition-replay.json";
const DEFAULT_SUITSPEC = "/examples/suitspec.sample.json";
const DEFAULT_MOCOPI = "examples/mocopi_sequence.sample.json";
const DEFAULT_BODY_SIM_LATEST = "http://localhost:8021/body-sim/latest";
const DEFAULT_SUIT_ID = "VDA-AXIS-OP-00-0001";
const DEFAULT_MANIFEST_ID = "MNF-20260424-SAMP";
const RECALL_CODE_RE = /^[A-Z0-9]{4}$/;
const XR_RECALL_CODE_EMPTY = "----";
const XR_RECALL_CHARS = "0123456789";
const TRIGGER_PHRASE = "\u751f\u6210";
const TRIGGER_ALIASES = [
  "\u5148\u751f",
  "\u305b\u3044\u305b\u3044",
  "\u305b\u3048\u305b\u3048",
  "\u305b\u30fc\u305b\u30fc",
  "\u305b\u3044\u305c\u3044",
  "\u305b\u3048\u305c\u3048",
  "\u30bb\u30a4\u30bb\u30a4",
  "\u30bb\u30fc\u30bb\u30fc",
  "\u30bb\u30a4\u30bc\u30a4",
  "\u7cbe\u88fd",
];
const ARMOR_PARTS = [
  "helmet",
  "chest",
  "back",
  "left_shoulder",
  "right_shoulder",
  "left_upperarm",
  "right_upperarm",
  "left_forearm",
  "right_forearm",
  "waist",
  "left_thigh",
  "right_thigh",
  "left_shin",
  "right_shin",
  "left_boot",
  "right_boot",
  "left_hand",
  "right_hand",
];

const PART_TO_SEGMENT = {
  helmet: "chest_core",
  chest: "chest_core",
  back: "chest_core",
  waist: "chest_core",
  left_shoulder: "left_upperarm",
  right_shoulder: "right_upperarm",
  left_upperarm: "left_upperarm",
  right_upperarm: "right_upperarm",
  left_forearm: "left_forearm",
  right_forearm: "right_forearm",
  left_hand: "left_hand",
  right_hand: "right_hand",
  left_thigh: "left_thigh",
  right_thigh: "right_thigh",
  left_shin: "left_shin",
  right_shin: "right_shin",
  left_boot: "left_shin",
  right_boot: "right_shin",
};

const PART_OFFSETS = {
  helmet: [0, 0.72, 0.02],
  chest: [0, 0.2, 0.0],
  back: [0, 0.2, -0.14],
  waist: [0, -0.38, 0.0],
  left_shoulder: [-0.14, 0.13, 0.0],
  right_shoulder: [0.14, 0.13, 0.0],
  left_hand: [0, -0.16, 0.0],
  right_hand: [0, -0.16, 0.0],
  left_boot: [0, -0.28, 0.02],
  right_boot: [0, -0.28, 0.02],
};

const PART_COLORS = {
  helmet: 0xffdf85,
  chest: 0xf6f1df,
  back: 0x8edfff,
  waist: 0xffcf5a,
  left_hand: 0x43d8ff,
  right_hand: 0x43d8ff,
};

const UI = {
  status: document.getElementById("status"),
  meterFill: document.getElementById("meterFill"),
  btnEnterVR: document.getElementById("btnEnterVR"),
  btnVoice: document.getElementById("btnVoice"),
  btnReplay: document.getElementById("btnReplay"),
  btnReplayView: document.getElementById("btnReplayView"),
  btnPause: document.getElementById("btnPause"),
  btnReset: document.getElementById("btnReset"),
  micState: document.getElementById("micState"),
  voiceLine: document.getElementById("voiceLine"),
  voiceDebug: document.getElementById("voiceDebug"),
  operatorStateHelp: document.getElementById("operatorStateHelp"),
  routeMode: document.getElementById("routeMode"),
  routeApi: document.getElementById("routeApi"),
  routeTrial: document.getElementById("routeTrial"),
  routeReplay: document.getElementById("routeReplay"),
  routeContract: document.getElementById("routeContract"),
  recallCodeInput: document.getElementById("recallCodeInput"),
  btnLoadRecallCode: document.getElementById("btnLoadRecallCode"),
  recallCodeState: document.getElementById("recallCodeState"),
  equipmentStatus: document.getElementById("equipmentStatus"),
  sessionId: document.getElementById("sessionId"),
  triggerState: document.getElementById("triggerState"),
  equipState: document.getElementById("equipState"),
};

const textureLoader = new THREE.TextureLoader();
const gltfLoader = new GLTFLoader();
const geometryCache = new Map();
const textureCache = new Map();
const TAU = Math.PI * 2;
const QUEST_PLACEMENT_BASE_EULER = new THREE.Euler(0, 0, 0, "XYZ");
const QUEST_PLACEMENT_ROTATION_EULER = new THREE.Euler(0, 0, 0, "XYZ");
const ARMOR_STAND_INSPECTION_EULER = new THREE.Euler(0, 0, 0, "YXZ");
const QUEST_PLACEMENT_BASE_QUATERNION = new THREE.Quaternion();
const QUEST_PLACEMENT_ROTATION_QUATERNION = new THREE.Quaternion();
const ARMOR_STAND_INSPECTION_QUATERNION = new THREE.Quaternion();
const ARMOR_STAND_RIG_EULER = new THREE.Euler(0, 0, 0, "YXZ");
const ARMOR_STAND_RIG_QUATERNION = new THREE.Quaternion();
const ARMOR_STAND_RIG_LOCAL_VECTOR = new THREE.Vector3();
const ARMOR_STAND_RIG_WORLD_VECTOR = new THREE.Vector3();
const ARMOR_STAND_RIG_OFFSET_VECTOR = new THREE.Vector3();
const ARMOR_STAND_MOVE_LOCAL_VECTOR = new THREE.Vector3();
const ARMOR_STAND_MOVE_WORLD_QUATERNION = new THREE.Quaternion();
const QUEST_DEBUG_EULER = new THREE.Euler(0, 0, 0, "YXZ");
const QUEST_DEBUG_VECTOR_A = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_B = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_C = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_D = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_E = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_F = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_G = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_H = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_I = new THREE.Vector3();
const QUEST_DEBUG_VECTOR_J = new THREE.Vector3();
const XR_VIEW_MODE_SELF = "self";
const XR_VIEW_MODE_OBSERVER = "observer";
const XR_VIEW_MODE_MIRROR = "mirror";
const XR_ANCHOR_PROFILE_SELF = "self";
const XR_ANCHOR_PROFILE_MIRROR = "mirror";
const XR_ANCHOR_PROFILE_REPLAY_OBSERVER = "replay_observer";
const XR_ANCHOR_PROFILE_ARMOR_STAND = "armor_stand";
const REPLAY_MOTION_SOURCE_LIVE_POSE = "live_pose";
const REPLAY_MOTION_SOURCE_BODY_SIM = "body_sim";
const REPLAY_MOTION_SOURCE_MOCOPI = "mocopi";
const REPLAY_MOTION_SOURCE_MIXED = "body_sim_plus_live_pose";
const REPLAY_MOTION_SOURCE_STATIC = "static_fallback";
const REPLAY_MOTION_SOURCE_CAPTURE = "live_capture";
const REPLAY_MOTION_SOURCE_SELF = "first_person";
const LIVE_BODY_SIM_DEFAULT_POLL_INTERVAL_MS = 90;
const LIVE_BODY_SIM_STALE_AFTER_MS = 1600;
const LIVE_BODY_SIM_MIN_POLL_INTERVAL_MS = 60;
const LIVE_BODY_SIM_MAX_POLL_INTERVAL_MS = 500;
const LIVE_BODY_SIM_RENDER_DEFAULTS = {
  xOffset: 0.05,
  yOffset: -0.76,
  zOffset: -0.2,
  xSign: 1,
  ySign: 1,
  zSign: -1,
  scale: 1,
  yawOffsetRad: 0,
};
const VRM_BASE_SUIT_STATUS_DISABLED = "disabled";
const VRM_BASE_SUIT_STATUS_PROCEDURAL = "procedural_fallback";
const VRM_BASE_SUIT_STATUS_PENDING = "pending";
const VRM_BASE_SUIT_STATUS_LOADED = "loaded";
const VRM_BASE_SUIT_STATUS_ERROR = "error_fallback";
const ARMOR_ASSET_LOAD_CONCURRENCY = 4;
const SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "left_hand", "right_hand"]);
const SELF_VIEW_STANDBY_HIDDEN_PARTS = new Set(["helmet"]);
const SELF_VIEW_HIDDEN_BASE_SUIT_PARTS = new Set(["head", "neck", "spine", "shoulder_line", "torso"]);
const VR_REPLAY_OBSERVER_DISTANCE = 2.15;
const VR_REPLAY_OBSERVER_HEIGHT_OFFSET = -0.06;
const VR_REPLAY_OBSERVER_SCALE = 0.88;
const VR_REPLAY_MIRROR_DISTANCE = 1.72;
const VR_REPLAY_MIRROR_HEIGHT_OFFSET = -0.1;
const VR_REPLAY_MIRROR_SCALE = 0.82;
const MIRROR_FRAME_WIDTH = 1.34;
const MIRROR_FRAME_HEIGHT = 2.08;
const LIVE_MIRROR_DISTANCE = 1.9;
const LIVE_MIRROR_HEIGHT_OFFSET = -0.12;
const LIVE_MIRROR_SCALE = 0.82;
const LIVE_MIRROR_SHOW_PROGRESS = 0.78;
const XR_ARMOR_STAND_DISTANCE = 2.0;
const XR_ARMOR_STAND_HEIGHT_OFFSET = -0.08;
const XR_ARMOR_STAND_SCALE = 0.84;
const XR_ARMOR_STAND_YAW_OFFSET_RAD = 0;
const XR_REPLAY_OBSERVER_YAW_OFFSET_RAD = 0;
const XR_MENU_FALLBACK_DISTANCE = 1.14;
const XR_MENU_FALLBACK_LEFT = 0.62;
const XR_MENU_FALLBACK_DOWN = 0.32;
const XR_MENU_FALLBACK_REANCHOR_DISTANCE = 1.85;
const XR_MENU_MODE_COMPACT = "compact";
const XR_MENU_MODE_OPEN = "open";
const XR_MENU_MODE_WORLD_LOCKED = "worldLocked";
const XR_MENU_OPEN_AUTO_COMPACT_MS = 8000;
// Map the panel's short side to the controller laser axis.
const WATCH_PANEL_BASE_ROTATION = new THREE.Quaternion().setFromEuler(new THREE.Euler(Math.PI / 2, 0, Math.PI, "XYZ"));
const WATCH_PANEL_FACE_FLIP = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, Math.PI, 0, "XYZ"));
const WATCH_PANEL_ROTATION = WATCH_PANEL_BASE_ROTATION.clone().multiply(WATCH_PANEL_FACE_FLIP);
const WATCH_PANEL_WIDTH = 1.74;
const WATCH_PANEL_HEIGHT = 1.06;
const WATCH_COMPACT_PANEL_WIDTH = 0.76;
const WATCH_COMPACT_PANEL_HEIGHT = 0.28;
const WATCH_PANEL_SCALE = 0.4;
const WATCH_COMPACT_SCALE = 0.34;
const WATCH_PANEL_FALLBACK_SCALE = 0.46;
const WATCH_PANEL_BOTTOM_CLEARANCE = 0.035;
const WATCH_PANEL_SURFACE_GAP = 0.07;
const DEPOSITION_PARTICLE_COUNT = 420;
const DEPOSITION_SPARK_COUNT = 84;
const DEPOSITION_BODY_Y_MIN = -1.62;
const DEPOSITION_BODY_Y_MAX = 0.88;
const DEPOSITION_BODY_Z = -0.28;
const DEPOSITION_LORE_COLORS = [0x43d8ff, 0xffcf5a, 0xf6f1df, 0x8edfff];
const MIRROR_DEPOSITION_DIMMING = 0.42;
const MIRROR_DEPOSITION_Z = -0.46;
const ARMOR_STAND_FLOOR_LIFT_M = 0.24;
const ARMOR_STAND_CENTER_Z = -0.28;
const ARMOR_STAND_CENTER_Y = -0.62;
const ARMOR_STAND_EXPLODE_DISTANCE_M = 0.26;
const ARMOR_STAND_SCALE_MIN = 0.62;
const ARMOR_STAND_SCALE_MAX = 1.65;
const ARMOR_STAND_PITCH_LIMIT_RAD = THREE.MathUtils.degToRad(58);
const ARMOR_STAND_GRAB_YAW_PER_M = 2.9;
const ARMOR_STAND_GRAB_PITCH_PER_M = 2.4;
const ARMOR_STAND_GRAB_DEADZONE_M = 0.003;
const ARMOR_STAND_GRAB_MAX_DELTA_M = 0.085;
const ARMOR_STAND_MOVE_DEADZONE_M = 0.002;
const ARMOR_STAND_MOVE_MAX_DELTA_M = 0.18;
const ARMOR_STAND_TWO_HAND_YAW_DEADZONE_RAD = THREE.MathUtils.degToRad(1.2);
const ARMOR_STAND_OFFSET_LIMITS_M = {
  x: [-1.15, 1.15],
  y: [-0.55, 0.85],
  z: [-1.25, 0.85],
};
const ARMOR_STAND_EXIT_ACTIONS = new Set(["stand", "view", "replay", "reset", "close"]);
const LIVE_MOTION_SAMPLE_INTERVAL = 0.1;
const LIVE_MOTION_MAX_FRAMES = 48;
const QUEST_DEBUG_TELEMETRY_INTERVAL_MS = 1000;
const QUEST_CENTERLINE_QA_THRESHOLDS = Object.freeze({
  anchorToRigDistanceMaxM: 0.05,
  anchorToRigYawMaxDeg: 3,
  cameraLocalXMaxM: 0.08,
  coherentPartLateralMinM: 0.08,
  partAnchorDeltaMaxM: 0.12,
  glbOriginToBoundsMaxM: 0.08,
});
const NON_VR_RIG_POSITION = new THREE.Vector3(0, 0.78, -2.55);
const QUEST_HUMAN_BODY_MOCK = {
  version: "quest-human-body-mock.v1",
  height_m: 1.7,
  spine_z_m: -0.28,
  points_m: {
    head_center: [0, -0.04, -0.28],
    neck: [0, -0.25, -0.28],
    upper_torso: [0, -0.52, -0.28],
    lower_torso: [0, -0.74, -0.28],
    pelvis: [0, -0.9, -0.28],
    left_shoulder_joint: [-0.31, -0.46, -0.28],
    right_shoulder_joint: [0.31, -0.46, -0.28],
    left_upperarm_mid: [-0.43, -0.69, -0.28],
    right_upperarm_mid: [0.43, -0.69, -0.28],
    left_forearm_mid: [-0.47, -0.98, -0.29],
    right_forearm_mid: [0.47, -0.98, -0.29],
    left_hand_center: [-0.46, -1.2, -0.3],
    right_hand_center: [0.46, -1.2, -0.3],
    left_thigh_mid: [-0.15, -1.17, -0.28],
    right_thigh_mid: [0.15, -1.17, -0.28],
    left_shin_mid: [-0.17, -1.48, -0.29],
    right_shin_mid: [0.17, -1.48, -0.29],
    left_foot_center: [-0.17, -1.66, -0.36],
    right_foot_center: [0.17, -1.66, -0.36],
  },
};
const VR_BODY_PART_POSES = {
  helmet: [0, -0.04, -0.28],
  chest: [0, -0.52, -0.42],
  back: [0, -0.52, -0.06],
  waist: [0, -0.9, -0.28],
  left_shoulder: [-0.36, -0.46, -0.3],
  right_shoulder: [0.36, -0.46, -0.3],
  left_upperarm: [-0.43, -0.69, -0.3],
  right_upperarm: [0.43, -0.69, -0.3],
  left_forearm: [-0.47, -0.98, -0.31],
  right_forearm: [0.47, -0.98, -0.31],
  left_hand: [-0.46, -1.2, -0.32],
  right_hand: [0.46, -1.2, -0.32],
  left_thigh: [-0.15, -1.17, -0.28],
  right_thigh: [0.15, -1.17, -0.28],
  left_shin: [-0.17, -1.48, -0.29],
  right_shin: [0.17, -1.48, -0.29],
  left_boot: [-0.17, -1.66, -0.36],
  right_boot: [0.17, -1.66, -0.36],
};
const QUEST_ASSEMBLY_ADJUSTMENTS = {
  chest: [0, 0.03, -0.035],
  back: [0, 0.025, 0.045],
  waist: [0, -0.025, -0.005],
  left_shoulder: [-0.075, 0.015, -0.005],
  right_shoulder: [0.075, 0.015, -0.005],
  left_upperarm: [-0.08, -0.015, 0.005],
  right_upperarm: [0.08, -0.015, 0.005],
  left_forearm: [-0.07, -0.02, 0.0],
  right_forearm: [0.07, -0.02, 0.0],
  left_hand: [-0.06, -0.02, 0.005],
  right_hand: [0.06, -0.02, 0.005],
  left_thigh: [-0.035, -0.015, 0.005],
  right_thigh: [0.035, -0.015, 0.005],
  left_shin: [-0.035, 0.0, 0.0],
  right_shin: [0.035, 0.0, 0.0],
  left_boot: [-0.035, 0.015, 0.0],
  right_boot: [0.035, 0.015, 0.0],
};
const QUEST_HUMAN_ANCHOR_CONTRACT = {
  helmet: {
    anchor: "head",
    side: "center",
    wearIntent: "head shell surrounding skull without blocking view",
    bodyPoint: "head_center",
    offset_m: [0, 0, 0],
    center_m: [0, -0.04, -0.28],
  },
  chest: {
    anchor: "upper_torso_front",
    side: "center",
    wearIntent: "front cuirass outside sternum and ribs",
    bodyPoint: "upper_torso",
    offset_m: [0, 0, -0.14],
    center_m: [0, -0.52, -0.42],
  },
  back: {
    anchor: "upper_torso_back",
    side: "center",
    wearIntent: "rear back plate outside scapula and spine",
    bodyPoint: "upper_torso",
    offset_m: [0, 0, 0.22],
    center_m: [0, -0.52, -0.06],
  },
  waist: {
    anchor: "pelvis_belt",
    side: "center",
    wearIntent: "belt ring around hips below torso",
    bodyPoint: "pelvis",
    offset_m: [0, 0, 0],
    center_m: [0, -0.9, -0.28],
  },
  left_shoulder: {
    anchor: "left_deltoid_cap",
    side: "left",
    wearIntent: "cap over shoulder joint, outside chest edge",
    bodyPoint: "left_shoulder_joint",
    offset_m: [-0.05, 0, -0.02],
    center_m: [-0.36, -0.46, -0.3],
  },
  right_shoulder: {
    anchor: "right_deltoid_cap",
    side: "right",
    wearIntent: "cap over shoulder joint, outside chest edge",
    bodyPoint: "right_shoulder_joint",
    offset_m: [0.05, 0, -0.02],
    center_m: [0.36, -0.46, -0.3],
  },
  left_upperarm: {
    anchor: "left_humerus_sleeve",
    side: "left",
    wearIntent: "upper arm sleeve below shoulder cap",
    bodyPoint: "left_upperarm_mid",
    offset_m: [0, 0, -0.02],
    center_m: [-0.43, -0.69, -0.3],
  },
  right_upperarm: {
    anchor: "right_humerus_sleeve",
    side: "right",
    wearIntent: "upper arm sleeve below shoulder cap",
    bodyPoint: "right_upperarm_mid",
    offset_m: [0, 0, -0.02],
    center_m: [0.43, -0.69, -0.3],
  },
  left_forearm: {
    anchor: "left_radius_ulna_guard",
    side: "left",
    wearIntent: "forearm guard between elbow and wrist",
    bodyPoint: "left_forearm_mid",
    offset_m: [0, 0, -0.02],
    center_m: [-0.47, -0.98, -0.31],
  },
  right_forearm: {
    anchor: "right_radius_ulna_guard",
    side: "right",
    wearIntent: "forearm guard between elbow and wrist",
    bodyPoint: "right_forearm_mid",
    offset_m: [0, 0, -0.02],
    center_m: [0.47, -0.98, -0.31],
  },
  left_hand: {
    anchor: "left_hand_gauntlet",
    side: "left",
    wearIntent: "gauntlet around hand at end of forearm",
    bodyPoint: "left_hand_center",
    offset_m: [0, 0, -0.02],
    center_m: [-0.46, -1.2, -0.32],
  },
  right_hand: {
    anchor: "right_hand_gauntlet",
    side: "right",
    wearIntent: "gauntlet around hand at end of forearm",
    bodyPoint: "right_hand_center",
    offset_m: [0, 0, -0.02],
    center_m: [0.46, -1.2, -0.32],
  },
  left_thigh: {
    anchor: "left_femur_guard",
    side: "left",
    wearIntent: "thigh guard outside femur, below pelvis",
    bodyPoint: "left_thigh_mid",
    offset_m: [0, 0, 0],
    center_m: [-0.15, -1.17, -0.28],
  },
  right_thigh: {
    anchor: "right_femur_guard",
    side: "right",
    wearIntent: "thigh guard outside femur, below pelvis",
    bodyPoint: "right_thigh_mid",
    offset_m: [0, 0, 0],
    center_m: [0.15, -1.17, -0.28],
  },
  left_shin: {
    anchor: "left_tibia_guard",
    side: "left",
    wearIntent: "shin guard below knee and above boot",
    bodyPoint: "left_shin_mid",
    offset_m: [0, 0, 0],
    center_m: [-0.17, -1.48, -0.29],
  },
  right_shin: {
    anchor: "right_tibia_guard",
    side: "right",
    wearIntent: "shin guard below knee and above boot",
    bodyPoint: "right_shin_mid",
    offset_m: [0, 0, 0],
    center_m: [0.17, -1.48, -0.29],
  },
  left_boot: {
    anchor: "left_foot_boot",
    side: "left",
    wearIntent: "boot shell around foot, resting above floor",
    bodyPoint: "left_foot_center",
    offset_m: [0, 0, 0],
    center_m: [-0.17, -1.66, -0.36],
  },
  right_boot: {
    anchor: "right_foot_boot",
    side: "right",
    wearIntent: "boot shell around foot, resting above floor",
    bodyPoint: "right_foot_center",
    offset_m: [0, 0, 0],
    center_m: [0.17, -1.66, -0.36],
  },
};
const VR_PART_SCALE = {
  helmet: 0.22,
  chest: 0.34,
  back: 0.3,
  waist: 0.26,
  left_shoulder: 0.24,
  right_shoulder: 0.24,
  left_hand: 0.18,
  right_hand: 0.18,
  left_boot: 0.22,
  right_boot: 0.22,
};
const QUEST_GLB_TARGET_SIZES = {
  helmet: [0.25, 0.34, 0.25],
  chest: [0.42, 0.34, 0.11],
  back: [0.4, 0.34, 0.12],
  waist: [0.34, 0.12, 0.14],
  left_shoulder: [0.15, 0.1, 0.13],
  right_shoulder: [0.15, 0.1, 0.13],
  left_upperarm: [0.09, 0.28, 0.09],
  right_upperarm: [0.09, 0.28, 0.09],
  left_forearm: [0.085, 0.25, 0.085],
  right_forearm: [0.085, 0.25, 0.085],
  left_hand: [0.095, 0.08, 0.11],
  right_hand: [0.095, 0.08, 0.11],
  left_thigh: [0.11, 0.36, 0.1],
  right_thigh: [0.11, 0.36, 0.1],
  left_shin: [0.095, 0.33, 0.095],
  right_shin: [0.095, 0.33, 0.095],
  left_boot: [0.12, 0.12, 0.2],
  right_boot: [0.12, 0.12, 0.2],
};

const VOICE_STATES = {
  ready: {
    label: "音声 待機",
    hint: `ここに向けてトリガー後、${TRIGGER_PHRASE} と発声。`,
    color: 0x36f28f,
    textColor: "#dfffe8",
    border: "rgba(54, 242, 143, 0.66)",
  },
  arming: {
    label: "準備中",
    hint: "発声案内まで少し待ってください。",
    color: 0x36f28f,
    textColor: "#dfffe8",
    border: "rgba(54, 242, 143, 0.76)",
  },
  recording: {
    label: "発声",
    hint: `${TRIGGER_PHRASE} と発声してください。`,
    color: 0xffcf5a,
    textColor: "#fff4c8",
    border: "rgba(255, 207, 90, 0.78)",
  },
  analyzing: {
    label: "解析中",
    hint: "音声合図を確認しています。",
    color: 0x8a7cff,
    textColor: "#e4dcff",
    border: "rgba(138, 124, 255, 0.74)",
  },
  detected: {
    label: `${TRIGGER_PHRASE} 確認`,
    hint: "変身を開始します。",
    color: 0x43d8ff,
    textColor: "#d7f8ff",
    border: "rgba(67, 216, 255, 0.74)",
  },
  deposition: {
    label: "変身中",
    hint: "装甲を展開しています。",
    color: 0xfff076,
    textColor: "#fff4c8",
    border: "rgba(255, 207, 90, 0.78)",
  },
  complete: {
    label: "完了",
    hint: "記録再生できます。",
    color: 0x43d8ff,
    textColor: "#d7f8ff",
    border: "rgba(67, 216, 255, 0.68)",
  },
  rejected: {
    label: "再試行",
    hint: `${TRIGGER_PHRASE} を確認できませんでした。右トリガーで再入力。`,
    color: 0xff6b6b,
    textColor: "#ffd2d2",
    border: "rgba(255, 107, 107, 0.78)",
  },
};
const BASE_SUIT_SURFACE_PARTS = [
  ["head", "sphere", [0, -0.04, -0.28], [0.14, 0.17, 0.13], [0, 0, 0]],
  ["neck", "capsule", [0, -0.25, -0.28], [0.055, 0.13, 0.055], [0, 0, 0]],
  ["spine", "capsule", [0, -0.72, -0.28], [0.018, 0.92, 0.018], [0, 0, 0]],
  ["shoulder_line", "capsule", [0, -0.46, -0.28], [0.018, 0.62, 0.018], [0, 0, Math.PI / 2]],
  ["hip_line", "capsule", [0, -0.9, -0.28], [0.016, 0.34, 0.016], [0, 0, Math.PI / 2]],
  ["torso", "capsule", [0, -0.62, -0.3], [0.2, 0.46, 0.13], [0, 0, 0]],
  ["pelvis", "capsule", [0, -0.92, -0.28], [0.18, 0.2, 0.12], [0, 0, Math.PI / 2]],
  ["left_upperarm", "capsule", [-0.43, -0.69, -0.28], [0.055, 0.32, 0.055], [0, 0, -0.18]],
  ["right_upperarm", "capsule", [0.43, -0.69, -0.28], [0.055, 0.32, 0.055], [0, 0, 0.18]],
  ["left_forearm", "capsule", [-0.47, -0.98, -0.29], [0.05, 0.3, 0.05], [0, 0, -0.08]],
  ["right_forearm", "capsule", [0.47, -0.98, -0.29], [0.05, 0.3, 0.05], [0, 0, 0.08]],
  ["left_thigh", "capsule", [-0.15, -1.17, -0.28], [0.065, 0.34, 0.065], [0, 0, 0.03]],
  ["right_thigh", "capsule", [0.15, -1.17, -0.28], [0.065, 0.34, 0.065], [0, 0, -0.03]],
  ["left_shin", "capsule", [-0.17, -1.48, -0.29], [0.058, 0.33, 0.058], [0, 0, 0.02]],
  ["right_shin", "capsule", [0.17, -1.48, -0.29], [0.058, 0.33, 0.058], [0, 0, -0.02]],
];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - clamp(t, 0, 1), 3);
}

function params() {
  return new URLSearchParams(window.location.search);
}

function normalizeRecallCodeInput(value) {
  return String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4);
}

function normalizeSpatialRecallDraft(value) {
  const source = String(value || "").toUpperCase();
  let draft = "";
  for (const char of source) {
    if (XR_RECALL_CHARS.includes(char)) draft += char;
    if (draft.length >= 4) break;
  }
  return draft.padEnd(4, "-");
}

function recallDraftToCode(value) {
  const draft = String(value || "");
  if (draft.length !== 4 || draft.includes("-")) return "";
  return normalizeRecallCodeInput(draft);
}

function recallDraftToInputValue(value) {
  return String(value || "").replace(/-/g, "");
}

function formatSpatialRecallDraft(value, slot) {
  const draft = normalizeSpatialRecallDraft(value);
  return Array.from(draft)
    .map((char, index) => (index === slot ? `[${char}]` : ` ${char} `))
    .join("");
}

function getRecallCode() {
  return normalizeRecallCodeInput(params().get("code") || params().get("recall") || "");
}

function normalizePath(path) {
  if (!path) return "";
  const raw = String(path).replace(/\\/g, "/");
  if (/^(https?:|data:|blob:)/i.test(raw) || raw.startsWith("/")) return raw;
  return `/${raw}`;
}

function normalizeServedAssetPath(path) {
  if (!path) return "";
  const raw = String(path).replace(/\\/g, "/");
  const match = raw.match(/(?:^|\/)sessions\/.+/);
  if (!match) return raw;
  if (match.index === 0 && raw.startsWith("sessions/")) return raw;
  return match[0].startsWith("/") ? match[0] : `/${match[0]}`;
}

function getReplayPath() {
  return params().get("replay") || DEFAULT_REPLAY;
}

function useAutoplayReplay() {
  return params().get("autoplayReplay") === "1" || params().get("qaReplay") === "1";
}

function getSuitSpecPath() {
  return params().get("suitspec") || DEFAULT_SUITSPEC;
}

function getVoiceSeconds() {
  const raw = Number(params().get("seconds") || "4.5");
  return clamp(Number.isFinite(raw) ? raw : 4.5, 1.5, 8);
}

function getVoiceArmDelay() {
  const raw = Number(params().get("armDelay") || "1.4");
  return clamp(Number.isFinite(raw) ? raw : 1.4, 0.4, 3);
}

function useMockTrigger() {
  return params().get("mockTrigger") === "1";
}

function getAudioMode() {
  return params().get("audio") === "webm" ? "webm" : "wav";
}

function useMicrophoneCapture() {
  return params().get("mic") === "1" || !useMockTrigger();
}

function useHandTracking() {
  return params().get("hands") === "1";
}

function useQuestLiveBodyPose() {
  return params().get("liveBody") === "1";
}

function useQuestBaseSuitGuide() {
  return params().get("baseSuitGuide") !== "0";
}

function useMocopiLiveBodySim() {
  const search = params();
  const value = String(search.get("mocopiLive") || search.get("liveBodySim") || search.get("bodySimLive") || "").toLowerCase();
  return search.has("bodySimLatest")
    || search.has("mocopiLatest")
    || ["1", "true", "yes", "mocopi", "body_sim", "latest"].includes(value);
}

function getBodySimLatestPath() {
  return params().get("bodySimLatest") || params().get("mocopiLatest") || DEFAULT_BODY_SIM_LATEST;
}

function numberQueryParam(name, fallback, min = -Infinity, max = Infinity) {
  const raw = Number(params().get(name));
  return clamp(Number.isFinite(raw) ? raw : fallback, min, max);
}

function getLiveBodySimPollIntervalMs() {
  return numberQueryParam(
    "mocopiPollMs",
    numberQueryParam("bodySimPollMs", LIVE_BODY_SIM_DEFAULT_POLL_INTERVAL_MS),
    LIVE_BODY_SIM_MIN_POLL_INTERVAL_MS,
    LIVE_BODY_SIM_MAX_POLL_INTERVAL_MS,
  );
}

function getLiveBodySimRenderProfile() {
  return {
    xOffset: numberQueryParam("mocopiX", LIVE_BODY_SIM_RENDER_DEFAULTS.xOffset, -1.5, 1.5),
    yOffset: numberQueryParam("mocopiY", LIVE_BODY_SIM_RENDER_DEFAULTS.yOffset, -1.5, 1.5),
    zOffset: numberQueryParam("mocopiZ", LIVE_BODY_SIM_RENDER_DEFAULTS.zOffset, -1.5, 1.5),
    xSign: numberQueryParam("mocopiXSign", LIVE_BODY_SIM_RENDER_DEFAULTS.xSign, -1, 1) < 0 ? -1 : 1,
    ySign: numberQueryParam("mocopiYSign", LIVE_BODY_SIM_RENDER_DEFAULTS.ySign, -1, 1) < 0 ? -1 : 1,
    zSign: numberQueryParam("mocopiZSign", LIVE_BODY_SIM_RENDER_DEFAULTS.zSign, -1, 1) < 0 ? -1 : 1,
    scale: numberQueryParam("mocopiScale", LIVE_BODY_SIM_RENDER_DEFAULTS.scale, 0.25, 2),
    yawOffsetRad: THREE.MathUtils.degToRad(
      numberQueryParam("mocopiYawDeg", THREE.MathUtils.radToDeg(LIVE_BODY_SIM_RENDER_DEFAULTS.yawOffsetRad), -360, 360),
    ),
  };
}

function useQuestDebugTelemetry() {
  return params().get("debug") === "1" || params().has("qa");
}

function useWebPreviewPlacementParityQuery() {
  const value = String(params().get("webPreviewParity") || params().get("webPreviewPlacement") || "").toLowerCase();
  return ["1", "true", "yes", "web", "web_preview", "parity"].includes(value);
}

function voiceDeviceColorForState(state) {
  if (state === "ready" || state === "arming") return 0x36f28f;
  if (state === "recording") return 0xffcf5a;
  if (state === "analyzing") return 0x8a7cff;
  if (state === "detected" || state === "complete") return 0x43d8ff;
  if (state === "deposition") return 0xfff076;
  if (state === "rejected") return 0xff6b6b;
  return (VOICE_STATES[state] || VOICE_STATES.ready).color;
}

function questDebugMicrophoneSnapshot() {
  return {
    captureEnabled: useMicrophoneCapture(),
    mockTrigger: useMockTrigger(),
    secureContext: window.isSecureContext,
    hasMediaDevices: Boolean(navigator.mediaDevices?.getUserMedia),
    hasMediaRecorder: Boolean(window.MediaRecorder),
    audioMode: getAudioMode(),
  };
}

function questDebugUxStateSnapshot(demo) {
  const xrSession = Boolean(demo.world?.session);
  const viewMode = demo.xrViewMode || XR_VIEW_MODE_SELF;
  const playing = Boolean(demo.playing);
  const armorStandPreview = Boolean(demo.armorStandPreview);
  const playbackSource = demo.playbackSource || "voice";
  const loadedMeshes = demo.meshes?.size || 0;
  const progress = demo.duration ? clamp(demo.elapsed / demo.duration, 0, 1) : 0;
  const voiceState = demo.voiceState || "ready";
  const voiceStateIsHistorical =
    !playing && progress === 0 && ["complete", "detected", "deposition"].includes(voiceState);
  let uxState = "loaded_idle";
  if (!loadedMeshes) {
    uxState = xrSession ? "no_suit_idle" : "browser_no_suit_idle";
  } else if (armorStandPreview && !playing && viewMode === XR_VIEW_MODE_OBSERVER) {
    uxState = xrSession ? "armor_stand_observer_idle" : "browser_armor_stand_observer_idle";
  } else if (playing && playbackSource === "archive" && viewMode === XR_VIEW_MODE_MIRROR) {
    uxState = xrSession ? "archive_replay_mirror_active" : "browser_archive_replay_mirror_active";
  } else if (playing && playbackSource === "archive" && viewMode === XR_VIEW_MODE_OBSERVER) {
    uxState = xrSession ? "archive_replay_observer_active" : "browser_archive_replay_observer_active";
  } else if (playing && viewMode === XR_VIEW_MODE_SELF) {
    uxState = xrSession ? "transform_active_self" : "browser_transform_active_self";
  } else if (!playing && !armorStandPreview && viewMode === XR_VIEW_MODE_MIRROR) {
    uxState = xrSession ? "mirror_idle" : "browser_mirror_idle";
  } else if (!playing && !armorStandPreview && viewMode === XR_VIEW_MODE_SELF && loadedMeshes) {
    uxState = xrSession ? "loaded_idle_self" : "browser_loaded_idle_self";
  } else if (!playing && !armorStandPreview && viewMode === XR_VIEW_MODE_OBSERVER) {
    uxState = xrSession ? "observer_idle" : "browser_observer_idle";
  } else if (playing) {
    uxState = xrSession ? "transform_active" : "browser_transform_active";
  } else if (!xrSession) {
    uxState = "browser_loaded_idle";
  }
  return {
    uxState,
    voiceState,
    voiceStateIsHistorical,
    playbackSource,
    viewMode,
    xrSession,
    armorStandPreview,
    playing,
    loadedMeshes,
    progress: roundDebugNumber(progress, 3),
    shouldExpectMirror: [
      "archive_replay_mirror_active",
      "browser_archive_replay_mirror_active",
      "mirror_idle",
      "browser_mirror_idle",
    ].includes(uxState),
    shouldExpectArmorStand: [
      "armor_stand_observer_idle",
      "browser_armor_stand_observer_idle",
    ].includes(uxState),
    shouldExpectBaseSuitGuide: [
      "transform_active_self",
      "browser_transform_active_self",
      "archive_replay_mirror_active",
      "browser_archive_replay_mirror_active",
    ].includes(uxState),
    realMicrophoneExpected: useMicrophoneCapture() && !useMockTrigger(),
  };
}

function roundDebugNumber(value, digits = 4) {
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  const factor = 10 ** digits;
  return Math.round(number * factor) / factor;
}

function vectorDebugSnapshot(vector) {
  if (!vector) return null;
  return [
    roundDebugNumber(vector.x),
    roundDebugNumber(vector.y),
    roundDebugNumber(vector.z),
  ];
}

function vectorArrayDebugSnapshot(values) {
  if (!Array.isArray(values) || values.length < 3) return null;
  const numbers = values.slice(0, 3).map((value) => Number(value));
  if (!numbers.every((value) => Number.isFinite(value))) return null;
  return numbers.map((value) => roundDebugNumber(value));
}

function eulerDebugSnapshot(euler) {
  if (!euler) return null;
  return [
    roundDebugNumber(euler.x),
    roundDebugNumber(euler.y),
    roundDebugNumber(euler.z),
  ];
}

function yawDegDebugSnapshot(quaternion) {
  if (!quaternion) return null;
  QUEST_DEBUG_EULER.setFromQuaternion(quaternion, "YXZ");
  return roundDebugNumber(THREE.MathUtils.radToDeg(QUEST_DEBUG_EULER.y), 1);
}

function vectorDeltaDebugSnapshot(toVector, fromVector) {
  if (!toVector || !fromVector) return null;
  QUEST_DEBUG_VECTOR_A.copy(toVector).sub(fromVector);
  return vectorDebugSnapshot(QUEST_DEBUG_VECTOR_A);
}

function vectorDistanceDebugSnapshot(toVector, fromVector) {
  if (!toVector || !fromVector) return null;
  QUEST_DEBUG_VECTOR_A.copy(toVector).sub(fromVector);
  return roundDebugNumber(QUEST_DEBUG_VECTOR_A.length(), 3);
}

function yawDeltaDegDebugSnapshot(toQuaternion, fromQuaternion) {
  if (!toQuaternion || !fromQuaternion) return null;
  QUEST_DEBUG_EULER.setFromQuaternion(toQuaternion, "YXZ");
  const toYaw = QUEST_DEBUG_EULER.y;
  QUEST_DEBUG_EULER.setFromQuaternion(fromQuaternion, "YXZ");
  let delta = toYaw - QUEST_DEBUG_EULER.y;
  while (delta > Math.PI) delta -= TAU;
  while (delta < -Math.PI) delta += TAU;
  return roundDebugNumber(THREE.MathUtils.radToDeg(delta), 1);
}

function localVectorInObjectDebugSnapshot(object, worldVector) {
  if (!object || !worldVector) return null;
  QUEST_DEBUG_VECTOR_B.copy(worldVector);
  object.worldToLocal(QUEST_DEBUG_VECTOR_B);
  return vectorDebugSnapshot(QUEST_DEBUG_VECTOR_B);
}

function forwardVectorDebugSnapshot(quaternion) {
  if (!quaternion) return null;
  QUEST_DEBUG_VECTOR_C.set(0, 0, -1).applyQuaternion(quaternion).normalize();
  return vectorDebugSnapshot(QUEST_DEBUG_VECTOR_C);
}

function rigLocalPointWorldDebugSnapshot(rig, point) {
  if (!rig || !Array.isArray(point) || point.length < 3) return null;
  QUEST_DEBUG_VECTOR_C.fromArray(point);
  rig.localToWorld(QUEST_DEBUG_VECTOR_C);
  return vectorDebugSnapshot(QUEST_DEBUG_VECTOR_C);
}

function rigLocalPointWorldVector(rig, point, target) {
  if (!rig || !Array.isArray(point) || point.length < 3 || !target) return null;
  target.fromArray(point);
  rig.localToWorld(target);
  return target;
}

function rigLocalVectorWorldVector(rig, vector, target) {
  if (!rig || !vector || !target) return null;
  target.copy(vector);
  rig.localToWorld(target);
  return target;
}

function rigWorldPointLocalVector(rig, vector, target) {
  if (!rig || !vector || !target) return null;
  target.copy(vector);
  rig.worldToLocal(target);
  return target;
}

function objectWorldPositionVector(object, target) {
  if (!object || !target) return null;
  object.updateWorldMatrix?.(true, false);
  object.getWorldPosition(target);
  return target;
}

function meshBoundsCenterWorldVector(mesh, target) {
  if (!mesh?.geometry || !target) return null;
  try {
    if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
  } catch (error) {
    return null;
  }
  if (!mesh.geometry.boundingBox) return null;
  mesh.updateWorldMatrix?.(true, false);
  mesh.geometry.boundingBox.getCenter(target);
  mesh.localToWorld(target);
  return target;
}

function questLivePartAnchorLocalVector(demo, part, target) {
  if (
    !demo?.world?.session
    || !useQuestLiveBodyPose()
    || demo.xrViewMode !== XR_VIEW_MODE_SELF
    || typeof demo.getLiveBodyPartPosition !== "function"
  ) {
    return null;
  }
  return demo.getLiveBodyPartPosition(part, target);
}

function armorStandDebugTransform(demo) {
  return {
    yaw: demo?.armorStandYaw || 0,
    pitch: demo?.armorStandPitch || 0,
    scale: demo?.armorStandScale || 1,
    explode: demo?.armorStandExploded ? 1 : 0,
    offset: demo?.armorStandOffset || null,
  };
}

function questDebugAnchorLocalForPart(demo, part) {
  const assemblyPose = questAssemblyPoseForPart(part);
  if (!demo?.armorStandPreview) return assemblyPose;
  return armorStandRigPoseForPoint(
    assemblyPose,
    armorStandDebugTransform(demo),
    [0, 0, 0],
    armorStandExplodeVectorForPart(part),
  );
}

function questPartCenterDebugSnapshot(demo, part, mesh) {
  const canonicalAnchorLocal = questDebugAnchorLocalForPart(demo, part);
  const canonicalAnchorWorld = rigLocalPointWorldVector(demo?.rig, canonicalAnchorLocal, QUEST_DEBUG_VECTOR_D);
  const liveAnchorLocal = questLivePartAnchorLocalVector(demo, part, QUEST_DEBUG_VECTOR_G);
  const liveAnchorWorld = rigLocalVectorWorldVector(demo?.rig, liveAnchorLocal, QUEST_DEBUG_VECTOR_H);
  const meshOriginWorld = objectWorldPositionVector(mesh, QUEST_DEBUG_VECTOR_E);
  const meshBoundsCenterWorld = meshBoundsCenterWorldVector(mesh, QUEST_DEBUG_VECTOR_F);
  const meshOriginRigLocal = rigWorldPointLocalVector(demo?.rig, meshOriginWorld, QUEST_DEBUG_VECTOR_I);
  const meshBoundsCenterRigLocal = rigWorldPointLocalVector(demo?.rig, meshBoundsCenterWorld, QUEST_DEBUG_VECTOR_J);
  return {
    anchorPoseMode: demo?.armorStandPreview ? "armor_stand" : "worn_body",
    canonicalAnchorLocal: vectorArrayDebugSnapshot(canonicalAnchorLocal),
    canonicalAnchorWorld: vectorDebugSnapshot(canonicalAnchorWorld),
    liveAnchorLocal: vectorDebugSnapshot(liveAnchorLocal),
    liveAnchorWorld: vectorDebugSnapshot(liveAnchorWorld),
    meshOriginWorld: vectorDebugSnapshot(meshOriginWorld),
    meshBoundsCenterWorld: vectorDebugSnapshot(meshBoundsCenterWorld),
    meshOriginRigLocal: vectorDebugSnapshot(meshOriginRigLocal),
    meshBoundsCenterRigLocal: vectorDebugSnapshot(meshBoundsCenterRigLocal),
    originToBoundsCenterWorldM: vectorDeltaDebugSnapshot(meshBoundsCenterWorld, meshOriginWorld),
    canonicalAnchorToMeshOriginWorldM: vectorDeltaDebugSnapshot(meshOriginWorld, canonicalAnchorWorld),
    canonicalAnchorToBoundsCenterWorldM: vectorDeltaDebugSnapshot(meshBoundsCenterWorld, canonicalAnchorWorld),
    liveAnchorToMeshOriginWorldM: vectorDeltaDebugSnapshot(meshOriginWorld, liveAnchorWorld),
    liveAnchorToBoundsCenterWorldM: vectorDeltaDebugSnapshot(meshBoundsCenterWorld, liveAnchorWorld),
    originToBoundsCenterRigLocalM: vectorDeltaDebugSnapshot(meshBoundsCenterRigLocal, meshOriginRigLocal),
    canonicalAnchorToMeshOriginRigLocalM: vectorDeltaDebugSnapshot(meshOriginRigLocal, canonicalAnchorLocal ? QUEST_DEBUG_VECTOR_D.fromArray(canonicalAnchorLocal) : null),
    canonicalAnchorToBoundsCenterRigLocalM: vectorDeltaDebugSnapshot(meshBoundsCenterRigLocal, canonicalAnchorLocal ? QUEST_DEBUG_VECTOR_D.fromArray(canonicalAnchorLocal) : null),
    liveAnchorToMeshOriginRigLocalM: vectorDeltaDebugSnapshot(meshOriginRigLocal, liveAnchorLocal),
    liveAnchorToBoundsCenterRigLocalM: vectorDeltaDebugSnapshot(meshBoundsCenterRigLocal, liveAnchorLocal),
  };
}

function questVectorArrayLength(value) {
  if (!Array.isArray(value) || value.length < 3) return null;
  const numbers = value.slice(0, 3).map((entry) => Number(entry));
  if (!numbers.every((entry) => Number.isFinite(entry))) return null;
  return Math.hypot(numbers[0], numbers[1], numbers[2]);
}

function questVectorArrayAxis(value, index) {
  if (!Array.isArray(value) || value.length <= index) return null;
  const number = Number(value[index]);
  return Number.isFinite(number) ? number : null;
}

function questVectorDeltaArrayDebugSnapshot(toVector, fromVector) {
  if (!Array.isArray(toVector) || !Array.isArray(fromVector)) return null;
  const values = [0, 1, 2].map((index) => Number(toVector[index]) - Number(fromVector[index]));
  return values.every((value) => Number.isFinite(value))
    ? values.map((value) => roundDebugNumber(value))
    : null;
}

function questVectorArrayDistanceDebugSnapshot(toVector, fromVector) {
  if (!Array.isArray(toVector) || !Array.isArray(fromVector)) return null;
  const values = [0, 1, 2].map((index) => Number(toVector[index]) - Number(fromVector[index]));
  return values.every((value) => Number.isFinite(value))
    ? roundDebugNumber(Math.hypot(values[0], values[1], values[2]), 3)
    : null;
}

function questVectorArraysNearlyEqual(left, right, epsilon = 0.0005) {
  if (!Array.isArray(left) || !Array.isArray(right)) return false;
  return [0, 1, 2].every((index) => {
    const delta = Math.abs(Number(left[index]) - Number(right[index]));
    return Number.isFinite(delta) && delta <= epsilon;
  });
}

function questRuntimePlacementAnchorDiagnosticsForPart(part, placement) {
  const activeMode = useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig";
  const questOffsetRaw = questOffsetArrayFromPlacement(placement);
  const questOffsetClamped = clampedQuestOffsetArrayFromPlacement(part, placement);
  const webOffsetRaw = webPreviewOffsetArrayFromPlacement(placement);
  const webOffsetClamped = webPreviewSurfaceOffsetArrayFromPlacement(placement)
    || (webOffsetRaw ? clampSurfaceOffsetForPart(part, webOffsetRaw, "vrm") : null);
  const activeOffsetClamped = runtimePlacementOffsetArrayForPart(part, placement);
  const activeOffsetSource =
    questVectorArraysNearlyEqual(activeOffsetClamped, webOffsetClamped) ? "web_preview_parity"
    : questVectorArraysNearlyEqual(activeOffsetClamped, questOffsetClamped) ? "quest_rig"
    : activeOffsetClamped ? "custom_or_unmatched"
    : "none";
  return {
    version: "quest-runtime-anchor-diagnostics.v1",
    activeMode,
    activeOffsetSource,
    activeOffsetClamped: vectorArrayDebugSnapshot(activeOffsetClamped),
    questRigOffsetRaw: vectorArrayDebugSnapshot(questOffsetRaw),
    questRigOffsetClamped: vectorArrayDebugSnapshot(questOffsetClamped),
    webPreviewOffsetRaw: vectorArrayDebugSnapshot(webOffsetRaw),
    webPreviewOffsetClamped: vectorArrayDebugSnapshot(webOffsetClamped),
    questVsWebOffsetDeltaM: questVectorDeltaArrayDebugSnapshot(webOffsetClamped, questOffsetClamped),
    questVsWebOffsetDistanceM: questVectorArrayDistanceDebugSnapshot(webOffsetClamped, questOffsetClamped),
  };
}

function questTopCenterlinePart(records, mapper, limit = 5) {
  return records
    .map((record) => {
      const vector = mapper(record);
      const length = questVectorArrayLength(vector);
      const valueM = Number.isFinite(length) ? roundDebugNumber(length, 3) : null;
      return {
        part: record.part,
        meshSource: record.meshSource || "",
        valueM,
        vector,
        runtimeOffsetClamped: record.runtimeOffsetClamped || null,
      };
    })
    .filter((record) => Number.isFinite(record.valueM))
    .sort((a, b) => b.valueM - a.valueM)
    .slice(0, limit);
}

function questCountBy(records, mapper) {
  return records.reduce((counts, record) => {
    const key = mapper(record) || "unknown";
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});
}

function questDominantCountKey(counts) {
  return Object.entries(counts)
    .sort((left, right) => right[1] - left[1])
    .map(([key]) => key)[0] || "none";
}

function questAnchorDiagnosticsSnapshot({
  payload,
  visibleRecords,
  anchorFailures,
  hardSyncFailures,
  partAnchorParts,
  glbOriginParts,
}) {
  const runtimePlacementModeCounts = questCountBy(visibleRecords, (record) => record.runtimePlacementMode);
  const activeOffsetSourceCounts = questCountBy(
    visibleRecords,
    (record) => record.anchorDiagnostics?.activeOffsetSource,
  );
  const dominantRuntimePlacementMode = questDominantCountKey(runtimePlacementModeCounts);
  const dominantActiveOffsetSource = questDominantCountKey(activeOffsetSourceCounts);
  const runtimeOffsetImplicated = partAnchorParts.length > 0;
  const likelySource =
    anchorFailures.length && !runtimeOffsetImplicated && glbOriginParts.length === 0
      ? "runtime_anchor_not_runtime_offset"
      : runtimeOffsetImplicated
      ? `runtime_offset_${dominantActiveOffsetSource}`
      : glbOriginParts.length
      ? "glb_origin_bounds"
      : hardSyncFailures.length
      ? "hard_sync_centerline"
      : "no_centerline_failure";
  return {
    version: "quest-anchor-diagnostics.v1",
    queryWebPreviewParity: payload?.query?.webPreviewParity || "",
    queryWebPreviewPlacement: payload?.query?.webPreviewPlacement || "",
    runtimePlacementModeCounts,
    activeOffsetSourceCounts,
    dominantRuntimePlacementMode,
    dominantActiveOffsetSource,
    runtimeOffsetImplicated,
    likelySource,
    failureCounts: {
      runtimeAnchor: anchorFailures.length,
      hardSync: hardSyncFailures.length,
      partRuntimeOffset: partAnchorParts.length,
      glbOriginBounds: glbOriginParts.length,
    },
    triageHint: `${likelySource}; activeOffset=${dominantActiveOffsetSource}; mode=${dominantRuntimePlacementMode}`,
  };
}

function questCoherentLateralDrift(records, mapper) {
  const samples = records
    .map((record) => questVectorArrayAxis(mapper(record), 0))
    .filter((value) => Number.isFinite(value) && Math.abs(value) >= QUEST_CENTERLINE_QA_THRESHOLDS.coherentPartLateralMinM);
  const positive = samples.filter((value) => value > 0);
  const negative = samples.filter((value) => value < 0);
  const dominant = positive.length >= negative.length ? positive : negative;
  const sign = dominant === positive ? "right" : "left";
  const averageAbsM = dominant.length
    ? dominant.reduce((sum, value) => sum + Math.abs(value), 0) / dominant.length
    : 0;
  return {
    sign: dominant.length ? sign : "none",
    count: dominant.length,
    sampleCount: samples.length,
    averageAbsM: roundDebugNumber(averageAbsM, 3),
  };
}

function questCenterlineQaSnapshot(payload) {
  const xr = payload?.xr || {};
  const records = payload?.meshes?.records || [];
  const visibleRecords = records.filter((record) => record.visible !== false && record.partCenter);
  const liveBodyActive = Boolean(xr.liveBodyPose && xr.viewMode === XR_VIEW_MODE_SELF);
  const activeAnchorToBounds = (record) =>
    (liveBodyActive && record.partCenter?.liveAnchorToBoundsCenterRigLocalM)
    || record.partCenter?.canonicalAnchorToBoundsCenterRigLocalM;
  const activeAnchorToOrigin = (record) =>
    (liveBodyActive && record.partCenter?.liveAnchorToMeshOriginRigLocalM)
    || record.partCenter?.canonicalAnchorToMeshOriginRigLocalM;
  const thresholds = QUEST_CENTERLINE_QA_THRESHOLDS;
  const xrAnchorQaActive = Boolean(xr.session);

  const anchorFailures = [];
  if (xrAnchorQaActive && !xr.xrWorldAnchorReady) anchorFailures.push("anchor_not_ready");
  if (
    xrAnchorQaActive
    && xr.xrWorldAnchorProfile
    && xr.expectedAnchorProfile
    && xr.xrWorldAnchorProfile !== xr.expectedAnchorProfile
  ) {
    anchorFailures.push("anchor_profile_mismatch");
  }
  if (xrAnchorQaActive && Number(xr.anchorToRigDistanceM) > thresholds.anchorToRigDistanceMaxM) {
    anchorFailures.push("anchor_to_rig_distance");
  }
  if (xrAnchorQaActive && Math.abs(Number(xr.anchorToRigYawDeltaDeg)) > thresholds.anchorToRigYawMaxDeg) {
    anchorFailures.push("anchor_to_rig_yaw");
  }

  const cameraLocalX = xrAnchorQaActive ? questVectorArrayAxis(xr.cameraLocalInRig, 0) : null;
  const coherentLateral = questCoherentLateralDrift(visibleRecords, activeAnchorToBounds);
  const hardSyncFailures = [];
  if (Number.isFinite(cameraLocalX) && Math.abs(cameraLocalX) > thresholds.cameraLocalXMaxM) {
    hardSyncFailures.push("camera_local_x");
  }
  if (coherentLateral.count >= 4 && coherentLateral.averageAbsM >= thresholds.coherentPartLateralMinM) {
    hardSyncFailures.push("coherent_part_lateral");
  }

  const topActiveAnchorToBounds = questTopCenterlinePart(visibleRecords, activeAnchorToBounds);
  const topActiveAnchorToOrigin = questTopCenterlinePart(visibleRecords, activeAnchorToOrigin);
  const topOriginToBounds = questTopCenterlinePart(
    visibleRecords,
    (record) => record.partCenter?.originToBoundsCenterRigLocalM,
  );
  const partAnchorParts = topActiveAnchorToOrigin.filter((record) => record.valueM > thresholds.partAnchorDeltaMaxM);
  const glbOriginParts = topOriginToBounds.filter((record) => record.valueM > thresholds.glbOriginToBoundsMaxM);

  const classification = [];
  if (anchorFailures.length) classification.push("runtime_anchor");
  if (!anchorFailures.length && hardSyncFailures.length) classification.push("hard_sync_centerline");
  if (!anchorFailures.length && partAnchorParts.length) classification.push("part_anchor_runtime_offset");
  if (!anchorFailures.length && glbOriginParts.length) classification.push("glb_origin_bounds");
  const finalClassification =
    classification.length > 1 ? "mixed" : classification[0] || "pass";
  const verdict = finalClassification === "pass" ? "pass" : anchorFailures.length ? "fail" : "warn";
  const anchorDiagnostics = questAnchorDiagnosticsSnapshot({
    payload,
    visibleRecords,
    anchorFailures,
    hardSyncFailures,
    partAnchorParts,
    glbOriginParts,
  });

  return {
    version: "quest-centerline-qa.v1",
    verdict,
    classification: finalClassification,
    flags: classification,
    thresholds,
    checks: {
      runtimeAnchor: {
        state: !xrAnchorQaActive ? "skipped" : anchorFailures.length ? "fail" : "pass",
        active: xrAnchorQaActive,
        failures: anchorFailures,
        anchorToRigDistanceM: xr.anchorToRigDistanceM ?? null,
        anchorToRigYawDeltaDeg: xr.anchorToRigYawDeltaDeg ?? null,
        anchorProfile: xr.xrWorldAnchorProfile || null,
        expectedAnchorProfile: xr.expectedAnchorProfile || null,
      },
      hardSync: {
        state: hardSyncFailures.length ? "warn" : "pass",
        failures: hardSyncFailures,
        cameraLocalX: Number.isFinite(cameraLocalX) ? roundDebugNumber(cameraLocalX, 3) : null,
        coherentLateral,
      },
      partAnchorRuntimeOffset: {
        state: partAnchorParts.length ? "warn" : "pass",
        parts: partAnchorParts,
        topActiveAnchorToOrigin,
        topActiveAnchorToBounds,
      },
      glbOriginBounds: {
        state: glbOriginParts.length ? "warn" : "pass",
        parts: glbOriginParts,
        topOriginToBounds,
      },
    },
    anchorDiagnostics,
    displayLine: `centerline QA ${verdict}/${finalClassification} anchor=${!xrAnchorQaActive ? "SKIP" : anchorFailures.length ? "NG" : "OK"} hard=${hardSyncFailures.length ? "WARN" : "OK"} part=${partAnchorParts.length} glb=${glbOriginParts.length} mode=${anchorDiagnostics.dominantRuntimePlacementMode} offset=${anchorDiagnostics.dominantActiveOffsetSource}`,
  };
}

function questDebugQuerySnapshot() {
  const query = params();
  return {
    href: window.location.href,
    userAgent: navigator.userAgent,
    newRoute: query.get("newRoute") || "",
    code: getRecallCode(),
    replay: query.get("replay") || "",
    replayView: query.get("replayView") || "",
    autoplayReplay: query.get("autoplayReplay") || "",
    mockTrigger: query.get("mockTrigger") || "",
    mic: query.get("mic") || "",
    liveBody: query.get("liveBody") || "",
    webPreviewParity: query.get("webPreviewParity") || "",
    webPreviewPlacement: query.get("webPreviewPlacement") || "",
    debug: query.get("debug") || "",
    qa: query.get("qa") || "",
    apiBase: getApiBase(),
  };
}

async function postQuestDebugTelemetry(payload) {
  if (!useQuestDebugTelemetry()) return;
  try {
    const response = await fetch(`${getApiBase()}/api/quest-debug`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    });
    if (!response.ok) throw new Error(`POST /api/quest-debug failed with ${response.status}`);
  } catch (error) {
    console.warn("[Quest debug telemetry]", error);
  }
}

function getArchiveViewMode() {
  return params().get("replayView") === XR_VIEW_MODE_OBSERVER ? XR_VIEW_MODE_OBSERVER : XR_VIEW_MODE_MIRROR;
}

function formatArchiveViewMode(mode) {
  return mode === XR_VIEW_MODE_OBSERVER ? "観察" : "鏡";
}

function makeMockAudioCapture() {
  return {
    blob: new Blob(["dry-run"], { type: "audio/wav" }),
    stats: {
      mode: "mock",
      mime_type: "audio/wav",
      sample_rate: 48000,
      channels: 1,
      samples: 0,
      duration_sec: 0.1,
      requested_sec: 0,
      peak: 0,
      rms: 0,
      quiet: false,
    },
  };
}

function useNewRouteApi() {
  return params().get("newRoute") === "1" || Boolean(getRecallCode());
}

function getApiBase() {
  const raw = params().get("apiBase") || "";
  return raw.replace(/\/$/, "");
}

function getSuitId() {
  return params().get("suit") || DEFAULT_SUIT_ID;
}

function getManifestId() {
  return params().get("manifest") || DEFAULT_MANIFEST_ID;
}

function getOperatorId() {
  return params().get("operator") || "quest-browser";
}

function getDeviceId() {
  return params().get("device") || (navigator.userAgent.includes("Quest") ? "quest-browser" : "iw-sdk-dev");
}

function makeTrialId() {
  return `S-IW-QUEST-${Date.now().toString(16).toUpperCase()}`;
}

async function postJson(path, payload) {
  const response = await fetch(`${getApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `POST ${path} failed with ${response.status}`);
  }
  return data;
}

async function getJson(path, options = {}) {
  const attempts = Math.max(1, Number(options.attempts || 1));
  let lastError = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(`${getApiBase()}${path}`, { cache: "no-store" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.ok === false) {
        const error = new Error(data.error || `GET ${path} failed with ${response.status}`);
        error.status = response.status;
        throw error;
      }
      return data;
    } catch (error) {
      lastError = error;
      const status = Number(error?.status || 0);
      const retriable = status >= 500 || error instanceof TypeError;
      if (!retriable || attempt >= attempts) throw error;
      await sleep(180 * attempt);
    }
  }
  throw lastError;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function compactToken(value, maxLength = 34) {
  const text = String(value || "");
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(4, maxLength - 4))}...`;
}

const ROUTE_LABELS_JA = new Map([
  ["/v1 ARMED", "/v1 待機"],
  ["OFF", "停止"],
  ["NEW", "新規"],
  ["LOCAL", "ローカル"],
  ["WAIT", "待機"],
  ["WAIT CODE", "コード待ち"],
  ["CODE INPUT", "コード確認"],
  ["CODE ERROR", "コードエラー"],
  ["VOICE ERROR", "音声エラー"],
  ["SUIT POST", "スーツ保存"],
  ["MANIFEST", "マニフェスト"],
  ["TRIAL CREATE", "試験作成"],
  ["TRIAL READY", "試験準備OK"],
  ["EVENT ERROR", "イベントエラー"],
  ["DEPOSITION_STARTED", "蒸着開始"],
  ["DEPOSITION_COMPLETED", "蒸着完了"],
  ["BUILDING", "作成中"],
  ["READY", "準備OK"],
  ["ERROR", "エラー"],
]);

function localizeRouteToken(value) {
  const text = String(value || "").trim();
  if (!text) return "待機";
  const upper = text.toUpperCase();
  const codeMatch = text.match(/^CODE\s+(\d{4})(.*)$/i);
  if (codeMatch) {
    const suffix = codeMatch[2]?.trim();
    return suffix ? `コード ${codeMatch[1]} ${localizeRouteToken(suffix)}` : `コード ${codeMatch[1]}`;
  }
  const eventMatch = text.match(/^([A-Z_]+)(\s+#\d+)?$/);
  if (eventMatch && ROUTE_LABELS_JA.has(eventMatch[1])) {
    return `${ROUTE_LABELS_JA.get(eventMatch[1])}${eventMatch[2] || ""}`;
  }
  const recallMatch = text.match(/^RECALL\s+(\d{4})$/i);
  if (recallMatch) return `呼び出し ${recallMatch[1]}`;
  if (/^RPL-[A-Z0-9-]+$/i.test(text)) return "記録作成済み";
  if (ROUTE_LABELS_JA.has(upper)) return ROUTE_LABELS_JA.get(upper);
  return text
    .replace(/\bWAIT\b/g, "待機")
    .replace(/\bREADY\b/g, "準備OK")
    .replace(/\bERROR\b/g, "エラー");
}

function localizeMotionToken(value) {
  const text = String(value || "").trim();
  const upper = text.toUpperCase();
  if (!upper) return "待機";
  if (upper.startsWith("MOCOPI+LIVE")) return upper.replace("MOCOPI+LIVE", "mocopi+実動");
  if (upper.startsWith("MOCOPI")) return upper.replace("MOCOPI", "mocopi");
  if (upper.startsWith("BODY")) return upper.replace("BODY", "身体");
  if (upper.startsWith("CAPTURE")) return upper.replace("CAPTURE", "取得中");
  if (upper.startsWith("STATIC")) return upper.replace("STATIC", "静止");
  if (upper.startsWith("SELF")) return upper.replace("SELF", "一人称");
  return text;
}

function setOperatorStateHelp(state = "pending", detail = "") {
  if (!UI.operatorStateHelp) return;
  const label = operatorStateLabel(state);
  const colorGuide = operatorStateColorGuide(state);
  UI.operatorStateHelp.dataset.state = state;
  UI.operatorStateHelp.textContent = `${label} / ${detail || colorGuide}`;
  UI.operatorStateHelp.title = colorGuide;
}

function setBadge(element, text, state = "idle") {
  if (!element) return;
  element.textContent = text;
  element.dataset.state = state;
  element.dataset.operatorStateLabel = operatorStateLabel(state);
  element.title = operatorStateColorGuide(state);
  element.setAttribute("aria-label", `${operatorStateLabel(state)}: ${text}`);
}

function setRouteContract(element, suitspec, runtimePackage = null) {
  if (!element) return;
  const checks = runtimeChecksFromPackage(runtimePackage);
  const bodyFit = bodyFitContractFromPackage(runtimePackage);
  if (checks || bodyFit) {
    const bodyFitLabel = bodyFit?.contract_version
      ? `体型適合v1 ${bodyFit.height_cm || "--"}cm`
      : "体型適合 --";
    const renderState = checks?.can_render_runtime_suit === false ? "装備不足" : "装備完了";
    const visible = Number(checks?.visible_overlay_count ?? 0);
    const minimum = Number(checks?.minimum_visible_overlay_parts ?? 0);
    element.textContent = `実行: ${renderState} / ${bodyFitLabel} / 表示 ${visible}/${minimum} / 表面 ${formatTextureFallbackLabel(suitspec)}`;
    return;
  }
  element.textContent = `体型適合: ${formatFitContractLabel(suitspec)} / 表面処理: ${formatTextureFallbackLabel(suitspec)}`;
}

function enabledArmorParts(suitspec) {
  const modules = suitspec?.modules || {};
  return ARMOR_PARTS.filter((part) => modules[part]?.enabled === true);
}

function runtimeArmorAsset(runtimePackage, part) {
  const asset = runtimePackage?.visual_layers?.armor_overlay?.assets?.[part]
    || runtimePackage?.visualLayers?.armorOverlay?.assets?.[part]
    || null;
  return asset && typeof asset === "object" ? asset : null;
}

function runtimeRenderPlacement(runtimePackage, part) {
  const placement = runtimePackage?.render_placements?.[part]
    || runtimePackage?.visual_layers?.armor_overlay?.render_placements?.[part]
    || runtimePackage?.visualLayers?.armorOverlay?.renderPlacements?.[part]
    || null;
  return placement && typeof placement === "object" ? placement : null;
}

function runtimePlacementContractUsesWebPreviewParity(runtimePackage, placement = null) {
  const contract = runtimePackage?.render_contract || runtimePackage?.renderContract || {};
  const values = [
    placement?.quest_runtime_placement_mode,
    placement?.runtime_placement_mode,
    placement?.placement_mode,
    placement?.web_preview_parity,
    contract?.quest_runtime_placement_mode,
    contract?.runtime_placement_mode,
    contract?.placement_mode,
    contract?.web_preview_parity,
  ].map((value) => String(value || "").toLowerCase());
  return values.some((value) => ["1", "true", "web_preview_parity", "web_preview", "web-preview", "web", "parity"].includes(value));
}

function webPreviewParityPlacement(runtimePackage, placement) {
  if (!placement || typeof placement !== "object") return null;
  const useParity = useWebPreviewPlacementParityQuery()
    || runtimePlacementContractUsesWebPreviewParity(runtimePackage, placement);
  return {
    ...placement,
    quest_runtime_placement_mode: useParity ? "web_preview_parity" : "quest_rig",
  };
}

function moduleForRuntimePart(suitspec, runtimePackage, part) {
  const source = suitspec?.modules?.[part];
  if (!source || source.enabled !== true) return null;
  const module = { ...source };
  const runtimeAsset = runtimeArmorAsset(runtimePackage, part);
  const runtimePlacement = runtimeRenderPlacement(runtimePackage, part);
  if (runtimeAsset?.asset_ref) module.asset_ref = runtimeAsset.asset_ref;
  if (runtimeAsset?.selected_variant_key) module.selected_variant_key = runtimeAsset.selected_variant_key;
  if (runtimeAsset?.asset_kind) module.asset_kind = runtimeAsset.asset_kind;
  if (runtimePlacement?.asset_ref) module.asset_ref = runtimePlacement.asset_ref;
  if (runtimePlacement?.selected_variant_key) module.selected_variant_key = runtimePlacement.selected_variant_key;
  if (runtimePlacement) module.runtime_placement = webPreviewParityPlacement(runtimePackage, runtimePlacement);
  return module;
}

function hasBaseSuitData(suitspec, suitRecord = null) {
  return Boolean(
    suitspec
      && (
        suitspec.base_suit
        || suitspec.baseSuit
        || suitspec.palette
        || suitspec.fit_contract
        || suitspec.suit_id
        || suitRecord?.suit_id
      ),
  );
}

function hasVrmReference(suitspec, suitRecord = null) {
  return Boolean(
    suitspec?.vrm
      || suitspec?.vrm_url
      || suitspec?.vrmUrl
      || suitspec?.base_vrm
      || suitspec?.avatar?.vrm
      || suitspec?.avatar?.vrm_url
      || suitspec?.artifacts?.vrm_path
      || suitspec?.artifacts?.vrm_url
      || suitRecord?.vrm
      || suitRecord?.vrm_url
      || suitRecord?.vrmUrl
      || suitRecord?.artifacts?.vrm_path
      || suitRecord?.artifacts?.vrm_url,
  );
}

function resolveBaseSuitVrmAssetRef(suitspec, suitRecord = null) {
  const candidates = [
    params().get("baseSuitVrm"),
    params().get("vrmBaseSuit"),
    suitspec?.body_profile?.vrm_baseline_ref,
    suitspec?.base_suit?.vrm_ref,
    suitspec?.base_suit?.vrm_url,
    suitspec?.baseSuit?.vrmRef,
    suitspec?.baseSuit?.vrmUrl,
    suitspec?.vrm,
    suitspec?.vrm_url,
    suitspec?.vrmUrl,
    suitspec?.base_vrm,
    suitspec?.avatar?.vrm,
    suitspec?.avatar?.vrm_url,
    suitspec?.artifacts?.vrm_path,
    suitspec?.artifacts?.vrm_url,
    suitRecord?.vrm,
    suitRecord?.vrm_url,
    suitRecord?.vrmUrl,
    suitRecord?.artifacts?.vrm_path,
    suitRecord?.artifacts?.vrm_url,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) return candidate.trim();
  }
  return "";
}

function runtimeChecksFromPackage(runtimePackage) {
  return runtimePackage?.runtime_checks && typeof runtimePackage.runtime_checks === "object"
    ? runtimePackage.runtime_checks
    : null;
}

function bodyFitContractFromPackage(runtimePackage) {
  return runtimePackage?.body_fit_contract && typeof runtimePackage.body_fit_contract === "object"
    ? runtimePackage.body_fit_contract
    : null;
}

function modelQualityGateFromPackage(runtimePackage) {
  return runtimePackage?.model_quality_gate && typeof runtimePackage.model_quality_gate === "object"
    ? runtimePackage.model_quality_gate
    : null;
}

function hasFiniteVector(values, length = 3) {
  return Array.isArray(values)
    && values.length >= length
    && values.slice(0, length).every((value) => Number.isFinite(Number(value)));
}

function runtimePlacementDiagnostic(runtimePackage, meshes = new Map()) {
  const checks = runtimeChecksFromPackage(runtimePackage);
  const placements = runtimePackage?.render_placements
    || runtimePackage?.visual_layers?.armor_overlay?.render_placements
    || {};
  const placementRecords = Object.values(placements).filter((placement) => placement && typeof placement === "object");
  const placementCount = placementRecords.length;
  const rotationCount = placementRecords.filter((placement) => hasFiniteVector(placement.rotation_deg)).length;
  const offsetCount = placementRecords.filter((placement) => (
    hasFiniteVector(placement.quest_surface_offset_clamped_m)
    || hasFiniteVector(placement.surface_anchor?.quest_rig_offset_clamped_m)
    || hasFiniteVector(placement.quest_rig_offset_m)
    || hasFiniteVector(placement.surface_offset_clamped_m)
    || hasFiniteVector(placement.surface_anchor?.offset_clamped_m)
    || hasFiniteVector(placement.offset_m)
  )).length;
  const targetCount = placementRecords.filter((placement) => (
    hasFiniteVector(placement.target_size_array_m)
    || hasFiniteVector([
      placement.target_size_m?.x,
      placement.target_size_m?.y,
      placement.target_size_m?.z,
    ])
  )).length;
  const meshRecords = Array.from(meshes.values());
  const glbCount = meshRecords.filter((mesh) => mesh?.userData?.meshSource === "glb_asset").length;
  const fallbackCount = meshRecords.filter((mesh) => String(mesh?.userData?.meshSource || "").includes("fallback")).length;
  const placedMeshCount = meshRecords.filter((mesh) => runtimePlacementForMesh(mesh)).length;
  const rotatedMeshCount = meshRecords.filter((mesh) => hasFiniteVector(runtimePlacementForMesh(mesh)?.rotation_deg)).length;
  const visible = Number(checks?.visible_overlay_count ?? glbCount);
  const minimum = Number(checks?.minimum_visible_overlay_parts ?? 0);
  const gate = checks?.can_render_runtime_suit === false ? "FAIL" : "OK";
  const missing = [
    ...(Array.isArray(checks?.missing_required_overlay_parts) ? checks.missing_required_overlay_parts : []),
    ...(Array.isArray(checks?.missing_required_body_fit_slots) ? checks.missing_required_body_fit_slots : []),
  ].filter((value, index, array) => value && array.indexOf(value) === index);
  return [
    "RUNTIME DIAGNOSTIC",
    `gate: ${gate} visible ${visible}/${minimum}`,
    `placement: ${placementCount} records, ${offsetCount} offsets, ${rotationCount} rotations, ${targetCount} targets`,
    `meshes: ${meshRecords.length} loaded, ${glbCount} GLB, ${fallbackCount} fallback, ${placedMeshCount} placed, ${rotatedMeshCount} rotated`,
    missing.length ? `missing: ${missing.join(",")}` : "missing: none",
  ].join("\n");
}

function makeEquipmentDiagnostic(suitspec, loadedPartCount = 0, suitRecord = null, runtimePackage = null) {
  const totalParts = ARMOR_PARTS.length;
  const checks = runtimeChecksFromPackage(runtimePackage);
  const bodyFit = bodyFitContractFromPackage(runtimePackage);
  const modelGate = modelQualityGateFromPackage(runtimePackage);
  const runtimeEnabledParts = Array.isArray(checks?.enabled_overlay_parts) ? checks.enabled_overlay_parts : [];
  const visibleRuntimeParts = Array.isArray(checks?.visible_overlay_parts) ? checks.visible_overlay_parts : [];
  const enabledParts = runtimeEnabledParts.length ? runtimeEnabledParts : enabledArmorParts(suitspec);
  const enabledCount = enabledParts.length;
  const loadedCount = clamp(Number(loadedPartCount) || visibleRuntimeParts.length || 0, 0, totalParts);
  const baseOk = Boolean(runtimePackage?.visual_layers?.base_suit?.asset_ref) || hasBaseSuitData(suitspec, suitRecord);
  const baseLabel = baseOk ? "基礎OK" : "基礎未確認";
  const missingCore = [
    ...(Array.isArray(checks?.missing_required_overlay_parts) ? checks.missing_required_overlay_parts : []),
    ...(Array.isArray(checks?.missing_required_body_fit_slots) ? checks.missing_required_body_fit_slots : []),
  ].filter((value, index, array) => value && array.indexOf(value) === index);
  const selectedSlotCount = Array.isArray(bodyFit?.selected_slots) ? bodyFit.selected_slots.length : enabledCount;
  const gateSummary = modelGate?.summary || {};
  const gateRequired = Number(gateSummary.required_count || modelGate?.required_parts?.length || modelGate?.p0_parts?.length || 0);
  const gatePass = Number(gateSummary.required_pass_count || gateSummary.pass_count || 0);
  const gateReason = Array.isArray(modelGate?.reasons) && modelGate.reasons.length
    ? String(modelGate.reasons[0])
    : "";

  if (!suitspec) {
    const payload = {
      state: "pending",
      label: "装備待機",
      summary: "4桁コードで呼び出し",
      detail: "基礎 -- / 分割鎧 --",
    };
  }

  if (checks && checks.can_render_runtime_suit === false) {
    return {
      state: "error",
      label: "装備データ不足",
      summary: missingCore.length ? `不足 ${missingCore.join("/")}` : "VRMのみ / 分割鎧不足",
      detail: `${baseLabel} / 表示鎧 ${visibleRuntimeParts.length}/${Math.max(selectedSlotCount, enabledCount, 1)}`,
    };
  }

  if (!enabledCount) {
    return {
      state: "error",
      label: "装備データ不足",
      summary: hasVrmReference(suitspec, suitRecord) ? "VRMのみ / 分割鎧なし" : "分割鎧なし",
      detail: `${baseLabel} / 分割鎧 0/${totalParts}`,
    };
  }

  if (!baseOk) {
    return {
      state: "warning",
      label: "基礎スーツ未確認",
      summary: `分割鎧 ${loadedCount}/${totalParts}`,
      detail: `基礎未確認 / 予定 ${enabledCount}/${totalParts}`,
    };
  }

  if (loadedCount < enabledCount) {
    return {
      state: "pending",
      label: "装備読込中",
      summary: `基礎OK / 分割鎧 ${loadedCount}/${enabledCount}`,
      detail: `体型適合 ${selectedSlotCount}スロット`,
    };
  }

  if (modelGate?.status === "fail") {
    return {
      state: "warning",
      label: "モデルGate未通過",
      summary: `P0 ${gatePass}/${gateRequired || "?"} / 試験表示は可能`,
      detail: gateReason || "bounds/UV/法線/三角形をWeb側で再構築してください",
    };
  }

  if (modelGate?.status === "warn") {
    return {
      state: "warning",
      label: "モデルGate要確認",
      summary: `P0 ${gatePass}/${gateRequired || "?"} / 試験表示は可能`,
      detail: gateReason || "P0モデル品質に警告があります",
    };
  }

  if (enabledCount < totalParts) {
    return {
      state: "warning",
      label: "装備一部不足",
      summary: `基礎OK / 分割鎧 ${enabledCount}/${totalParts}`,
      detail: `不足 ${totalParts - enabledCount}パーツ`,
    };
  }

  return {
    state: "ok",
    label: "装備完了",
    summary: `基礎OK / 分割鎧 ${loadedCount}/${enabledCount}`,
    detail: runtimePackage
      ? `実行パッケージ確認済み / 体型適合 ${selectedSlotCount}スロット / モデル ${formatModelGateStatusLabel(modelGate?.status)}`
      : "スーツ仕様 + マニフェスト確認済み",
  };
}

function equipmentStateStyle(state) {
  if (state === "error") {
    return { color: "#ffd2d2", border: "rgba(255, 107, 107, 0.72)" };
  }
  if (state === "warning") {
    return { color: "#fff4c8", border: "rgba(255, 207, 90, 0.72)" };
  }
  if (state === "ok") {
    return { color: "#d7f8ff", border: "rgba(67, 216, 255, 0.58)" };
  }
  return { color: "#fff4c8", border: "rgba(255, 207, 90, 0.42)" };
}

function formatEquipmentSpatialText(diagnostic) {
  const status = diagnostic || makeEquipmentDiagnostic(null);
  return `${status.label} | ${status.summary}`;
}

function ensureEquipmentStatusElement() {
  if (UI.equipmentStatus) return UI.equipmentStatus;
  const recallDock = document.querySelector(".recall-dock");
  if (!recallDock) return null;

  const root = document.createElement("div");
  root.id = "equipmentStatus";
  root.className = "equipment-status";
  root.dataset.state = "pending";
  root.setAttribute("role", "status");
  root.setAttribute("aria-live", "polite");

  const title = document.createElement("strong");
  title.className = "equipment-status__title";
  title.dataset.equipmentTitle = "";
  const body = document.createElement("span");
  body.className = "equipment-status__body";
  body.dataset.equipmentBody = "";
  const meta = document.createElement("span");
  meta.className = "equipment-status__meta";
  meta.dataset.equipmentMeta = "";

  root.append(title, body, meta);
  if (UI.recallCodeState?.parentElement) {
    UI.recallCodeState.insertAdjacentElement("afterend", root);
  } else {
    recallDock.appendChild(root);
  }
  UI.equipmentStatus = root;
  return root;
}

function updateEquipmentStatusElement(diagnostic) {
  const root = ensureEquipmentStatusElement();
  if (!root) return;
  const status = diagnostic || makeEquipmentDiagnostic(null);
  root.dataset.state = status.state;
  root.querySelector("[data-equipment-title]").textContent = status.label;
  root.querySelector("[data-equipment-body]").textContent = status.summary;
  root.querySelector("[data-equipment-meta]").textContent = status.detail;
}

function normalizeTriggerText(text) {
  return String(text || "")
    .normalize("NFKC")
    .replace(/[\s\u3000、。,.!！?？「」『』"'`・…-]+/g, "")
    .toLowerCase();
}

function normalizeVoiceIntentText(text) {
  const punctuation = new Set([" ", "\t", "\n", "\r", "\u3000", "\u3001", "\u3002", ",", ".", "!", "！", "?", "？", "「", "」", "『", "』", "\"", "'", "`", "\u30fb", "\u2026", "-", "\u30fc"]);
  return Array.from(String(text || "").normalize("NFKC").toLowerCase())
    .filter((char) => !punctuation.has(char))
    .join("");
}

function transcriptHasTrigger(text) {
  const normalized = normalizeVoiceIntentText(text);
  const trigger = normalizeVoiceIntentText(TRIGGER_PHRASE);
  if (trigger && normalized.includes(trigger)) return true;
  return TRIGGER_ALIASES.some((alias) => {
    const normalizedAlias = normalizeVoiceIntentText(alias);
    return normalized === normalizedAlias || (normalized.startsWith(normalizedAlias) && normalized.length <= normalizedAlias.length + 4);
  });
}

function formatAudioStats(stats) {
  if (!stats || typeof stats !== "object") return "";
  const mode = String(stats.mode || stats.mime_type || "").toUpperCase();
  const peak = Number(stats.peak);
  const rms = Number(stats.rms);
  const duration = Number(stats.duration_sec);
  const parts = [];
  if (mode) parts.push(mode);
  if (Number.isFinite(duration)) parts.push(`${duration.toFixed(1)}s`);
  if (Number.isFinite(peak)) parts.push(`ピーク ${peak.toFixed(3)}`);
  if (Number.isFinite(rms)) parts.push(`平均 ${rms.toFixed(3)}`);
  if (stats.quiet) parts.push("音量小");
  return parts.join(" / ");
}

function formatVoiceRetryDetail(data, transcript) {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const heard = transcript ? `Whisper結果: ${transcript}` : "Whisper結果: 文字起こしなし。";
  const diagnostic = formatAudioStats(stats);
  const saved = voiceAudio.url ? ` 保存先: ${voiceAudio.url}` : "";
  return `${heard}${diagnostic ? ` (${diagnostic})` : ""}.${saved}`;
}

function formatVoiceRetryHint(data, transcript) {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const diagnostic = formatAudioStats(stats);
  if (transcript) {
    return `Whisper結果: "${transcript}" / 合図「${TRIGGER_PHRASE}」未検出。${diagnostic ? ` ${diagnostic}` : ""}`;
  }
  return `Whisper結果: 文字起こしなし。${diagnostic ? ` ${diagnostic}` : ""}`;
}

function formatVoiceDebug(data, transcript, reason = "") {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const match = data?.replay?.trigger?.match || data?.result?.trigger_match;
  const lines = [
    "音声デバッグ",
    `結果: ${data?.ok ? "成功" : "再試行"}`,
    `合図: ${TRIGGER_PHRASE}`,
    `文字起こし: ${transcript || "なし"}`,
  ];
  if (match?.mode && match.mode !== "none") {
    lines.push(`一致: ${match.mode}${match.matched ? ` / ${match.matched}` : ""}`);
  }
  const diagnostic = formatAudioStats(stats);
  if (diagnostic) lines.push(`音声: ${diagnostic}`);
  if (voiceAudio.bytes) lines.push(`容量: ${voiceAudio.bytes}`);
  if (voiceAudio.mime_type) lines.push(`形式: ${voiceAudio.mime_type}`);
  if (voiceAudio.url) lines.push(`保存先: ${voiceAudio.url}`);
  if (reason) lines.push(`理由: ${reason}`);
  return lines.join("\n");
}

function numericMotionVector(value, fallback = [0, 0, 0]) {
  const source = Array.isArray(value) && value.length >= 3 ? value : fallback;
  return source.slice(0, 3).map((item, index) => {
    const number = Number(item);
    return Number.isFinite(number) ? number : Number(fallback[index] || 0);
  });
}

function normalizeMotionFrame(frame, atTimeSec = null) {
  if (!frame || typeof frame !== "object") return null;
  const rawTime = Number(frame.t);
  const fallbackTime = Number(atTimeSec);
  const t = Number.isFinite(rawTime)
    ? rawTime
    : Number.isFinite(fallbackTime)
      ? fallbackTime
      : 0;
  return {
    ...frame,
    t: Math.max(0, Number(t.toFixed(3))),
    progress: Number.isFinite(Number(frame.progress)) ? clamp(Number(frame.progress), 0, 1) : 0,
    head: numericMotionVector(frame.head, [0, 1.56, 0]),
    left_hand: numericMotionVector(frame.left_hand, [-0.42, 0.76, -0.34]),
    right_hand: numericMotionVector(frame.right_hand, [0.42, 0.76, -0.34]),
    torso_yaw: Number.isFinite(Number(frame.torso_yaw)) ? Number(frame.torso_yaw) : 0,
    left_hand_tracked: frame.left_hand_tracked !== false,
    right_hand_tracked: frame.right_hand_tracked !== false,
  };
}

function lerpMotionVector(a, b, amount) {
  return [
    lerp(a[0], b[0], amount),
    lerp(a[1], b[1], amount),
    lerp(a[2], b[2], amount),
  ];
}

function interpolateMotionFrame(a, b, elapsed) {
  if (!a || !b || a === b) return a || b || null;
  const span = Math.max(0.001, b.t - a.t);
  const amount = clamp((elapsed - a.t) / span, 0, 1);
  return {
    ...a,
    t: Number(elapsed.toFixed(3)),
    progress: lerp(a.progress || 0, b.progress || 0, amount),
    head: lerpMotionVector(a.head, b.head, amount),
    left_hand: lerpMotionVector(a.left_hand, b.left_hand, amount),
    right_hand: lerpMotionVector(a.right_hand, b.right_hand, amount),
    torso_yaw: lerp(a.torso_yaw || 0, b.torso_yaw || 0, amount),
    left_hand_tracked: amount < 0.5 ? a.left_hand_tracked : b.left_hand_tracked,
    right_hand_tracked: amount < 0.5 ? a.right_hand_tracked : b.right_hand_tracked,
  };
}

function motionFramesFromReplayScript(replayScript) {
  const timeline = Array.isArray(replayScript?.timeline) ? replayScript.timeline : [];
  const frames = [];
  for (const segment of timeline) {
    const actions = Array.isArray(segment?.actions) ? segment.actions : [];
    for (const action of actions) {
      const motionFrame = action?.params?.motion_frame;
      const actionTime = Number(action?.at_time_sec);
      const timelineFrame = Number.isFinite(actionTime) && motionFrame
        ? { ...motionFrame, t: actionTime }
        : motionFrame;
      const normalized = normalizeMotionFrame(timelineFrame, action?.at_time_sec);
      if (normalized) frames.push(normalized);
    }
  }
  return frames.sort((a, b) => a.t - b.t);
}

function normalizeReplayMotionSource(value) {
  const token = String(value || "").trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (!token) return "";
  if (token.includes("mocopi")) return REPLAY_MOTION_SOURCE_MOCOPI;
  if (token.includes("body_sim") || token.includes("simulated_body") || token.includes("simulation")) {
    return REPLAY_MOTION_SOURCE_BODY_SIM;
  }
  if (token.includes("live_pose") || token.includes("quest_pose")) return REPLAY_MOTION_SOURCE_LIVE_POSE;
  return "";
}

function replayMotionSourceFromRecord(replay, bodySim = null) {
  const candidates = [
    replay?.playback?.motion_source,
    replay?.source?.tracking,
    replay?.tracking?.source,
    replay?.tracking?.provider,
    replay?.motion_provenance?.primary_source,
    replay?.motion_provenance?.capture_system?.provider,
    bodySim?.motion_source,
    bodySim?.source,
    bodySim?.metadata?.motion_source,
    bodySim?.metadata?.source,
  ];
  for (const candidate of candidates) {
    const normalized = normalizeReplayMotionSource(candidate);
    if (normalized) return normalized;
  }
  return "";
}

function makeReplayMotionDiagnostic(source, livePoseFrames = 0, bodySimFrames = 0, replayMotionSource = "") {
  const live = Math.max(0, livePoseFrames);
  const body = Math.max(0, bodySimFrames);
  const normalizedReplayMotionSource = (live || body) ? normalizeReplayMotionSource(replayMotionSource) : "";
  if (source === REPLAY_MOTION_SOURCE_MIXED && normalizedReplayMotionSource === REPLAY_MOTION_SOURCE_MOCOPI) {
    return {
      source: REPLAY_MOTION_SOURCE_MIXED,
      token: "MOCOPI+LIVE",
      label: `mocopi-derived body-sim ${body} frames + live-pose ${live} frames`,
      motion_source: REPLAY_MOTION_SOURCE_MOCOPI,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_MIXED) {
    return {
      source,
      token: "BODY+LIVE",
      label: `body-sim ${body} frames + live-pose ${live} frames`,
      motion_source: REPLAY_MOTION_SOURCE_BODY_SIM,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_LIVE_POSE && normalizedReplayMotionSource === REPLAY_MOTION_SOURCE_MOCOPI) {
    return {
      source: REPLAY_MOTION_SOURCE_MOCOPI,
      token: `MOCOPI ${live}f`,
      label: `mocopi replay ${live} frames`,
      motion_source: REPLAY_MOTION_SOURCE_MOCOPI,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_LIVE_POSE) {
    return {
      source,
      token: `LIVE ${live}f`,
      label: `live-pose ${live} frames`,
      motion_source: REPLAY_MOTION_SOURCE_LIVE_POSE,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_BODY_SIM && normalizedReplayMotionSource === REPLAY_MOTION_SOURCE_MOCOPI) {
    return {
      source: REPLAY_MOTION_SOURCE_MOCOPI,
      token: `MOCOPI ${body}f`,
      label: `mocopi-derived body-sim ${body} frames`,
      motion_source: REPLAY_MOTION_SOURCE_MOCOPI,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_BODY_SIM) {
    return {
      source,
      token: `BODY ${body}f`,
      label: `body-sim ${body} frames`,
      motion_source: REPLAY_MOTION_SOURCE_BODY_SIM,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_CAPTURE) {
    return {
      source,
      token: "CAPTURE",
      label: "live capture",
      motion_source: REPLAY_MOTION_SOURCE_CAPTURE,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_SELF) {
    return {
      source,
      token: "SELF",
      label: "first-person transform",
      motion_source: REPLAY_MOTION_SOURCE_SELF,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  return {
    source: REPLAY_MOTION_SOURCE_STATIC,
    token: "STATIC",
    label: "static fallback",
    motion_source: REPLAY_MOTION_SOURCE_STATIC,
    live_pose_frames: live,
    body_sim_frames: body,
  };
}

async function loadJson(path) {
  const normalized = normalizePath(normalizeServedAssetPath(path));
  const response = await fetch(normalized, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`JSON load failed: ${response.status} ${normalized}`);
  }
  return response.json();
}

async function loadReplay(path = getReplayPath()) {
  return loadJson(path);
}

async function loadSuitSpec() {
  return loadJson(getSuitSpecPath()).catch((error) => {
    console.warn(error);
    UI.micState.textContent = "スーツ仕様のテクスチャマップを読めないため、代替メッシュ表示を継続します。";
    return { modules: {} };
  });
}

function colorFromSuitHex(hex, fallbackHex) {
  const color = new THREE.Color(fallbackHex);
  if (typeof hex === "string" && hex.trim()) {
    try {
      color.set(hex.trim());
    } catch {
      color.setHex(fallbackHex);
    }
  }
  return color.getHex();
}

function createBaseSuitTexture(suitspec) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const primary = suitspec?.palette?.primary || "#f4f1e8";
  const secondary = suitspec?.palette?.secondary || "#8c96a3";
  const emissive = suitspec?.palette?.emissive || "#43d8ff";
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, secondary);
  gradient.addColorStop(0.48, primary);
  gradient.addColorStop(1, "#0c1f26");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.globalAlpha = 0.22;
  ctx.strokeStyle = emissive;
  ctx.lineWidth = 3;
  for (let y = -canvas.height; y < canvas.height * 2; y += 52) {
    ctx.beginPath();
    ctx.moveTo(-20, y);
    ctx.lineTo(canvas.width + 20, y + canvas.height * 0.34);
    ctx.stroke();
  }
  ctx.globalAlpha = 0.28;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth = 1;
  for (let x = 0; x < canvas.width; x += 64) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x + 28, canvas.height);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(1.6, 2.4);
  return texture;
}

function createBaseSuitMaterial(suitspec) {
  const primary = colorFromSuitHex(suitspec?.palette?.primary, 0xf4f1e8);
  return new THREE.MeshStandardMaterial({
    color: primary,
    map: createBaseSuitTexture(suitspec),
    metalness: 0.18,
    roughness: 0.62,
    emissive: new THREE.Color(colorFromSuitHex(suitspec?.palette?.emissive, 0x43d8ff)).multiplyScalar(0.18),
    transparent: true,
    opacity: 0.42,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
}

function fallbackArmorColor(part, suitspec) {
  if (suitspec?.texture_fallback?.mode !== "palette_material") {
    return PART_COLORS[part] || 0xd9f6ff;
  }
  if (["helmet", "chest", "back", "waist"].includes(part)) {
    return colorFromSuitHex(suitspec?.palette?.primary, 0xf4f1e8);
  }
  const primary = new THREE.Color(colorFromSuitHex(suitspec?.palette?.primary, 0xf4f1e8));
  const secondary = new THREE.Color(colorFromSuitHex(suitspec?.palette?.secondary, 0x8c96a3));
  return secondary.lerp(primary, 0.32).getHex();
}

function formatFitContract(suitspec) {
  const contract = suitspec?.fit_contract || {};
  return `${contract.module_fit_stage || "missing"} / ${contract.module_fit_space || "missing"}`;
}

function formatFitContractLabel(suitspec) {
  const contract = suitspec?.fit_contract || {};
  const stage = contract.module_fit_stage || "missing";
  const space = contract.module_fit_space || "missing";
  const stageLabel = stage === "body-fit" ? "体型適合" : stage === "missing" ? "未設定" : stage;
  const spaceLabel = space === "local-body-space" ? "身体座標" : space === "missing" ? "未設定" : space;
  return `${stageLabel} / ${spaceLabel}`;
}

function formatTextureFallback(suitspec) {
  const fallback = suitspec?.texture_fallback || {};
  return `${fallback.mode || "missing"} / ${fallback.source || "missing"}`;
}

function formatTextureFallbackLabel(suitspec) {
  const fallback = suitspec?.texture_fallback || {};
  const mode = fallback.mode || "missing";
  const source = fallback.source || "missing";
  const modeLabel = mode === "palette_material" ? "パレット材質" : mode === "missing" ? "未設定" : mode;
  const sourceLabel = source === "palette" ? "パレット" : source === "missing" ? "未設定" : source;
  return `${modeLabel} / ${sourceLabel}`;
}

function formatModelGateStatusLabel(status) {
  const text = String(status || "unknown").toLowerCase();
  if (text === "pass") return "合格";
  if (text === "fail") return "不合格";
  if (text === "warn" || text === "warning") return "要確認";
  if (text === "unknown") return "未確認";
  return status;
}

function createMaterial(color, opacity = 0.0) {
  return new THREE.MeshStandardMaterial({
    color,
    metalness: 0.72,
    roughness: 0.28,
    emissive: new THREE.Color(color).multiplyScalar(0.16),
    side: THREE.DoubleSide,
    transparent: true,
    opacity,
  });
}

function createDepositionPointTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 64;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  const gradient = context.createRadialGradient(32, 32, 0, 32, 32, 32);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.26, "rgba(142,223,255,0.92)");
  gradient.addColorStop(0.62, "rgba(255,207,90,0.36)");
  gradient.addColorStop(1, "rgba(255,207,90,0)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, 64, 64);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function depositionBodyRadiusAtY(y) {
  if (y > 0.42) return 0.22;
  if (y > -0.12) return 0.34;
  if (y > -0.72) return 0.42;
  if (y > -1.1) return 0.28;
  return 0.18;
}

function depositionSeed(index, count) {
  const band = index / Math.max(1, count - 1);
  const color = new THREE.Color(DEPOSITION_LORE_COLORS[index % DEPOSITION_LORE_COLORS.length]);
  return {
    angle: (band * 9.7 + (index % 17) * 0.37) * TAU,
    height: (index * 0.61803398875) % 1,
    start: (index % count) / count,
    radius: 0.92 + ((index * 13) % 31) / 100,
    speed: 0.52 + ((index * 7) % 23) / 25,
    twist: ((index % 2) ? -1 : 1) * (0.9 + ((index * 5) % 17) / 10),
    surfaceOffset: ((index * 11) % 19) / 1000,
    color,
  };
}

function createDepositionParticleField() {
  const group = new THREE.Group();
  group.name = "IWSDK-蒸着粒子フィールド";
  group.visible = false;

  const positions = new Float32Array(DEPOSITION_PARTICLE_COUNT * 3);
  const colors = new Float32Array(DEPOSITION_PARTICLE_COUNT * 3);
  const seeds = Array.from({ length: DEPOSITION_PARTICLE_COUNT }, (_, index) =>
    depositionSeed(index, DEPOSITION_PARTICLE_COUNT),
  );
  for (let i = 0; i < seeds.length; i += 1) {
    seeds[i].color.toArray(colors, i * 3);
  }
  const particleGeometry = new THREE.BufferGeometry();
  particleGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  particleGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  const particleMaterial = new THREE.PointsMaterial({
    size: 0.034,
    map: createDepositionPointTexture(),
    transparent: true,
    opacity: 0,
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  });
  const points = new THREE.Points(particleGeometry, particleMaterial);
  points.name = "蒸着粒子";
  points.renderOrder = 22;
  group.add(points);

  const sparkPositions = new Float32Array(DEPOSITION_SPARK_COUNT * 2 * 3);
  const sparkGeometry = new THREE.BufferGeometry();
  sparkGeometry.setAttribute("position", new THREE.BufferAttribute(sparkPositions, 3));
  const sparkMaterial = new THREE.LineBasicMaterial({
    color: 0x8edfff,
    transparent: true,
    opacity: 0,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const sparks = new THREE.LineSegments(sparkGeometry, sparkMaterial);
  sparks.name = "蒸着光跡";
  sparks.renderOrder = 23;
  group.add(sparks);

  return { group, points, sparks, positions, colors, sparkPositions, seeds };
}

function disposeObjectResources(root, disposedGeometries = new Set(), disposedMaterials = new Set()) {
  if (!root) return { disposedGeometries, disposedMaterials };
  root.traverse((object) => {
    if (object.geometry && !disposedGeometries.has(object.geometry)) {
      disposedGeometries.add(object.geometry);
      object.geometry.dispose?.();
    }
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      if (!material || disposedMaterials.has(material)) continue;
      disposedMaterials.add(material);
      material.dispose?.();
    }
  });
  return { disposedGeometries, disposedMaterials };
}

function disposeGltfResources(gltf) {
  const scenes = [gltf?.scene, ...(Array.isArray(gltf?.scenes) ? gltf.scenes : [])].filter(Boolean);
  const seen = new Set();
  const disposedGeometries = new Set();
  const disposedMaterials = new Set();
  for (const scene of scenes) {
    if (seen.has(scene)) continue;
    seen.add(scene);
    disposeObjectResources(scene, disposedGeometries, disposedMaterials);
  }
}

async function mapWithConcurrency(items, limit, worker, onProgress = null) {
  const results = new Array(items.length);
  let nextIndex = 0;
  let done = 0;
  const workerCount = Math.min(Math.max(1, limit), Math.max(items.length, 1));
  await Promise.all(Array.from({ length: workerCount }, async () => {
    while (nextIndex < items.length) {
      const index = nextIndex;
      nextIndex += 1;
      results[index] = await worker(items[index], index);
      done += 1;
      onProgress?.({ done, total: items.length, index, result: results[index] });
    }
  }));
  return results;
}

function fallbackGeometry(part) {
  const geometry = part === "helmet"
    ? new THREE.SphereGeometry(0.18, 32, 18)
    : new THREE.CapsuleGeometry(0.18, 0.62, 8, 20);
  geometry.userData.meshSource = "generated_fallback";
  geometry.userData.loadedAssetRef = null;
  return geometry;
}

function boxSizeArray(geometry) {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return [1, 1, 1];
  const size = new THREE.Vector3();
  box.getSize(size);
  return [
    Number.isFinite(size.x) && size.x > 0 ? size.x : 1,
    Number.isFinite(size.y) && size.y > 0 ? size.y : 1,
    Number.isFinite(size.z) && size.z > 0 ? size.z : 1,
  ];
}

function normalizeGeometry(geometry) {
  geometry.computeBoundingBox();
  const box = geometry.boundingBox;
  if (!box) return geometry;
  const center = new THREE.Vector3();
  const size = new THREE.Vector3();
  box.getCenter(center);
  box.getSize(size);
  const scale = Math.max(size.x, size.y, size.z) || 1;
  geometry.userData.sourceSize = [size.x, size.y, size.z];
  geometry.userData.normalizeScale = scale;
  geometry.translate(-center.x, -center.y, -center.z);
  geometry.scale(1 / scale, 1 / scale, 1 / scale);
  geometry.userData.normalizedSize = boxSizeArray(geometry);
  geometry.computeBoundingSphere();
  return geometry;
}

function positiveVectorFromArray(values, fallback = [1, 1, 1]) {
  if (!Array.isArray(values)) return fallback;
  return [0, 1, 2].map((index) => {
    const value = Number(values[index]);
    return Number.isFinite(value) && value > 0 ? value : fallback[index];
  });
}

function vectorArrayFromRecord(record) {
  return sharedVectorArrayFromRuntimeRecord(record);
}

function runtimePlacementForMesh(mesh) {
  const placement = mesh?.userData?.runtimePlacement || mesh?.userData?.module?.runtime_placement || null;
  return placement && typeof placement === "object" ? placement : null;
}

function useWebPreviewRuntimePlacement(placement) {
  return resolveRuntimePlacementMode({
    placement,
    webPreviewParity: useWebPreviewPlacementParityQuery(),
  }) === "web_preview_parity";
}

function targetSizeArrayFromPlacement(placement, fallback) {
  return resolveRuntimeTargetSize({
    placement,
    fallback,
    mode: useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig",
  });
}

function questOffsetArrayFromPlacement(placement) {
  return sharedQuestOffsetArrayFromPlacement(placement);
}

function webPreviewOffsetArrayFromPlacement(placement) {
  return sharedWebPreviewOffsetArrayFromPlacement(placement);
}

function questSurfaceOffsetArrayFromPlacement(placement) {
  const source = Array.isArray(placement?.quest_surface_offset_clamped_m)
    ? placement.quest_surface_offset_clamped_m
    : placement?.surface_anchor?.quest_rig_offset_clamped_m;
  if (!Array.isArray(source)) return null;
  const offset = source.map((value) => Number(value));
  return offset.length >= 3 && offset.slice(0, 3).every((value) => Number.isFinite(value))
    ? offset.slice(0, 3)
    : null;
}

function webPreviewSurfaceOffsetArrayFromPlacement(placement) {
  return sharedWebPreviewSurfaceOffsetArrayFromPlacement(placement);
}

function clampedQuestOffsetArrayFromPlacement(part, placement) {
  return sharedClampedQuestOffsetArrayFromPlacement(part, placement);
}

function runtimePlacementOffsetArrayForPart(part, placement) {
  return resolveRuntimeOffset({
    part,
    placement,
    mode: useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig",
  });
}

function questRotationArrayFromPlacement(placement) {
  if (!Array.isArray(placement?.rotation_deg)) return null;
  const rotation = placement.rotation_deg.map((value) => Number(value));
  if (rotation.length < 3 || !rotation.slice(0, 3).every((value) => Number.isFinite(value))) {
    return null;
  }
  return [
    THREE.MathUtils.degToRad(-rotation[0]),
    THREE.MathUtils.degToRad(-rotation[1]),
    THREE.MathUtils.degToRad(rotation[2]),
  ];
}

function webPreviewRotationArrayFromPlacement(placement) {
  if (!Array.isArray(placement?.rotation_deg)) return null;
  const rotation = placement.rotation_deg.map((value) => Number(value));
  if (rotation.length < 3 || !rotation.slice(0, 3).every((value) => Number.isFinite(value))) {
    return null;
  }
  return [
    THREE.MathUtils.degToRad(rotation[0]),
    THREE.MathUtils.degToRad(rotation[1]),
    THREE.MathUtils.degToRad(rotation[2]),
  ];
}

function runtimePlacementRotationArray(placement) {
  return resolveRuntimeRotation({
    placement,
    mode: useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig",
  });
}

function applyRuntimePlacementOffset(mesh, part, reveal = 1, yaw = 0) {
  const offset = runtimePlacementOffsetArrayForPart(part, runtimePlacementForMesh(mesh));
  if (!offset) return;
  const amount = Number.isFinite(reveal) ? reveal : 1;
  const angle = Number(yaw) || 0;
  const sin = Math.sin(angle);
  const cos = Math.cos(angle);
  const rotatedX = offset[0] * cos - offset[2] * sin;
  const rotatedZ = offset[0] * sin + offset[2] * cos;
  mesh.position.x += rotatedX * amount;
  mesh.position.y += offset[1] * amount;
  mesh.position.z += rotatedZ * amount;
}

function applyRuntimePlacementRotation(mesh, baseX, baseY, baseZ) {
  const rotation = runtimePlacementRotationArray(runtimePlacementForMesh(mesh));
  if (!rotation) {
    mesh.rotation.set(baseX, baseY, baseZ);
    return;
  }
  QUEST_PLACEMENT_BASE_EULER.set(baseX, baseY, baseZ, "XYZ");
  QUEST_PLACEMENT_ROTATION_EULER.set(rotation[0], rotation[1], rotation[2], "XYZ");
  QUEST_PLACEMENT_BASE_QUATERNION.setFromEuler(QUEST_PLACEMENT_BASE_EULER);
  QUEST_PLACEMENT_ROTATION_QUATERNION.setFromEuler(QUEST_PLACEMENT_ROTATION_EULER);
  mesh.quaternion.copy(
    QUEST_PLACEMENT_BASE_QUATERNION.multiply(QUEST_PLACEMENT_ROTATION_QUATERNION).normalize(),
  );
}

function isGlbArmorMesh(mesh) {
  return mesh?.userData?.meshSource === "glb_asset";
}

function isGeneratedFallbackArmorMesh(mesh) {
  return mesh?.userData?.meshSource === "generated_fallback";
}

function questBaseRotationXForMesh(mesh) {
  return isGlbArmorMesh(mesh) && runtimePlacementForMesh(mesh) ? 0 : Math.PI / 2;
}

function questGlbScaleForPart(mesh, part, reveal = 1) {
  const fallbackTarget = QUEST_GLB_TARGET_SIZES[part] || [0.2, 0.2, 0.2];
  const target = targetSizeArrayFromPlacement(runtimePlacementForMesh(mesh), fallbackTarget);
  const source = positiveVectorFromArray(mesh?.userData?.normalizedSize, [1, 1, 1]);
  const emerge = Number.isFinite(reveal) ? reveal : 1;
  return [
    (target[0] / Math.max(source[0], 0.001)) * emerge,
    (target[1] / Math.max(source[1], 0.001)) * emerge,
    (target[2] / Math.max(source[2], 0.001)) * emerge,
  ];
}

function questHumanBodyPoint(name) {
  const point = QUEST_HUMAN_BODY_MOCK.points_m?.[name];
  if (!Array.isArray(point) || point.length < 3) return null;
  return point.slice(0, 3);
}

function questHumanAnchorCenterForPart(part) {
  const anchorCenter = QUEST_HUMAN_ANCHOR_CONTRACT[part]?.center_m;
  const contract = QUEST_HUMAN_ANCHOR_CONTRACT[part];
  const bodyPoint = questHumanBodyPoint(contract?.bodyPoint);
  const offset = Array.isArray(contract?.offset_m) ? contract.offset_m : [0, 0, 0];
  if (bodyPoint) {
    return [
      bodyPoint[0] + Number(offset[0] || 0),
      bodyPoint[1] + Number(offset[1] || 0),
      bodyPoint[2] + Number(offset[2] || 0),
    ];
  }
  if (Array.isArray(anchorCenter) && anchorCenter.length >= 3) {
    return anchorCenter.slice(0, 3);
  }
  return null;
}

function questAssemblyPoseForPart(part) {
  const humanCenter = questHumanAnchorCenterForPart(part);
  if (humanCenter) return humanCenter;
  const pose = VR_BODY_PART_POSES[part] || [0, -0.5, -0.28];
  const adjustment = QUEST_ASSEMBLY_ADJUSTMENTS[part] || [0, 0, 0];
  return [pose[0] + adjustment[0], pose[1] + adjustment[1], pose[2] + adjustment[2]];
}

function questBodyRelativeOffsetForPart(part) {
  const pose = questAssemblyPoseForPart(part);
  return [pose[0], pose[1], pose[2] - QUEST_HUMAN_BODY_MOCK.spine_z_m - 0.06];
}

function armorStandExplodeVectorForPart(part) {
  const pose = questAssemblyPoseForPart(part);
  const xSign = part.startsWith("left_") ? -1 : part.startsWith("right_") ? 1 : Math.sign(pose[0]);
  const ySign = part === "helmet" ? 1 : part.includes("boot") || part.includes("shin") ? -0.35 : 0;
  const zSign = part === "back" ? 0.9 : part === "chest" || part === "waist" ? -0.35 : Math.sign(pose[2] - ARMOR_STAND_CENTER_Z);
  const length = Math.max(0.001, Math.hypot(xSign, ySign, zSign));
  return [xSign / length, ySign / length, zSign / length];
}

function armorStandPoseForPart(part, transform = {}) {
  const options = typeof transform === "number" ? { yaw: transform } : transform || {};
  const yaw = Number(options.yaw) || 0;
  const pitch = clamp(Number(options.pitch) || 0, -ARMOR_STAND_PITCH_LIMIT_RAD, ARMOR_STAND_PITCH_LIMIT_RAD);
  const scale = clamp(Number(options.scale) || 1, ARMOR_STAND_SCALE_MIN, ARMOR_STAND_SCALE_MAX);
  const explode = clamp(Number(options.explode) || 0, 0, 1);
  const pose = questAssemblyPoseForPart(part);
  const explodeVector = armorStandExplodeVectorForPart(part);
  const localX = (pose[0] + explodeVector[0] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M) * scale;
  const localY = (pose[1] + ARMOR_STAND_FLOOR_LIFT_M - ARMOR_STAND_CENTER_Y + explodeVector[1] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M) * scale;
  const localZ = (pose[2] - ARMOR_STAND_CENTER_Z + explodeVector[2] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M) * scale;
  const pitchSin = Math.sin(pitch);
  const pitchCos = Math.cos(pitch);
  const pitchedY = localY * pitchCos - localZ * pitchSin;
  const pitchedZ = localY * pitchSin + localZ * pitchCos;
  const yawSin = Math.sin(yaw);
  const yawCos = Math.cos(yaw);
  return [
    localX * yawCos - pitchedZ * yawSin,
    ARMOR_STAND_CENTER_Y + pitchedY,
    ARMOR_STAND_CENTER_Z + localX * yawSin + pitchedZ * yawCos,
  ];
}

function armorStandRigQuaternionFromTransform(transform = {}) {
  const options = typeof transform === "number" ? { yaw: transform } : transform || {};
  const yaw = Number(options.yaw) || 0;
  const pitch = clamp(Number(options.pitch) || 0, -ARMOR_STAND_PITCH_LIMIT_RAD, ARMOR_STAND_PITCH_LIMIT_RAD);
  ARMOR_STAND_RIG_EULER.set(pitch, yaw, 0, "YXZ");
  return ARMOR_STAND_RIG_QUATERNION.setFromEuler(ARMOR_STAND_RIG_EULER);
}

function armorStandRigPoseForPoint(point, transform = {}, runtimeOffset = [0, 0, 0], explodeVector = [0, 0, 0]) {
  const options = typeof transform === "number" ? { yaw: transform } : transform || {};
  const scale = clamp(Number(options.scale) || 1, ARMOR_STAND_SCALE_MIN, ARMOR_STAND_SCALE_MAX);
  const explode = clamp(Number(options.explode) || 0, 0, 1);
  const offset = options.offset || {};
  ARMOR_STAND_RIG_OFFSET_VECTOR.set(Number(offset.x) || 0, Number(offset.y) || 0, Number(offset.z) || 0);
  ARMOR_STAND_RIG_LOCAL_VECTOR.set(
    point[0] + runtimeOffset[0] + explodeVector[0] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M,
    point[1] + ARMOR_STAND_FLOOR_LIFT_M - ARMOR_STAND_CENTER_Y + runtimeOffset[1] + explodeVector[1] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M,
    point[2] - ARMOR_STAND_CENTER_Z + runtimeOffset[2] + explodeVector[2] * explode * ARMOR_STAND_EXPLODE_DISTANCE_M,
  );
  ARMOR_STAND_RIG_LOCAL_VECTOR.multiplyScalar(scale);
  ARMOR_STAND_RIG_WORLD_VECTOR.copy(ARMOR_STAND_RIG_LOCAL_VECTOR).applyQuaternion(
    armorStandRigQuaternionFromTransform(options),
  );
  return [
    ARMOR_STAND_RIG_WORLD_VECTOR.x + ARMOR_STAND_RIG_OFFSET_VECTOR.x,
    ARMOR_STAND_CENTER_Y + ARMOR_STAND_RIG_WORLD_VECTOR.y + ARMOR_STAND_RIG_OFFSET_VECTOR.y,
    ARMOR_STAND_CENTER_Z + ARMOR_STAND_RIG_WORLD_VECTOR.z + ARMOR_STAND_RIG_OFFSET_VECTOR.z,
  ];
}

function armorStandRigPoseForPart(part, mesh, transform = {}) {
  const pose = questAssemblyPoseForPart(part);
  const explodeVector = armorStandExplodeVectorForPart(part);
  const runtimeOffset = clampedQuestOffsetArrayFromPlacement(part, runtimePlacementForMesh(mesh)) || [0, 0, 0];
  return armorStandRigPoseForPoint(pose, transform, runtimeOffset, explodeVector);
}

function applyArmorStandInspectionRotation(mesh, pitch = 0, yaw = 0) {
  const safePitch = clamp(Number(pitch) || 0, -ARMOR_STAND_PITCH_LIMIT_RAD, ARMOR_STAND_PITCH_LIMIT_RAD);
  const safeYaw = Number(yaw) || 0;
  if (Math.abs(safePitch) < 0.0001 && Math.abs(safeYaw) < 0.0001) return;
  ARMOR_STAND_INSPECTION_EULER.set(safePitch, safeYaw, 0, "YXZ");
  ARMOR_STAND_INSPECTION_QUATERNION.setFromEuler(ARMOR_STAND_INSPECTION_EULER);
  mesh.quaternion.premultiply(ARMOR_STAND_INSPECTION_QUATERNION);
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh asset format.");
  }
  const positions = new Float32Array(payload.positions || []);
  const normals = new Float32Array(payload.normals || []);
  const uv = new Float32Array(payload.uv || payload.uvs || []);
  const indices = Array.isArray(payload.indices) ? payload.indices : [];
  if (positions.length < 9 || positions.length % 3 !== 0) {
    throw new Error("Invalid mesh positions.");
  }
  let geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  if (uv.length === (positions.length / 3) * 2) {
    geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  }
  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new THREE.BufferAttribute(normals, 3));
  }
  if (indices.length) geometry.setIndex(indices);
  if (geometry.index) geometry = geometry.toNonIndexed();
  if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();
  return normalizeGeometry(geometry);
}

function isGlbAssetPath(assetPath) {
  return /\.glb(?:$|[?#])/i.test(assetPath || "");
}

function geometryFromGltf(gltf, assetPath) {
  const scene = gltf?.scene || gltf?.scenes?.[0];
  if (!scene) {
    throw new Error(`GLB has no scene: ${assetPath}`);
  }

  const geometries = [];
  scene.updateMatrixWorld(true);
  scene.traverse((node) => {
    if (!node.isMesh || !node.geometry) return;
    let geometry = node.geometry.clone();
    if (geometry.index) geometry = geometry.toNonIndexed();
    geometry.applyMatrix4(node.matrixWorld);
    if (!geometry.getAttribute("normal")) geometry.computeVertexNormals();
    for (const name of Object.keys(geometry.attributes)) {
      if (!["position", "normal", "uv"].includes(name)) geometry.deleteAttribute(name);
    }
    geometry.morphAttributes = {};
    geometries.push(geometry);
  });

  if (!geometries.length) {
    throw new Error(`GLB has no mesh geometry: ${assetPath}`);
  }

  if (!geometries.every((geometry) => geometry.getAttribute("uv"))) {
    for (const geometry of geometries) geometry.deleteAttribute("uv");
  }

  const merged = geometries.length === 1 ? geometries[0] : mergeGeometries(geometries, false);
  if (!merged) {
    for (const geometry of geometries) geometry.dispose?.();
    throw new Error(`GLB geometry merge failed: ${assetPath}`);
  }
  for (const geometry of geometries) {
    if (geometry !== merged) geometry.dispose?.();
  }
  return normalizeGeometry(merged);
}

async function loadGlbGeometry(assetPath) {
  let gltf = null;
  try {
    gltf = await new Promise((resolve, reject) => {
      gltfLoader.load(
        assetPath,
        resolve,
        undefined,
        (error) => reject(error || new Error(`GLB load failed: ${assetPath}`)),
      );
    });
    const geometry = geometryFromGltf(gltf, assetPath);
    geometry.userData.meshSource = "glb_asset";
    geometry.userData.loadedAssetRef = assetPath;
    return geometry;
  } finally {
    disposeGltfResources(gltf);
  }
}

async function loadJsonMeshGeometry(assetPath) {
  if (geometryCache.has(assetPath)) return geometryCache.get(assetPath).clone();
  const payload = await loadJson(assetPath);
  const geometry = meshGeometryFromPayload(payload);
  geometry.userData.meshSource = "mesh_asset";
  geometry.userData.loadedAssetRef = assetPath;
  geometryCache.set(assetPath, geometry);
  return geometry.clone();
}

async function loadMeshGeometry(assetRef, part) {
  const fallbackPath = normalizePath(`viewer/assets/meshes/${part}.mesh.json`);
  const assetPath = normalizePath(assetRef || fallbackPath);
  if (geometryCache.has(assetPath)) return geometryCache.get(assetPath).clone();
  if (!isGlbAssetPath(assetPath)) {
    const geometry = await loadJsonMeshGeometry(assetPath);
    geometry.userData.meshSource = "mesh_asset";
    geometry.userData.loadedAssetRef = assetPath;
    return geometry;
  }

  try {
    const geometry = await loadGlbGeometry(assetPath);
    geometryCache.set(assetPath, geometry);
    return geometry.clone();
  } catch (error) {
    console.warn(`GLB mesh fallback for ${part}: ${fallbackPath}`, error);
    const geometry = await loadJsonMeshGeometry(fallbackPath);
    geometry.userData.meshSource = "mesh_json_fallback";
    geometry.userData.loadedAssetRef = fallbackPath;
    geometry.userData.meshError = `GLB: ${String(error?.message || error)}`;
    return geometry;
  }
}

async function loadTexture(texturePath, options = {}) {
  const key = normalizePath(texturePath);
  if (!key) return null;
  if (textureCache.has(key)) return textureCache.get(key);
  const allowPaletteFallback = Boolean(options.allowPaletteFallback);
  const pending = new Promise((resolve, reject) => {
    textureLoader.load(
      key,
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        resolve(texture);
      },
      undefined,
      (error) => reject(error || new Error(`Texture load failed: ${key}`)),
    );
  }).catch((error) => {
    if (allowPaletteFallback) {
      return null;
    }
    textureCache.delete(key);
    throw error;
  });
  textureCache.set(key, pending);
  return pending;
}

async function createArmorMesh(part, module, suitspec) {
  const color = fallbackArmorColor(part, suitspec);
  let geometry;
  try {
    geometry = await loadMeshGeometry(module?.asset_ref, part);
  } catch (error) {
    console.warn(`mesh fallback for ${part}`, error);
    geometry = fallbackGeometry(part);
    geometry.userData.meshError = String(error?.message || error);
  }

  const mesh = new THREE.Mesh(geometry, createMaterial(color, 0.0));
  mesh.name = part;
  mesh.userData.module = module || {};
  mesh.userData.runtimePlacement = module?.runtime_placement || null;
  mesh.userData.meshSource = geometry.userData?.meshSource || "mesh_asset";
  mesh.userData.assetRef = normalizePath(module?.asset_ref || `viewer/assets/meshes/${part}.mesh.json`);
  mesh.userData.loadedAssetRef = geometry.userData?.loadedAssetRef || null;
  mesh.userData.meshError = geometry.userData?.meshError || "";
  mesh.userData.sourceSize = geometry.userData?.sourceSize || null;
  mesh.userData.normalizedSize = geometry.userData?.normalizedSize || null;
  mesh.userData.normalizeScale = geometry.userData?.normalizeScale || null;
  if (module?.texture_path) {
    const allowPaletteFallback = suitspec?.texture_fallback?.mode === "palette_material";
    loadTexture(module.texture_path, { allowPaletteFallback })
      .then((texture) => {
        if (mesh.userData.disposed) return;
        if (!texture) {
          mesh.userData.textureFallbackActive = allowPaletteFallback;
          return;
        }
        mesh.material.map = texture;
        mesh.material.color.setHex(0xffffff);
        mesh.material.needsUpdate = true;
      })
      .catch((error) => {
        if (mesh.userData.disposed) return;
        mesh.userData.textureFallbackActive = allowPaletteFallback;
        console.warn(`texture fallback for ${part}`, error);
      });
  }
  return mesh;
}

function applySegmentPose(mesh, pose, part, reveal, options = {}) {
  if (!pose) return;
  const offset = PART_OFFSETS[part] || [0, 0, 0];
  const liveProfile = options.liveMocopi ? (options.liveMocopiProfile || LIVE_BODY_SIM_RENDER_DEFAULTS) : null;
  const sourceX = Number(pose.position_x || 0);
  const sourceY = Number(pose.position_y || 0);
  const sourceZ = Number(pose.position_z || 0);
  const x = liveProfile
    ? sourceX * liveProfile.scale * liveProfile.xSign + liveProfile.xOffset + offset[0]
    : sourceX - 0.55 + offset[0];
  const y = liveProfile
    ? sourceY * liveProfile.scale * liveProfile.ySign + liveProfile.yOffset + offset[1]
    : sourceY + 0.2 + offset[1];
  const z = liveProfile
    ? sourceZ * liveProfile.scale * liveProfile.zSign + liveProfile.zOffset + offset[2]
    : -sourceZ + offset[2];
  if (options.centered) {
    const index = mesh.userData.partIndex || 0;
    const angle = (index / ARMOR_PARTS.length) * TAU + options.progress * 1.35;
    const stageRadius = 0.38 + (index % 3) * 0.06;
    const stageLift = part === "helmet" ? 0.12 : 0.05;
    const fitProgress = easeOutCubic(clamp((options.progress - 0.18) / 0.68, 0, 1));
    const bodyPose = questAssemblyPoseForPart(part);
    if (bodyPose) {
      options.finalPosition.fromArray(bodyPose);
    } else {
      options.finalPosition.set(x * 0.55, y - 0.58, z - 0.1);
    }
    options.stagePosition.set(
      options.finalPosition.x + Math.cos(angle) * stageRadius,
      options.finalPosition.y + stageLift + Math.sin(options.progress * Math.PI) * 0.12,
      options.finalPosition.z + Math.sin(angle) * stageRadius,
    );
    mesh.position.lerpVectors(options.stagePosition, options.finalPosition, fitProgress);
  } else {
    mesh.position.set(x, y, z);
  }
  const poseYaw = options.centered ? 0 : liveProfile ? (liveProfile.yawOffsetRad || 0) : (pose.rotation_z || 0);
  applyRuntimePlacementOffset(mesh, part, reveal, poseYaw);
  applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, poseYaw);

  const fit = mesh.userData.module?.fit || {};
  const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
  const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
  const sx = Math.max(Number(pose.scale_x || 1) * Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
  const sy = Math.max(Number(pose.scale_y || 1) * Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
  const sz = Math.max(Number(pose.scale_z || 1) * Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
  const emerge = lerp(0.08, 1, reveal);
  if (isGlbArmorMesh(mesh)) {
    mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));
    return;
  }
  const vrScale = options.centered ? VR_PART_SCALE[part] || 0.28 : 1.0;
  mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
}

function makeTextSprite(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 160;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = "700 58px system-ui, sans-serif";
  ctx.fillStyle = "#fff4c8";
  ctx.shadowColor = "#ffcf5a";
  ctx.shadowBlur = 18;
  ctx.fillText(text, 36, 92);
  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.9 });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(2.4, 0.5, 1);
  return sprite;
}

function drawTextPlaneCanvas(canvas, text, options) {
  const ctx = canvas.getContext("2d");
  const {
    background = null,
    border = null,
    color = "#fff4c8",
    fontSize = 54,
    fontWeight = 760,
    align = "center",
    baseline = "middle",
    paddingX = 34,
    paddingY = 20,
    lineHeight = fontSize * 1.22,
    maxLines = 1,
    fitText = true,
    minFontSize = Math.max(24, Math.floor(fontSize * 0.62)),
  } = options;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (background) {
    ctx.fillStyle = background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  if (border) {
    ctx.strokeStyle = border;
    ctx.lineWidth = 5;
    ctx.strokeRect(3, 3, canvas.width - 6, canvas.height - 6);
  }
  const applyFont = (size) => {
    ctx.font = `${fontWeight} ${size}px system-ui, sans-serif`;
  };
  let activeFontSize = fontSize;
  applyFont(activeFontSize);
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = baseline;
  ctx.shadowColor = "rgba(255, 207, 90, 0.65)";
  ctx.shadowBlur = 10;
  const x = align === "left" ? paddingX : canvas.width / 2;
  const maxWidth = canvas.width - paddingX * 2;
  if (maxLines <= 1) {
    const textValue = String(text || "");
    while (fitText && activeFontSize > minFontSize && ctx.measureText(textValue).width > maxWidth) {
      activeFontSize -= 2;
      applyFont(activeFontSize);
    }
    ctx.fillText(text, x, canvas.height / 2);
    return;
  }

  const lines = [];
  for (const rawLine of String(text || "").split("\n")) {
    let line = "";
    for (const char of rawLine) {
      const next = line + char;
      if (line && ctx.measureText(next).width > maxWidth) {
        lines.push(line);
        line = char;
        if (lines.length >= maxLines) break;
      } else {
        line = next;
      }
    }
    if (lines.length >= maxLines) break;
    lines.push(line);
  }
  if (lines.length > maxLines) lines.length = maxLines;
  if (lines.length === maxLines && ctx.measureText(lines[lines.length - 1]).width > maxWidth * 0.96) {
    lines[lines.length - 1] = `${lines[lines.length - 1].slice(0, -1)}...`;
  }
  ctx.textBaseline = "top";
  const startY = baseline === "top" ? paddingY : Math.max(paddingY, (canvas.height - lines.length * lineHeight) / 2);
  lines.slice(0, maxLines).forEach((line, index) => {
    ctx.fillText(line, x, startY + index * lineHeight);
  });
}

function makeTextPlane(text, options = {}) {
  const settings = {
    width: 0.72,
    height: 0.12,
    canvasWidth: 1024,
    canvasHeight: 180,
    ...options,
  };
  const canvas = document.createElement("canvas");
  canvas.width = settings.canvasWidth;
  canvas.height = settings.canvasHeight;
  drawTextPlaneCanvas(canvas, text, settings);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
    side: THREE.DoubleSide,
    depthTest: false,
  });
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(settings.width, settings.height), material);
  mesh.renderOrder = 20;
  mesh.userData.textCanvas = canvas;
  mesh.userData.textTexture = texture;
  mesh.userData.textOptions = settings;
  return mesh;
}

function updateTextPlane(mesh, text, options = {}) {
  const settings = { ...mesh.userData.textOptions, ...options };
  drawTextPlaneCanvas(mesh.userData.textCanvas, text, settings);
  mesh.userData.textTexture.needsUpdate = true;
  mesh.userData.textOptions = settings;
}

function pickAudioMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  if (!window.MediaRecorder) return "";
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Audio encoding failed."));
    reader.readAsDataURL(blob);
  });
}

function mergeFloat32Chunks(chunks, totalLength) {
  const samples = new Float32Array(totalLength);
  let offset = 0;
  chunks.forEach((chunk) => {
    samples.set(chunk, offset);
    offset += chunk.length;
  });
  return samples;
}

function calculatePcmStats(samples, sampleRate, seconds, armDelaySec = 0) {
  let peak = 0;
  let sumSquares = 0;
  let crossings = 0;
  let previous = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index];
    const absolute = Math.abs(value);
    peak = Math.max(peak, absolute);
    sumSquares += value * value;
    if (index > 0 && Math.sign(value) !== Math.sign(previous)) crossings += 1;
    previous = value;
  }
  const rms = samples.length ? Math.sqrt(sumSquares / samples.length) : 0;
  return {
    mode: "wav",
    sample_rate: sampleRate,
    channels: 1,
    samples: samples.length,
    duration_sec: samples.length && sampleRate ? samples.length / sampleRate : seconds,
    requested_sec: seconds,
    arm_delay_sec: armDelaySec,
    peak: Number(peak.toFixed(6)),
    rms: Number(rms.toFixed(6)),
    dbfs: rms > 0 ? Number((20 * Math.log10(rms)).toFixed(1)) : -120,
    zero_crossings: crossings,
    quiet: rms < 0.004 || peak < 0.025,
  };
}

function encodeWavMono(samples, sampleRate) {
  const bytesPerSample = 2;
  const blockAlign = bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = samples.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  const writeString = (offset, value) => {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, dataSize, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1, offset += 2) {
    const clamped = clamp(samples[index], -1, 1);
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return buffer;
}

async function getMicrophoneStream() {
  if (!window.isSecureContext) {
    throw new Error("Microphone requires a secure context. Use Quest localhost via adb reverse, or HTTPS.");
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not expose microphone capture.");
  }
  return navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: true, channelCount: 1 },
    video: false,
  });
}

function stopMediaStream(stream) {
  stream?.getTracks?.().forEach((track) => track.stop());
}

function disconnectAudioNode(node) {
  try {
    node?.disconnect?.();
  } catch {
    // Web Audio nodes throw if they were never connected.
  }
}

async function recordAudioWebm(seconds, options = {}) {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    throw new Error("This browser does not expose MediaRecorder audio capture.");
  }
  const stream = await getMicrophoneStream();
  try {
    const mimeType = pickAudioMimeType();
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    const chunks = [];
    recorder.addEventListener("dataavailable", (event) => {
      if (event.data?.size) chunks.push(event.data);
    });
    const stopped = new Promise((resolve, reject) => {
      recorder.addEventListener("stop", resolve, { once: true });
      recorder.addEventListener("error", () => reject(recorder.error), { once: true });
    });
    options.onReady?.();
    await sleep((options.armDelaySec || 0) * 1000);
    options.onStart?.();
    recorder.start();
    await sleep(seconds * 1000);
    recorder.stop();
    await stopped;
    const blob = new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" });
    return {
      blob,
      stats: {
        mode: "webm",
        mime_type: blob.type,
        duration_sec: seconds,
        arm_delay_sec: options.armDelaySec || 0,
        bytes: blob.size,
      },
    };
  } finally {
    stopMediaStream(stream);
  }
}

async function recordAudioWav(seconds, options = {}) {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) throw new Error("This browser does not expose Web Audio capture.");
  const stream = await getMicrophoneStream();
  const context = new AudioContext();
  await context.resume?.();
  const source = context.createMediaStreamSource(stream);
  const processor = context.createScriptProcessor(4096, 1, 1);
  const silent = context.createGain();
  silent.gain.value = 0;
  const chunks = [];
  let totalLength = 0;
  let capturing = false;
  const sampleRate = context.sampleRate;

  processor.onaudioprocess = (event) => {
    if (!capturing) return;
    const input = event.inputBuffer.getChannelData(0);
    const chunk = new Float32Array(input.length);
    chunk.set(input);
    chunks.push(chunk);
    totalLength += chunk.length;
  };

  try {
    source.connect(processor);
    processor.connect(silent);
    silent.connect(context.destination);
    options.onReady?.();
    await sleep((options.armDelaySec || 0) * 1000);
    capturing = true;
    options.onStart?.();
    await sleep(seconds * 1000);
    capturing = false;

    const samples = mergeFloat32Chunks(chunks, totalLength);
    const wav = encodeWavMono(samples, sampleRate);
    const stats = calculatePcmStats(samples, sampleRate, seconds, options.armDelaySec || 0);
    stats.bytes = wav.byteLength;
    return { blob: new Blob([wav], { type: "audio/wav" }), stats };
  } finally {
    capturing = false;
    disconnectAudioNode(source);
    disconnectAudioNode(processor);
    disconnectAudioNode(silent);
    stopMediaStream(stream);
    try {
      await context.close?.();
    } catch {
      // Closing an already-interrupted context should not mask the capture error.
    }
  }
}

async function recordAudio(seconds, options = {}) {
  if (getAudioMode() === "webm") return recordAudioWebm(seconds, options);
  return recordAudioWav(seconds, options);
}

class AudioBed {
  constructor() {
    this.enabled = params().get("bgm") === "1";
    this.sourcePath = params().get("bgmSrc") || "";
    this.context = null;
    this.master = null;
    this.duckGain = null;
    this.oscillators = [];
    this.loopAudio = null;
  }

  start() {
    if (!this.enabled || this.context) return;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    this.context = new AudioContext();
    void this.context.resume?.();
    this.master = this.context.createGain();
    this.duckGain = this.context.createGain();
    this.master.gain.value = 0.0;
    this.duckGain.gain.value = 1.0;
    this.master.connect(this.duckGain).connect(this.context.destination);

    if (this.sourcePath && !this.loopAudio) {
      this.loopAudio = new Audio(normalizePath(this.sourcePath));
      this.loopAudio.loop = true;
      this.loopAudio.volume = 0.08;
      void this.loopAudio.play().catch((error) => console.warn("BGM playback failed", error));
    }
    this.master.gain.linearRampToValueAtTime(0.08, this.context.currentTime + 1.5);
  }

  pulse(frequency = 660, duration = 0.12) {
    if (!this.enabled) return;
    this.start();
    if (!this.context || !this.master) return;
    const oscillator = this.context.createOscillator();
    const gain = this.context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0, this.context.currentTime);
    gain.gain.linearRampToValueAtTime(0.18, this.context.currentTime + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.001, this.context.currentTime + duration);
    oscillator.connect(gain).connect(this.context.destination);
    oscillator.start();
    oscillator.stop(this.context.currentTime + duration + 0.02);
  }

  duck(duration = 2.2) {
    if (!this.context || !this.duckGain) return;
    const now = this.context.currentTime;
    this.duckGain.gain.cancelScheduledValues(now);
    this.duckGain.gain.setValueAtTime(this.duckGain.gain.value, now);
    this.duckGain.gain.linearRampToValueAtTime(0.28, now + 0.12);
    this.duckGain.gain.linearRampToValueAtTime(1.0, now + duration);
  }

  async playFile(path) {
    this.start();
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!this.context && AudioContext) {
      this.context = new AudioContext();
      void this.context.resume?.();
    }
    if (!this.context) throw new Error("Web Audio is not available.");
    const response = await fetch(normalizePath(path), { cache: "no-store" });
    if (!response.ok) throw new Error(`TTS audio load failed: ${response.status}`);
    const arrayBuffer = await response.arrayBuffer();
    const audioBuffer = await this.context.decodeAudioData(arrayBuffer);
    const source = this.context.createBufferSource();
    const gain = this.context.createGain();
    source.buffer = audioBuffer;
    gain.gain.value = 1.0;
    source.connect(gain).connect(this.context.destination);
    source.start();
    return new Promise((resolve) => {
      source.onended = resolve;
    });
  }
}

class SpatialControlPanel {
  constructor(demo) {
    this.demo = demo;
    this.group = new THREE.Group();
    this.group.name = "XR-Spatial-Control-Panel";
    this.group.visible = false;
    this.raycaster = new THREE.Raycaster();
    this.tempMatrix = new THREE.Matrix4();
    this.cameraPosition = new THREE.Vector3();
    this.cameraQuaternion = new THREE.Quaternion();
    this.controllerQuaternion = new THREE.Quaternion();
    this.controllerPosition = new THREE.Vector3();
    this.menuOffset = new THREE.Vector3();
    this.panelAnchorLift = new THREE.Vector3();
    this.deviceScaleTarget = new THREE.Vector3(1, 1, 1);
    this.workshopRightPosition = new THREE.Vector3();
    this.workshopLeftPosition = new THREE.Vector3();
    this.workshopLastRightPosition = new THREE.Vector3();
    this.workshopPinchCenter = new THREE.Vector3();
    this.workshopLastPinchCenter = new THREE.Vector3();
    this.workshopPinchVector = new THREE.Vector3();
    this.workshopLastPinchVector = new THREE.Vector3();
    this.workshopDelta = new THREE.Vector3();
    this.workshopCameraRight = new THREE.Vector3();
    this.workshopCameraUp = new THREE.Vector3();
    this.workshopGrabActive = false;
    this.workshopPinchActive = false;
    this.workshopPinchStartDistance = 0;
    this.workshopPinchStartScale = 1;
    this.controllers = [];
    this.buttons = [];
    this.hovered = null;
    this.hoveredController = null;
    this.menuMode = XR_MENU_MODE_COMPACT;
    this.fullPanelElements = [];
    this.normalInputElements = [];
    this.codeInputElements = [];
    this.codeInputMode = false;
    this.compactGroup = null;
    this.worldLockReady = false;
    this.worldLockPosition = new THREE.Vector3();
    this.worldLockQuaternion = new THREE.Quaternion();
    this.worldLockScale = new THREE.Vector3(1, 1, 1);
    this.lastMenuInteractionAt = performance.now();
    this.pulseClock = 0;
    this.recallSlot = 0;
    this.recallDraft = normalizeSpatialRecallDraft(this.demo.recallCode || UI.recallCodeInput?.value || "");

    this.buildPanel();
    this.initControllers();
    this.demo.scene.add(this.group);
  }

  buildPanel() {
    const panel = new THREE.Mesh(
      new THREE.PlaneGeometry(WATCH_PANEL_WIDTH, WATCH_PANEL_HEIGHT),
      new THREE.MeshBasicMaterial({
        color: 0x061116,
        transparent: true,
        opacity: 0.68,
        side: THREE.DoubleSide,
        depthTest: false,
      }),
    );
    panel.renderOrder = 10;
    this.group.add(panel);

    this.status = makeTextPlane("音声 待機", {
      width: 0.72,
      height: 0.12,
      fontSize: 68,
      color: "#fff4c8",
      background: "rgba(10, 26, 32, 0.82)",
      border: "rgba(255, 207, 90, 0.72)",
    });
    this.status.position.set(-0.38, 0.37, 0.012);
    this.group.add(this.status);

    this.hint = makeTextPlane(`合図: ${TRIGGER_PHRASE}`, {
      width: 0.78,
      height: 0.12,
      canvasHeight: 220,
      fontSize: 34,
      color: "#d7f8ff",
      background: "rgba(4, 13, 17, 0.58)",
      maxLines: 2,
    });
    this.hint.position.set(0.46, 0.37, 0.014);
    this.group.add(this.hint);

    this.progressBack = new THREE.Mesh(
      new THREE.PlaneGeometry(1.3, 0.025),
      new THREE.MeshBasicMaterial({ color: 0x223139, transparent: true, opacity: 0.8, depthTest: false }),
    );
    this.progressBack.position.set(0.03, 0.25, 0.014);
    this.progressBack.renderOrder = 12;
    this.group.add(this.progressBack);

    this.progressFill = new THREE.Mesh(
      new THREE.PlaneGeometry(1.3, 0.025),
      new THREE.MeshBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.95, depthTest: false }),
    );
    this.progressFill.position.set(-0.62, 0.25, 0.016);
    this.progressFill.scale.x = 0.001;
    this.progressFill.geometry.translate(0.65, 0, 0);
    this.progressFill.renderOrder = 13;
    this.group.add(this.progressFill);

    this.routeStatus = makeTextPlane("生成 ローカル | 試験 待機 | 記録 待機", {
      width: 1.42,
      height: 0.09,
      canvasWidth: 1400,
      canvasHeight: 160,
      fontSize: 30,
      fontWeight: 760,
      color: "#fff4c8",
      background: "rgba(4, 13, 17, 0.7)",
      border: "rgba(255, 207, 90, 0.42)",
      maxLines: 1,
    });
    this.routeStatus.position.set(0, 0.15, 0.017);
    this.group.add(this.routeStatus);

    this.equipmentStatus = makeTextPlane(formatEquipmentSpatialText(this.demo.equipmentDiagnostic), {
      width: 1.42,
      height: 0.085,
      canvasWidth: 1400,
      canvasHeight: 150,
      fontSize: 34,
      fontWeight: 820,
      color: "#fff4c8",
      background: "rgba(4, 13, 17, 0.72)",
      border: "rgba(255, 207, 90, 0.42)",
      maxLines: 1,
    });
    this.equipmentStatus.position.set(0, 0.055, 0.018);
    this.group.add(this.equipmentStatus);

    this.debug = makeTextPlane("音声デバッグ: 待機", {
      width: 1.42,
      height: 0.13,
      canvasWidth: 1400,
      canvasHeight: 240,
      fontSize: 25,
      fontWeight: 680,
      align: "left",
      baseline: "top",
      color: "#eef9ff",
      background: "rgba(2, 9, 13, 0.74)",
      border: "rgba(67, 216, 255, 0.34)",
      maxLines: 3,
    });
    this.debug.position.set(0, -0.05, 0.019);
    this.group.add(this.debug);

    this.listenRing = new THREE.Mesh(
      new THREE.RingGeometry(0.07, 0.08, 64),
      new THREE.MeshBasicMaterial({ color: 0x43d8ff, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthTest: false }),
    );
    this.listenRing.position.set(-0.74, 0.25, 0.019);
    this.listenRing.renderOrder = 15;
    this.group.add(this.listenRing);

    this.recallDisplay = makeTextPlane(`CODE ${this.recallDisplayCode()}`, {
      width: 0.82,
      height: 0.115,
      canvasWidth: 900,
      canvasHeight: 220,
      fontSize: 64,
      fontWeight: 850,
      color: "#fff4c8",
      background: "rgba(4, 13, 17, 0.76)",
      border: "rgba(255, 207, 90, 0.42)",
    });
    this.recallDisplay.position.set(-0.39, -0.18, 0.02);
    this.group.add(this.recallDisplay);

    this.normalInputElements.push(this.addButton("codeMode", "コード入力", 0.48, -0.18, 0xffcf5a, { width: 0.42, height: 0.098, fontSize: 46 }).group);
    this.normalInputElements.push(this.addButton("voice", "音声", -0.6, -0.31, 0xffcf5a).group);
    this.normalInputElements.push(this.addButton("replay", "記録再生", -0.2, -0.31, 0x43d8ff).group);
    this.normalInputElements.push(this.addButton("view", "鏡", 0.2, -0.31, 0x8edfff).group);
    this.normalInputElements.push(this.addButton("pause", "停止", 0.6, -0.31, 0xf6f1df).group);
    this.normalInputElements.push(this.addButton("reset", "\u30ea\u30bb\u30c3\u30c8", -0.68, -0.45, 0xff6b6b, { width: 0.28, fontSize: 42 }).group);
    this.normalInputElements.push(this.addButton("stand", "\u93a7\u7acb\u3066", -0.36, -0.45, 0xffcf5a, { width: 0.28, fontSize: 42 }).group);
    this.normalInputElements.push(this.addButton("mocopiCalibrate", "\u88dc\u6b63", -0.04, -0.45, 0x36f28f, { width: 0.28, fontSize: 46 }).group);
    this.normalInputElements.push(this.addButton("lock", "\u56fa\u5b9a", 0.28, -0.45, 0x8edfff, { width: 0.28, fontSize: 46 }).group);
    this.normalInputElements.push(this.addButton("close", "\u623b\u308b", 0.6, -0.45, 0x43d8ff, { width: 0.28, fontSize: 46 }).group);
    this.buildCodeInputPanel();
    this.fullPanelElements = [...this.group.children];
    this.buildCompactPanel();
    this.applyMenuMode();
  }

  buildCodeInputPanel() {
    this.codeInputHint = makeTextPlane("VRコード入力 数字4桁", {
      width: 1.24,
      height: 0.105,
      canvasWidth: 1200,
      canvasHeight: 190,
      fontSize: 48,
      fontWeight: 780,
      color: "#d7f8ff",
      background: "rgba(4, 13, 17, 0.68)",
      border: "rgba(67, 216, 255, 0.34)",
      maxLines: 1,
    });
    this.codeInputHint.position.set(0, 0.205, 0.022);
    this.group.add(this.codeInputHint);
    this.codeInputElements.push(this.codeInputHint);

    const rows = [
      ["1", "2", "3"],
      ["4", "5", "6"],
      ["7", "8", "9"],
      ["消", "0", "呼出"],
      ["戻る", "全消", ""],
    ];
    const xs = [-0.36, 0, 0.36];
    const ys = [-0.055, -0.16, -0.265, -0.37, -0.475];
    rows.forEach((row, rowIndex) => {
      row.forEach((label, colIndex) => {
        if (!label) return;
        const action = /^[0-9]$/.test(label)
          ? `codeDigit${label}`
          : label === "消"
            ? "codeBackspace"
            : label === "全消"
              ? "codeClear"
              : label === "呼出"
                ? "codeSubmit"
                : "codeBack";
        const width = label === "呼出" || label === "戻る" || label === "全消" ? 0.34 : 0.3;
        const color = label === "呼出" ? 0x43d8ff : label === "戻る" ? 0x8edfff : label === "全消" || label === "消" ? 0xff6b6b : 0xffcf5a;
        const button = this.addButton(action, label, xs[colIndex], ys[rowIndex], color, {
          width,
          height: 0.1,
          fontSize: /^[0-9]$/.test(label) ? 76 : 52,
          minFontSize: 42,
        });
        this.codeInputElements.push(button.group);
      });
    });
  }

  buildCompactPanel() {
    const group = new THREE.Group();
    group.name = "XR-Compact-Bracelet-Menu";
    group.position.z = 0.026;

    const base = new THREE.Mesh(
      new THREE.PlaneGeometry(WATCH_COMPACT_PANEL_WIDTH, WATCH_COMPACT_PANEL_HEIGHT),
      new THREE.MeshBasicMaterial({
        color: 0x061116,
        transparent: true,
        opacity: 0.82,
        side: THREE.DoubleSide,
        depthTest: false,
      }),
    );
    base.renderOrder = 22;
    group.add(base);

    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.05, 0.058, 36),
      new THREE.MeshBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthTest: false }),
    );
    ring.position.set(-0.27, 0, 0.011);
    ring.renderOrder = 23;
    group.add(ring);
    this.compactRing = ring;

    this.compactTitle = makeTextPlane("メニュー", {
      width: 0.42,
      height: 0.07,
      canvasWidth: 720,
      canvasHeight: 140,
      fontSize: 54,
      color: "#fff4c8",
      background: null,
    });
    this.compactTitle.position.set(0.08, 0.055, 0.012);
    group.add(this.compactTitle);

    this.compactStatus = makeTextPlane("音声 待機", {
      width: 0.5,
      height: 0.055,
      canvasWidth: 760,
      canvasHeight: 120,
      fontSize: 40,
      color: "#d7f8ff",
      background: null,
    });
    this.compactStatus.position.set(0.08, -0.055, 0.013);
    group.add(this.compactStatus);

    this.compactGroup = group;
    this.group.add(group);
  }

  addButton(action, label, x, y, color, options = {}) {
    const width = options.width || 0.38;
    const height = options.height || 0.112;
    const button = new THREE.Group();
    button.name = `XR-Button-${action}`;
    button.position.set(x, y, 0.025);

    const hit = new THREE.Mesh(
      new THREE.PlaneGeometry(width, height),
      new THREE.MeshBasicMaterial({
        color: 0x0a1d24,
        transparent: true,
        opacity: 0.92,
        side: THREE.DoubleSide,
        depthTest: false,
      }),
    );
    hit.renderOrder = 16;
    hit.userData.action = action;
    hit.userData.baseColor = 0x0a1d24;
    hit.userData.hoverColor = color;
    button.add(hit);

    const text = makeTextPlane(label, {
      width: Math.max(0.1, width - 0.026),
      height: Math.max(0.086, height * 0.86),
      canvasWidth: options.canvasWidth || 900,
      canvasHeight: options.canvasHeight || 240,
      fontSize: options.fontSize || 58,
      fontWeight: options.fontWeight || 850,
      minFontSize: options.minFontSize || 38,
      paddingX: options.paddingX || 20,
      color: "#eef9ff",
      background: null,
    });
    text.position.z = 0.01;
    button.add(text);

    this.group.add(button);
    const entry = { action, group: button, hit, text };
    this.buttons.push(entry);
    return entry;
  }

  applyMenuMode() {
    const compact = this.menuMode === XR_MENU_MODE_COMPACT;
    for (const element of this.fullPanelElements) {
      element.visible = !compact;
    }
    if (this.compactGroup) this.compactGroup.visible = compact;
    this.applyCodeInputModeVisibility();
    this.updateMenuModeLabels();
  }

  applyCodeInputModeVisibility() {
    const panelOpen = this.menuMode !== XR_MENU_MODE_COMPACT;
    for (const element of this.normalInputElements) {
      element.visible = panelOpen && !this.codeInputMode;
    }
    for (const element of this.codeInputElements) {
      element.visible = panelOpen && this.codeInputMode;
    }
    for (const element of [this.progressBack, this.progressFill, this.routeStatus, this.equipmentStatus, this.debug, this.listenRing]) {
      if (element) element.visible = panelOpen && !this.codeInputMode;
    }
    if (this.recallDisplay) {
      this.recallDisplay.position.set(this.codeInputMode ? 0 : -0.39, this.codeInputMode ? 0.085 : -0.18, 0.02);
    }
  }

  markMenuInteraction() {
    this.lastMenuInteractionAt = performance.now();
  }

  setMenuMode(mode) {
    const nextMode = [XR_MENU_MODE_COMPACT, XR_MENU_MODE_OPEN, XR_MENU_MODE_WORLD_LOCKED].includes(mode)
      ? mode
      : XR_MENU_MODE_COMPACT;
    if (nextMode === XR_MENU_MODE_WORLD_LOCKED) {
      this.captureWorldLockAnchor();
    } else {
      this.worldLockReady = false;
    }
    this.menuMode = nextMode;
    this.markMenuInteraction();
    this.applyMenuMode();
  }

  setCodeInputMode(enabled) {
    this.codeInputMode = Boolean(enabled);
    if (this.codeInputMode) {
      this.setMenuMode(this.menuMode === XR_MENU_MODE_COMPACT ? XR_MENU_MODE_OPEN : this.menuMode);
      this.setRecallDraft(UI.recallCodeInput?.value || this.demo.recallCode || XR_RECALL_CODE_EMPTY, { syncInput: false });
    }
    this.markMenuInteraction();
    this.applyCodeInputModeVisibility();
    this.updateRecallDisplay();
  }

  togglePanelOpen() {
    if (this.menuMode === XR_MENU_MODE_COMPACT) {
      this.setMenuMode(XR_MENU_MODE_OPEN);
      return;
    }
    if (this.menuMode === XR_MENU_MODE_WORLD_LOCKED) {
      this.setMenuMode(XR_MENU_MODE_OPEN);
      return;
    }
    this.setMenuMode(XR_MENU_MODE_COMPACT);
  }

  toggleWorldLock() {
    this.setMenuMode(this.menuMode === XR_MENU_MODE_WORLD_LOCKED ? XR_MENU_MODE_OPEN : XR_MENU_MODE_WORLD_LOCKED);
  }

  captureWorldLockAnchor() {
    this.worldLockPosition.copy(this.group.position);
    this.worldLockQuaternion.copy(this.group.quaternion);
    this.worldLockScale.copy(this.group.scale);
    this.worldLockReady = true;
  }

  updateMenuModeLabels() {
    for (const button of this.buttons) {
      if (button.action === "lock") {
        updateTextPlane(button.text, this.menuMode === XR_MENU_MODE_WORLD_LOCKED ? "追従" : "固定");
      }
      if (button.action === "stand") {
        updateTextPlane(button.text, this.demo.armorStandPreview ? "収納" : "鎧立て");
      }
      if (button.action === "view") {
        updateTextPlane(button.text, this.demo.armorStandPreview ? "鏡へ" : "鏡");
      }
      if (button.action === "close") {
        updateTextPlane(button.text, this.demo.armorStandPreview ? "戻る" : "閉じる");
      }
    }
    if (this.compactTitle) updateTextPlane(this.compactTitle, "メニュー");
  }

  setArmorStandPreview(active) {
    this.updateMenuModeLabels();
    if (this.compactStatus && active) {
      updateTextPlane(this.compactStatus, "鎧立て", { color: "#fff4c8" });
    }
  }

  updateRecallDisplay(state = "pending") {
    if (!this.recallDisplay) return;
    const color = state === "error" ? "#ffd2d2" : state === "ok" ? "#d7f8ff" : "#fff4c8";
    const border =
      state === "error"
        ? "rgba(255, 107, 107, 0.72)"
        : state === "ok"
          ? "rgba(67, 216, 255, 0.58)"
          : "rgba(255, 207, 90, 0.42)";
    updateTextPlane(this.recallDisplay, `CODE ${this.recallDisplayCode()}`, {
      color,
      border,
    });
  }

  recallDisplayCode() {
    if (this.codeInputMode) return formatSpatialRecallDraft(this.recallDraft, this.recallSlot);
    return this.demo.recallCode || recallDraftToCode(this.recallDraft) || "未呼出";
  }

  setRecallDraft(code, options = {}) {
    const next = normalizeSpatialRecallDraft(code || XR_RECALL_CODE_EMPTY);
    this.recallDraft = next;
    this.recallSlot = clamp(this.recallSlot, 0, 3);
    if (options.syncInput !== false && UI.recallCodeInput) {
      UI.recallCodeInput.value = recallDraftToInputValue(next);
    }
    this.updateRecallDisplay(options.state || "pending");
  }

  cycleRecallSlot() {
    this.recallSlot = (this.recallSlot + 1) % 4;
    this.updateRecallDisplay();
  }

  cycleRecallChar(delta = 1) {
    const draft = Array.from(normalizeSpatialRecallDraft(this.recallDraft));
    const current = draft[this.recallSlot];
    const currentIndex = XR_RECALL_CHARS.includes(current) ? XR_RECALL_CHARS.indexOf(current) : -1;
    const nextIndex = (currentIndex + delta + XR_RECALL_CHARS.length) % XR_RECALL_CHARS.length;
    draft[this.recallSlot] = XR_RECALL_CHARS[nextIndex];
    this.setRecallDraft(draft.join(""));
  }

  appendRecallDigit(digit) {
    if (!/^[0-9]$/.test(String(digit))) return;
    const draft = Array.from(normalizeSpatialRecallDraft(this.recallDraft));
    const slot = draft.indexOf("-");
    if (slot < 0) return;
    draft[slot] = String(digit);
    this.recallSlot = clamp(slot + 1, 0, 3);
    this.setRecallDraft(draft.join(""));
  }

  backspaceRecallDigit() {
    const draft = Array.from(normalizeSpatialRecallDraft(this.recallDraft));
    let slot = draft.indexOf("-");
    slot = slot < 0 ? 3 : Math.max(0, slot - 1);
    draft[slot] = "-";
    this.recallSlot = slot;
    this.setRecallDraft(draft.join(""));
  }

  clearRecallDraft() {
    this.recallSlot = 0;
    this.setRecallDraft(XR_RECALL_CODE_EMPTY);
  }

  async loadRecallDraft() {
    const code = recallDraftToCode(this.recallDraft);
    if (!RECALL_CODE_RE.test(code)) {
      this.updateRecallDisplay("error");
      this.demo.setRecallCodeState("VRコードは数字4桁です。", "error");
      this.demo.setRouteApi("CODE INPUT", "error");
      return;
    }
    try {
      await this.demo.loadSuitByRecallCode(code, { reloadMeshes: true, pushUrl: true });
      this.setCodeInputMode(false);
    } catch (error) {
      this.updateRecallDisplay("error");
      this.demo.setRecallCodeState(String(error?.message || error), "error");
      this.demo.setRouteApi("CODE ERROR", "error");
    }
  }

  canUseRightTriggerShortcut() {
    return this.menuMode !== XR_MENU_MODE_OPEN && !this.demo.isArmorStandPreviewMode();
  }

  compactForTransformStart() {
    if (this.menuMode !== XR_MENU_MODE_COMPACT) this.setMenuMode(XR_MENU_MODE_COMPACT);
  }

  initControllers() {
    for (let index = 0; index < 2; index += 1) {
      const controller = this.demo.renderer.xr.getController(index);
      controller.userData.controllerIndex = index;
      controller.addEventListener("connected", (event) => {
        controller.userData.handedness = event.data?.handedness || controller.userData.handedness;
        controller.userData.inputSource = event.data || null;
        controller.userData.squeezePressed = false;
      });
      controller.addEventListener("disconnected", () => {
        controller.userData.inputSource = null;
        controller.userData.squeezePressed = false;
      });
      controller.addEventListener("squeezestart", () => {
        controller.userData.squeezePressed = true;
      });
      controller.addEventListener("squeezeend", () => {
        controller.userData.squeezePressed = false;
      });
      controller.addEventListener("selectstart", () => this.activateController(controller));
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)]),
        new THREE.LineBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.55 }),
      );
      line.name = "XR-Menu-Ray";
      line.scale.z = 1.4;
      controller.add(line);
      const device = this.createTransformDevice();
      controller.add(device);
      controller.userData.transformDevice = device;
      this.demo.scene.add(controller);
      this.controllers.push(controller);
    }
  }

  createTransformDevice() {
    const device = new THREE.Group();
    device.name = "XR-Right-Hand-Henshin-Device";
    device.visible = false;
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(0.09, 0.045, 0.16),
      new THREE.MeshBasicMaterial({ color: 0x061116, transparent: true, opacity: 0.88, side: THREE.DoubleSide }),
    );
    body.position.set(0, -0.025, -0.055);
    device.add(body);
    const lens = new THREE.Mesh(
      new THREE.RingGeometry(0.032, 0.042, 28),
      new THREE.MeshBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.9, side: THREE.DoubleSide }),
    );
    lens.position.set(0, -0.025, -0.14);
    lens.rotation.x = Math.PI / 2;
    device.add(lens);
    const glow = new THREE.PointLight(0xffcf5a, 0.45, 0.45);
    glow.position.set(0, -0.02, -0.1);
    device.add(glow);
    device.userData.body = body;
    device.userData.lens = lens;
    device.userData.glow = glow;
    device.userData.baseScale = 1;
    return device;
  }

  controllerHandedness(controller) {
    if (!controller) return "";
    return controller.userData.handedness || (controller.userData.controllerIndex === 0 ? "left" : "right");
  }

  getControllerByHand(hand, { allowIndexFallback = false } = {}) {
    const tracked = this.controllers.find(
      (controller) => controller?.userData?.inputSource && this.controllerHandedness(controller) === hand,
    );
    if (tracked) return tracked;
    if (!allowIndexFallback) return null;
    const fallback = hand === "left" ? this.controllers[0] : this.controllers[1];
    if (!fallback || fallback?.userData?.inputSource) return null;
    return this.controllerHandedness(fallback) === hand ? fallback : null;
  }

  controllerInputSnapshot(controller, index) {
    const inputSource = controller?.userData?.inputSource || null;
    const gamepad = inputSource?.gamepad || null;
    const buttons = gamepad?.buttons || [];
    const button = buttons[index] || null;
    const value = Number(button?.value || 0);
    const squeezeEventPressed = index === 1 && controller?.userData?.squeezePressed === true;
    return {
      handedness: this.controllerHandedness(controller),
      connected: Boolean(controller),
      inputSource: Boolean(inputSource),
      profiles: Array.isArray(inputSource?.profiles) ? inputSource.profiles.slice(0, 4) : [],
      gamepad: Boolean(gamepad),
      mapping: gamepad?.mapping || "",
      buttonCount: Number(buttons.length || 0),
      axesCount: Number(gamepad?.axes?.length || 0),
      index,
      available: Boolean(button),
      squeezeEventPressed,
      pressed: Boolean(button?.pressed || value > 0.65 || squeezeEventPressed),
      value: roundDebugNumber(value, 3),
    };
  }

  controllerButtonPressed(controller, index) {
    return this.controllerInputSnapshot(controller, index).pressed;
  }

  controllerSqueezePressed(controller) {
    return this.controllerButtonPressed(controller, 1);
  }

  resetArmorStandWorkshopControlState({ notifyDemo = false } = {}) {
    const wasManipulating = this.workshopGrabActive || this.workshopPinchActive;
    this.workshopGrabActive = false;
    this.workshopPinchActive = false;
    if (wasManipulating && notifyDemo) this.demo.finishArmorStandWorkshopManipulation();
  }

  armorStandWorkshopInputSnapshot() {
    const right = this.getControllerByHand("right");
    const left = this.getControllerByHand("left");
    return {
      active: Boolean(this.demo.isArmorStandPreviewMode()),
      mode: this.workshopPinchActive ? "two_grip_scale_rotate_move" : this.workshopGrabActive ? "right_grip_rig_move" : "idle",
      triggerMapping: "gamepad.buttons[0]",
      gripMapping: "gamepad.buttons[1]",
      rightTrigger: this.controllerInputSnapshot(right, 0),
      rightGrip: this.controllerInputSnapshot(right, 1),
      leftTrigger: this.controllerInputSnapshot(left, 0),
      leftGrip: this.controllerInputSnapshot(left, 1),
      controllerCount: this.controllers.length,
    };
  }

  getMenuController() {
    return this.getControllerByHand("left", { allowIndexFallback: true }) || this.controllers[0] || null;
  }

  setDebug(text) {
    if (!this.debug) return;
    updateTextPlane(this.debug, text || "音声デバッグ: 待機", {
      color: "#eef9ff",
      maxLines: 3,
    });
  }

  setEquipmentStatus(diagnostic) {
    if (!this.equipmentStatus) return;
    const status = diagnostic || makeEquipmentDiagnostic(null);
    updateTextPlane(this.equipmentStatus, formatEquipmentSpatialText(status), {
      ...equipmentStateStyle(status.state),
      maxLines: 1,
    });
  }

  setRouteStatus(text, state = "pending") {
    if (!this.routeStatus) return;
    const color = state === "error" ? "#ffd2d2" : state === "ok" ? "#eef9ff" : "#fff4c8";
    const border =
      state === "error"
        ? "rgba(255, 107, 107, 0.72)"
        : state === "ok"
          ? "rgba(67, 216, 255, 0.54)"
          : "rgba(255, 207, 90, 0.42)";
    updateTextPlane(this.routeStatus, text || "生成 ローカル | 試験 待機 | 記録 待機", {
      color,
      border,
      maxLines: 1,
    });
  }

  setVoiceState(state, detail = "") {
    const voiceState = VOICE_STATES[state] || VOICE_STATES.ready;
    const textColor = voiceState.textColor || "#fff4c8";
    const border = voiceState.border || "rgba(255, 207, 90, 0.72)";
    updateTextPlane(this.status, voiceState.label, {
      color: textColor,
      border,
    });
    updateTextPlane(this.hint, detail || voiceState.hint, {
      color: textColor,
    });
    if (this.compactStatus) {
      updateTextPlane(this.compactStatus, voiceState.label, {
        color: textColor,
      });
    }
    const stateColor = voiceDeviceColorForState(state);
    this.listenRing.material.color.setHex(stateColor);
    if (this.compactRing) this.compactRing.material.color.setHex(stateColor);
    for (const button of this.buttons) {
      if (button.action === "pause") {
        updateTextPlane(button.text, this.demo.playing ? "停止" : "再開");
      }
    }
  }

  setArchiveViewMode(mode) {
    for (const button of this.buttons) {
      if (button.action === "view") {
        updateTextPlane(button.text, mode === XR_VIEW_MODE_OBSERVER ? "鏡へ" : "観察へ");
      }
    }
  }

  setProgress(progress) {
    this.progressFill.scale.x = Math.max(0.001, clamp(progress, 0, 1));
  }

  update(dt) {
    const inVR = Boolean(this.demo.world.session);
    this.group.visible = inVR;
    if (
      this.menuMode === XR_MENU_MODE_OPEN
      && !this.codeInputMode
      && performance.now() - this.lastMenuInteractionAt > XR_MENU_OPEN_AUTO_COMPACT_MS
    ) {
      this.setMenuMode(XR_MENU_MODE_COMPACT);
    }
    for (const controller of this.controllers) {
      controller.visible = inVR;
      const ray = controller.getObjectByName("XR-Menu-Ray");
      if (ray) ray.visible = inVR;
      const device = controller.userData.transformDevice;
      if (device) {
        const isRightHand = this.controllerHandedness(controller) === "right";
        device.visible = inVR && isRightHand;
        if (isRightHand) this.updateTransformDevice(device, dt);
      }
    }
    if (!inVR) {
      this.resetArmorStandWorkshopControlState({ notifyDemo: true });
      return;
    }

    const xrCamera = this.demo.renderer.xr.getCamera(this.demo.camera) || this.demo.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    xrCamera.getWorldQuaternion(this.cameraQuaternion);
    this.updateArmorStandWorkshopControls(dt);
    const wrist = this.getMenuController();
    if (wrist) {
      wrist.getWorldPosition(this.controllerPosition);
      wrist.getWorldQuaternion(this.controllerQuaternion);
    }
    const wristDistance = wrist ? this.controllerPosition.distanceTo(this.cameraPosition) : 0;
    if (this.menuMode === XR_MENU_MODE_WORLD_LOCKED && this.worldLockReady) {
      this.group.position.copy(this.worldLockPosition);
      this.group.quaternion.copy(this.worldLockQuaternion);
      this.group.scale.copy(this.worldLockScale);
    } else if (wrist && wristDistance > 0.08 && wristDistance < 1.7) {
      const compact = this.menuMode === XR_MENU_MODE_COMPACT;
      const menuScale = compact ? WATCH_COMPACT_SCALE : WATCH_PANEL_SCALE;
      const panelHeight = compact ? WATCH_COMPACT_PANEL_HEIGHT : WATCH_PANEL_HEIGHT;
      this.group.quaternion.copy(this.controllerQuaternion).multiply(WATCH_PANEL_ROTATION);
      this.group.scale.setScalar(menuScale);
      this.menuOffset.set(0, 0, -WATCH_PANEL_SURFACE_GAP).applyQuaternion(this.controllerQuaternion);
      this.panelAnchorLift
        .set(0, panelHeight * menuScale * 0.5 + WATCH_PANEL_BOTTOM_CLEARANCE, 0)
        .applyQuaternion(this.group.quaternion);
      this.group.position.copy(this.controllerPosition).add(this.menuOffset).add(this.panelAnchorLift);
    } else {
      const needsReanchor =
        !this.demo.menuFallbackReady
        || this.demo.menuFallbackPosition.distanceTo(this.cameraPosition) > XR_MENU_FALLBACK_REANCHOR_DISTANCE;
      this.demo.ensureMenuFallbackAnchor({ force: needsReanchor });
      this.group.position.lerp(this.demo.menuFallbackPosition, 0.35);
      this.group.quaternion.copy(this.demo.menuFallbackQuaternion);
      this.group.scale.setScalar(this.menuMode === XR_MENU_MODE_COMPACT ? WATCH_COMPACT_SCALE : WATCH_PANEL_FALLBACK_SCALE);
    }

    this.pulseClock += dt;
    const pulse = 1 + Math.sin(this.pulseClock * 5.8) * 0.08;
    this.listenRing.scale.setScalar(pulse);
    this.listenRing.material.opacity = this.demo.voiceState === "recording" ? 0.95 : 0.45 + Math.sin(this.pulseClock * 3.0) * 0.18;
    if (this.compactRing) {
      this.compactRing.scale.setScalar(pulse);
      this.compactRing.material.opacity = this.listenRing.material.opacity;
    }

    this.updateHover();
  }

  updateArmorStandWorkshopControls(dt) {
    if (!this.demo.isArmorStandPreviewMode()) {
      this.resetArmorStandWorkshopControlState({ notifyDemo: true });
      return;
    }
    const right = this.getControllerByHand("right");
    const left = this.getControllerByHand("left");
    const rightGrip = this.controllerButtonPressed(right, 1);
    const leftGrip = this.controllerButtonPressed(left, 1);

    if (rightGrip && leftGrip && right && left) {
      right.getWorldPosition(this.workshopRightPosition);
      left.getWorldPosition(this.workshopLeftPosition);
      const distance = Math.max(0.08, this.workshopRightPosition.distanceTo(this.workshopLeftPosition));
      this.workshopPinchCenter.copy(this.workshopRightPosition).add(this.workshopLeftPosition).multiplyScalar(0.5);
      this.workshopPinchVector.copy(this.workshopRightPosition).sub(this.workshopLeftPosition);
      if (!this.workshopPinchActive) {
        this.workshopPinchActive = true;
        this.workshopGrabActive = false;
        this.workshopPinchStartDistance = distance;
        this.workshopPinchStartScale = this.demo.armorStandScale || 1;
        this.workshopLastPinchCenter.copy(this.workshopPinchCenter);
        this.workshopLastPinchVector.copy(this.workshopPinchVector);
      } else {
        this.demo.setArmorStandWorkshopScale(
          this.workshopPinchStartScale * (distance / Math.max(this.workshopPinchStartDistance, 0.08)),
          { source: "twoGripScale" },
        );
        this.workshopDelta.copy(this.workshopPinchCenter).sub(this.workshopLastPinchCenter);
        if (this.workshopDelta.length() > ARMOR_STAND_MOVE_DEADZONE_M) {
          this.workshopDelta.clampLength(0, ARMOR_STAND_MOVE_MAX_DELTA_M);
          this.demo.applyArmorStandWorkshopMove({ delta: this.workshopDelta, source: "twoGripRigMove" });
        }
        const previousYaw = Math.atan2(this.workshopLastPinchVector.x, this.workshopLastPinchVector.z);
        const nextYaw = Math.atan2(this.workshopPinchVector.x, this.workshopPinchVector.z);
        let yawDelta = nextYaw - previousYaw;
        if (yawDelta > Math.PI) yawDelta -= TAU;
        if (yawDelta < -Math.PI) yawDelta += TAU;
        if (Math.abs(yawDelta) > ARMOR_STAND_TWO_HAND_YAW_DEADZONE_RAD) {
          this.demo.applyArmorStandWorkshopDrag({ yawDelta, pitchDelta: 0, source: "twoGripRigYaw" });
        }
        this.workshopLastPinchCenter.copy(this.workshopPinchCenter);
        this.workshopLastPinchVector.copy(this.workshopPinchVector);
      }
      return;
    }

    if (this.workshopPinchActive) {
      this.workshopPinchActive = false;
      this.demo.finishArmorStandWorkshopManipulation();
    }

    if (rightGrip && right) {
      right.getWorldPosition(this.workshopRightPosition);
      if (!this.workshopGrabActive) {
        this.workshopGrabActive = true;
        this.workshopLastRightPosition.copy(this.workshopRightPosition);
        return;
      }
      this.workshopDelta.copy(this.workshopRightPosition).sub(this.workshopLastRightPosition);
      if (this.workshopDelta.length() > ARMOR_STAND_MOVE_DEADZONE_M) {
        this.workshopDelta.clampLength(0, ARMOR_STAND_MOVE_MAX_DELTA_M);
        this.demo.applyArmorStandWorkshopMove({ delta: this.workshopDelta, source: "rightGripRigMove" });
      }
      this.workshopLastRightPosition.copy(this.workshopRightPosition);
      return;
    }

    if (this.workshopGrabActive) {
      this.workshopGrabActive = false;
      this.demo.finishArmorStandWorkshopManipulation();
    }
  }

  updateTransformDevice(device, dt) {
    const lens = device.userData.lens;
    const glow = device.userData.glow;
    const body = device.userData.body;
    const active = ["arming", "recording", "analyzing", "detected", "deposition"].includes(this.demo.voiceState);
    const ready = this.demo.voiceState === "ready";
    const pulse = 0.5 + Math.sin(this.pulseClock * (active ? 9.0 : 3.4)) * 0.5;
    const color = voiceDeviceColorForState(this.demo.voiceState);
    if (lens) {
      lens.material.color.setHex(color);
      lens.material.opacity = active ? 0.95 : ready ? 0.72 + pulse * 0.16 : 0.56;
    }
    if (body) {
      body.material.color.setHex(active ? 0x15100a : 0x061116);
      body.material.opacity = active ? 0.96 : 0.84;
    }
    if (glow) {
      glow.color.setHex(color);
      glow.intensity = active ? 1.0 + pulse * 1.05 : ready ? 0.38 + pulse * 0.36 : 0.28;
    }
    const scale = active ? 1.0 + pulse * 0.08 : 1.0;
    this.deviceScaleTarget.set(scale, scale, scale);
    device.scale.lerp(this.deviceScaleTarget, Math.min(1, dt * 10));
  }

  updateHover() {
    let nextHover = null;
    let nextController = null;
    for (const controller of this.controllers) {
      this.tempMatrix.identity().extractRotation(controller.matrixWorld);
      this.raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
      this.raycaster.ray.direction.set(0, 0, -1).applyMatrix4(this.tempMatrix);
      const activeHits = this.buttons
        .filter((button) => button.group.visible && button.hit.visible)
        .map((button) => button.hit);
      const intersections = activeHits.length ? this.raycaster.intersectObjects(activeHits, false) : [];
      if (intersections.length) {
        nextHover = intersections[0].object;
        nextController = controller;
        this.markMenuInteraction();
        break;
      }
    }
    if (nextHover === this.hovered) {
      this.hoveredController = nextController;
      return;
    }
    for (const button of this.buttons) {
      const hovered = button.hit === nextHover;
      button.hit.material.color.setHex(hovered ? button.hit.userData.hoverColor : button.hit.userData.baseColor);
      button.group.scale.setScalar(hovered ? 1.045 : 1);
    }
    this.hovered = nextHover;
    this.hoveredController = nextController;
  }

  activateHovered() {
    if (!this.group.visible || !this.hovered) return;
    this.markMenuInteraction();
    this.demo.audioBed.pulse(820, 0.08);
    const action = this.hovered.userData.action;
    if (action === "voice") void this.demo.runVoiceCommand();
    if (action === "replay") this.demo.replayFromStart({ speak: true, viewMode: this.demo.archiveViewMode, source: "archive" });
    if (action === "view") this.demo.activateMirrorOrToggleArchiveView();
    if (action === "pause") this.demo.togglePause();
    if (action === "reset") this.demo.reset();
    if (action === "mocopiCalibrate") this.demo.calibrateLiveBodySimArmorToBody({ source: "xrPanel" });
    if (action === "stand") {
      if (this.demo.isArmorStandPreviewMode()) {
        this.demo.exitArmorStandToMirror({ source: "xrStandButton" });
      } else {
        this.demo.toggleArmorStandPreview();
      }
    }
    if (action === "lock") this.toggleWorldLock();
    if (action === "close") {
      if (this.demo.isArmorStandPreviewMode()) {
        this.demo.exitArmorStandToMirror({ source: "xrCloseButton" });
      } else {
        this.setMenuMode(XR_MENU_MODE_COMPACT);
      }
    }
    if (action === "codeMode") this.setCodeInputMode(true);
    if (action === "codeBack") this.setCodeInputMode(false);
    if (action === "codeClear") this.clearRecallDraft();
    if (action === "codeBackspace") this.backspaceRecallDigit();
    if (action === "codeSubmit") void this.loadRecallDraft();
    if (action.startsWith("codeDigit")) this.appendRecallDigit(action.slice("codeDigit".length));
  }

  canActivateHoveredInArmorStand(action) {
    return ARMOR_STAND_EXIT_ACTIONS.has(action);
  }

  activateController(controller) {
    if (this.controllerHandedness(controller) === "right" && this.demo.isArmorStandPreviewMode()) {
      if (this.controllerButtonPressed(controller, 1)) {
        this.demo.exitArmorStandToMirror({ source: "rightGripTriggerEscape" });
        return;
      }
      if (
        this.group.visible
        && this.hovered
        && this.hoveredController === controller
        && this.canActivateHoveredInArmorStand(this.hovered.userData.action)
      ) {
        this.activateHovered();
        return;
      }
      this.markMenuInteraction();
      this.demo.audioBed.pulse(1040, 0.1);
      this.demo.toggleArmorStandPartExplosion({ source: "rightTrigger", handedness: "right" });
      return;
    }
    if (this.group.visible && this.hovered && this.hoveredController === controller) {
      this.activateHovered();
      return;
    }
    if (this.controllerHandedness(controller) === "left") {
      this.markMenuInteraction();
      this.demo.audioBed.pulse(620, 0.08);
      this.togglePanelOpen();
      return;
    }
    if (this.controllerHandedness(controller) === "right") {
      this.demo.audioBed.pulse(1040, 0.1);
      if (this.demo.voiceState === "rejected" && this.demo.canRunVoiceCommand()) {
        this.compactForTransformStart();
        this.demo.setVoiceState("ready", `右トリガーで再入力します。${TRIGGER_PHRASE} の発声案内を待ってください。`);
        void this.demo.runVoiceCommand();
        return;
      }
      if (!this.canUseRightTriggerShortcut() || !this.demo.canRunVoiceCommand()) return;
      this.compactForTransformStart();
      void this.demo.runVoiceCommand();
    }
  }
}

class QuestHenshinDemo {
  constructor(world) {
    this.world = world;
    this.scene = world.scene;
    this.camera = world.camera;
    this.renderer = world.renderer;
    this.clock = new THREE.Clock();
    this.duration = 3.2;
    this.elapsed = 0;
    this.playing = true;
    this.completionAnnounced = false;
    this.replay = null;
    this.frames = [];
    this.suitspec = null;
    this.suitRecord = null;
    this.recallCode = getRecallCode();
    this.activeSuitId = getSuitId();
    this.activeManifestId = getManifestId();
    this.runtimePackage = null;
    this.meshes = new Map();
    this.liveMirrorMeshes = new Map();
    this.armorStandPreview = false;
    this.armorStandYaw = 0;
    this.armorStandPitch = 0;
    this.armorStandScale = 1;
    this.armorStandOffset = new THREE.Vector3();
    this.armorStandExploded = false;
    this.armorStandInteractionMode = "assembled";
    this.armorStandInteractCount = 0;
    this.depositionEffects = null;
    this.voiceState = "ready";
    this.trialId = null;
    this.trialReady = false;
    this.trialReplayPath = null;
    this.depositionStartPromise = null;
    this.xrViewMode = XR_VIEW_MODE_SELF;
    this.archiveViewMode = getArchiveViewMode();
    this.playbackSource = "voice";
    this.routeState = {
      apiLabel: useNewRouteApi() ? "/v1 ARMED" : "OFF",
      apiState: useNewRouteApi() ? "pending" : "idle",
      trialLabel: "WAIT",
      trialState: "pending",
      replayLabel: "WAIT",
      replayState: "pending",
    };
    this.equipmentDiagnostic = makeEquipmentDiagnostic(null);
    this.audioBed = new AudioBed();
    this.cameraPosition = new THREE.Vector3();
    this.cameraQuaternion = new THREE.Quaternion();
    this.xrForward = new THREE.Vector3();
    this.rigTargetPosition = new THREE.Vector3();
    this.rigTargetQuaternion = new THREE.Quaternion();
    this.viewForwardQuaternion = new THREE.Quaternion();
    this.rigTargetEuler = new THREE.Euler(0, 0, 0, "YXZ");
    this.xrWorldAnchorReady = false;
    this.xrWorldAnchorMode = null;
    this.xrWorldAnchorProfile = null;
    this.xrWorldAnchorPosition = new THREE.Vector3();
    this.xrWorldAnchorQuaternion = new THREE.Quaternion();
    this.xrWorldAnchorScale = new THREE.Vector3(1, 1, 1);
    this.menuFallbackReady = false;
    this.menuFallbackPosition = new THREE.Vector3();
    this.menuFallbackQuaternion = new THREE.Quaternion();
    this.menuFallbackRight = new THREE.Vector3();
    this.menuFallbackForward = new THREE.Vector3();
    this.liveMirrorReady = false;
    this.liveMirrorPosition = new THREE.Vector3();
    this.liveMirrorQuaternion = new THREE.Quaternion();
    this.liveMirrorScale = new THREE.Vector3(LIVE_MIRROR_SCALE, LIVE_MIRROR_SCALE, LIVE_MIRROR_SCALE);
    this.liveHeadPosition = new THREE.Vector3();
    this.liveLeftHandPosition = new THREE.Vector3();
    this.liveRightHandPosition = new THREE.Vector3();
    this.livePartPosition = new THREE.Vector3();
    this.livePartPositionB = new THREE.Vector3();
    this.livePartPositionC = new THREE.Vector3();
    this.leftHandTracked = false;
    this.rightHandTracked = false;
    this.liveTorsoYaw = 0;
    this.liveMotionFrames = [];
    this.archiveMotionFrames = [];
    this.replayMotionSource = "";
    this.replayMotionDiagnostic = makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);
    this.lastLiveMotionSampleAt = -Infinity;
    this.liveBodySimEnabled = useMocopiLiveBodySim();
    this.liveBodySimLatestPath = getBodySimLatestPath();
    this.liveBodySimPollIntervalMs = getLiveBodySimPollIntervalMs();
    this.liveBodySimRenderProfile = getLiveBodySimRenderProfile();
    this.liveBodySimRenderCalibratedAt = "";
    this.liveBodySimRenderCalibrationSource = "";
    this.liveBodySimLastPollAt = -Infinity;
    this.liveBodySimLastOkAt = -Infinity;
    this.liveBodySimInFlight = false;
    this.liveBodySimFrameCount = 0;
    this.liveBodySimUpdatedAt = "";
    this.liveBodySimAdapterAgeMs = null;
    this.liveBodySimSourceStale = false;
    this.liveBodySimLastError = "";
    this.liveBodySimPollCount = 0;
    this.baseSuitVrmAssetRef = "";
    this.baseSuitVrmStatus = VRM_BASE_SUIT_STATUS_PROCEDURAL;
    this.baseSuitVrmFallbackReason = "";
    this.lastQuestDebugTelemetryAt = -Infinity;
    this.motionHeadPosition = new THREE.Vector3();
    this.motionPartPosition = new THREE.Vector3();
    this.motionPartPositionB = new THREE.Vector3();
    this.motionPartPositionC = new THREE.Vector3();
    this.nonVrScale = new THREE.Vector3(0.68, 0.68, 0.68);
    this.selfScale = new THREE.Vector3(1, 1, 1);
    this.observerScale = new THREE.Vector3(
      VR_REPLAY_OBSERVER_SCALE,
      VR_REPLAY_OBSERVER_SCALE,
      VR_REPLAY_OBSERVER_SCALE,
    );
    this.mirrorScale = new THREE.Vector3(VR_REPLAY_MIRROR_SCALE, VR_REPLAY_MIRROR_SCALE, VR_REPLAY_MIRROR_SCALE);
    this.finalPosition = new THREE.Vector3();
    this.stagePosition = new THREE.Vector3();

    this.rig = new THREE.Group();
    this.rig.name = "IWSDK-Henshin-Rig";
    this.rig.position.copy(NON_VR_RIG_POSITION);
    this.rig.rotation.y = 0;
    this.rig.scale.setScalar(0.68);
    this.world.createTransformEntity(this.rig, { persistent: true });

    this.initScene();
    this.spatialPanel = new SpatialControlPanel(this);
    if (UI.recallCodeInput) UI.recallCodeInput.value = this.recallCode;
    this.spatialPanel?.setRecallDraft(this.recallCode || UI.recallCodeInput?.value || XR_RECALL_CODE_EMPTY, {
      syncInput: false,
    });
    UI.status.textContent = EXHIBITION_OPERATOR_COPY.quest.statusReady;
    UI.sessionId.textContent = EXHIBITION_OPERATOR_COPY.quest.sessionWaiting;
    UI.triggerState.textContent = EXHIBITION_OPERATOR_COPY.quest.triggerWaiting;
    UI.equipState.textContent = EXHIBITION_OPERATOR_COPY.quest.equipWaiting;
    setOperatorStateHelp("pending", EXHIBITION_OPERATOR_COPY.quest.operatorHelpReady);
    this.setRecallCodeState(this.recallCode ? `入力コード ${this.recallCode} を待機中` : "4桁コード未指定");
    this.setVoiceState("ready");
    this.updateArchiveViewModeLabel();
    this.updateVoiceDebug("音声デバッグ\n結果: 待機\n合図: 生成");
    this.syncRoutePanel();
    this.refreshEquipmentStatus();
    this.bind();
  }

  static async create() {
    const root = document.getElementById("xrRoot");
    const world = await World.create(root, {
      xr: {
        sessionMode: SessionMode.ImmersiveVR,
        referenceSpace: {
          type: ReferenceSpaceType.LocalFloor,
          fallbackOrder: [ReferenceSpaceType.Local, ReferenceSpaceType.Viewer],
        },
        features: {
          handTracking: useHandTracking(),
          layers: true,
        },
        offer: "none",
      },
      render: {
        fov: 54,
        near: 0.05,
        far: 80,
        defaultLighting: false,
      },
      features: {
        locomotion: false,
        grabbing: false,
        spatialUI: false,
      },
    });
    world.renderer.setClearColor(0x020405, 1);
    return new QuestHenshinDemo(world);
  }

  initScene() {
    this.scene.add(new THREE.HemisphereLight(0xdff8ff, 0x101418, 1.8));
    const key = new THREE.DirectionalLight(0xfff5d1, 2.4);
    key.position.set(2.5, 3.0, 2.2);
    this.scene.add(key);

    const grid = new THREE.GridHelper(4.6, 18, 0x2b5360, 0x13252b);
    grid.position.y = -1.48;
    grid.material.transparent = true;
    grid.material.opacity = 0.45;
    this.rig.add(grid);

    const ringGeo = new THREE.TorusGeometry(0.72, 0.01, 12, 96);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.55 });
    this.rings = [];
    for (let i = 0; i < 3; i += 1) {
      const ring = new THREE.Mesh(ringGeo, ringMat.clone());
      ring.rotation.x = Math.PI / 2;
      this.rig.add(ring);
      this.rings.push(ring);
    }

    this.depositionEffects = createDepositionParticleField();
    this.rig.add(this.depositionEffects.group);

    this.mirrorFrame = new THREE.Group();
    this.mirrorFrame.name = "XR-Archive-Mirror-Frame";
    this.mirrorFrame.visible = false;
    const mirrorGlass = new THREE.Mesh(
      new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH, MIRROR_FRAME_HEIGHT),
      new THREE.MeshBasicMaterial({
        color: 0x9eefff,
        transparent: true,
        opacity: 0.16,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    mirrorGlass.position.set(0, -0.58, 0.26);
    mirrorGlass.renderOrder = 1;
    this.mirrorFrame.add(mirrorGlass);

    const frameMaterial = new THREE.MeshBasicMaterial({
      color: 0x43d8ff,
      transparent: true,
      opacity: 0.72,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const topBottom = new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH + 0.08, 0.035);
    const sides = new THREE.PlaneGeometry(0.035, MIRROR_FRAME_HEIGHT + 0.08);
    for (const [geometry, x, y] of [
      [topBottom, 0, 0.48],
      [topBottom, 0, -1.64],
      [sides, -0.69, -0.58],
      [sides, 0.69, -0.58],
    ]) {
      const bar = new THREE.Mesh(geometry, frameMaterial.clone());
      bar.position.set(x, y, 0.275);
      bar.renderOrder = 2;
      this.mirrorFrame.add(bar);
    }
    const mirrorLabel = makeTextPlane("鏡", {
      width: 0.26,
      height: 0.08,
      fontSize: 54,
      color: "#d7f8ff",
      background: "rgba(4, 13, 17, 0.44)",
      border: "rgba(67, 216, 255, 0.46)",
    });
    mirrorLabel.position.set(0, 0.59, 0.29);
    this.mirrorFrame.add(mirrorLabel);
    this.rig.add(this.mirrorFrame);

    this.liveMirror = new THREE.Group();
    this.liveMirror.name = "XR-Live-Suit-Mirror";
    this.liveMirror.visible = false;
    const liveGlass = new THREE.Mesh(
      new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH * 1.08, MIRROR_FRAME_HEIGHT * 1.02),
      new THREE.MeshBasicMaterial({
        color: 0x9eefff,
        transparent: true,
        opacity: 0.14,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    liveGlass.position.set(0, -0.58, 0.32);
    this.liveMirror.add(liveGlass);
    const liveFrameMaterial = new THREE.MeshBasicMaterial({
      color: 0x43d8ff,
      transparent: true,
      opacity: 0.7,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    for (const [geometry, x, y] of [
      [new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH + 0.18, 0.035), 0, 0.48],
      [new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH + 0.18, 0.035), 0, -1.64],
      [new THREE.PlaneGeometry(0.035, MIRROR_FRAME_HEIGHT + 0.1), -0.73, -0.58],
      [new THREE.PlaneGeometry(0.035, MIRROR_FRAME_HEIGHT + 0.1), 0.73, -0.58],
    ]) {
      const bar = new THREE.Mesh(geometry, liveFrameMaterial.clone());
      bar.position.set(x, y, 0.34);
      this.liveMirror.add(bar);
    }
    const liveLabel = makeTextPlane("装着確認", {
      width: 0.42,
      height: 0.08,
      fontSize: 48,
      color: "#d7f8ff",
      background: "rgba(4, 13, 17, 0.44)",
      border: "rgba(67, 216, 255, 0.46)",
    });
    liveLabel.position.set(0, 0.6, 0.36);
    this.liveMirror.add(liveLabel);
    this.liveMirrorAvatar = new THREE.Group();
    this.liveMirrorAvatar.name = "XR-Live-Mirror-Avatar";
    this.liveMirror.add(this.liveMirrorAvatar);
    this.scene.add(this.liveMirror);

    this.baseSuitGroup = new THREE.Group();
    this.baseSuitGroup.name = "XR-Base-Suit-Surface";
    this.baseSuitGroup.visible = false;
    this.rig.add(this.baseSuitGroup);

    const title = makeTextSprite(TRIGGER_PHRASE);
    title.position.set(0, 1.18, -0.3);
    this.rig.add(title);
    this.titleSprite = title;

    this.renderer.xr.addEventListener("sessionstart", () => {
      this.audioBed.start();
      this.xrWorldAnchorReady = false;
      this.menuFallbackReady = false;
      this.liveMirrorReady = false;
      this.spatialPanel?.setMenuMode(XR_MENU_MODE_COMPACT);
      this.captureWorldAnchor(this.xrViewMode);
      this.snapRigToWorldAnchor({ source: "sessionstart" });
      this.ensureMenuFallbackAnchor();
      UI.status.textContent = "VR開始。音声は一人称変身、記録再生は鏡/観察で確認します。";
      UI.btnEnterVR.textContent = "VR終了";
      this.setVoiceState(this.voiceState, "音声は一人称変身。記録再生は鏡/観察で確認します。");
    });
    this.renderer.xr.addEventListener("sessionend", () => {
      this.xrWorldAnchorReady = false;
      this.menuFallbackReady = false;
      this.liveMirrorReady = false;
      this.spatialPanel?.setMenuMode(XR_MENU_MODE_COMPACT);
      if (this.liveMirror) this.liveMirror.visible = false;
      UI.status.textContent = "VR終了。再開するにはVR開始を押してください。";
      UI.btnEnterVR.textContent = "VR開始";
    });
  }

  async submitRecallCodeFromInput() {
    const code = normalizeRecallCodeInput(UI.recallCodeInput?.value || "");
    try {
      if (!RECALL_CODE_RE.test(code)) {
        throw new Error("Quest入力コードは4桁英数字です。");
      }
      await this.loadSuitByRecallCode(code, { reloadMeshes: true, pushUrl: true });
    } catch (error) {
      const rawMessage = String(error?.message || error);
      const message = rawMessage.includes("Unknown recall_code") ? `未登録コード: ${code}` : rawMessage;
      this.clearArmorMeshes();
      this.suitspec = null;
      this.suitRecord = null;
      this.runtimePackage = null;
      this.recallCode = "";
      this.setRecallCodeState(message, "error");
      this.setRouteApi("CODE ERROR", "error");
    }
  }

  bind() {
    UI.btnEnterVR.onclick = () => this.toggleVR();
    UI.btnVoice.onclick = () => this.runVoiceCommand();
    UI.btnReplay.onclick = () => this.replayFromStart({ speak: true, viewMode: this.archiveViewMode, source: "archive" });
    if (UI.btnReplayView) UI.btnReplayView.onclick = () => this.cycleArchiveViewMode();
    UI.btnPause.onclick = () => this.togglePause();
    UI.btnReset.onclick = () => this.reset();
    if (UI.recallCodeInput) {
      UI.recallCodeInput.oninput = () => {
        const code = normalizeRecallCodeInput(UI.recallCodeInput.value);
        UI.recallCodeInput.value = code;
        this.spatialPanel?.setRecallDraft(code || XR_RECALL_CODE_EMPTY, { syncInput: false });
        this.setRecallCodeState(code ? `${code.length}/4` : "4桁コード未指定");
      };
      UI.recallCodeInput.onkeydown = (event) => {
        if (event.key !== "Enter") return;
        event.preventDefault();
        void this.submitRecallCodeFromInput();
      };
    }
    if (UI.btnLoadRecallCode) {
      UI.btnLoadRecallCode.textContent = "呼出";
      UI.btnLoadRecallCode.setAttribute("aria-label", "4桁コードを呼び出す");
      UI.btnLoadRecallCode.onclick = () => {
        void this.submitRecallCodeFromInput();
      };
    }
  }

  setRecallCodeState(text, state = "pending") {
    if (!UI.recallCodeState) return;
    UI.recallCodeState.textContent = text;
    UI.recallCodeState.dataset.state = state;
  }

  setEquipmentStatus(diagnostic) {
    this.equipmentDiagnostic = diagnostic || makeEquipmentDiagnostic(null);
    updateEquipmentStatusElement(this.equipmentDiagnostic);
    this.spatialPanel?.setEquipmentStatus(this.equipmentDiagnostic);
  }

  refreshEquipmentStatus() {
    this.setEquipmentStatus(makeEquipmentDiagnostic(this.suitspec, this.meshes.size, this.suitRecord, this.runtimePackage));
  }

  refreshBaseSuitVrmContractStatus() {
    const assetRef = resolveBaseSuitVrmAssetRef(this.suitspec, this.suitRecord);
    this.baseSuitVrmAssetRef = assetRef;
    if (!assetRef) {
      this.baseSuitVrmStatus = VRM_BASE_SUIT_STATUS_PROCEDURAL;
      this.baseSuitVrmFallbackReason = "no_vrm_asset_ref";
      return;
    }
    this.baseSuitVrmStatus = VRM_BASE_SUIT_STATUS_DISABLED;
    this.baseSuitVrmFallbackReason = "raw_vrm_disabled_until_head_neck_mask_adapter";
  }

  async loadInitialSuitSpec() {
    if (useNewRouteApi() && this.recallCode) {
      return await this.loadSuitByRecallCode(this.recallCode, { reloadMeshes: false, pushUrl: false });
    }
    if (useNewRouteApi()) {
      this.suitspec = null;
      this.suitRecord = null;
      this.runtimePackage = null;
      this.clearArmorMeshes();
      this.setRecallCodeState("コード待ち / 装備未読み込み");
      this.setRouteApi("WAIT CODE", "pending");
      this.refreshBaseSuitVrmContractStatus();
      this.refreshEquipmentStatus();
      return false;
    }
    const localSuitSpec = await loadSuitSpec();
    this.suitspec = localSuitSpec;
    this.runtimePackage = localSuitSpec?.runtime_package || localSuitSpec?.runtimePackage || null;
    this.activeSuitId = localSuitSpec?.suit_id || this.activeSuitId;
    this.refreshBaseSuitVrmContractStatus();
    this.setRecallCodeState("サンプルSuitSpecを使用中");
    this.refreshEquipmentStatus();
    return localSuitSpec;
  }

  resetRuntimeForRecalledSuit() {
    this.elapsed = 0;
    this.playing = false;
    this.completionAnnounced = false;
    this.trialId = null;
    this.trialReady = false;
    this.trialReplayPath = null;
    this.depositionStartPromise = null;
    this.liveMotionFrames = [];
    this.archiveMotionFrames = [];
    this.replayMotionSource = "";
    this.lastLiveMotionSampleAt = -Infinity;
    this.frames = [];
    this.replay = null;
    this.playbackSource = "voice";
    this.runtimePackage = null;
    this.armorStandPreview = false;
    this.clearArmorMeshes();
    this.setReplayMotionDiagnostic(makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC));
    if (UI.meterFill) UI.meterFill.style.width = "0%";
    if (UI.btnPause) UI.btnPause.textContent = "再開";
    if (UI.equipState) UI.equipState.textContent = "変身: 待機";
    this.setRouteTrial("WAIT", "pending");
    this.setRouteReplay("WAIT", "pending");
  }

  async loadSuitByRecallCode(code, { reloadMeshes = false, pushUrl = false } = {}) {
    const recallCode = normalizeRecallCodeInput(code);
    if (!RECALL_CODE_RE.test(recallCode)) {
      throw new Error("Quest入力コードは4桁英数字です。");
    }
    this.setRecallCodeState(`呼び出し中: ${recallCode}`);
    this.setRouteApi(`CODE ${recallCode}`, "pending");
    const data = await getJson(`/v1/quest/recall/${encodeURIComponent(recallCode)}`);
    if (!data.suitspec) {
      throw new Error(`SuitSpec未保存: ${recallCode}`);
    }
    if (!data.manifest_id || data.manifest_ready === false) {
      throw new Error(`Manifest未発行: ${recallCode}`);
    }
    const runtimePackage = data.runtime_package || data.runtimePackage || data.runtime || data.suitspec?.runtime_package || null;
    const nextSuitId = data.suit_id || data.suit?.suit_id || data.suitspec?.suit_id || this.activeSuitId;
    const hasRuntimeState = Boolean(
      this.trialId
        || this.trialReady
        || this.trialReplayPath
        || this.liveMotionFrames.length
        || this.archiveMotionFrames.length
        || this.frames.length
        || this.replay,
    );
    if ((this.recallCode && this.recallCode !== recallCode) || this.activeSuitId !== nextSuitId || hasRuntimeState) {
      this.resetRuntimeForRecalledSuit();
    }
    this.suitRecord = data.suit || null;
    this.suitspec = data.suitspec;
    this.runtimePackage = runtimePackage;
    this.recallCode = data.recall_code || recallCode;
    this.activeSuitId = nextSuitId;
    this.activeManifestId = data.manifest_id || data.suit?.manifest_id || this.activeManifestId;
    this.refreshBaseSuitVrmContractStatus();
    this.refreshEquipmentStatus();
    if (UI.recallCodeInput) UI.recallCodeInput.value = this.recallCode;
    this.spatialPanel?.setRecallDraft(this.recallCode, { syncInput: false, state: "ok" });
    if (pushUrl) {
      const next = new URL(window.location.href);
      next.searchParams.set("newRoute", "1");
      next.searchParams.set("code", this.recallCode);
      window.history.replaceState(null, "", next);
    }
    if (reloadMeshes) {
      this.clearArmorMeshes();
      await this.loadArmorMeshes();
    }
    this.setArmorStandPreview(false);
    this.hideLoadedArmorMeshes();
    if (this.equipmentDiagnostic?.state === "error") {
      this.setRecallCodeState(`${this.equipmentDiagnostic.label}: ${this.equipmentDiagnostic.summary}`, "error");
      this.setRouteApi(`CODE ${this.recallCode} 装備不足`, "error");
    } else {
      this.setRecallCodeState(`呼び出しOK: コード ${this.recallCode} / スーツ読込完了`, "ok");
      this.setRouteApi(`CODE ${this.recallCode}`, "ok");
    }
    this.appendVoiceDebug(`recall_code: ${this.recallCode} suit: ${this.activeSuitId}`);
    return this.suitspec;
  }

  clearArmorMeshes() {
    const disposedGeometries = new Set();
    const disposedMaterials = new Set();
    for (const mesh of this.meshes.values()) {
      mesh.userData.disposed = true;
      disposeObjectResources(mesh, disposedGeometries, disposedMaterials);
      mesh.removeFromParent();
    }
    this.meshes.clear();
    for (const mesh of this.liveMirrorMeshes.values()) {
      mesh.userData.disposed = true;
      disposeObjectResources(mesh, disposedGeometries, disposedMaterials);
      mesh.removeFromParent();
    }
    this.liveMirrorMeshes.clear();
    this.refreshEquipmentStatus();
  }

  updateArchiveViewModeLabel() {
    if (UI.btnReplayView) UI.btnReplayView.textContent = `次: ${this.archiveViewMode === XR_VIEW_MODE_OBSERVER ? "鏡" : "観察"}`;
    this.spatialPanel?.setArchiveViewMode(this.archiveViewMode);
  }

  cycleArchiveViewMode() {
    this.archiveViewMode =
      this.archiveViewMode === XR_VIEW_MODE_MIRROR ? XR_VIEW_MODE_OBSERVER : XR_VIEW_MODE_MIRROR;
    this.updateArchiveViewModeLabel();
    const diagnostic = this.refreshReplayMotionDiagnostic({
      playbackSource: "archive",
      viewMode: this.archiveViewMode,
    });
    UI.status.textContent = `記録再生の視点: ${formatArchiveViewMode(this.archiveViewMode)}`;
    this.setVoiceState(this.voiceState, `記録再生は${formatArchiveViewMode(this.archiveViewMode)}視点で再生します。動き ${diagnostic.token}。`);
  }

  activateMirrorOrToggleArchiveView() {
    const leavingStandOrObserver =
      this.armorStandPreview || (this.world.session && this.xrViewMode === XR_VIEW_MODE_OBSERVER && !this.playing);
    if (!leavingStandOrObserver) {
      this.cycleArchiveViewMode();
      return;
    }

    this.archiveViewMode = XR_VIEW_MODE_MIRROR;
    this.updateArchiveViewModeLabel();
    if (this.replay || this.frames.length || this.archiveMotionFrames.length) {
      this.replayFromStart({ speak: true, viewMode: XR_VIEW_MODE_MIRROR, source: "archive" });
      UI.status.textContent = "鎧立てを閉じ、鏡で記録再生を開始します。";
      return;
    }

    this.setArmorStandPreview(false);
    this.xrViewMode = XR_VIEW_MODE_MIRROR;
    this.xrWorldAnchorReady = false;
    this.captureWorldAnchor(this.xrViewMode);
    UI.status.textContent = "鏡視点に切り替えました。記録ができたら再生できます。";
    this.setVoiceState(this.voiceState, "鏡視点です。音声変身後に記録再生で装着姿を確認できます。");
  }

  exitArmorStandToMirror({ source = "armorStandExit" } = {}) {
    if (!this.isArmorStandPreviewMode()) return false;
    this.setArmorStandPreview(false);
    this.xrViewMode = XR_VIEW_MODE_MIRROR;
    this.archiveViewMode = XR_VIEW_MODE_MIRROR;
    this.updateArchiveViewModeLabel();
    this.xrWorldAnchorReady = false;
    this.captureWorldAnchor(this.xrViewMode);
    UI.status.textContent = "鎧立てを閉じて鏡へ戻りました。右トリガーは音声/変身導線に戻ります。";
    this.setVoiceState(this.voiceState, `鎧立てを閉じました。${TRIGGER_PHRASE} は鏡/一人称で使えます。`);
    this.appendVoiceDebug(`armor stand exit: ${source}`);
    this.sendQuestDebugTelemetry("armor-stand-exit", { force: true });
    return true;
  }

  setVoiceState(state, detail = "", options = {}) {
    this.voiceState = state;
    const voiceState = VOICE_STATES[state] || VOICE_STATES.ready;
    UI.triggerState.textContent = `音声: ${voiceState.label}`;
    UI.micState.textContent = detail || voiceState.hint;
    if (options.status) UI.status.textContent = options.status;
    const operatorState = state === "rejected"
      ? "error"
      : ["arming", "recording", "analyzing"].includes(state)
      ? "running"
      : ["detected", "deposition", "complete"].includes(state)
      ? "complete"
      : "pending";
    const operatorDetail = operatorState === "running"
      ? EXHIBITION_OPERATOR_COPY.quest.operatorHelpListening
      : operatorState === "complete"
      ? EXHIBITION_OPERATOR_COPY.quest.operatorHelpComplete
      : operatorState === "error"
      ? EXHIBITION_OPERATOR_COPY.quest.operatorHelpError
      : EXHIBITION_OPERATOR_COPY.quest.operatorHelpReady;
    setOperatorStateHelp(operatorState, operatorDetail);
    this.spatialPanel?.setVoiceState(state, detail);
  }

  updateVoiceDebug(text) {
    const value = text || "音声デバッグ: 待機";
    if (UI.voiceDebug) UI.voiceDebug.textContent = value;
    this.spatialPanel?.setDebug(value);
  }

  appendVoiceDebug(line) {
    if (!line) return;
    const next = `${UI.voiceDebug?.textContent || "音声デバッグ"}\n${line}`;
    this.updateVoiceDebug(next);
  }

  collectQuestDebugSnapshot(event = "scene") {
    const meshRecords = Array.from(this.meshes.entries()).map(([part, mesh]) => {
      const material = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
      const placement = runtimePlacementForMesh(mesh);
      const module = mesh.userData?.module || {};
      const surfacePolicy = wearableSurfaceFitPolicyForPart(part);
      return {
        part,
        visible: Boolean(mesh.visible),
        opacity: roundDebugNumber(material?.opacity),
        meshSource: mesh.userData?.meshSource || "",
        assetRef: module.asset_ref || module.assetRef || "",
        selectedVariantKey: module.selected_variant_key || "",
        hasRuntimePlacement: Boolean(placement),
        runtimePlacementMode: useWebPreviewRuntimePlacement(placement) ? "web_preview_parity" : "quest_rig",
        runtimeOffset: useWebPreviewRuntimePlacement(placement)
          ? placement?.offset_m || null
          : placement?.quest_rig_offset_m || null,
        runtimeOffsetClamped: runtimePlacementOffsetArrayForPart(part, placement),
        runtimeRotation: placement?.rotation_deg || null,
        anchorDiagnostics: questRuntimePlacementAnchorDiagnosticsForPart(part, placement),
        surfaceFitRole: surfacePolicy?.role || "",
        surfaceFitContact: surfacePolicy?.targetContact || "",
        position: vectorDebugSnapshot(mesh.position),
        scale: vectorDebugSnapshot(mesh.scale),
        rotation: eulerDebugSnapshot(mesh.rotation),
        partCenter: questPartCenterDebugSnapshot(this, part, mesh),
      };
    });
    const baseShellChildren = this.baseSuitGroup
      ? this.baseSuitGroup.children.map((mesh) => ({
          part: mesh.userData?.baseSuitPart || mesh.name || "",
          visible: Boolean(mesh.visible),
          position: vectorDebugSnapshot(mesh.position),
          scale: vectorDebugSnapshot(mesh.scale),
          rotation: eulerDebugSnapshot(mesh.rotation),
        }))
      : [];
    const liveMirrorRecords = Array.from(this.liveMirrorMeshes.entries()).map(([part, mesh]) => ({
      part,
      visible: Boolean(mesh.visible),
      position: vectorDebugSnapshot(mesh.position),
      scale: vectorDebugSnapshot(mesh.scale),
      rotation: eulerDebugSnapshot(mesh.rotation),
    }));
    const experienceState = questDebugUxStateSnapshot(this);
    const replayMotionDiagnostic = this.replayMotionDiagnostic || makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);
    const liveBodySimAgeMs = Number.isFinite(this.liveBodySimLastOkAt)
      ? Math.max(0, performance.now() - this.liveBodySimLastOkAt)
      : null;
    const liveBodySimStale =
      liveBodySimAgeMs === null
      || liveBodySimAgeMs > LIVE_BODY_SIM_STALE_AFTER_MS
      || this.liveBodySimSourceStale;
    const payload = {
      event,
      at: new Date().toISOString(),
      query: questDebugQuerySnapshot(),
      uxState: experienceState.uxState,
      experience: experienceState,
      route: {
        recallCode: this.recallCode,
        activeSuitId: this.activeSuitId,
        activeManifestId: this.activeManifestId,
        trialId: this.trialId,
        voiceState: this.voiceState,
        playbackSource: this.playbackSource,
        trialReplayPath: this.trialReplayPath,
        replayMotionDiagnostic,
        armorStandPreview: this.armorStandPreview,
        playing: this.playing,
        elapsed: roundDebugNumber(this.elapsed, 3),
        progress: roundDebugNumber(this.elapsed / this.duration, 3),
      },
      replayMotion: {
        ...replayMotionDiagnostic,
        archiveMotionFrames: this.archiveMotionFrames.length,
        bodySimFrames: this.frames.length,
        replayMotionSource: this.replayMotionSource,
      },
      liveBodySim: {
        enabled: this.liveBodySimEnabled,
        latestPath: this.liveBodySimLatestPath,
        pollIntervalMs: this.liveBodySimPollIntervalMs,
        renderProfile: this.liveBodySimRenderProfile,
        renderCalibratedAt: this.liveBodySimRenderCalibratedAt,
        renderCalibrationSource: this.liveBodySimRenderCalibrationSource,
        inFlight: this.liveBodySimInFlight,
        pollCount: this.liveBodySimPollCount,
        frameCount: this.liveBodySimFrameCount,
        lastOkAgeMs: liveBodySimAgeMs === null ? null : roundDebugNumber(liveBodySimAgeMs, 0),
        adapterPacketAgeMs: Number.isFinite(this.liveBodySimAdapterAgeMs)
          ? roundDebugNumber(this.liveBodySimAdapterAgeMs, 0)
          : null,
        sourceStale: this.liveBodySimSourceStale,
        stale: liveBodySimStale,
        renderMode: this.liveBodySimEnabled ? "latest_segment_pose" : "replay_or_static",
        updatedAt: this.liveBodySimUpdatedAt,
        lastError: this.liveBodySimLastError,
      },
      microphone: questDebugMicrophoneSnapshot(),
      xr: {
        session: Boolean(this.world.session),
        viewMode: this.xrViewMode,
        archiveViewMode: this.archiveViewMode,
        liveBodyPose: useQuestLiveBodyPose(),
        xrWorldAnchorReady: this.xrWorldAnchorReady,
        xrWorldAnchorMode: this.xrWorldAnchorMode,
        xrWorldAnchorProfile: this.xrWorldAnchorProfile,
        expectedAnchorProfile: this.worldAnchorProfileForViewMode(this.xrViewMode),
        xrWorldAnchorPosition: vectorDebugSnapshot(this.xrWorldAnchorPosition),
        xrWorldAnchorYawDeg: yawDegDebugSnapshot(this.xrWorldAnchorQuaternion),
        xrWorldAnchorScale: vectorDebugSnapshot(this.xrWorldAnchorScale),
        cameraPosition: vectorDebugSnapshot(this.cameraPosition),
        cameraYawDeg: yawDegDebugSnapshot(this.cameraQuaternion),
        cameraForwardWorld: forwardVectorDebugSnapshot(this.cameraQuaternion),
        cameraLocalInRig: localVectorInObjectDebugSnapshot(this.rig, this.cameraPosition),
        cameraToAnchorWorldM: vectorDeltaDebugSnapshot(this.xrWorldAnchorPosition, this.cameraPosition),
        cameraToAnchorDistanceM: vectorDistanceDebugSnapshot(this.xrWorldAnchorPosition, this.cameraPosition),
        rigPosition: vectorDebugSnapshot(this.rig?.position),
        rigYawDeg: yawDegDebugSnapshot(this.rig?.quaternion),
        rigForwardWorld: forwardVectorDebugSnapshot(this.rig?.quaternion),
        anchorToRigDeltaM: vectorDeltaDebugSnapshot(this.rig?.position, this.xrWorldAnchorPosition),
        anchorToRigDistanceM: vectorDistanceDebugSnapshot(this.rig?.position, this.xrWorldAnchorPosition),
        anchorToRigYawDeltaDeg: yawDeltaDegDebugSnapshot(this.rig?.quaternion, this.xrWorldAnchorQuaternion),
        leftHandTracked: this.leftHandTracked,
        rightHandTracked: this.rightHandTracked,
        liveTorsoYaw: roundDebugNumber(this.liveTorsoYaw),
      },
      humanBodyMock: {
        version: QUEST_HUMAN_BODY_MOCK.version,
        spineZM: QUEST_HUMAN_BODY_MOCK.spine_z_m,
        pointCount: Object.keys(QUEST_HUMAN_BODY_MOCK.points_m || {}).length,
        armorCenterCount: Object.keys(QUEST_HUMAN_ANCHOR_CONTRACT || {}).length,
        centerlineWorld: {
          head: rigLocalPointWorldDebugSnapshot(this.rig, questHumanBodyPoint("head")),
          upperTorso: rigLocalPointWorldDebugSnapshot(this.rig, questHumanBodyPoint("upper_torso")),
          pelvis: rigLocalPointWorldDebugSnapshot(this.rig, questHumanBodyPoint("pelvis")),
        },
      },
      baseShell: {
        visible: Boolean(this.baseSuitGroup?.visible),
        childCount: baseShellChildren.length,
        vrm: {
          status: this.baseSuitVrmStatus,
          assetRef: this.baseSuitVrmAssetRef,
          fallbackReason: this.baseSuitVrmFallbackReason,
        },
        children: baseShellChildren,
      },
      armorStand: {
        active: this.armorStandPreview,
        yawDeg: roundDebugNumber(THREE.MathUtils.radToDeg(this.armorStandYaw), 1),
        pitchDeg: roundDebugNumber(THREE.MathUtils.radToDeg(this.armorStandPitch), 1),
        scale: roundDebugNumber(this.armorStandScale, 3),
        offset: vectorDebugSnapshot(this.armorStandOffset),
        exploded: this.armorStandExploded,
        interactionMode: this.armorStandInteractionMode,
        input: this.spatialPanel?.armorStandWorkshopInputSnapshot?.() || null,
        floorLiftM: ARMOR_STAND_FLOOR_LIFT_M,
        rightTriggerMode: this.armorStandPreview ? "ui_exit_or_grip_escape_or_explode_toggle" : "voice_shortcut",
        interactionCount: this.armorStandInteractCount,
      },
      meshes: {
        loaded: this.meshes.size,
        visibleCount: meshRecords.filter((record) => record.visible).length,
        records: meshRecords,
      },
      liveMirror: {
        visible: Boolean(this.liveMirror?.visible),
        ready: this.liveMirrorReady,
        meshCount: this.liveMirrorMeshes.size,
        visibleCount: liveMirrorRecords.filter((record) => record.visible).length,
        records: liveMirrorRecords,
      },
      depositionEffects: {
        visible: Boolean(this.depositionEffects?.group?.visible),
        pointsOpacity: roundDebugNumber(this.depositionEffects?.points?.material?.opacity),
        sparksOpacity: roundDebugNumber(this.depositionEffects?.sparks?.material?.opacity),
        pointsSize: roundDebugNumber(this.depositionEffects?.points?.material?.size),
      },
      runtimeDiagnostic: runtimePlacementDiagnostic(this.runtimePackage, this.meshes),
    };
    payload.centerlineQa = questCenterlineQaSnapshot(payload);
    return payload;
  }

  updateCenterlineQaDisplay(centerlineQa) {
    if (!centerlineQa?.displayLine || params().get("qa") !== "centerline") return;
    if (this.lastCenterlineQaDisplayLine === centerlineQa.displayLine) return;
    this.lastCenterlineQaDisplayLine = centerlineQa.displayLine;
    this.appendVoiceDebug(centerlineQa.displayLine);
  }

  sendQuestDebugTelemetry(event = "scene", { force = false } = {}) {
    if (!useQuestDebugTelemetry()) return;
    const now = performance.now();
    if (!force && now - this.lastQuestDebugTelemetryAt < QUEST_DEBUG_TELEMETRY_INTERVAL_MS) return;
    this.lastQuestDebugTelemetryAt = now;
    const payload = this.collectQuestDebugSnapshot(event);
    this.updateCenterlineQaDisplay(payload.centerlineQa);
    void postQuestDebugTelemetry(payload);
  }

  syncRoutePanel() {
    const newRoute = useNewRouteApi();
    setBadge(UI.routeMode, newRoute ? "生成: 新規" : "生成: ローカル", newRoute ? "ok" : "idle");
    setBadge(UI.routeApi, newRoute ? "適合監査: /v1" : "適合監査: 停止", newRoute ? "pending" : "idle");
    setBadge(
      UI.routeTrial,
      this.trialId ? `変身試験: ${compactToken(this.trialId)}` : "変身試験: 待機",
      this.trialId ? "ok" : "pending",
    );
    setBadge(
      UI.routeReplay,
      this.trialReplayPath
        ? `記録保管: ${compactToken(localizeRouteToken(this.trialReplayPath), 20)} | 動き ${localizeMotionToken(this.replayMotionDiagnostic.token)}`
        : `記録保管: 待機 | 動き ${localizeMotionToken(this.replayMotionDiagnostic.token)}`,
      this.trialReplayPath ? "ok" : "pending",
    );
    setRouteContract(UI.routeContract, this.suitspec, this.runtimePackage);
    this.routeState.apiLabel = newRoute ? "/v1 ARMED" : "OFF";
    this.routeState.apiState = newRoute ? "pending" : "idle";
    this.routeState.trialLabel = this.trialId || "WAIT";
    this.routeState.trialState = this.trialId ? "ok" : "pending";
    this.routeState.replayLabel = this.trialReplayPath || "WAIT";
    this.routeState.replayState = this.trialReplayPath ? "ok" : "pending";
    this.syncSpatialRouteStatus();
  }

  setRouteApi(label, state = "pending") {
    setBadge(UI.routeApi, `適合監査: ${compactToken(localizeRouteToken(label), 28)}`, state);
    this.routeState.apiLabel = label;
    this.routeState.apiState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteTrial(label, state = "pending") {
    setBadge(UI.routeTrial, `変身試験: ${compactToken(localizeRouteToken(label), 30)}`, state);
    this.routeState.trialLabel = label;
    this.routeState.trialState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteReplay(label, state = "pending") {
    setBadge(UI.routeReplay, `記録保管: ${compactToken(localizeRouteToken(label), 20)} | 動き ${localizeMotionToken(this.replayMotionDiagnostic.token)}`, state);
    this.routeState.replayLabel = label;
    this.routeState.replayState = state;
    this.syncSpatialRouteStatus();
  }

  computeReplayMotionDiagnostic({ viewMode = this.xrViewMode, playbackSource = this.playbackSource } = {}) {
    const livePoseFrames = this.archiveMotionFrames.length;
    const bodySimFrames = this.frames.length;
    const replayMotionSource = this.replayMotionSource;
    if (playbackSource !== "archive") {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_CAPTURE, livePoseFrames, bodySimFrames, replayMotionSource);
    }
    if (viewMode === XR_VIEW_MODE_SELF) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_SELF, livePoseFrames, bodySimFrames, replayMotionSource);
    }
    if (livePoseFrames && bodySimFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_MIXED, livePoseFrames, bodySimFrames, replayMotionSource);
    }
    if (livePoseFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_LIVE_POSE, livePoseFrames, bodySimFrames, replayMotionSource);
    }
    if (bodySimFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_BODY_SIM, livePoseFrames, bodySimFrames, replayMotionSource);
    }
    return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC, livePoseFrames, bodySimFrames, replayMotionSource);
  }

  setReplayMotionDiagnostic(diagnostic) {
    this.replayMotionDiagnostic = diagnostic || makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);
    if (UI.routeReplay && this.routeState) {
      setBadge(
        UI.routeReplay,
        `記録保管: ${compactToken(localizeRouteToken(this.routeState.replayLabel || "WAIT"), 20)} | 動き ${localizeMotionToken(this.replayMotionDiagnostic.token)}`,
        this.routeState.replayState || "pending",
      );
    }
    this.syncSpatialRouteStatus();
  }

  refreshReplayMotionDiagnostic(options = {}) {
    const diagnostic = this.computeReplayMotionDiagnostic(options);
    this.setReplayMotionDiagnostic(diagnostic);
    return diagnostic;
  }

  syncSpatialRouteStatus() {
    const mode = useNewRouteApi() ? "新規" : "ローカル";
    const api = compactToken(localizeRouteToken(this.routeState.apiLabel || "OFF"), 18);
    const trial = compactToken(localizeRouteToken(this.trialId || this.routeState.trialLabel || "WAIT"), 20);
    const replaySource =
      this.routeState.replayState === "ok"
        ? this.routeState.replayLabel
        : this.trialReplayPath || this.routeState.replayLabel || "WAIT";
    const replay = compactToken(localizeRouteToken(replaySource), 18);
    const motion = compactToken(localizeMotionToken(this.replayMotionDiagnostic?.token || "WAIT"), 12);
    const state =
      this.routeState.apiState === "error" || this.routeState.replayState === "error"
        ? "error"
        : this.routeState.replayState === "ok"
          ? "ok"
          : "pending";
    this.spatialPanel?.setRouteStatus(`生成 ${mode} | 適合 ${api} | 試験 ${trial} | 記録 ${replay} | 動き ${motion}`, state);
  }

  async ensureTrial() {
    if (!useNewRouteApi()) return null;
    if (this.trialReady && this.trialId) {
      this.setRouteTrial(this.trialId, "ok");
      return this.trialId;
    }
    this.trialId = this.trialId || makeTrialId();
    const suitId = this.activeSuitId || getSuitId();
    const manifestId = this.activeManifestId || getManifestId();
    this.setRouteTrial(this.trialId, "pending");
    if (this.recallCode && this.suitRecord?.manifest_id) {
      this.setRouteApi(`RECALL ${this.recallCode}`, "ok");
    } else {
      this.setRouteApi("SUIT POST", "pending");
      await postJson("/v1/suits", {
        suitspec: this.suitspec,
        overwrite: true,
      });
      this.setRouteApi("MANIFEST", "pending");
      await postJson(`/v1/suits/${suitId}/manifest`, {
        manifest_id: manifestId,
        status: "READY",
      });
    }
    this.setRouteApi("TRIAL CREATE", "pending");
    const trial = await postJson("/v1/trials", {
      manifest_id: manifestId,
      suit_id: suitId,
      session_id: this.trialId,
      operator_id: getOperatorId(),
      device_id: getDeviceId(),
      tracking_source: "iw_sdk",
      state: "POSTED",
    });
    this.trialId = trial.trial_id || trial.session_id || this.trialId;
    this.trialReady = true;
    UI.sessionId.textContent = this.trialId;
    this.setRouteApi("TRIAL READY", "ok");
    this.setRouteTrial(this.trialId, "ok");
    this.appendVoiceDebug(`trial: ${this.trialId}`);
    return this.trialId;
  }

  async appendTrialEvent(eventType, options = {}) {
    if (!useNewRouteApi()) return null;
    try {
      const trialId = await this.ensureTrial();
      if (!trialId) return null;
      this.setRouteApi(eventType, "pending");
      const event = await postJson(`/v1/trials/${trialId}/events`, {
        event_type: eventType,
        state_after: options.stateAfter,
        actor: options.actor || { type: "device", id: getDeviceId() },
        payload: options.payload || {},
        idempotency_key: options.idempotencyKey,
      });
      this.appendVoiceDebug(`trial event: ${event.event?.event_type || eventType} #${event.event?.sequence}`);
      const sequence = event.event?.sequence ? ` #${event.event.sequence}` : "";
      this.setRouteApi(`${event.event?.event_type || eventType}${sequence}`, "ok");
      return event;
    } catch (error) {
      console.warn(error);
      this.appendVoiceDebug(`trial api: ${error?.message || error}`);
      this.setRouteApi("EVENT ERROR", "error");
      return null;
    }
  }

  trialEventKey(name) {
    return `${name}-${this.trialId || "local"}`;
  }

  async generateTrialReplay() {
    if (!useNewRouteApi() || !this.trialId) return null;
    try {
      this.setRouteReplay("BUILDING", "pending");
      const replay = await getJson(`/v1/trials/${this.trialId}/replay`, { attempts: 3 });
      this.trialReplayPath = replay.replay_path || null;
      const motionFrames = motionFramesFromReplayScript(replay.replay);
      this.setArchiveMotionFrames(motionFrames);
      this.replayMotionSource = replayMotionSourceFromRecord(replay.replay || replay);
      if (motionFrames.length) {
        const diagnostic = this.refreshReplayMotionDiagnostic({
          playbackSource: "archive",
          viewMode: this.archiveViewMode,
        });
        this.appendVoiceDebug(`motion replay: ${diagnostic.label}`);
      } else {
        this.refreshReplayMotionDiagnostic({
          playbackSource: "archive",
          viewMode: this.archiveViewMode,
        });
      }
      this.appendVoiceDebug(`trial replay: ${replay.replay_id || this.trialReplayPath}`);
      this.setRouteReplay(replay.replay_id || this.trialReplayPath || "READY", "ok");
      return replay;
    } catch (error) {
      console.warn(error);
      this.appendVoiceDebug(`trial replay: ${error?.message || error}`);
      this.setRouteReplay("ERROR", "error");
      return null;
    }
  }

  togglePause() {
    this.playing = !this.playing;
    UI.btnPause.textContent = this.playing ? "停止" : "再開";
    this.spatialPanel?.setVoiceState(this.voiceState);
  }

  async start() {
    await this.updateVRAvailability();
    const loadedRecalledSuit = await this.loadInitialSuitSpec();
    if (loadedRecalledSuit) {
      await this.loadArmorMeshes();
      const replay = await loadReplay();
      const autoplayReplay = useAutoplayReplay();
      await this.applyReplay(replay, {
        speak: false,
        autoplay: autoplayReplay,
        viewMode: this.archiveViewMode,
        source: "archive",
      });
      if (this.liveBodySimEnabled) {
        void this.refreshLiveBodySimLatest({ force: true });
      }
    } else {
      this.clearArmorMeshes();
      this.elapsed = 0;
      this.playing = false;
      if (UI.meterFill) UI.meterFill.style.width = "0%";
      if (UI.equipState) UI.equipState.textContent = "変身: コード待ち";
      UI.status.textContent = "Quest呼び出し待機。4桁コードを入力すると鎧を読み込みます。";
      this.setVoiceState("ready", "変身前に4桁コードを入力してください。");
    }
    this.startRenderLoop();
  }

  async updateVRAvailability() {
    if (!navigator.xr?.isSessionSupported) {
      UI.micState.textContent = "WebXRを利用できません。Quest BrowserまたはIWSDK Vite emulatorで確認してください。";
      return;
    }
    const supported = await navigator.xr.isSessionSupported(SessionMode.ImmersiveVR).catch(() => false);
    UI.btnEnterVR.disabled = !supported;
    UI.micState.textContent = supported
      ? "Quest VRモード利用可能。Quest BrowserからVR開始できます。"
      : "このブラウザではQuest VRモードを利用できません。";
  }

  startRenderLoop() {
    this.clock.start();
    this.renderer.setAnimationLoop(() => {
      const dt = Math.min(this.clock.getDelta(), 0.05);
      const elapsed = this.clock.elapsedTime;
      this.updateScene(dt);
      this.world.visibilityState.value = this.world.session?.visibilityState || VisibilityState.NonImmersive;
      this.world.update(dt, elapsed);
      this.renderer.render(this.scene, this.camera);
    });
  }

  toggleVR() {
    this.audioBed.start();
    if (this.world.session) {
      this.world.exitXR();
      return;
    }
    const launch = this.world.launchXR({
      sessionMode: SessionMode.ImmersiveVR,
      referenceSpace: {
        type: ReferenceSpaceType.LocalFloor,
        fallbackOrder: [ReferenceSpaceType.Local, ReferenceSpaceType.Viewer],
      },
      features: {
        handTracking: useHandTracking(),
        layers: true,
      },
    });
    if (launch?.catch) {
      launch.catch((error) => {
        console.error(error);
        UI.status.textContent = `VRを開始できません: ${error?.message || error}`;
        setOperatorStateHelp("error", EXHIBITION_OPERATOR_COPY.quest.operatorHelpError);
      });
    }
  }

  async loadArmorMeshes() {
    if (!this.suitspec) {
      this.clearArmorMeshes();
      if (UI.micState) UI.micState.textContent = "鎧未読込。4桁コードを入力してください。";
      return;
    }
    const modules = this.suitspec?.modules || {};
    this.refreshBaseSuitSurface();
    const enabledRecords = ARMOR_PARTS.map((part, index) => {
      const source = modules[part];
      if (!source || source.enabled !== true) return null;
      const module = moduleForRuntimePart(this.suitspec, this.runtimePackage, part);
      if (!module || module.enabled !== true) return null;
      return { part, index, module };
    }).filter(Boolean);
    if (UI.micState) {
      UI.micState.textContent = `装甲アセット読込中 0/${enabledRecords.length}.`;
    }
    const loadedMeshes = await mapWithConcurrency(enabledRecords, ARMOR_ASSET_LOAD_CONCURRENCY, async ({ part, index, module }) => {
      const mesh = await createArmorMesh(part, module, this.suitspec);
      return { index, mesh, part };
    }, ({ done, total, result }) => {
      const source = result?.mesh?.userData?.meshSource || "pending";
      if (UI.micState) {
        UI.micState.textContent = `装甲アセット読込中 ${done}/${total}. Last: ${result?.part || "--"} (${source}).`;
      }
    });
    for (const record of loadedMeshes) {
      if (!record) continue;
      record.mesh.userData.partIndex = record.index;
      this.rig.add(record.mesh);
      this.meshes.set(record.part, record.mesh);
      if (this.liveMirrorAvatar) {
        const mirrorMesh = record.mesh.clone();
        mirrorMesh.material = record.mesh.material.clone();
        mirrorMesh.visible = false;
        mirrorMesh.userData.partIndex = record.index;
        mirrorMesh.userData.module = record.mesh.userData.module;
        mirrorMesh.userData.runtimePlacement = record.mesh.userData.runtimePlacement;
        this.liveMirrorAvatar.add(mirrorMesh);
        this.liveMirrorMeshes.set(record.part, mirrorMesh);
      }
    }
    const fallbackText =
      this.suitspec?.texture_fallback?.mode === "palette_material"
        ? "不足テクスチャはパレット材質で補完します。"
        : "テクスチャ補完契約は未設定です。";
    const meshFallbackCount = Array.from(this.meshes.values()).filter((mesh) => String(mesh.userData.meshSource || "").includes("fallback")).length;
    const glbCount = Array.from(this.meshes.values()).filter((mesh) => mesh.userData.meshSource === "glb_asset").length;
    setRouteContract(UI.routeContract, this.suitspec, this.runtimePackage);
    UI.micState.textContent = `装備メッシュ ${this.meshes.size}件を読み込みました（GLB ${glbCount}件、代替メッシュ ${meshFallbackCount}件）。体型適合 ${formatFitContractLabel(this.suitspec)}。表面処理 ${formatTextureFallbackLabel(this.suitspec)}。${fallbackText}`;
    const runtimeDiagnostic = runtimePlacementDiagnostic(this.runtimePackage, this.meshes);
    console.info("[Quest runtime diagnostic]", runtimeDiagnostic);
    this.appendVoiceDebug(runtimeDiagnostic);
    this.refreshEquipmentStatus();
    this.hideLoadedArmorMeshes();
    this.sendQuestDebugTelemetry("armor-loaded", { force: true });
  }

  hideLoadedArmorMeshes() {
    for (const mesh of this.meshes.values()) mesh.visible = false;
    for (const mesh of this.liveMirrorMeshes.values()) mesh.visible = false;
    if (this.baseSuitGroup) {
      this.baseSuitGroup.visible = false;
      for (const mesh of this.baseSuitGroup.children) mesh.visible = false;
    }
  }

  refreshBaseSuitSurface() {
    if (!this.baseSuitGroup) return;
    const disposedMaps = new Set();
    for (const child of [...this.baseSuitGroup.children]) {
      child.geometry?.dispose?.();
      if (child.material?.map && !disposedMaps.has(child.material.map)) {
        disposedMaps.add(child.material.map);
        child.material.map.dispose?.();
      }
      child.material?.dispose?.();
      child.removeFromParent();
    }
    if (!this.suitspec) {
      this.baseSuitGroup.visible = false;
      return;
    }
    const material = createBaseSuitMaterial(this.suitspec);
    for (const [basePart, shape, position, scale, rotation] of BASE_SUIT_SURFACE_PARTS) {
      const geometry = shape === "sphere"
        ? new THREE.SphereGeometry(1, 32, 18)
        : new THREE.CapsuleGeometry(1, 1, 8, 24);
      const mesh = new THREE.Mesh(geometry, material.clone());
      mesh.name = `base-suit-${basePart}`;
      mesh.userData.baseSuitPart = basePart;
      mesh.userData.baseSuitLocalPosition = position.slice(0, 3);
      mesh.userData.baseSuitLocalScale = scale.slice(0, 3);
      mesh.userData.baseSuitLocalRotation = rotation.slice(0, 3);
      mesh.position.fromArray(position);
      mesh.scale.fromArray(scale);
      mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
      mesh.renderOrder = 2;
      this.baseSuitGroup.add(mesh);
    }
    material.dispose?.();
    this.baseSuitGroup.visible = this.meshes.size > 0 || Object.values(this.suitspec?.modules || {}).some((module) => module?.enabled);
  }

  applyBaseSuitGuidePose({ standbyPreview }) {
    if (!this.baseSuitGroup) return;
    const standTransform = {
      yaw: this.armorStandYaw,
      pitch: this.armorStandPitch,
      scale: this.armorStandScale,
      explode: 0,
      offset: this.armorStandOffset,
    };
    const standQuaternion = armorStandRigQuaternionFromTransform(standTransform);
    for (const mesh of this.baseSuitGroup.children) {
      const position = mesh.userData?.baseSuitLocalPosition || [0, 0, 0];
      const scale = mesh.userData?.baseSuitLocalScale || [1, 1, 1];
      const rotation = mesh.userData?.baseSuitLocalRotation || [0, 0, 0];
      if (standbyPreview) {
        mesh.position.fromArray(armorStandRigPoseForPoint(position, standTransform));
        mesh.scale.set(
          scale[0] * this.armorStandScale,
          scale[1] * this.armorStandScale,
          scale[2] * this.armorStandScale,
        );
        mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
        mesh.quaternion.premultiply(standQuaternion);
      } else {
        mesh.position.fromArray(position);
        mesh.scale.fromArray(scale);
        mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
      }
    }
  }

  updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView = false, reveal, bodyShellAligned = true }) {
    if (!this.baseSuitGroup) return;
    const hasSuit = this.meshes.size > 0;
    const xrCapsuleGuide = useQuestBaseSuitGuide();
    const xrTransformGuide =
      xrCapsuleGuide && this.world.session && this.playing && !standbyPreview && bodyShellAligned && (selfView || mirrorView);
    const armorStandBodyGuide = standbyPreview;
    const canShowBodyShell = armorStandBodyGuide || (!this.world.session && bodyShellAligned) || xrTransformGuide;
    this.baseSuitGroup.visible = hasSuit && canShowBodyShell && (standbyPreview || this.playing);
    this.applyBaseSuitGuidePose({ standbyPreview });
    const opacity = standbyPreview ? 0.2 : this.world.session ? lerp(0.04, 0.08, reveal) : lerp(0.16, 0.42, reveal);
    for (const mesh of this.baseSuitGroup.children) {
      const baseSuitPart = mesh.userData?.baseSuitPart || "";
      const hiddenForSelfView =
        selfView
        && !standbyPreview
        && SELF_VIEW_HIDDEN_BASE_SUIT_PARTS.has(baseSuitPart);
      mesh.visible = this.baseSuitGroup.visible && !hiddenForSelfView;
      mesh.material.opacity = opacity;
      mesh.material.wireframe = this.world.session || standbyPreview;
      mesh.material.emissiveIntensity = this.world.session || standbyPreview ? 0.34 : 0.14;
    }
  }

  isArmorStandPreviewMode() {
    return this.armorStandPreview === true && this.playing === false;
  }

  setArmorStandPreview(active) {
    this.armorStandPreview = Boolean(active) && this.meshes.size > 0;
    this.spatialPanel?.setArmorStandPreview(this.armorStandPreview);
    if (this.armorStandPreview) {
      this.playing = false;
      this.elapsed = 0;
      this.resetArmorStandWorkshopTransform({ preserveExploded: false });
      this.xrViewMode = XR_VIEW_MODE_OBSERVER;
      this.xrWorldAnchorReady = false;
      this.captureWorldAnchor(this.xrViewMode);
      this.snapRigToWorldAnchor({ source: "armorStandPreview" });
      if (UI.meterFill) UI.meterFill.style.width = "0%";
      UI.status.textContent = "鎧立て表示中。右グリップで全身移動、両グリップで拡縮/回転、右トリガーで展開。右グリップ+トリガーで鏡へ戻れます。";
    } else if (!this.playing && this.xrViewMode === XR_VIEW_MODE_OBSERVER) {
      this.hideLoadedArmorMeshes();
      this.xrViewMode = XR_VIEW_MODE_SELF;
      this.xrWorldAnchorReady = false;
      this.captureWorldAnchor(this.xrViewMode);
      this.snapRigToWorldAnchor({ source: "armorStandExit" });
    } else if (!this.playing) {
      this.hideLoadedArmorMeshes();
    }
  }

  resetArmorStandWorkshopTransform({ preserveExploded = false } = {}) {
    this.armorStandYaw = 0;
    this.armorStandPitch = 0;
    this.armorStandScale = 1;
    this.armorStandOffset.set(0, 0, 0);
    if (!preserveExploded) this.armorStandExploded = false;
    this.armorStandInteractionMode = this.armorStandExploded ? "exploded_parts" : "assembled";
  }

  applyArmorStandWorkshopMove({ delta = null, source = "rightGripRigMove", coordinateSpace = "world" } = {}) {
    if (!this.isArmorStandPreviewMode()) return false;
    const dx = Number(delta?.x);
    const dy = Number(delta?.y);
    const dz = Number(delta?.z);
    if (![dx, dy, dz].every(Number.isFinite)) return false;
    ARMOR_STAND_MOVE_LOCAL_VECTOR.set(dx, dy, dz);
    if (coordinateSpace !== "local" && this.rig) {
      this.rig.getWorldQuaternion(ARMOR_STAND_MOVE_WORLD_QUATERNION).invert();
      ARMOR_STAND_MOVE_LOCAL_VECTOR.applyQuaternion(ARMOR_STAND_MOVE_WORLD_QUATERNION);
    }
    if (ARMOR_STAND_MOVE_LOCAL_VECTOR.length() < ARMOR_STAND_MOVE_DEADZONE_M) return false;
    this.armorStandOffset.x = clamp(
      this.armorStandOffset.x + ARMOR_STAND_MOVE_LOCAL_VECTOR.x,
      ARMOR_STAND_OFFSET_LIMITS_M.x[0],
      ARMOR_STAND_OFFSET_LIMITS_M.x[1],
    );
    this.armorStandOffset.y = clamp(
      this.armorStandOffset.y + ARMOR_STAND_MOVE_LOCAL_VECTOR.y,
      ARMOR_STAND_OFFSET_LIMITS_M.y[0],
      ARMOR_STAND_OFFSET_LIMITS_M.y[1],
    );
    this.armorStandOffset.z = clamp(
      this.armorStandOffset.z + ARMOR_STAND_MOVE_LOCAL_VECTOR.z,
      ARMOR_STAND_OFFSET_LIMITS_M.z[0],
      ARMOR_STAND_OFFSET_LIMITS_M.z[1],
    );
    this.armorStandInteractionMode = this.armorStandExploded ? "exploded_parts" : "assembled";
    this.appendVoiceDebug(`armor stand move: ${source}/${this.armorStandOffset.x.toFixed(2)},${this.armorStandOffset.y.toFixed(2)},${this.armorStandOffset.z.toFixed(2)}`);
    this.sendQuestDebugTelemetry("armor-stand-workshop-move");
    return true;
  }

  applyArmorStandWorkshopDrag({ yawDelta = 0, pitchDelta = 0, source = "twoGripRigYaw" } = {}) {
    if (!this.isArmorStandPreviewMode()) return false;
    const safeYawDelta = Number.isFinite(Number(yawDelta)) ? Number(yawDelta) : 0;
    const safePitchDelta = Number.isFinite(Number(pitchDelta)) ? Number(pitchDelta) : 0;
    if (Math.abs(safeYawDelta) < 0.00001 && Math.abs(safePitchDelta) < 0.00001) return false;
    this.armorStandYaw = THREE.MathUtils.euclideanModulo(this.armorStandYaw + safeYawDelta, TAU);
    this.armorStandPitch = clamp(
      this.armorStandPitch + safePitchDelta,
      -ARMOR_STAND_PITCH_LIMIT_RAD,
      ARMOR_STAND_PITCH_LIMIT_RAD,
    );
    this.armorStandInteractionMode = this.armorStandExploded ? "exploded_parts" : "assembled";
    this.appendVoiceDebug(`armor stand drag: ${source}/${Math.round(THREE.MathUtils.radToDeg(this.armorStandYaw))}deg/${this.armorStandScale.toFixed(2)}x`);
    this.sendQuestDebugTelemetry("armor-stand-workshop-drag");
    return true;
  }

  setArmorStandWorkshopScale(scale, { source = "twoGripScale" } = {}) {
    if (!this.isArmorStandPreviewMode()) return false;
    const nextScale = clamp(Number(scale) || 1, ARMOR_STAND_SCALE_MIN, ARMOR_STAND_SCALE_MAX);
    if (Math.abs(nextScale - this.armorStandScale) < 0.002) return false;
    this.armorStandScale = nextScale;
    this.armorStandInteractionMode = this.armorStandExploded ? "exploded_parts" : "assembled";
    this.appendVoiceDebug(`armor stand scale: ${source}/${this.armorStandScale.toFixed(2)}x`);
    this.sendQuestDebugTelemetry("armor-stand-workshop-scale");
    return true;
  }

  finishArmorStandWorkshopManipulation() {
    if (!this.isArmorStandPreviewMode()) return false;
    this.armorStandInteractCount += 1;
    const yawDeg = Math.round(THREE.MathUtils.radToDeg(this.armorStandYaw));
    const pitchDeg = Math.round(THREE.MathUtils.radToDeg(this.armorStandPitch));
    UI.status.textContent = `鎧立て確認: 全身位置 ${this.armorStandOffset.x.toFixed(2)}/${this.armorStandOffset.y.toFixed(2)}/${this.armorStandOffset.z.toFixed(2)}、角度 ${yawDeg}/${pitchDeg}度、倍率 ${this.armorStandScale.toFixed(2)}。右グリップ+トリガーで鏡へ戻れます。`;
    this.sendQuestDebugTelemetry("armor-stand-interact", { force: true });
    return true;
  }

  toggleArmorStandPartExplosion({ source = "rightTrigger", handedness = "right" } = {}) {
    if (!this.isArmorStandPreviewMode()) return false;
    this.armorStandExploded = !this.armorStandExploded;
    this.armorStandInteractionMode = this.armorStandExploded ? "exploded_parts" : "assembled";
    this.armorStandInteractCount += 1;
    const modeLabel = this.armorStandExploded ? "パーツ展開" : "全身へ戻す";
    UI.status.textContent = `鎧立て確認: ${modeLabel}。右グリップは全身移動、両グリップは一体拡縮/回転です。右グリップ+トリガーで鏡へ戻れます。`;
    this.setVoiceState(this.voiceState, `鎧立て操作中。右トリガーは展開/戻す、右グリップは全身移動、両グリップは一体拡縮/回転です。右グリップ+トリガーで戻れます。${TRIGGER_PHRASE} は鏡/一人称に戻ってから。`);
    this.spatialPanel?.setArmorStandPreview(true);
    this.appendVoiceDebug(`armor stand workshop: ${source}/${handedness}/${this.armorStandInteractionMode}`);
    this.sendQuestDebugTelemetry("armor-stand-interact", { force: true });
    return true;
  }

  toggleArmorStandPreview() {
    if (!this.meshes.size) {
      this.setRecallCodeState("先に4桁コードで呼び出してください", "error");
      this.setRouteApi("WAIT CODE", "error");
      return;
    }
    this.setArmorStandPreview(!this.armorStandPreview);
  }

  async applyReplay(replay, { speak, autoplay = true, viewMode = XR_VIEW_MODE_SELF, source = "voice" }) {
    this.replay = replay;
    const replayScript = Array.isArray(replay?.replay?.timeline) ? replay.replay : replay;
    const replayMotionFrames = motionFramesFromReplayScript(replayScript);
    this.setArchiveMotionFrames(replayMotionFrames);
    if (replayMotionFrames.length && Number.isFinite(Number(replayScript?.duration_sec))) {
      this.duration = clamp(Number(replayScript.duration_sec), 0.8, 12);
    }
    let bodySim = null;
    const bodySimPath = this.liveBodySimEnabled ? this.liveBodySimLatestPath : replay?.deposition?.body_sim_path;
    if (bodySimPath) {
      try {
        bodySim = await this.loadBodySimRecord(bodySimPath);
      } catch (error) {
        console.warn("body-sim replay unavailable; falling back to replay motion/static", error);
        this.appendVoiceDebug("motion fallback: body-sim unavailable; using replay/static");
      }
    }
    this.frames = bodySim?.frames || [];
    this.replayMotionSource = replayMotionSourceFromRecord(replay, bodySim);
    this.refreshReplayMotionDiagnostic({
      playbackSource: autoplay ? source : "archive",
      viewMode: autoplay ? viewMode : this.archiveViewMode,
    });
    UI.sessionId.textContent = replay.session_id || EXHIBITION_OPERATOR_COPY.quest.sessionWaiting;
    UI.triggerState.textContent = replay.trigger?.detected
      ? `音声: ${replay.trigger.phrase || TRIGGER_PHRASE}`
      : EXHIBITION_OPERATOR_COPY.quest.triggerWaiting;
    UI.equipState.textContent = autoplay && replay.deposition?.completed
      ? "変身: 完了"
      : EXHIBITION_OPERATOR_COPY.quest.equipWaiting;
    UI.voiceLine.textContent = replay.tts?.text || "";
    if (autoplay) {
      this.replayFromStart({ speak, viewMode, source });
    } else {
      this.elapsed = 0;
      this.playing = false;
      this.xrViewMode = XR_VIEW_MODE_SELF;
      this.xrWorldAnchorReady = false;
      this.captureWorldAnchor(this.xrViewMode);
      UI.btnPause.textContent = "再開";
      this.setVoiceState("ready", `音声ボタン後に ${TRIGGER_PHRASE} と発声してください。`);
    }
  }

  async loadBodySim(rawPath) {
    const bodySim = await this.loadBodySimRecord(rawPath);
    return bodySim.frames;
  }

  async loadBodySimRecord(rawPath) {
    const bodySim = await loadJson(rawPath);
    return {
      ...(bodySim && typeof bodySim === "object" ? bodySim : {}),
      frames: Array.isArray(bodySim?.frames) ? bodySim.frames : [],
    };
  }

  async refreshLiveBodySimLatest({ force = false } = {}) {
    if (!this.liveBodySimEnabled || this.liveBodySimInFlight) return false;
    const now = performance.now();
    if (!force && now - this.liveBodySimLastPollAt < this.liveBodySimPollIntervalMs) return false;
    this.liveBodySimLastPollAt = now;
    this.liveBodySimPollCount += 1;
    this.liveBodySimInFlight = true;
    try {
      const bodySim = await this.loadBodySimRecord(this.liveBodySimLatestPath);
      const frames = Array.isArray(bodySim?.frames) ? bodySim.frames : [];
      if (!frames.length) {
        throw new Error("body-sim/latest has no frames");
      }
      this.frames = frames;
      this.replayMotionSource = replayMotionSourceFromRecord(this.replay, bodySim) || REPLAY_MOTION_SOURCE_MOCOPI;
      this.liveBodySimFrameCount = frames.length;
      this.liveBodySimLastOkAt = performance.now();
      this.liveBodySimUpdatedAt = bodySim.updated_at || bodySim.updated_at_unix_ms || bodySim.metadata?.updated_at || "";
      const adapterAgeMs = Number(bodySim.adapter_packet_age_ms ?? bodySim.metadata?.adapter_packet_age_ms);
      this.liveBodySimAdapterAgeMs = Number.isFinite(adapterAgeMs) ? adapterAgeMs : null;
      this.liveBodySimSourceStale = Boolean(bodySim.adapter_stale || bodySim.metadata?.adapter_stale);
      this.liveBodySimLastError = this.liveBodySimSourceStale
        ? `mocopi stream stale (${Math.round(this.liveBodySimAdapterAgeMs || 0)}ms)`
        : "";
      this.refreshReplayMotionDiagnostic({
        playbackSource: this.playbackSource,
        viewMode: this.xrViewMode,
      });
      return true;
    } catch (error) {
      this.liveBodySimLastError = String(error?.message || error);
      return false;
    } finally {
      this.liveBodySimInFlight = false;
    }
  }

  calibrateLiveBodySimArmorToBody({ source = "manual" } = {}) {
    const frame = this.frames.at(-1);
    const segmentPose = frame?.segments?.chest_core;
    if (!this.liveBodySimEnabled || !segmentPose) {
      const message = "mocopi\u88dc\u6b63: \u30e9\u30a4\u30d6\u59ff\u52e2\u304c\u672a\u53d6\u5f97\u3067\u3059\u3002\u30b9\u30de\u30db\u9001\u4fe1\u3092\u518d\u958b\u3057\u3066\u304b\u3089\u518d\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002";
      UI.status.textContent = message;
      this.setVoiceState(this.voiceState, message);
      this.appendVoiceDebug(message);
      return false;
    }

    const profile = this.liveBodySimRenderProfile || getLiveBodySimRenderProfile();
    const scale = Number(profile.scale || 1);
    const xSign = Number(profile.xSign || 1) < 0 ? -1 : 1;
    const ySign = Number(profile.ySign || 1) < 0 ? -1 : 1;
    const zSign = Number(profile.zSign || -1) < 0 ? -1 : 1;
    const target = questAssemblyPoseForPart("chest");
    const offset = PART_OFFSETS.chest || [0, 0, 0];
    const sourceX = Number(segmentPose.position_x || 0);
    const sourceY = Number(segmentPose.position_y || 0);
    const sourceZ = Number(segmentPose.position_z || 0);

    this.liveBodySimRenderProfile = {
      ...profile,
      xSign,
      ySign,
      zSign,
      scale,
      xOffset: roundDebugNumber(target[0] - offset[0] - sourceX * scale * xSign, 4),
      yOffset: roundDebugNumber(target[1] - offset[1] - sourceY * scale * ySign, 4),
      zOffset: roundDebugNumber(target[2] - offset[2] - sourceZ * scale * zSign, 4),
      yawOffsetRad: 0,
    };
    this.liveBodySimRenderCalibratedAt = new Date().toISOString();
    this.liveBodySimRenderCalibrationSource = source;
    const message = `mocopi\u88dc\u6b63: \u80f8\u4f4d\u7f6\u3092\u57fa\u6e96\u306b\u30a2\u30fc\u30de\u30fc\u539f\u70b9\u3092\u5408\u308f\u305b\u307e\u3057\u305f\u3002x=${this.liveBodySimRenderProfile.xOffset}, y=${this.liveBodySimRenderProfile.yOffset}, z=${this.liveBodySimRenderProfile.zOffset}`;
    UI.status.textContent = message;
    this.setVoiceState(this.voiceState, message);
    this.appendVoiceDebug(message);
    this.sendQuestDebugTelemetry("mocopi-calibrated", { force: true });
    return true;
  }

  reset() {
    this.elapsed = 0;
    this.playing = false;
    this.completionAnnounced = false;
    this.depositionStartPromise = null;
    this.trialId = null;
    this.trialReady = false;
    this.trialReplayPath = null;
    this.liveMotionFrames = [];
    this.replayMotionSource = "";
    this.lastLiveMotionSampleAt = -Infinity;
    this.setArmorStandPreview(false);
    this.setReplayMotionDiagnostic(makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC));
    this.xrViewMode = XR_VIEW_MODE_SELF;
    this.xrWorldAnchorReady = false;
    this.captureWorldAnchor(this.xrViewMode);
    UI.btnPause.textContent = "再開";
    UI.equipState.textContent = "変身: 待機";
    UI.meterFill.style.width = "0%";
    UI.status.textContent = "リセット完了。音声で一人称変身、記録再生で鏡/観察を確認できます。";
    this.setVoiceState("ready");
    this.updateArchiveViewModeLabel();
    this.syncRoutePanel();
    this.updateVoiceDebug("音声デバッグ\n結果: リセット\n合図: 生成");
    this.updateVoiceDebug(`音声デバッグ\n結果: リセット\n合図: ${TRIGGER_PHRASE}`);
  }

  replayFromStart({ speak, audio = speak, viewMode = XR_VIEW_MODE_SELF, source = "voice" }) {
    if (audio) this.audioBed.start();
    this.setArmorStandPreview(false);
    this.xrViewMode = viewMode;
    this.playbackSource = source;
    this.xrWorldAnchorReady = false;
    this.captureWorldAnchor(viewMode);
    if (source !== "archive") {
      this.liveMotionFrames = [];
      this.archiveMotionFrames = [];
      this.lastLiveMotionSampleAt = -Infinity;
    }
    this.elapsed = 0;
    this.playing = true;
    this.completionAnnounced = false;
    UI.btnPause.textContent = "停止";
    const archive = source === "archive";
    const diagnostic = this.refreshReplayMotionDiagnostic({ playbackSource: source, viewMode });
    const motionCount = archive ? this.playbackMotionFrames().length : 0;
    UI.status.textContent = archive
      ? `記録再生: ${formatArchiveViewMode(viewMode)}視点。動き ${diagnostic.token}。${motionCount ? `姿勢 ${motionCount} フレーム。` : ""}`
      : `音声合図 ${TRIGGER_PHRASE} を確認。一人称変身を開始します。`;
    this.setVoiceState(
      "deposition",
      archive ? `記録再生は${formatArchiveViewMode(viewMode)}視点です。動きは ${diagnostic.token}。` : "一人称変身中。手先表示は安全のため抑制中です。",
    );
    this.depositionStartPromise = archive
      ? null
      : this.appendTrialEvent("DEPOSITION_STARTED", {
          stateAfter: "DEPOSITION",
          payload: {
            source: "quest-iw-demo",
            trigger_phrase: TRIGGER_PHRASE,
            view_mode: viewMode,
            replay_source: source,
            replay_motion: diagnostic,
          },
          idempotencyKey: this.trialEventKey("deposition-started"),
        });
    void this.depositionStartPromise;
    if (speak) this.speakExplanation();
  }

  async runVoiceCommand() {
    if (useNewRouteApi() && !this.suitspec) {
      this.setRecallCodeState("先に4桁コードで呼び出してください", "error");
      this.setRouteApi("WAIT CODE", "error");
      this.setVoiceState("ready", "変身前に4桁コードを入力してください。");
      return;
    }
    if (!this.canRunVoiceCommand()) return;
    this.audioBed.start();
    UI.btnVoice.disabled = true;
    try {
      const seconds = getVoiceSeconds();
      const armDelay = getVoiceArmDelay();
      const useMic = useMicrophoneCapture();
      const mode = useMic ? getAudioMode().toUpperCase() : "MOCK";
      UI.status.textContent = useMic
        ? `マイク準備中。合図が出たら「${TRIGGER_PHRASE}」と発声してください。`
        : "モック音声トリガーで変身試験を開始します。";
      this.setVoiceState(
        useMic ? "arming" : "analyzing",
        useMic ? `マイク準備 ${armDelay.toFixed(1)}秒。まだ発声しないでください。` : "モックトリガーで記録再生を準備中。",
      );
      this.updateVoiceDebug(`音声デバッグ\n結果: ${useMic ? "録音準備" : "モック"}\n合図: ${TRIGGER_PHRASE}\n音声: ${mode}\n待機: ${useMic ? `${armDelay.toFixed(1)}s` : "省略"}`);

      let blob;
      let stats;
      if (useMic) {
        const captured = await recordAudio(seconds, {
          armDelaySec: armDelay,
          onReady: () => {
            UI.status.textContent = `マイク待機完了。${armDelay.toFixed(1)}秒後の合図を待ってください。`;
            this.setVoiceState("arming", `${armDelay.toFixed(1)}秒待機。合図の後だけ発声してください。`);
          },
          onStart: () => {
            UI.status.textContent = `${mode}で${seconds.toFixed(1)}秒録音中。「${TRIGGER_PHRASE}」とはっきり発声してください。`;
            this.setVoiceState("recording", `発声してください: ${seconds.toFixed(1)}秒録音。`);
            this.updateVoiceDebug(`音声デバッグ\n結果: 録音中\n合図: ${TRIGGER_PHRASE}\n音声: ${mode} ${seconds.toFixed(1)}s\n待機: ${armDelay.toFixed(1)}s`);
          },
        });
        blob = captured.blob;
        stats = captured.stats;
      } else {
        await sleep(160);
        const captured = makeMockAudioCapture();
        blob = captured.blob;
        stats = captured.stats;
      }
      const statsLine = formatAudioStats(stats);
      this.setVoiceState(
        "analyzing",
        useMockTrigger()
          ? `モックトリガーで記録再生を準備中。${statsLine ? ` ${statsLine}` : ""}`
          : `Sakura Whisperで音声解析中。${statsLine ? ` ${statsLine}` : ""}`
      );
      this.updateVoiceDebug(`音声デバッグ\n結果: 送信中\n合図: ${TRIGGER_PHRASE}\n音声: ${statsLine || mode}\n容量: ${blob.size}`);
      const audioBase64 = await blobToDataUrl(blob);
      const trialId = useNewRouteApi() ? await this.ensureTrial() : makeTrialId();
      const response = await fetch("/api/iw-henshin/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_base64: audioBase64,
          mime_type: blob.type || (getAudioMode() === "wav" ? "audio/wav" : "audio/webm"),
          audio_stats: stats,
          session_id: trialId,
          mocopi: params().get("mocopi") || DEFAULT_MOCOPI,
          trigger_phrase: TRIGGER_PHRASE,
          dry_run: useMockTrigger(),
          tts_enabled: true,
        }),
      });
      const data = await response.json().catch(() => ({}));
      const transcript = data.result?.transcript || data.replay?.trigger?.transcript || "";
      const debugText = formatVoiceDebug(data, transcript, data.result?.error || data.error || "");
      this.updateVoiceDebug(debugText);
      await this.appendTrialEvent("VOICE_CAPTURED", {
        stateAfter: "POSTED",
        payload: { transcript, audio_stats: stats, trigger_phrase: TRIGGER_PHRASE },
        idempotencyKey: `voice-captured-${trialId}`,
      });
      UI.voiceLine.textContent = formatVoiceRetryHint(data, transcript);
      const triggerMatched =
        useMockTrigger() ||
        data.replay?.trigger?.detected === true ||
        data.result?.triggered === true ||
        transcriptHasTrigger(transcript);
      if (!response.ok || !data.ok) {
        const retryDetail = formatVoiceRetryDetail(data, transcript);
        const reason = data.result?.error || data.error;
        throw new Error(reason ? `${reason}. ${retryDetail}` : retryDetail);
      }
      if (!triggerMatched) {
        throw new Error(formatVoiceRetryDetail(data, transcript));
      }
      await this.appendTrialEvent("TRIGGER_DETECTED", {
        stateAfter: "TRY_ON",
        payload: { transcript, trigger_phrase: TRIGGER_PHRASE },
        idempotencyKey: `trigger-detected-${trialId}`,
      });
      this.setVoiceState("detected", transcript ? `文字起こし: ${transcript}` : `合図「${TRIGGER_PHRASE}」を確認しました。`);
      this.audioBed.pulse(980, 0.18);
      if (data.replay && data.result?.tts?.audio_path && !data.replay.tts?.audio_path) {
        data.replay.tts = data.result.tts;
      }
      if (data.replay) {
        await this.applyReplay(data.replay, {
          speak: Boolean(data.ok),
          autoplay: true,
          viewMode: XR_VIEW_MODE_SELF,
          source: "voice",
        });
      }
    } catch (error) {
      console.error(error);
      const message = String(error?.message || error);
      UI.status.textContent = "音声を確認できません。音声デバッグを確認してください。";
      UI.equipState.textContent = "変身: 確認";
      if (useNewRouteApi()) this.setRouteApi("VOICE ERROR", "error");
      this.setVoiceState("rejected", message.length > 92 ? `${message.slice(0, 89)}...` : message);
      if (UI.voiceDebug && UI.voiceDebug.textContent.startsWith("音声デバッグ")) {
        UI.voiceDebug.textContent += `\nエラー: ${message}`;
        this.spatialPanel?.setDebug(UI.voiceDebug.textContent);
      } else {
        this.updateVoiceDebug(`音声デバッグ\n結果: エラー\n合図: ${TRIGGER_PHRASE}\nエラー: ${message}`);
      }
      this.audioBed.pulse(180, 0.22);
    } finally {
      UI.btnVoice.disabled = false;
    }
  }

  canRunVoiceCommand() {
    if (useNewRouteApi() && !this.suitspec) return false;
    return !this.playing && !["arming", "recording", "analyzing", "detected", "deposition"].includes(this.voiceState);
  }

  speakExplanation() {
    const text = this.replay?.tts?.text;
    if (!text) return;
    this.audioBed.duck(4.5);
    const audioPath = this.replay?.tts?.audio_path;
    if (audioPath) {
      UI.micState.textContent = "変身説明の音声を再生中です。";
      void this.playTtsAudio(audioPath, text);
      return;
    }
    UI.micState.textContent = `変身説明の音声ファイルがありません（${this.replay?.tts?.status || "no_audio"}）。`;
    this.speakWithBrowser(text);
  }

  async playTtsAudio(audioPath, fallbackText) {
    try {
      await this.audioBed.playFile(audioPath);
      return;
    } catch (error) {
      console.warn(error);
    }

    try {
      await new Promise((resolve, reject) => {
        this.ttsAudio = new Audio(normalizePath(audioPath));
        this.ttsAudio.volume = 1.0;
        this.ttsAudio.onended = resolve;
        this.ttsAudio.onerror = () => reject(new Error("HTMLAudio TTS playback failed."));
        const play = this.ttsAudio.play();
        if (play?.catch) play.catch(reject);
      });
      return;
    } catch (error) {
      console.warn(error);
      UI.micState.textContent = "変身説明の音声再生に失敗したため、ブラウザ読み上げに切り替えます。";
    }

    this.speakWithBrowser(fallbackText);
  }

  speakWithBrowser(text) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "ja-JP";
    utterance.rate = 1.02;
    utterance.pitch = 0.92;
    window.speechSynthesis.speak(utterance);
  }

  currentFrame(progress) {
    if (!this.frames.length) return null;
    if (this.liveBodySimEnabled) return this.frames.at(-1);
    const index = Math.min(this.frames.length - 1, Math.floor(progress * this.frames.length));
    return this.frames[index];
  }

  getXrYawPose() {
    const xrCamera = this.renderer.xr.getCamera(this.camera) || this.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    xrCamera.getWorldQuaternion(this.cameraQuaternion);
    this.rigTargetEuler.setFromQuaternion(this.cameraQuaternion, "YXZ");
    const yaw = this.rigTargetEuler.y;
    this.viewForwardQuaternion.setFromEuler(new THREE.Euler(0, yaw, 0, "YXZ"));
    return yaw;
  }

  worldAnchorProfileForViewMode(viewMode = this.xrViewMode) {
    if (viewMode === XR_VIEW_MODE_MIRROR) return XR_ANCHOR_PROFILE_MIRROR;
    if (viewMode === XR_VIEW_MODE_OBSERVER) {
      return this.armorStandPreview && !this.playing
        ? XR_ANCHOR_PROFILE_ARMOR_STAND
        : XR_ANCHOR_PROFILE_REPLAY_OBSERVER;
    }
    return XR_ANCHOR_PROFILE_SELF;
  }

  captureWorldAnchor(viewMode = this.xrViewMode) {
    if (!this.world.session) return;
    const anchorProfile = this.worldAnchorProfileForViewMode(viewMode);
    const yaw = this.getXrYawPose();
    const forward = this.xrForward.set(0, 0, -1).applyQuaternion(this.viewForwardQuaternion).normalize();
    let rigYaw = yaw;
    this.xrWorldAnchorPosition.copy(this.cameraPosition);
    this.liveMirrorPosition
      .copy(this.cameraPosition)
      .add(this.livePartPosition.copy(forward).multiplyScalar(LIVE_MIRROR_DISTANCE));
    this.liveMirrorPosition.y = this.cameraPosition.y + LIVE_MIRROR_HEIGHT_OFFSET;
    this.liveMirrorQuaternion.setFromEuler(new THREE.Euler(0, yaw + Math.PI, 0, "YXZ"));
    this.liveMirrorReady = true;

    if (viewMode === XR_VIEW_MODE_MIRROR) {
      this.xrWorldAnchorPosition.add(forward.multiplyScalar(VR_REPLAY_MIRROR_DISTANCE));
      this.xrWorldAnchorPosition.y = this.cameraPosition.y + VR_REPLAY_MIRROR_HEIGHT_OFFSET;
      this.xrWorldAnchorScale.copy(this.mirrorScale);
      rigYaw = yaw + Math.PI;
    } else if (viewMode === XR_VIEW_MODE_OBSERVER) {
      const armorStandObserver = anchorProfile === XR_ANCHOR_PROFILE_ARMOR_STAND;
      const observerDistance = armorStandObserver ? XR_ARMOR_STAND_DISTANCE : VR_REPLAY_OBSERVER_DISTANCE;
      const observerHeightOffset = armorStandObserver ? XR_ARMOR_STAND_HEIGHT_OFFSET : VR_REPLAY_OBSERVER_HEIGHT_OFFSET;
      const observerScale = armorStandObserver ? XR_ARMOR_STAND_SCALE : VR_REPLAY_OBSERVER_SCALE;
      const observerYawOffset = armorStandObserver ? XR_ARMOR_STAND_YAW_OFFSET_RAD : XR_REPLAY_OBSERVER_YAW_OFFSET_RAD;
      this.xrWorldAnchorPosition.add(forward.multiplyScalar(observerDistance));
      this.xrWorldAnchorPosition.y = this.cameraPosition.y + observerHeightOffset;
      this.xrWorldAnchorScale.setScalar(observerScale);
      rigYaw = yaw + Math.PI + observerYawOffset;
    } else {
      this.xrWorldAnchorPosition.y = this.cameraPosition.y;
      this.xrWorldAnchorScale.copy(this.selfScale);
    }

    this.xrWorldAnchorQuaternion.setFromEuler(new THREE.Euler(0, rigYaw, 0, "YXZ"));
    this.xrWorldAnchorMode = viewMode;
    this.xrWorldAnchorProfile = anchorProfile;
    this.xrWorldAnchorReady = true;
  }

  snapRigToWorldAnchor({ source = "manual" } = {}) {
    if (!this.xrWorldAnchorReady || !this.rig) return false;
    this.rig.position.copy(this.xrWorldAnchorPosition);
    this.rig.quaternion.copy(this.xrWorldAnchorQuaternion);
    this.rig.scale.copy(this.xrWorldAnchorScale);
    this.appendVoiceDebug(`xr anchor snap: ${source}`);
    return true;
  }

  ensureMenuFallbackAnchor({ force = false } = {}) {
    if ((!force && this.menuFallbackReady) || !this.world.session) return;
    const yaw = this.getXrYawPose();
    this.menuFallbackQuaternion.setFromEuler(new THREE.Euler(0, yaw, 0, "YXZ"));
    this.menuFallbackForward.set(0, 0, -1).applyQuaternion(this.menuFallbackQuaternion).normalize();
    this.menuFallbackRight.set(1, 0, 0).applyQuaternion(this.menuFallbackQuaternion).normalize();
    this.menuFallbackPosition
      .copy(this.cameraPosition)
      .add(this.menuFallbackForward.multiplyScalar(XR_MENU_FALLBACK_DISTANCE))
      .add(this.menuFallbackRight.multiplyScalar(-XR_MENU_FALLBACK_LEFT));
    this.menuFallbackPosition.y = this.cameraPosition.y - XR_MENU_FALLBACK_DOWN;
    this.menuFallbackReady = true;
  }

  updateLiveBodyAnchors() {
    if (!this.world.session) return;
    const xrCamera = this.renderer.xr.getCamera(this.camera) || this.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    this.liveHeadPosition.copy(this.cameraPosition);
    this.rig.worldToLocal(this.liveHeadPosition);

    this.leftHandTracked = this.updateControllerLocalPosition("left", this.liveLeftHandPosition);
    this.rightHandTracked = this.updateControllerLocalPosition("right", this.liveRightHandPosition);
    let torsoYawTarget = 0;
    if (this.leftHandTracked && this.rightHandTracked) {
      const dx = this.liveRightHandPosition.x - this.liveLeftHandPosition.x;
      const dz = this.liveRightHandPosition.z - this.liveLeftHandPosition.z;
      torsoYawTarget = clamp(Math.atan2(dz, Math.max(0.22, Math.abs(dx))), -0.48, 0.48);
    }
    this.liveTorsoYaw = lerp(this.liveTorsoYaw, torsoYawTarget, 0.18);
  }

  updateControllerLocalPosition(hand, target) {
    const controller = this.spatialPanel?.getControllerByHand(hand);
    if (!controller) return false;
    if (!controller?.userData?.inputSource) return false;
    controller.getWorldPosition(target);
    const distance = target.distanceTo(this.cameraPosition);
    if (distance < 0.08 || distance > 2.2) return false;
    this.rig.worldToLocal(target);
    return true;
  }

  getEstimatedHandPosition(hand, target) {
    const tracked = hand === "left" ? this.leftHandTracked : this.rightHandTracked;
    const source = hand === "left" ? this.liveLeftHandPosition : this.liveRightHandPosition;
    if (tracked) {
      target.copy(source);
      return target;
    }
    const offset = questBodyRelativeOffsetForPart(`${hand}_hand`);
    return this.setLiveBodyOffset(target, offset[0], offset[1], offset[2]);
  }

  setLiveBodyOffset(target, x, y, z) {
    const sin = Math.sin(this.liveTorsoYaw);
    const cos = Math.cos(this.liveTorsoYaw);
    return target.set(
      this.liveHeadPosition.x + x * cos - z * sin,
      this.liveHeadPosition.y + y,
      this.liveHeadPosition.z + x * sin + z * cos,
    );
  }

  getLiveBodyPartPosition(part, target) {
    const side = part.startsWith("left_") ? -1 : part.startsWith("right_") ? 1 : 0;
    const bodyOffset = questBodyRelativeOffsetForPart(part);
    if (["helmet", "chest", "back", "waist"].includes(part)) {
      return this.setLiveBodyOffset(target, bodyOffset[0], bodyOffset[1], bodyOffset[2]);
    }
    if (part.includes("_thigh") || part.includes("_shin") || part.includes("_boot")) {
      return this.setLiveBodyOffset(target, bodyOffset[0], bodyOffset[1], bodyOffset[2]);
    }

    const hand = side < 0 ? "left" : "right";
    const shoulderOffset = questBodyRelativeOffsetForPart(`${hand}_shoulder`);
    const shoulder = this.setLiveBodyOffset(this.livePartPositionB, shoulderOffset[0], shoulderOffset[1], shoulderOffset[2]);
    const handPosition = this.getEstimatedHandPosition(hand, this.livePartPositionC);
    if (part.endsWith("_shoulder")) return target.copy(shoulder);
    if (part.endsWith("_upperarm")) return target.lerpVectors(shoulder, handPosition, 0.36);
    if (part.endsWith("_forearm")) return target.lerpVectors(shoulder, handPosition, 0.72);
    if (part.endsWith("_hand")) return target.copy(handPosition);

    const fallback = questAssemblyPoseForPart(part);
    if (fallback) return target.fromArray(fallback);
    return this.setLiveBodyOffset(target, 0, -0.5, 0);
  }

  applyLiveSuitPose(mesh, part, reveal) {
    this.getLiveBodyPartPosition(part, this.livePartPosition);
    mesh.position.copy(this.livePartPosition);
    applyRuntimePlacementOffset(mesh, part, reveal, this.liveTorsoYaw);
    applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, this.liveTorsoYaw);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const emerge = lerp(0.08, 1, reveal);
    if (isGlbArmorMesh(mesh)) {
      mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));
      return;
    }
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
  }

  applyLiveMirrorSuitPose(mesh, part, reveal) {
    const pose = questAssemblyPoseForPart(part);
    mesh.position.fromArray(pose);
    applyRuntimePlacementOffset(mesh, part, reveal, 0);
    applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, 0);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const emerge = lerp(0.08, 1, reveal);
    if (isGlbArmorMesh(mesh)) {
      mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));
      return;
    }
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
  }

  applyStandbySuitPose(mesh, part) {
    const standTransform = {
      yaw: this.armorStandYaw,
      pitch: this.armorStandPitch,
      scale: this.armorStandScale,
      explode: this.armorStandExploded ? 1 : 0,
      offset: this.armorStandOffset,
    };
    const pose = armorStandRigPoseForPart(part, mesh, standTransform);
    mesh.position.fromArray(pose);
    applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, 0);
    applyArmorStandInspectionRotation(mesh, this.armorStandPitch, this.armorStandYaw);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    if (isGlbArmorMesh(mesh)) {
      mesh.scale.set(...questGlbScaleForPart(mesh, part, this.armorStandScale));
      return;
    }
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(
      sx * vrScale * this.armorStandScale,
      sy * vrScale * this.armorStandScale,
      sz * vrScale * this.armorStandScale,
    );
  }

  vectorSample(vector) {
    return [vector.x, vector.y, vector.z].map((value) => Number(value.toFixed(4)));
  }

  captureLiveMotionSample(progress) {
    if (!this.playing || this.xrViewMode !== XR_VIEW_MODE_SELF) return;
    if (this.liveMotionFrames.length >= LIVE_MOTION_MAX_FRAMES) return;
    if (this.elapsed - this.lastLiveMotionSampleAt < LIVE_MOTION_SAMPLE_INTERVAL) return;
    this.lastLiveMotionSampleAt = this.elapsed;
    this.liveMotionFrames.push({
      t: Number(this.elapsed.toFixed(3)),
      progress: Number(progress.toFixed(4)),
      root: this.vectorSample(this.xrWorldAnchorPosition),
      head: this.vectorSample(this.liveHeadPosition),
      left_hand: this.vectorSample(this.liveLeftHandPosition),
      right_hand: this.vectorSample(this.liveRightHandPosition),
      torso_yaw: Number(this.liveTorsoYaw.toFixed(4)),
      left_hand_tracked: this.leftHandTracked,
      right_hand_tracked: this.rightHandTracked,
    });
  }

  motionCapturePayload() {
    if (!this.liveMotionFrames.length) return null;
    return {
      format: "quest-live-pose.v0",
      tracking: "hmd_plus_controllers",
      timebase: "deposition_elapsed_sec",
      coordinate_space: {
        root: "xr_world_anchor",
        head: "rig_local",
        left_hand: "rig_local",
        right_hand: "rig_local",
      },
      sample_interval_sec: LIVE_MOTION_SAMPLE_INTERVAL,
      frame_count: this.liveMotionFrames.length,
      frames: this.liveMotionFrames,
      note: "Hips, torso twist, and feet are estimated until mocopi/IK/VRM retargeting is connected.",
    };
  }

  setArchiveMotionFrames(frames) {
    this.archiveMotionFrames = Array.isArray(frames)
      ? frames.map((frame) => normalizeMotionFrame(frame)).filter(Boolean).sort((a, b) => a.t - b.t)
      : [];
  }

  playbackMotionFrames() {
    if (this.playbackSource !== "archive") return [];
    if (this.xrViewMode === XR_VIEW_MODE_SELF) return [];
    return this.archiveMotionFrames;
  }

  currentReplayMotionFrame(elapsed = this.elapsed) {
    const frames = this.playbackMotionFrames();
    if (!frames.length) return null;
    if (frames.length === 1) return frames[0];
    const time = clamp(elapsed, frames[0].t, frames.at(-1).t);
    let upperIndex = frames.findIndex((frame) => frame.t >= time);
    if (upperIndex <= 0) return frames[0];
    if (upperIndex < 0) return frames.at(-1);
    const lower = frames[upperIndex - 1];
    const upper = frames[upperIndex];
    return interpolateMotionFrame(lower, upper, time);
  }

  setMotionBodyOffset(frame, target, x, y, z) {
    this.motionHeadPosition.fromArray(frame.head || [0, 1.56, 0]);
    const yaw = Number(frame.torso_yaw || 0);
    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    return target.set(
      this.motionHeadPosition.x + x * cos - z * sin,
      this.motionHeadPosition.y + y,
      this.motionHeadPosition.z + x * sin + z * cos,
    );
  }

  getMotionHandPosition(frame, hand, target) {
    const tracked = hand === "left" ? frame.left_hand_tracked : frame.right_hand_tracked;
    const source = hand === "left" ? frame.left_hand : frame.right_hand;
    if (tracked && Array.isArray(source)) {
      target.fromArray(source);
      return target;
    }
    const offset = questBodyRelativeOffsetForPart(`${hand}_hand`);
    return this.setMotionBodyOffset(frame, target, offset[0], offset[1], offset[2]);
  }

  getMotionBodyPartPosition(part, frame, target) {
    const side = part.startsWith("left_") ? -1 : part.startsWith("right_") ? 1 : 0;
    const bodyOffset = questBodyRelativeOffsetForPart(part);
    if (["helmet", "chest", "back", "waist"].includes(part)) {
      return this.setMotionBodyOffset(frame, target, bodyOffset[0], bodyOffset[1], bodyOffset[2]);
    }
    if (part.includes("_thigh") || part.includes("_shin") || part.includes("_boot")) {
      return this.setMotionBodyOffset(frame, target, bodyOffset[0], bodyOffset[1], bodyOffset[2]);
    }

    const hand = side < 0 ? "left" : "right";
    const shoulderOffset = questBodyRelativeOffsetForPart(`${hand}_shoulder`);
    const shoulder = this.setMotionBodyOffset(frame, this.motionPartPositionB, shoulderOffset[0], shoulderOffset[1], shoulderOffset[2]);
    const handPosition = this.getMotionHandPosition(frame, hand, this.motionPartPositionC);
    if (part.endsWith("_shoulder")) return target.copy(shoulder);
    if (part.endsWith("_upperarm")) return target.lerpVectors(shoulder, handPosition, 0.36);
    if (part.endsWith("_forearm")) return target.lerpVectors(shoulder, handPosition, 0.72);
    if (part.endsWith("_hand")) return target.copy(handPosition);

    const fallback = questAssemblyPoseForPart(part);
    if (fallback) return target.fromArray(fallback);
    return this.setMotionBodyOffset(frame, target, 0, -0.5, 0);
  }

  applyMotionSuitPose(mesh, part, frame, reveal, options = {}) {
    const bodyPose = options.centered ? questAssemblyPoseForPart(part) : null;
    if (bodyPose) {
      mesh.position.fromArray(bodyPose);
    } else {
      this.getMotionBodyPartPosition(part, frame, this.motionPartPosition);
      mesh.position.copy(this.motionPartPosition);
    }
    const torsoYaw = options.centered ? 0 : Number(frame.torso_yaw || 0);
    applyRuntimePlacementOffset(mesh, part, reveal, torsoYaw);
    applyRuntimePlacementRotation(mesh, questBaseRotationXForMesh(mesh), 0, torsoYaw);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const emerge = lerp(0.08, 1, reveal);
    if (isGlbArmorMesh(mesh)) {
      mesh.scale.set(...questGlbScaleForPart(mesh, part, emerge));
      return;
    }
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
  }

  updateLiveMirrorAvatar(progress, reveal, { liveBodyPose = useQuestLiveBodyPose() } = {}) {
    if (!this.liveMirror) return;
    const wasVisible = this.liveMirror.visible;
    const visible =
      Boolean(this.world.session)
      && this.xrViewMode === XR_VIEW_MODE_SELF
      && liveBodyPose
      && this.liveMirrorReady
      && progress >= LIVE_MIRROR_SHOW_PROGRESS;
    if (!visible) {
      this.liveMirror.visible = false;
      for (const mesh of this.liveMirrorMeshes.values()) mesh.visible = false;
      return;
    }

    if (!wasVisible) {
      this.liveMirror.position.copy(this.liveMirrorPosition);
      this.liveMirror.quaternion.copy(this.liveMirrorQuaternion);
      this.liveMirror.scale.copy(this.liveMirrorScale);
    } else {
      this.liveMirror.position.lerp(this.liveMirrorPosition, 0.22);
      this.liveMirror.quaternion.slerp(this.liveMirrorQuaternion, 0.18);
      this.liveMirror.scale.lerp(this.liveMirrorScale, 0.16);
    }
    this.liveMirror.visible = true;
    let order = 0;
    for (const [part, mesh] of this.liveMirrorMeshes.entries()) {
      const sourceMesh = this.meshes.get(part);
      if (sourceMesh?.material?.map && mesh.material.map !== sourceMesh.material.map) {
        mesh.material.map = sourceMesh.material.map;
        mesh.material.color.setHex(0xffffff);
        mesh.material.needsUpdate = true;
      }
      this.applyLiveMirrorSuitPose(mesh, part, reveal);
      const stagger = clamp((progress * ARMOR_PARTS.length - order) / 3.2, 0, 1);
      const depositionFlash = Math.sin(Math.PI * stagger) * clamp(progress, 0, 1);
      mesh.material.opacity = 0.08 + easeOutCubic(stagger) * 0.86 + depositionFlash * 0.06;
      mesh.material.emissiveIntensity = (this.world.session ? 0.35 + stagger * 0.75 : 0.18) + depositionFlash * 0.85;
      mesh.visible = mesh.material.opacity > 0.09;
      order += 1;
    }
  }

  updateDepositionEffects(dt, progress, { active = false, selfView = false, mirrorView = false } = {}) {
    const effects = this.depositionEffects;
    if (!effects) return;
    const fieldActive = active && progress > 0.015 && progress < 0.995;
    effects.group.visible = fieldActive;
    if (!fieldActive) {
      effects.points.material.opacity = 0;
      effects.sparks.material.opacity = 0;
      return;
    }

    const glow = Math.sin(Math.PI * clamp(progress, 0, 1));
    const shellPull = easeOutCubic(progress);
    const time = this.elapsed + this.clock.elapsedTime * 0.18;
    const zCenter = mirrorView ? MIRROR_DEPOSITION_Z : selfView ? -0.18 : DEPOSITION_BODY_Z;
    const mirrorParticleDimming = mirrorView ? MIRROR_DEPOSITION_DIMMING : 1;
    effects.points.material.opacity = (0.2 + glow * 0.7) * mirrorParticleDimming;
    effects.points.material.size = this.world.session ? 0.029 + glow * 0.018 : 0.025 + glow * 0.014;
    effects.sparks.material.opacity = (0.12 + glow * 0.58) * mirrorParticleDimming;

    const positions = effects.positions;
    const colors = effects.colors;
    for (let i = 0; i < effects.seeds.length; i += 1) {
      const seed = effects.seeds[i];
      const wave = clamp((progress * 1.24 - seed.start) / 0.34, 0, 1);
      const lock = easeOutCubic(wave);
      const yBase = lerp(DEPOSITION_BODY_Y_MIN, DEPOSITION_BODY_Y_MAX, seed.height);
      const y = yBase + Math.sin(time * seed.speed + seed.angle) * (0.02 + (1 - lock) * 0.06);
      const surfaceRadius = depositionBodyRadiusAtY(y) + seed.surfaceOffset;
      const outerRadius = seed.radius + Math.sin(seed.angle * 0.37) * 0.08;
      const radius = lerp(outerRadius, surfaceRadius, lock);
      const angle = seed.angle + time * seed.speed + shellPull * seed.twist;
      const idx = i * 3;
      positions[idx] = Math.cos(angle) * radius;
      positions[idx + 1] = y;
      positions[idx + 2] = zCenter + Math.sin(angle) * radius * 0.44;

      const heat = Math.sin(Math.PI * lock) * glow;
      colors[idx] = lerp(seed.color.r, 1, heat);
      colors[idx + 1] = lerp(seed.color.g, 0.93, heat * 0.78);
      colors[idx + 2] = lerp(seed.color.b, 0.72, heat * 0.62);
    }
    effects.points.geometry.attributes.position.needsUpdate = true;
    effects.points.geometry.attributes.color.needsUpdate = true;

    const sparkPositions = effects.sparkPositions;
    for (let i = 0; i < DEPOSITION_SPARK_COUNT; i += 1) {
      const seed = effects.seeds[(i * 5) % effects.seeds.length];
      const wave = clamp((progress * 1.32 - seed.start) / 0.22, 0, 1);
      const lock = easeOutCubic(wave);
      const y = lerp(DEPOSITION_BODY_Y_MIN, DEPOSITION_BODY_Y_MAX, seed.height);
      const surfaceRadius = depositionBodyRadiusAtY(y);
      const angle = seed.angle + time * (seed.speed + 0.8) + shellPull * seed.twist;
      const outerRadius = lerp(seed.radius + 0.18, surfaceRadius + 0.05, lock);
      const innerRadius = lerp(seed.radius + 0.02, surfaceRadius - 0.02, lock);
      const idx = i * 6;
      sparkPositions[idx] = Math.cos(angle) * outerRadius;
      sparkPositions[idx + 1] = y + 0.04;
      sparkPositions[idx + 2] = zCenter + Math.sin(angle) * outerRadius * 0.44;
      sparkPositions[idx + 3] = Math.cos(angle + 0.08) * innerRadius;
      sparkPositions[idx + 4] = y - 0.05;
      sparkPositions[idx + 5] = zCenter + Math.sin(angle + 0.08) * innerRadius * 0.44;
    }
    effects.sparks.geometry.attributes.position.needsUpdate = true;
  }

  updateRigAnchor() {
    if (!this.world.session) {
      this.rig.position.lerp(NON_VR_RIG_POSITION, 0.16);
      this.rig.scale.lerp(this.nonVrScale, 0.16);
      this.rigTargetQuaternion.identity();
      this.rig.quaternion.slerp(this.rigTargetQuaternion, 0.16);
      return;
    }

    const expectedAnchorProfile = this.worldAnchorProfileForViewMode(this.xrViewMode);
    if (
      !this.xrWorldAnchorReady
      || this.xrWorldAnchorMode !== this.xrViewMode
      || this.xrWorldAnchorProfile !== expectedAnchorProfile
    ) {
      this.captureWorldAnchor(this.xrViewMode);
    }
    this.rigTargetPosition.copy(this.xrWorldAnchorPosition);
    this.rigTargetQuaternion.copy(this.xrWorldAnchorQuaternion);
    this.rig.scale.lerp(this.xrWorldAnchorScale, 0.18);
    this.rig.position.lerp(this.rigTargetPosition, 0.28);
    this.rig.quaternion.slerp(this.rigTargetQuaternion, 0.22);
  }

  updateScene(dt) {
    this.updateRigAnchor();
    if (this.liveBodySimEnabled) {
      void this.refreshLiveBodySimLatest();
    }

    if (this.playing) {
      this.elapsed = Math.min(this.elapsed + dt, this.duration);
      if (this.elapsed >= this.duration && !this.completionAnnounced) {
        UI.status.textContent = "変身完了。記録再生で確認できます。";
        this.setVoiceState("complete");
        this.audioBed.pulse(1180, 0.18);
        if (this.playbackSource !== "archive") {
          void Promise.resolve(this.depositionStartPromise)
            .then(() =>
              this.appendTrialEvent("DEPOSITION_COMPLETED", {
                stateAfter: "ACTIVE",
                payload: {
                  source: "quest-iw-demo",
                  completed: true,
                  motion_capture: this.motionCapturePayload(),
                },
                idempotencyKey: this.trialEventKey("deposition-completed"),
              }),
            )
            .then(() => this.generateTrialReplay());
        }
        this.completionAnnounced = true;
      }
    }

    const progress = clamp(this.elapsed / this.duration, 0, 1);
    const reveal = easeOutCubic(progress);
    const frame = this.currentFrame(progress) || this.frames.at(-1);
    const segments = frame?.segments || {};
    const hasSegmentPose = Object.keys(segments).length > 0;
    const replayMotionFrame = this.currentReplayMotionFrame(this.elapsed);

    UI.meterFill.style.width = `${Math.round(progress * 100)}%`;

    let order = 0;
    const inXr = Boolean(this.world.session);
    const selfView = inXr && this.xrViewMode === XR_VIEW_MODE_SELF;
    const mirrorView = inXr && this.xrViewMode === XR_VIEW_MODE_MIRROR;
    const liveBodyPose = useQuestLiveBodyPose();
    const mocopiSegmentPose = this.liveBodySimEnabled && hasSegmentPose && !this.liveBodySimSourceStale;
    const fixedBodyPose = inXr && !liveBodyPose && !mocopiSegmentPose;
    const bodyShellAligned = fixedBodyPose || (selfView && !mocopiSegmentPose) || (!inXr && !mocopiSegmentPose);
    const useLiveSuit = liveBodyPose && selfView && this.xrWorldAnchorReady;
    const hasRuntimePose = useLiveSuit || hasSegmentPose || Boolean(replayMotionFrame);
    const standbyPreview = this.meshes.size > 0 && this.isArmorStandPreviewMode();
    const canRenderTransformSuit = this.playing && hasRuntimePose;
    const shouldShowSuit = standbyPreview || canRenderTransformSuit;
    if (useLiveSuit) {
      this.updateLiveBodyAnchors();
      this.captureLiveMotionSample(progress);
    }
    this.updateBaseSuitVisibility({ standbyPreview, selfView, mirrorView, reveal, bodyShellAligned });
    if (this.mirrorFrame) {
      this.mirrorFrame.visible = inXr && this.xrViewMode === XR_VIEW_MODE_MIRROR;
    }
    for (const [part, mesh] of this.meshes.entries()) {
      const segmentName = PART_TO_SEGMENT[part] || part;
      const pose = segments[segmentName];
      const useReplayMotion = !hasSegmentPose && replayMotionFrame;
      const hiddenForSelf =
        selfView
        && (
          (standbyPreview ? SELF_VIEW_STANDBY_HIDDEN_PARTS : SELF_VIEW_HIDDEN_PARTS).has(part)
          || (!standbyPreview && isGeneratedFallbackArmorMesh(mesh))
        );
      if (hiddenForSelf) {
        mesh.visible = false;
        order += 1;
        continue;
      }
      if (standbyPreview) {
        this.applyStandbySuitPose(mesh, part);
      } else if (!canRenderTransformSuit || (!useLiveSuit && !pose && !useReplayMotion)) {
        mesh.visible = false;
        order += 1;
        continue;
      } else if (useLiveSuit) {
        this.applyLiveSuitPose(mesh, part, reveal);
      } else if (useReplayMotion) {
        this.applyMotionSuitPose(mesh, part, replayMotionFrame, reveal, { centered: bodyShellAligned });
      } else {
        applySegmentPose(mesh, pose, part, reveal, {
          centered: bodyShellAligned && !mocopiSegmentPose,
          liveMocopi: mocopiSegmentPose,
          liveMocopiProfile: this.liveBodySimRenderProfile,
          progress,
          finalPosition: this.finalPosition,
          stagePosition: this.stagePosition,
        });
      }
      const stagger = standbyPreview ? 1 : clamp((progress * ARMOR_PARTS.length - order) / 3.2, 0, 1);
      const depositionFlash = standbyPreview ? 0 : Math.sin(Math.PI * stagger) * clamp(progress, 0, 1);
      mesh.material.opacity = standbyPreview ? 0.82 : 0.08 + easeOutCubic(stagger) * 0.86 + depositionFlash * 0.06;
      mesh.material.emissiveIntensity = (this.world.session ? 0.35 + stagger * 0.75 : 0.18) + depositionFlash * 0.9;
      mesh.visible = shouldShowSuit && mesh.material.opacity > 0.09;
      order += 1;
    }
    this.updateLiveMirrorAvatar(progress, reveal, { liveBodyPose });
    this.updateDepositionEffects(dt, progress, {
      active: canRenderTransformSuit && !standbyPreview,
      selfView,
      mirrorView,
    });
    this.sendQuestDebugTelemetry("scene");

    for (let i = 0; i < this.rings.length; i += 1) {
      const ring = this.rings[i];
      const ringProgress = (progress + i * 0.17) % 1;
      const scale = (0.38 + ringProgress * 1.75) * (standbyPreview ? this.armorStandScale : 1);
      ring.scale.setScalar(scale);
      ring.position.x = standbyPreview ? this.armorStandOffset.x : 0;
      ring.position.y = lerp(-1.15, 0.92, ringProgress);
      ring.position.z = standbyPreview ? ARMOR_STAND_CENTER_Z + this.armorStandOffset.z : DEPOSITION_BODY_Z;
      ring.material.opacity = (1 - ringProgress) * 0.55;
      ring.rotation.z += dt * (0.8 + i * 0.35);
    }

    this.spatialPanel.update(dt);

    if (!this.world.session) {
      this.rig.rotation.y = Math.sin(performance.now() * 0.00025) * 0.08;
    }
    this.titleSprite.material.opacity = 0.45 + Math.sin(performance.now() * 0.005) * 0.25;
  }
}

function setQuestBootPhase(phase, extra = {}) {
  window.__questHenshinBoot = {
    ...(window.__questHenshinBoot || {}),
    phase,
    at: new Date().toISOString(),
    href: window.location.href,
    ...extra,
  };
}

setQuestBootPhase("before-world-create");

QuestHenshinDemo.create()
  .then((demo) => {
    setQuestBootPhase("after-world-create");
    window.__questHenshinDemo = demo;
    Promise.resolve(demo.start())
      .then(() => setQuestBootPhase("start-complete"))
      .catch((error) => {
        console.error("[Quest start]", error);
        setQuestBootPhase("start-error", { error: String(error?.message || error) });
        UI.status.textContent = String(error?.message || error);
      });
    setQuestBootPhase("start-called");
    demo.sendQuestDebugTelemetry("started", { force: true });
  })
  .catch((error) => {
    console.error(error);
    setQuestBootPhase("create-error", { error: String(error?.message || error) });
    UI.status.textContent = String(error?.message || error);
  });
