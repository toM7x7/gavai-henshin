import {
  ReferenceSpaceType,
  SessionMode,
  VisibilityState,
  World,
} from "@iwsdk/core";
import * as THREE from "three";

const DEFAULT_REPLAY = "/sessions/S-IW-DEMO/artifacts/iwsdk-deposition-replay.json";
const DEFAULT_SUITSPEC = "/examples/suitspec.sample.json";
const DEFAULT_MOCOPI = "examples/mocopi_sequence.sample.json";
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
  routeMode: document.getElementById("routeMode"),
  routeApi: document.getElementById("routeApi"),
  routeTrial: document.getElementById("routeTrial"),
  routeReplay: document.getElementById("routeReplay"),
  routeContract: document.getElementById("routeContract"),
  recallCodeInput: document.getElementById("recallCodeInput"),
  btnLoadRecallCode: document.getElementById("btnLoadRecallCode"),
  recallCodeState: document.getElementById("recallCodeState"),
  sessionId: document.getElementById("sessionId"),
  triggerState: document.getElementById("triggerState"),
  equipState: document.getElementById("equipState"),
};

const textureLoader = new THREE.TextureLoader();
const geometryCache = new Map();
const textureCache = new Map();
const TAU = Math.PI * 2;
const XR_VIEW_MODE_SELF = "self";
const XR_VIEW_MODE_OBSERVER = "observer";
const XR_VIEW_MODE_MIRROR = "mirror";
const REPLAY_MOTION_SOURCE_LIVE_POSE = "live_pose";
const REPLAY_MOTION_SOURCE_BODY_SIM = "body_sim";
const REPLAY_MOTION_SOURCE_MIXED = "body_sim_plus_live_pose";
const REPLAY_MOTION_SOURCE_STATIC = "static_fallback";
const REPLAY_MOTION_SOURCE_CAPTURE = "live_capture";
const REPLAY_MOTION_SOURCE_SELF = "first_person";
const SELF_VIEW_HIDDEN_PARTS = new Set(["helmet", "left_hand", "right_hand"]);
const SELF_VIEW_STANDBY_HIDDEN_PARTS = new Set(["helmet"]);
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
const LIVE_MOTION_SAMPLE_INTERVAL = 0.1;
const LIVE_MOTION_MAX_FRAMES = 48;
const NON_VR_RIG_POSITION = new THREE.Vector3(0, 0.78, -2.55);
const VR_BODY_PART_POSES = {
  helmet: [0, -0.04, -0.2],
  chest: [0, -0.52, -0.32],
  back: [0, -0.52, 0.12],
  waist: [0, -0.84, -0.3],
  left_shoulder: [-0.34, -0.42, -0.28],
  right_shoulder: [0.34, -0.42, -0.28],
  left_upperarm: [-0.48, -0.64, -0.28],
  right_upperarm: [0.48, -0.64, -0.28],
  left_forearm: [-0.52, -0.92, -0.34],
  right_forearm: [0.52, -0.92, -0.34],
  left_hand: [-0.5, -1.1, -0.36],
  right_hand: [0.5, -1.1, -0.36],
  left_thigh: [-0.18, -1.08, -0.24],
  right_thigh: [0.18, -1.08, -0.24],
  left_shin: [-0.18, -1.42, -0.27],
  right_shin: [0.18, -1.42, -0.27],
  left_boot: [-0.18, -1.68, -0.33],
  right_boot: [0.18, -1.68, -0.33],
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

const VOICE_STATES = {
  ready: {
    label: "音声 待機",
    hint: `ここに向けてトリガー後、${TRIGGER_PHRASE} と発声。`,
    color: 0x43d8ff,
    textColor: "#d7f8ff",
    border: "rgba(67, 216, 255, 0.62)",
  },
  arming: {
    label: "準備中",
    hint: "発声案内まで少し待ってください。",
    color: 0x8edfff,
    textColor: "#d7f8ff",
    border: "rgba(142, 223, 255, 0.74)",
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
    color: 0x8edfff,
    textColor: "#d7f8ff",
    border: "rgba(142, 223, 255, 0.7)",
  },
  detected: {
    label: `${TRIGGER_PHRASE} 確認`,
    hint: "変身を開始します。",
    color: 0xfff4c8,
    textColor: "#fff4c8",
    border: "rgba(255, 244, 200, 0.72)",
  },
  deposition: {
    label: "変身中",
    hint: "装甲を展開しています。",
    color: 0xffcf5a,
    textColor: "#fff4c8",
    border: "rgba(255, 207, 90, 0.78)",
  },
  complete: {
    label: "完了",
    hint: "記録再生できます。",
    color: 0xf6f1df,
    textColor: "#f6f1df",
    border: "rgba(246, 241, 223, 0.68)",
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
  ["head", "sphere", [0, -0.08, -0.24], [0.16, 0.18, 0.14], [0, 0, 0]],
  ["torso", "capsule", [0, -0.58, -0.28], [0.28, 0.54, 0.18], [0, 0, 0]],
  ["pelvis", "capsule", [0, -0.98, -0.28], [0.24, 0.28, 0.16], [0, 0, Math.PI / 2]],
  ["left_upperarm", "capsule", [-0.42, -0.62, -0.28], [0.075, 0.42, 0.075], [0, 0, -0.26]],
  ["right_upperarm", "capsule", [0.42, -0.62, -0.28], [0.075, 0.42, 0.075], [0, 0, 0.26]],
  ["left_forearm", "capsule", [-0.58, -0.98, -0.29], [0.065, 0.36, 0.065], [0, 0, -0.18]],
  ["right_forearm", "capsule", [0.58, -0.98, -0.29], [0.065, 0.36, 0.065], [0, 0, 0.18]],
  ["left_thigh", "capsule", [-0.15, -1.22, -0.29], [0.085, 0.42, 0.085], [0, 0, 0.04]],
  ["right_thigh", "capsule", [0.15, -1.22, -0.29], [0.085, 0.42, 0.085], [0, 0, -0.04]],
  ["left_shin", "capsule", [-0.17, -1.58, -0.31], [0.073, 0.4, 0.073], [0, 0, 0.03]],
  ["right_shin", "capsule", [0.17, -1.58, -0.31], [0.073, 0.4, 0.073], [0, 0, -0.03]],
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

function getReplayPath() {
  return params().get("replay") || DEFAULT_REPLAY;
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

async function getJson(path) {
  const response = await fetch(`${getApiBase()}${path}`, { cache: "no-store" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `GET ${path} failed with ${response.status}`);
  }
  return data;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function compactToken(value, maxLength = 34) {
  const text = String(value || "");
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(4, maxLength - 4))}...`;
}

function setBadge(element, text, state = "idle") {
  if (!element) return;
  element.textContent = text;
  element.dataset.state = state;
}

function setRouteContract(element, suitspec) {
  if (!element) return;
  element.textContent = `FIT CONTRACT: ${formatFitContract(suitspec)} / TEXTURE FALLBACK: ${formatTextureFallback(suitspec)}`;
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
  if (Number.isFinite(peak)) parts.push(`peak ${peak.toFixed(3)}`);
  if (Number.isFinite(rms)) parts.push(`rms ${rms.toFixed(3)}`);
  if (stats.quiet) parts.push("quiet");
  return parts.join(" / ");
}

function formatVoiceRetryDetail(data, transcript) {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const heard = transcript ? `Whisper heard: ${transcript}` : "Whisper returned an empty transcript.";
  const diagnostic = formatAudioStats(stats);
  const saved = voiceAudio.url ? ` Saved: ${voiceAudio.url}` : "";
  return `${heard}${diagnostic ? ` (${diagnostic})` : ""}.${saved}`;
}

function formatVoiceRetryHint(data, transcript) {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const diagnostic = formatAudioStats(stats);
  if (transcript) {
    return `Whisper: "${transcript}" / no ${TRIGGER_PHRASE}.${diagnostic ? ` ${diagnostic}` : ""}`;
  }
  return `Whisper: empty.${diagnostic ? ` ${diagnostic}` : ""}`;
}

function formatVoiceDebug(data, transcript, reason = "") {
  const voiceAudio = data?.voice_audio || data?.result?.voice_audio || {};
  const stats = voiceAudio.stats || data?.result?.audio_stats;
  const match = data?.replay?.trigger?.match || data?.result?.trigger_match;
  const lines = [
    "VOICE DEBUG",
    `result: ${data?.ok ? "ok" : "retry"}`,
    `trigger: ${TRIGGER_PHRASE}`,
    `transcript: ${transcript || "(empty)"}`,
  ];
  if (match?.mode && match.mode !== "none") {
    lines.push(`match: ${match.mode}${match.matched ? ` / ${match.matched}` : ""}`);
  }
  const diagnostic = formatAudioStats(stats);
  if (diagnostic) lines.push(`audio: ${diagnostic}`);
  if (voiceAudio.bytes) lines.push(`bytes: ${voiceAudio.bytes}`);
  if (voiceAudio.mime_type) lines.push(`mime: ${voiceAudio.mime_type}`);
  if (voiceAudio.url) lines.push(`saved: ${voiceAudio.url}`);
  if (reason) lines.push(`reason: ${reason}`);
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

function makeReplayMotionDiagnostic(source, livePoseFrames = 0, bodySimFrames = 0) {
  const live = Math.max(0, livePoseFrames);
  const body = Math.max(0, bodySimFrames);
  if (source === REPLAY_MOTION_SOURCE_MIXED) {
    return {
      source,
      token: "BODY+LIVE",
      label: `body-sim ${body} frames + live-pose ${live} frames`,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_LIVE_POSE) {
    return {
      source,
      token: `LIVE ${live}f`,
      label: `live-pose ${live} frames`,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_BODY_SIM) {
    return {
      source,
      token: `BODY ${body}f`,
      label: `body-sim ${body} frames`,
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_CAPTURE) {
    return {
      source,
      token: "CAPTURE",
      label: "live capture",
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  if (source === REPLAY_MOTION_SOURCE_SELF) {
    return {
      source,
      token: "SELF",
      label: "first-person transform",
      live_pose_frames: live,
      body_sim_frames: body,
    };
  }
  return {
    source: REPLAY_MOTION_SOURCE_STATIC,
    token: "STATIC",
    label: "static fallback",
    live_pose_frames: live,
    body_sim_frames: body,
  };
}

async function loadJson(path) {
  const normalized = normalizePath(path);
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
    UI.micState.textContent = "SuitSpec texture map unavailable; mesh fallback remains active.";
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

function formatTextureFallback(suitspec) {
  const fallback = suitspec?.texture_fallback || {};
  return `${fallback.mode || "missing"} / ${fallback.source || "missing"}`;
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

function fallbackGeometry(part) {
  return part === "helmet"
    ? new THREE.SphereGeometry(0.18, 32, 18)
    : new THREE.CapsuleGeometry(0.18, 0.62, 8, 20);
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
  geometry.translate(-center.x, -center.y, -center.z);
  geometry.scale(1 / scale, 1 / scale, 1 / scale);
  geometry.computeBoundingSphere();
  return geometry;
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

async function loadMeshGeometry(assetRef, part) {
  const assetPath = normalizePath(assetRef || `viewer/assets/meshes/${part}.mesh.json`);
  if (geometryCache.has(assetPath)) return geometryCache.get(assetPath).clone();
  const payload = await loadJson(assetPath);
  const geometry = meshGeometryFromPayload(payload);
  geometryCache.set(assetPath, geometry);
  return geometry.clone();
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
  }

  const mesh = new THREE.Mesh(geometry, createMaterial(color, 0.0));
  mesh.name = part;
  mesh.userData.module = module || {};
  if (module?.texture_path) {
    const allowPaletteFallback = suitspec?.texture_fallback?.mode === "palette_material";
    loadTexture(module.texture_path, { allowPaletteFallback })
      .then((texture) => {
        if (!texture) {
          mesh.userData.textureFallbackActive = allowPaletteFallback;
          return;
        }
        mesh.material.map = texture;
        mesh.material.color.setHex(0xffffff);
        mesh.material.needsUpdate = true;
      })
      .catch((error) => {
        mesh.userData.textureFallbackActive = allowPaletteFallback;
        console.warn(`texture fallback for ${part}`, error);
      });
  }
  return mesh;
}

function applySegmentPose(mesh, pose, part, reveal, options = {}) {
  if (!pose) return;
  const offset = PART_OFFSETS[part] || [0, 0, 0];
  const x = pose.position_x - 0.55 + offset[0];
  const y = pose.position_y + 0.2 + offset[1];
  const z = -pose.position_z + offset[2];
  if (options.centered) {
    const index = mesh.userData.partIndex || 0;
    const angle = (index / ARMOR_PARTS.length) * TAU + options.progress * 1.35;
    const stageRadius = 0.38 + (index % 3) * 0.06;
    const stageLift = part === "helmet" ? 0.12 : 0.05;
    const fitProgress = easeOutCubic(clamp((options.progress - 0.18) / 0.68, 0, 1));
    const bodyPose = VR_BODY_PART_POSES[part];
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
  mesh.rotation.set(Math.PI / 2, 0, pose.rotation_z || 0);

  const fit = mesh.userData.module?.fit || {};
  const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
  const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
  const sx = Math.max(Number(pose.scale_x || 1) * Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
  const sy = Math.max(Number(pose.scale_y || 1) * Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
  const sz = Math.max(Number(pose.scale_z || 1) * Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
  const emerge = lerp(0.08, 1, reveal);
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

    this.routeStatus = makeTextPlane("生成 LOCAL | 試験 WAIT | 記録 WAIT", {
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

    this.debug = makeTextPlane("音声デバッグ: 待機", {
      width: 1.42,
      height: 0.2,
      canvasWidth: 1400,
      canvasHeight: 280,
      fontSize: 28,
      fontWeight: 680,
      align: "left",
      baseline: "top",
      color: "#eef9ff",
      background: "rgba(2, 9, 13, 0.74)",
      border: "rgba(67, 216, 255, 0.34)",
      maxLines: 4,
    });
    this.debug.position.set(0, -0.005, 0.018);
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
    this.normalInputElements.push(this.addButton("reset", "リセット", -0.42, -0.45, 0xff6b6b).group);
    this.normalInputElements.push(this.addButton("lock", "固定", 0, -0.45, 0x8edfff).group);
    this.normalInputElements.push(this.addButton("close", "戻る", 0.42, -0.45, 0x43d8ff).group);
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
    for (const element of [this.progressBack, this.progressFill, this.routeStatus, this.debug, this.listenRing]) {
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
    }
    if (this.compactTitle) updateTextPlane(this.compactTitle, "メニュー");
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
    return this.menuMode !== XR_MENU_MODE_OPEN;
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

  getControllerByHand(hand) {
    return this.controllers.find((controller) => this.controllerHandedness(controller) === hand)
      || (hand === "left" ? this.controllers[0] : this.controllers[1])
      || null;
  }

  getMenuController() {
    return this.getControllerByHand("left") || this.controllers[0] || null;
  }

  setDebug(text) {
    if (!this.debug) return;
    updateTextPlane(this.debug, text || "音声デバッグ: 待機", {
      color: "#eef9ff",
      maxLines: 4,
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
    updateTextPlane(this.routeStatus, text || "生成 LOCAL | 試験 WAIT | 記録 WAIT", {
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
    this.listenRing.material.color.setHex(voiceState.color);
    if (this.compactRing) this.compactRing.material.color.setHex(voiceState.color);
    for (const button of this.buttons) {
      if (button.action === "pause") {
        updateTextPlane(button.text, this.demo.playing ? "停止" : "再開");
      }
    }
  }

  setArchiveViewMode(mode) {
    for (const button of this.buttons) {
      if (button.action === "view") {
        updateTextPlane(button.text, mode === XR_VIEW_MODE_OBSERVER ? "観察" : "鏡");
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
    if (!inVR) return;

    const xrCamera = this.demo.renderer.xr.getCamera(this.demo.camera) || this.demo.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    xrCamera.getWorldQuaternion(this.cameraQuaternion);
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

  updateTransformDevice(device, dt) {
    const lens = device.userData.lens;
    const glow = device.userData.glow;
    const body = device.userData.body;
    const active = ["arming", "recording", "detected", "deposition"].includes(this.demo.voiceState);
    const ready = this.demo.voiceState === "ready";
    const complete = this.demo.voiceState === "complete";
    const pulse = 0.5 + Math.sin(this.pulseClock * (active ? 9.0 : 3.4)) * 0.5;
    const color = active ? 0xffcf5a : complete ? 0x43d8ff : ready ? 0x8edfff : 0xff6b6b;
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
    if (action === "view") this.demo.cycleArchiveViewMode();
    if (action === "pause") this.demo.togglePause();
    if (action === "reset") this.demo.reset();
    if (action === "lock") this.toggleWorldLock();
    if (action === "close") this.setMenuMode(XR_MENU_MODE_COMPACT);
    if (action === "codeMode") this.setCodeInputMode(true);
    if (action === "codeBack") this.setCodeInputMode(false);
    if (action === "codeClear") this.clearRecallDraft();
    if (action === "codeBackspace") this.backspaceRecallDigit();
    if (action === "codeSubmit") void this.loadRecallDraft();
    if (action.startsWith("codeDigit")) this.appendRecallDigit(action.slice("codeDigit".length));
  }

  activateController(controller) {
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
    this.meshes = new Map();
    this.liveMirrorMeshes = new Map();
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
    this.replayMotionDiagnostic = makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);
    this.lastLiveMotionSampleAt = -Infinity;
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
    this.setRecallCodeState(this.recallCode ? `入力コード ${this.recallCode} を待機中` : "4桁コード未指定");
    this.setVoiceState("ready");
    this.updateArchiveViewModeLabel();
    this.updateVoiceDebug("VOICE DEBUG\nresult: waiting\ntrigger: 生成");
    this.syncRoutePanel();
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

    this.mirrorFrame = new THREE.Group();
    this.mirrorFrame.name = "XR-Archive-Mirror-Frame";
    this.mirrorFrame.visible = false;
    const mirrorGlass = new THREE.Mesh(
      new THREE.PlaneGeometry(MIRROR_FRAME_WIDTH, MIRROR_FRAME_HEIGHT),
      new THREE.MeshBasicMaterial({
        color: 0x9eefff,
        transparent: true,
        opacity: 0.08,
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
      opacity: 0.52,
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
        opacity: 0.07,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    );
    liveGlass.position.set(0, -0.58, 0.32);
    this.liveMirror.add(liveGlass);
    const liveFrameMaterial = new THREE.MeshBasicMaterial({
      color: 0x43d8ff,
      transparent: true,
      opacity: 0.5,
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

  async loadInitialSuitSpec() {
    if (useNewRouteApi() && this.recallCode) {
      return this.loadSuitByRecallCode(this.recallCode, { reloadMeshes: false, pushUrl: false });
    }
    this.suitspec = await loadSuitSpec();
    this.activeSuitId = this.suitspec?.suit_id || this.activeSuitId;
    this.setRecallCodeState("サンプルSuitSpecを使用中");
    return this.suitspec;
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
    this.lastLiveMotionSampleAt = -Infinity;
    this.frames = [];
    this.replay = null;
    this.playbackSource = "voice";
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
    this.recallCode = data.recall_code || recallCode;
    this.activeSuitId = nextSuitId;
    this.activeManifestId = data.manifest_id || data.suit?.manifest_id || this.activeManifestId;
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
    this.setRecallCodeState(`呼び出しOK: ${this.recallCode} / ${this.activeSuitId}`, "ok");
    this.setRouteApi(`CODE ${this.recallCode}`, "ok");
    this.appendVoiceDebug(`recall_code: ${this.recallCode} suit: ${this.activeSuitId}`);
    return this.suitspec;
  }

  clearArmorMeshes() {
    for (const mesh of this.meshes.values()) {
      mesh.removeFromParent();
    }
    this.meshes.clear();
    for (const mesh of this.liveMirrorMeshes.values()) {
      mesh.removeFromParent();
    }
    this.liveMirrorMeshes.clear();
  }

  updateArchiveViewModeLabel() {
    const label = formatArchiveViewMode(this.archiveViewMode);
    if (UI.btnReplayView) UI.btnReplayView.textContent = label;
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

  setVoiceState(state, detail = "", options = {}) {
    this.voiceState = state;
    const voiceState = VOICE_STATES[state] || VOICE_STATES.ready;
    UI.triggerState.textContent = `音声: ${voiceState.label}`;
    UI.micState.textContent = detail || voiceState.hint;
    if (options.status) UI.status.textContent = options.status;
    this.spatialPanel?.setVoiceState(state, detail);
  }

  updateVoiceDebug(text) {
    const value = text || "音声デバッグ: 待機";
    if (UI.voiceDebug) UI.voiceDebug.textContent = value;
    this.spatialPanel?.setDebug(value);
  }

  appendVoiceDebug(line) {
    if (!line) return;
    const next = `${UI.voiceDebug?.textContent || "VOICE DEBUG"}\n${line}`;
    this.updateVoiceDebug(next);
  }

  syncRoutePanel() {
    const newRoute = useNewRouteApi();
    setBadge(UI.routeMode, newRoute ? "生成: NEW" : "生成: LOCAL", newRoute ? "ok" : "idle");
    setBadge(UI.routeApi, newRoute ? "適合監査: /v1" : "適合監査: OFF", newRoute ? "pending" : "idle");
    setBadge(
      UI.routeTrial,
      this.trialId ? `変身試験: ${compactToken(this.trialId)}` : "変身試験: WAIT",
      this.trialId ? "ok" : "pending",
    );
    setBadge(
      UI.routeReplay,
      this.trialReplayPath
        ? `記録保管: ${compactToken(this.trialReplayPath, 20)} | 動き ${this.replayMotionDiagnostic.token}`
        : `記録保管: WAIT | 動き ${this.replayMotionDiagnostic.token}`,
      this.trialReplayPath ? "ok" : "pending",
    );
    setRouteContract(UI.routeContract, this.suitspec);
    this.routeState.apiLabel = newRoute ? "/v1 ARMED" : "OFF";
    this.routeState.apiState = newRoute ? "pending" : "idle";
    this.routeState.trialLabel = this.trialId || "WAIT";
    this.routeState.trialState = this.trialId ? "ok" : "pending";
    this.routeState.replayLabel = this.trialReplayPath || "WAIT";
    this.routeState.replayState = this.trialReplayPath ? "ok" : "pending";
    this.syncSpatialRouteStatus();
  }

  setRouteApi(label, state = "pending") {
    setBadge(UI.routeApi, `適合監査: ${compactToken(label, 28)}`, state);
    this.routeState.apiLabel = label;
    this.routeState.apiState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteTrial(label, state = "pending") {
    setBadge(UI.routeTrial, `変身試験: ${compactToken(label, 30)}`, state);
    this.routeState.trialLabel = label;
    this.routeState.trialState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteReplay(label, state = "pending") {
    setBadge(UI.routeReplay, `記録保管: ${compactToken(label, 20)} | 動き ${this.replayMotionDiagnostic.token}`, state);
    this.routeState.replayLabel = label;
    this.routeState.replayState = state;
    this.syncSpatialRouteStatus();
  }

  computeReplayMotionDiagnostic({ viewMode = this.xrViewMode, playbackSource = this.playbackSource } = {}) {
    const livePoseFrames = this.archiveMotionFrames.length;
    const bodySimFrames = this.frames.length;
    if (playbackSource !== "archive") {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_CAPTURE, livePoseFrames, bodySimFrames);
    }
    if (viewMode === XR_VIEW_MODE_SELF) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_SELF, livePoseFrames, bodySimFrames);
    }
    if (livePoseFrames && bodySimFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_MIXED, livePoseFrames, bodySimFrames);
    }
    if (livePoseFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_LIVE_POSE, livePoseFrames, bodySimFrames);
    }
    if (bodySimFrames) {
      return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_BODY_SIM, livePoseFrames, bodySimFrames);
    }
    return makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC, livePoseFrames, bodySimFrames);
  }

  setReplayMotionDiagnostic(diagnostic) {
    this.replayMotionDiagnostic = diagnostic || makeReplayMotionDiagnostic(REPLAY_MOTION_SOURCE_STATIC);
    if (UI.routeReplay && this.routeState) {
      setBadge(
        UI.routeReplay,
        `記録保管: ${compactToken(this.routeState.replayLabel || "WAIT", 20)} | 動き ${this.replayMotionDiagnostic.token}`,
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
    const mode = useNewRouteApi() ? "NEW" : "LOCAL";
    const api = compactToken(this.routeState.apiLabel || "OFF", 18);
    const trial = compactToken(this.trialId || this.routeState.trialLabel || "WAIT", 20);
    const replaySource =
      this.routeState.replayState === "ok"
        ? this.routeState.replayLabel
        : this.trialReplayPath || this.routeState.replayLabel || "WAIT";
    const replay = compactToken(replaySource, 18);
    const motion = compactToken(this.replayMotionDiagnostic?.token || "WAIT", 12);
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
      const replay = await getJson(`/v1/trials/${this.trialId}/replay`);
      this.trialReplayPath = replay.replay_path || null;
      const motionFrames = motionFramesFromReplayScript(replay.replay);
      this.setArchiveMotionFrames(motionFrames);
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
    this.suitspec = await this.loadInitialSuitSpec();
    await this.loadArmorMeshes();
    const replay = await loadReplay();
    await this.applyReplay(replay, { speak: false, autoplay: false });
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
      ? "immersive-vr利用可能。Quest BrowserからVR開始できます。"
      : "このブラウザではimmersive-vrを利用できません。";
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
        UI.status.textContent = `VR session could not start: ${error?.message || error}`;
      });
    }
  }

  async loadArmorMeshes() {
    const modules = this.suitspec?.modules || {};
    this.refreshBaseSuitSurface();
    const loadedMeshes = await Promise.all(ARMOR_PARTS.map(async (part, index) => {
      const module = modules[part];
      if (!module || module.enabled !== true) return null;
      const mesh = await createArmorMesh(part, module, this.suitspec);
      return { index, mesh, part };
    }));
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
        this.liveMirrorAvatar.add(mirrorMesh);
        this.liveMirrorMeshes.set(record.part, mirrorMesh);
      }
    }
    const fallbackText =
      this.suitspec?.texture_fallback?.mode === "palette_material"
        ? "Palette fallback armed for missing runtime textures."
        : "No texture fallback contract.";
    setRouteContract(UI.routeContract, this.suitspec);
    UI.micState.textContent = `Loaded ${this.meshes.size} mesh assets. FIT ${formatFitContract(this.suitspec)}. TEX ${formatTextureFallback(this.suitspec)}. ${fallbackText}`;
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
    const material = createBaseSuitMaterial(this.suitspec);
    for (const [, shape, position, scale, rotation] of BASE_SUIT_SURFACE_PARTS) {
      const geometry = shape === "sphere"
        ? new THREE.SphereGeometry(1, 32, 18)
        : new THREE.CapsuleGeometry(1, 1, 8, 24);
      const mesh = new THREE.Mesh(geometry, material.clone());
      mesh.position.fromArray(position);
      mesh.scale.fromArray(scale);
      mesh.rotation.set(rotation[0], rotation[1], rotation[2]);
      mesh.renderOrder = 2;
      this.baseSuitGroup.add(mesh);
    }
    material.dispose?.();
    this.baseSuitGroup.visible = this.meshes.size > 0 || Object.values(this.suitspec?.modules || {}).some((module) => module?.enabled);
  }

  updateBaseSuitVisibility({ standbyPreview, selfView, reveal }) {
    if (!this.baseSuitGroup) return;
    const hasSuit = this.meshes.size > 0;
    this.baseSuitGroup.visible = hasSuit && (standbyPreview || this.playing);
    const opacity = standbyPreview ? 0.46 : lerp(0.16, 0.42, reveal);
    for (const mesh of this.baseSuitGroup.children) {
      mesh.visible = this.baseSuitGroup.visible && !(selfView && !standbyPreview && mesh.position.y > -0.22);
      mesh.material.opacity = opacity;
      mesh.material.emissiveIntensity = this.world.session ? 0.22 : 0.14;
    }
  }

  async applyReplay(replay, { speak, autoplay = true, viewMode = XR_VIEW_MODE_SELF, source = "voice" }) {
    this.replay = replay;
    const replayScript = Array.isArray(replay?.replay?.timeline) ? replay.replay : replay;
    const replayMotionFrames = motionFramesFromReplayScript(replayScript);
    this.setArchiveMotionFrames(replayMotionFrames);
    if (replayMotionFrames.length && Number.isFinite(Number(replayScript?.duration_sec))) {
      this.duration = clamp(Number(replayScript.duration_sec), 0.8, 12);
    }
    this.frames = replay?.deposition?.body_sim_path
      ? await this.loadBodySim(replay.deposition.body_sim_path)
      : [];
    this.refreshReplayMotionDiagnostic({
      playbackSource: autoplay ? source : "archive",
      viewMode: autoplay ? viewMode : this.archiveViewMode,
    });
    UI.sessionId.textContent = replay.session_id || "SESSION";
    UI.triggerState.textContent = replay.trigger?.detected ? `音声: ${replay.trigger.phrase || TRIGGER_PHRASE}` : "音声: 待機";
    UI.equipState.textContent = autoplay && replay.deposition?.completed ? "変身: 完了" : "変身: 待機";
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
    const bodySim = await loadJson(rawPath);
    return Array.isArray(bodySim.frames) ? bodySim.frames : [];
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
    this.lastLiveMotionSampleAt = -Infinity;
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
    this.updateVoiceDebug("VOICE DEBUG\nresult: reset\ntrigger: 生成");
    this.updateVoiceDebug(`VOICE DEBUG\nresult: reset\ntrigger: ${TRIGGER_PHRASE}`);
  }

  replayFromStart({ speak, audio = speak, viewMode = XR_VIEW_MODE_SELF, source = "voice" }) {
    if (audio) this.audioBed.start();
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
    if (!this.canRunVoiceCommand()) return;
    this.audioBed.start();
    UI.btnVoice.disabled = true;
    try {
      const seconds = getVoiceSeconds();
      const armDelay = getVoiceArmDelay();
      const useMic = useMicrophoneCapture();
      const mode = useMic ? getAudioMode().toUpperCase() : "MOCK";
      UI.status.textContent = useMic
        ? `Preparing microphone. Wait for SPEAK NOW, then say ${TRIGGER_PHRASE}.`
        : `Mock voice trigger is running without microphone capture.`;
      this.setVoiceState(
        useMic ? "arming" : "analyzing",
        useMic ? `Mic arming ${armDelay.toFixed(1)}s. Do not speak yet.` : "Mock trigger is preparing replay.",
      );
      this.updateVoiceDebug(`VOICE DEBUG\nresult: ${useMic ? "arming" : "mock"}\ntrigger: ${TRIGGER_PHRASE}\naudio: ${mode}\narmDelay: ${useMic ? `${armDelay.toFixed(1)}s` : "skipped"}`);

      let blob;
      let stats;
      if (useMic) {
        const captured = await recordAudio(seconds, {
          armDelaySec: armDelay,
          onReady: () => {
            UI.status.textContent = `Microphone armed. Wait ${armDelay.toFixed(1)}s for SPEAK NOW.`;
            this.setVoiceState("arming", `Wait ${armDelay.toFixed(1)}s. Speak only after SPEAK NOW.`);
          },
          onStart: () => {
            UI.status.textContent = `Recording ${seconds.toFixed(1)}s ${mode}. Say ${TRIGGER_PHRASE} clearly now.`;
            this.setVoiceState("recording", `SPEAK NOW: ${seconds.toFixed(1)}s capture.`);
            this.updateVoiceDebug(`VOICE DEBUG\nresult: recording\ntrigger: ${TRIGGER_PHRASE}\naudio: ${mode} ${seconds.toFixed(1)}s\narmDelay: ${armDelay.toFixed(1)}s`);
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
          ? `Mock trigger is preparing replay.${statsLine ? ` ${statsLine}` : ""}`
          : `Sakura Whisper is transcribing.${statsLine ? ` ${statsLine}` : ""}`
      );
      this.updateVoiceDebug(`VOICE DEBUG\nresult: captured\ntrigger: ${TRIGGER_PHRASE}\naudio: ${statsLine || mode}\nbytes: ${blob.size}`);
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
      this.setVoiceState("detected", transcript ? `Transcript: ${transcript}` : `${TRIGGER_PHRASE} confirmed.`);
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
      if (UI.voiceDebug && UI.voiceDebug.textContent.startsWith("VOICE DEBUG")) {
        UI.voiceDebug.textContent += `\nerror: ${message}`;
        this.spatialPanel?.setDebug(UI.voiceDebug.textContent);
      } else {
        this.updateVoiceDebug(`VOICE DEBUG\nresult: error\ntrigger: ${TRIGGER_PHRASE}\nerror: ${message}`);
      }
      this.audioBed.pulse(180, 0.22);
    } finally {
      UI.btnVoice.disabled = false;
    }
  }

  canRunVoiceCommand() {
    return !this.playing && !["arming", "recording", "analyzing", "detected", "deposition"].includes(this.voiceState);
  }

  speakExplanation() {
    const text = this.replay?.tts?.text;
    if (!text) return;
    this.audioBed.duck(4.5);
    const audioPath = this.replay?.tts?.audio_path;
    if (audioPath) {
      UI.micState.textContent = "TTS explanation is playing.";
      void this.playTtsAudio(audioPath, text);
      return;
    }
    UI.micState.textContent = `TTS audio unavailable (${this.replay?.tts?.status || "no_audio"}).`;
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
      UI.micState.textContent = "TTS audio playback failed. Falling back to browser speech.";
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

  captureWorldAnchor(viewMode = this.xrViewMode) {
    if (!this.world.session) return;
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
      this.xrWorldAnchorPosition.add(forward.multiplyScalar(VR_REPLAY_OBSERVER_DISTANCE));
      this.xrWorldAnchorPosition.y = this.cameraPosition.y + VR_REPLAY_OBSERVER_HEIGHT_OFFSET;
      this.xrWorldAnchorScale.copy(this.observerScale);
      rigYaw = yaw + Math.PI * 0.82;
    } else {
      this.xrWorldAnchorPosition.y = this.cameraPosition.y;
      this.xrWorldAnchorScale.copy(this.selfScale);
    }

    this.xrWorldAnchorQuaternion.setFromEuler(new THREE.Euler(0, rigYaw, 0, "YXZ"));
    this.xrWorldAnchorMode = viewMode;
    this.xrWorldAnchorReady = true;
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
    controller.getWorldPosition(target);
    const distance = target.distanceTo(this.cameraPosition);
    if (distance < 0.08 || distance > 2.2) return false;
    this.rig.worldToLocal(target);
    return true;
  }

  getEstimatedHandPosition(hand, target) {
    const side = hand === "left" ? -1 : 1;
    const tracked = hand === "left" ? this.leftHandTracked : this.rightHandTracked;
    const source = hand === "left" ? this.liveLeftHandPosition : this.liveRightHandPosition;
    if (tracked) {
      target.copy(source);
      return target;
    }
    return this.setLiveBodyOffset(target, side * 0.46, -0.92, -0.34);
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
    if (part === "helmet") return this.setLiveBodyOffset(target, 0, -0.08, -0.02);
    if (part === "chest") return this.setLiveBodyOffset(target, 0, -0.48, -0.08);
    if (part === "back") return this.setLiveBodyOffset(target, 0, -0.48, 0.12);
    if (part === "waist") return this.setLiveBodyOffset(target, 0, -0.84, -0.02);
    if (part === "left_thigh" || part === "right_thigh") return this.setLiveBodyOffset(target, side * 0.16, -1.08, -0.06);
    if (part === "left_shin" || part === "right_shin") return this.setLiveBodyOffset(target, side * 0.18, -1.4, -0.08);
    if (part === "left_boot" || part === "right_boot") return this.setLiveBodyOffset(target, side * 0.18, -1.66, -0.12);

    const hand = side < 0 ? "left" : "right";
    const shoulder = this.setLiveBodyOffset(this.livePartPositionB, side * 0.32, -0.43, -0.08);
    const handPosition = this.getEstimatedHandPosition(hand, this.livePartPositionC);
    if (part.endsWith("_shoulder")) return target.copy(shoulder);
    if (part.endsWith("_upperarm")) return target.lerpVectors(shoulder, handPosition, 0.36);
    if (part.endsWith("_forearm")) return target.lerpVectors(shoulder, handPosition, 0.72);
    if (part.endsWith("_hand")) return target.copy(handPosition);

    const fallback = VR_BODY_PART_POSES[part];
    if (fallback) return target.fromArray(fallback);
    return this.setLiveBodyOffset(target, 0, -0.5, 0);
  }

  applyLiveSuitPose(mesh, part, reveal) {
    this.getLiveBodyPartPosition(part, this.livePartPosition);
    mesh.position.copy(this.livePartPosition);
    mesh.rotation.set(Math.PI / 2, 0, this.liveTorsoYaw);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const emerge = lerp(0.08, 1, reveal);
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
  }

  applyStandbySuitPose(mesh, part) {
    const pose = VR_BODY_PART_POSES[part] || [0, -0.5, -0.28];
    mesh.position.fromArray(pose);
    mesh.rotation.set(Math.PI / 2, 0, 0);
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * vrScale, sy * vrScale, sz * vrScale);
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
    const side = hand === "left" ? -1 : 1;
    const tracked = hand === "left" ? frame.left_hand_tracked : frame.right_hand_tracked;
    const source = hand === "left" ? frame.left_hand : frame.right_hand;
    if (tracked && Array.isArray(source)) {
      target.fromArray(source);
      return target;
    }
    return this.setMotionBodyOffset(frame, target, side * 0.46, -0.92, -0.34);
  }

  getMotionBodyPartPosition(part, frame, target) {
    const side = part.startsWith("left_") ? -1 : part.startsWith("right_") ? 1 : 0;
    if (part === "helmet") return this.setMotionBodyOffset(frame, target, 0, -0.08, -0.02);
    if (part === "chest") return this.setMotionBodyOffset(frame, target, 0, -0.48, -0.08);
    if (part === "back") return this.setMotionBodyOffset(frame, target, 0, -0.48, 0.12);
    if (part === "waist") return this.setMotionBodyOffset(frame, target, 0, -0.84, -0.02);
    if (part === "left_thigh" || part === "right_thigh") return this.setMotionBodyOffset(frame, target, side * 0.16, -1.08, -0.06);
    if (part === "left_shin" || part === "right_shin") return this.setMotionBodyOffset(frame, target, side * 0.18, -1.4, -0.08);
    if (part === "left_boot" || part === "right_boot") return this.setMotionBodyOffset(frame, target, side * 0.18, -1.66, -0.12);

    const hand = side < 0 ? "left" : "right";
    const shoulder = this.setMotionBodyOffset(frame, this.motionPartPositionB, side * 0.32, -0.43, -0.08);
    const handPosition = this.getMotionHandPosition(frame, hand, this.motionPartPositionC);
    if (part.endsWith("_shoulder")) return target.copy(shoulder);
    if (part.endsWith("_upperarm")) return target.lerpVectors(shoulder, handPosition, 0.36);
    if (part.endsWith("_forearm")) return target.lerpVectors(shoulder, handPosition, 0.72);
    if (part.endsWith("_hand")) return target.copy(handPosition);

    const fallback = VR_BODY_PART_POSES[part];
    if (fallback) return target.fromArray(fallback);
    return this.setMotionBodyOffset(frame, target, 0, -0.5, 0);
  }

  applyMotionSuitPose(mesh, part, frame, reveal) {
    this.getMotionBodyPartPosition(part, frame, this.motionPartPosition);
    mesh.position.copy(this.motionPartPosition);
    mesh.rotation.set(Math.PI / 2, 0, Number(frame.torso_yaw || 0));
    const fit = mesh.userData.module?.fit || {};
    const minScale = Array.isArray(fit.minScale) ? fit.minScale : [0.16, 0.16, 0.16];
    const fitScale = Array.isArray(fit.scale) ? fit.scale : [0.2, 0.48, 0.2];
    const sx = Math.max(Number(fitScale[0] || 0.18) * 4.8, Number(minScale[0] || 0.1));
    const sy = Math.max(Number(fitScale[1] || 0.44) * 3.0, Number(minScale[1] || 0.1));
    const sz = Math.max(Number(fitScale[2] || 0.18) * 4.8, Number(minScale[2] || 0.1));
    const emerge = lerp(0.08, 1, reveal);
    const vrScale = VR_PART_SCALE[part] || 0.28;
    mesh.scale.set(sx * emerge * vrScale, sy * emerge * vrScale, sz * emerge * vrScale);
  }

  updateLiveMirrorAvatar(progress, reveal) {
    if (!this.liveMirror) return;
    const wasVisible = this.liveMirror.visible;
    const visible =
      Boolean(this.world.session)
      && this.xrViewMode === XR_VIEW_MODE_SELF
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
      this.applyLiveSuitPose(mesh, part, reveal);
      const stagger = clamp((progress * ARMOR_PARTS.length - order) / 3.2, 0, 1);
      mesh.material.opacity = 0.08 + easeOutCubic(stagger) * 0.86;
      mesh.material.emissiveIntensity = this.world.session ? 0.35 + stagger * 0.75 : 0.18;
      mesh.visible = mesh.material.opacity > 0.09;
      order += 1;
    }
  }

  updateRigAnchor() {
    if (!this.world.session) {
      this.rig.position.lerp(NON_VR_RIG_POSITION, 0.16);
      this.rig.scale.lerp(this.nonVrScale, 0.16);
      this.rigTargetQuaternion.identity();
      this.rig.quaternion.slerp(this.rigTargetQuaternion, 0.16);
      return;
    }

    if (!this.xrWorldAnchorReady || this.xrWorldAnchorMode !== this.xrViewMode) {
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
    const replayMotionFrame = this.currentReplayMotionFrame(this.elapsed);

    UI.meterFill.style.width = `${Math.round(progress * 100)}%`;

    let order = 0;
    const inXr = Boolean(this.world.session);
    const selfView = inXr && this.xrViewMode === XR_VIEW_MODE_SELF;
    const useLiveSuit = selfView && this.xrWorldAnchorReady;
    const hasRuntimePose = useLiveSuit || Object.keys(segments).length > 0 || Boolean(replayMotionFrame);
    const standbyPreview = this.meshes.size > 0 && (!this.playing || !hasRuntimePose);
    if (useLiveSuit) {
      this.updateLiveBodyAnchors();
      this.captureLiveMotionSample(progress);
    }
    this.updateBaseSuitVisibility({ standbyPreview, selfView, reveal });
    if (this.mirrorFrame) {
      this.mirrorFrame.visible = inXr && this.xrViewMode === XR_VIEW_MODE_MIRROR;
    }
    for (const [part, mesh] of this.meshes.entries()) {
      const segmentName = PART_TO_SEGMENT[part] || part;
      const pose = segments[segmentName];
      const useReplayMotion = !pose && replayMotionFrame;
      const hiddenForSelf =
        selfView
        && (standbyPreview ? SELF_VIEW_STANDBY_HIDDEN_PARTS : SELF_VIEW_HIDDEN_PARTS).has(part);
      if (hiddenForSelf) {
        mesh.visible = false;
        order += 1;
        continue;
      }
      if (standbyPreview) {
        this.applyStandbySuitPose(mesh, part);
      } else if (!useLiveSuit && !pose && !useReplayMotion) {
        mesh.visible = false;
        order += 1;
        continue;
      } else if (useLiveSuit) {
        this.applyLiveSuitPose(mesh, part, reveal);
      } else if (useReplayMotion) {
        this.applyMotionSuitPose(mesh, part, replayMotionFrame, reveal);
      } else {
        applySegmentPose(mesh, pose, part, reveal, {
          centered: selfView,
          progress,
          finalPosition: this.finalPosition,
          stagePosition: this.stagePosition,
        });
      }
      const stagger = standbyPreview ? 1 : clamp((progress * ARMOR_PARTS.length - order) / 3.2, 0, 1);
      mesh.material.opacity = standbyPreview ? 0.82 : 0.08 + easeOutCubic(stagger) * 0.86;
      mesh.material.emissiveIntensity = this.world.session ? 0.35 + stagger * 0.75 : 0.18;
      mesh.visible = standbyPreview || mesh.material.opacity > 0.09;
      order += 1;
    }
    this.updateLiveMirrorAvatar(progress, reveal);

    for (let i = 0; i < this.rings.length; i += 1) {
      const ring = this.rings[i];
      const ringProgress = (progress + i * 0.17) % 1;
      const scale = 0.38 + ringProgress * 1.75;
      ring.scale.setScalar(scale);
      ring.position.y = lerp(-1.15, 0.92, ringProgress);
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

QuestHenshinDemo.create()
  .then((demo) => demo.start())
  .catch((error) => {
    console.error(error);
    UI.status.textContent = String(error?.message || error);
  });
