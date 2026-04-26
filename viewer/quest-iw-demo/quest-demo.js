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
  sessionId: document.getElementById("sessionId"),
  triggerState: document.getElementById("triggerState"),
  equipState: document.getElementById("equipState"),
};

const textureLoader = new THREE.TextureLoader();
const geometryCache = new Map();
const textureCache = new Map();
const TAU = Math.PI * 2;
const VR_REPLAY_OBSERVER_DISTANCE = 2.15;
const VR_REPLAY_OBSERVER_HEIGHT_OFFSET = -0.06;
const VR_REPLAY_OBSERVER_SCALE = 0.88;
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
    label: "VOICE READY",
    hint: `Point here, pull trigger, then say ${TRIGGER_PHRASE}.`,
    color: 0x43d8ff,
  },
  arming: {
    label: "MIC ARMING",
    hint: "Wait for SPEAK NOW before talking.",
    color: 0x8edfff,
  },
  recording: {
    label: "SPEAK NOW",
    hint: `Say ${TRIGGER_PHRASE} clearly.`,
    color: 0xffcf5a,
  },
  analyzing: {
    label: "ANALYZING",
    hint: "Whisper is checking the command.",
    color: 0x8edfff,
  },
  detected: {
    label: `${TRIGGER_PHRASE} DETECTED`,
    hint: "Armor deposition is starting.",
    color: 0xfff4c8,
  },
  deposition: {
    label: "DEPOSITION",
    hint: "Armor is forming around you.",
    color: 0xffcf5a,
  },
  complete: {
    label: "ARMOR ONLINE",
    hint: "Replay remains available.",
    color: 0xf6f1df,
  },
  rejected: {
    label: "RETRY VOICE",
    hint: `I could not confirm ${TRIGGER_PHRASE}.`,
    color: 0xff6b6b,
  },
};

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
  return params().get("newRoute") === "1";
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
  ctx.font = `${fontWeight} ${fontSize}px system-ui, sans-serif`;
  ctx.fillStyle = color;
  ctx.textAlign = align;
  ctx.textBaseline = baseline;
  ctx.shadowColor = "rgba(255, 207, 90, 0.65)";
  ctx.shadowBlur = 10;
  const x = align === "left" ? paddingX : canvas.width / 2;
  if (maxLines <= 1) {
    ctx.fillText(text, x, canvas.height / 2);
    return;
  }

  const maxWidth = canvas.width - paddingX * 2;
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
    this.forward = new THREE.Vector3();
    this.controllers = [];
    this.buttons = [];
    this.hovered = null;
    this.pulseClock = 0;

    this.buildPanel();
    this.initControllers();
    this.demo.scene.add(this.group);
  }

  buildPanel() {
    const panel = new THREE.Mesh(
      new THREE.PlaneGeometry(1.22, 1.68),
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

    this.status = makeTextPlane("VOICE READY", {
      width: 1.02,
      height: 0.12,
      fontSize: 68,
      color: "#fff4c8",
      background: "rgba(10, 26, 32, 0.82)",
      border: "rgba(255, 207, 90, 0.72)",
    });
    this.status.position.set(0, 0.5, 0.012);
    this.group.add(this.status);

    this.hint = makeTextPlane(`Trigger: ${TRIGGER_PHRASE}`, {
      width: 1.02,
      height: 0.12,
      canvasHeight: 220,
      fontSize: 34,
      color: "#d7f8ff",
      background: "rgba(4, 13, 17, 0.58)",
      maxLines: 2,
    });
    this.hint.position.set(0, 0.35, 0.014);
    this.group.add(this.hint);

    this.progressBack = new THREE.Mesh(
      new THREE.PlaneGeometry(0.74, 0.025),
      new THREE.MeshBasicMaterial({ color: 0x223139, transparent: true, opacity: 0.8, depthTest: false }),
    );
    this.progressBack.position.set(0, 0.24, 0.014);
    this.progressBack.renderOrder = 12;
    this.group.add(this.progressBack);

    this.progressFill = new THREE.Mesh(
      new THREE.PlaneGeometry(0.74, 0.025),
      new THREE.MeshBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.95, depthTest: false }),
    );
    this.progressFill.position.set(-0.37, 0.24, 0.016);
    this.progressFill.scale.x = 0.001;
    this.progressFill.geometry.translate(0.37, 0, 0);
    this.progressFill.renderOrder = 13;
    this.group.add(this.progressFill);

    this.routeStatus = makeTextPlane("FORGE LOCAL | TRIAL WAIT | ARCHIVE WAIT", {
      width: 1.02,
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
    this.routeStatus.position.set(0, 0.16, 0.017);
    this.group.add(this.routeStatus);

    this.debug = makeTextPlane("Voice debug: waiting.", {
      width: 1.02,
      height: 0.18,
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
    this.debug.position.set(0, 0.005, 0.018);
    this.group.add(this.debug);

    this.listenRing = new THREE.Mesh(
      new THREE.RingGeometry(0.17, 0.185, 64),
      new THREE.MeshBasicMaterial({ color: 0x43d8ff, transparent: true, opacity: 0.8, side: THREE.DoubleSide, depthTest: false }),
    );
    this.listenRing.position.set(-0.36, -0.285, 0.019);
    this.listenRing.renderOrder = 15;
    this.group.add(this.listenRing);

    this.addButton("voice", "VOICE", -0.26, 0xffcf5a);
    this.addButton("replay", "ARCHIVE", -0.43, 0x43d8ff);
    this.addButton("pause", "PAUSE", -0.6, 0xf6f1df);
    this.addButton("reset", "RESET", -0.77, 0xff6b6b);
  }

  addButton(action, label, y, color) {
    const button = new THREE.Group();
    button.name = `XR-Button-${action}`;
    button.position.set(0.08, y, 0.025);

    const hit = new THREE.Mesh(
      new THREE.PlaneGeometry(0.58, 0.115),
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
      width: 0.5,
      height: 0.08,
      fontSize: 56,
      color: "#eef9ff",
      background: null,
    });
    text.position.z = 0.01;
    button.add(text);

    this.group.add(button);
    this.buttons.push({ action, group: button, hit, text });
  }

  initControllers() {
    for (let index = 0; index < 2; index += 1) {
      const controller = this.demo.renderer.xr.getController(index);
      controller.addEventListener("selectstart", () => this.activateHovered());
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)]),
        new THREE.LineBasicMaterial({ color: 0xffcf5a, transparent: true, opacity: 0.55 }),
      );
      line.name = "XR-Menu-Ray";
      line.scale.z = 1.4;
      controller.add(line);
      this.demo.scene.add(controller);
      this.controllers.push(controller);
    }
  }

  setDebug(text) {
    if (!this.debug) return;
    updateTextPlane(this.debug, text || "Voice debug: waiting.", {
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
    updateTextPlane(this.routeStatus, text || "FORGE LOCAL | TRIAL WAIT | ARCHIVE WAIT", {
      color,
      border,
      maxLines: 1,
    });
  }

  setVoiceState(state, detail = "") {
    const voiceState = VOICE_STATES[state] || VOICE_STATES.ready;
    updateTextPlane(this.status, voiceState.label, {
      color: state === "rejected" ? "#ffd2d2" : "#fff4c8",
      border: state === "rejected" ? "rgba(255, 107, 107, 0.78)" : "rgba(255, 207, 90, 0.72)",
    });
    updateTextPlane(this.hint, detail || voiceState.hint, {
      color: state === "rejected" ? "#ffd2d2" : "#d7f8ff",
    });
    this.listenRing.material.color.setHex(voiceState.color);
    for (const button of this.buttons) {
      if (button.action === "pause") {
        updateTextPlane(button.text, this.demo.playing ? "PAUSE" : "RESUME");
      }
    }
  }

  setProgress(progress) {
    this.progressFill.scale.x = Math.max(0.001, clamp(progress, 0, 1));
  }

  update(dt) {
    const inVR = Boolean(this.demo.world.session);
    this.group.visible = inVR;
    for (const controller of this.controllers) {
      controller.visible = inVR;
      const ray = controller.getObjectByName("XR-Menu-Ray");
      if (ray) ray.visible = inVR;
    }
    if (!inVR) return;

    const xrCamera = this.demo.renderer.xr.getCamera(this.demo.camera) || this.demo.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    xrCamera.getWorldQuaternion(this.cameraQuaternion);
    this.forward.set(0, 0, -1).applyQuaternion(this.cameraQuaternion).normalize();
    this.group.position.copy(this.cameraPosition).add(this.forward.multiplyScalar(1.18));
    this.group.position.y -= 0.42;
    this.group.quaternion.copy(this.cameraQuaternion);

    this.pulseClock += dt;
    const pulse = 1 + Math.sin(this.pulseClock * 5.8) * 0.08;
    this.listenRing.scale.setScalar(pulse);
    this.listenRing.material.opacity = this.demo.voiceState === "recording" ? 0.95 : 0.45 + Math.sin(this.pulseClock * 3.0) * 0.18;

    this.updateHover();
  }

  updateHover() {
    let nextHover = null;
    for (const controller of this.controllers) {
      this.tempMatrix.identity().extractRotation(controller.matrixWorld);
      this.raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
      this.raycaster.ray.direction.set(0, 0, -1).applyMatrix4(this.tempMatrix);
      const intersections = this.raycaster.intersectObjects(this.buttons.map((button) => button.hit), false);
      if (intersections.length) {
        nextHover = intersections[0].object;
        break;
      }
    }
    if (nextHover === this.hovered) return;
    for (const button of this.buttons) {
      const hovered = button.hit === nextHover;
      button.hit.material.color.setHex(hovered ? button.hit.userData.hoverColor : button.hit.userData.baseColor);
      button.group.scale.setScalar(hovered ? 1.045 : 1);
    }
    this.hovered = nextHover;
  }

  activateHovered() {
    if (!this.group.visible || !this.hovered) return;
    this.demo.audioBed.pulse(820, 0.08);
    const action = this.hovered.userData.action;
    if (action === "voice") void this.demo.runVoiceCommand();
    if (action === "replay") this.demo.replayFromStart({ speak: true });
    if (action === "pause") this.demo.togglePause();
    if (action === "reset") this.demo.reset();
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
    this.meshes = new Map();
    this.voiceState = "ready";
    this.trialId = null;
    this.trialReady = false;
    this.trialReplayPath = null;
    this.depositionStartPromise = null;
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
    this.rigTargetEuler = new THREE.Euler(0, 0, 0, "YXZ");
    this.nonVrScale = new THREE.Vector3(0.68, 0.68, 0.68);
    this.observerScale = new THREE.Vector3(
      VR_REPLAY_OBSERVER_SCALE,
      VR_REPLAY_OBSERVER_SCALE,
      VR_REPLAY_OBSERVER_SCALE,
    );
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
    this.setVoiceState("ready");
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

    const title = makeTextSprite(TRIGGER_PHRASE);
    title.position.set(0, 1.18, -0.3);
    this.rig.add(title);
    this.titleSprite = title;

    this.renderer.xr.addEventListener("sessionstart", () => {
      this.audioBed.start();
      UI.status.textContent = "IWSDK immersive-vr session started. Archive replay uses a third-person observer view.";
      UI.btnEnterVR.textContent = "Exit VR";
      this.setVoiceState(this.voiceState, "Observer replay active. Live body attachment is still under fit audit.");
    });
    this.renderer.xr.addEventListener("sessionend", () => {
      UI.status.textContent = "VR session ended. Enter VR to return to immersive mode.";
      UI.btnEnterVR.textContent = "Enter VR";
    });
  }

  bind() {
    UI.btnEnterVR.onclick = () => this.toggleVR();
    UI.btnVoice.onclick = () => this.runVoiceCommand();
    UI.btnReplay.onclick = () => this.replayFromStart({ speak: true });
    UI.btnPause.onclick = () => this.togglePause();
    UI.btnReset.onclick = () => this.reset();
  }

  setVoiceState(state, detail = "", options = {}) {
    this.voiceState = state;
    const voiceState = VOICE_STATES[state] || VOICE_STATES.ready;
    UI.triggerState.textContent = `VOICE: ${voiceState.label}`;
    UI.micState.textContent = detail || voiceState.hint;
    if (options.status) UI.status.textContent = options.status;
    this.spatialPanel?.setVoiceState(state, detail);
  }

  updateVoiceDebug(text) {
    const value = text || "Voice debug: waiting.";
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
    setBadge(UI.routeMode, newRoute ? "SUIT FORGE: NEW" : "SUIT FORGE: LOCAL", newRoute ? "ok" : "idle");
    setBadge(UI.routeApi, newRoute ? "FIT AUDIT: /v1 ARMED" : "FIT AUDIT: OFF", newRoute ? "pending" : "idle");
    setBadge(
      UI.routeTrial,
      this.trialId ? `HENSHIN TRIAL: ${compactToken(this.trialId)}` : "HENSHIN TRIAL: WAIT",
      this.trialId ? "ok" : "pending",
    );
    setBadge(
      UI.routeReplay,
      this.trialReplayPath ? `REPLAY ARCHIVE: ${compactToken(this.trialReplayPath)}` : "REPLAY ARCHIVE: WAIT",
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
    setBadge(UI.routeApi, `FIT AUDIT: ${compactToken(label, 28)}`, state);
    this.routeState.apiLabel = label;
    this.routeState.apiState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteTrial(label, state = "pending") {
    setBadge(UI.routeTrial, `HENSHIN TRIAL: ${compactToken(label, 30)}`, state);
    this.routeState.trialLabel = label;
    this.routeState.trialState = state;
    this.syncSpatialRouteStatus();
  }

  setRouteReplay(label, state = "pending") {
    setBadge(UI.routeReplay, `REPLAY ARCHIVE: ${compactToken(label, 30)}`, state);
    this.routeState.replayLabel = label;
    this.routeState.replayState = state;
    this.syncSpatialRouteStatus();
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
    const state =
      this.routeState.apiState === "error" || this.routeState.replayState === "error"
        ? "error"
        : this.routeState.replayState === "ok"
          ? "ok"
          : "pending";
    this.spatialPanel?.setRouteStatus(`FORGE ${mode} | FIT ${api} | TRIAL ${trial} | ARCHIVE ${replay}`, state);
  }

  async ensureTrial() {
    if (!useNewRouteApi()) return null;
    if (this.trialReady && this.trialId) {
      this.setRouteTrial(this.trialId, "ok");
      return this.trialId;
    }
    this.trialId = this.trialId || makeTrialId();
    const suitId = getSuitId();
    const manifestId = getManifestId();
    this.setRouteApi("SUIT POST", "pending");
    this.setRouteTrial(this.trialId, "pending");
    await postJson("/v1/suits", {
      suitspec: this.suitspec,
      overwrite: true,
    });
    this.setRouteApi("MANIFEST", "pending");
    await postJson(`/v1/suits/${suitId}/manifest`, {
      manifest_id: manifestId,
      status: "READY",
    });
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

  async generateTrialReplay() {
    if (!useNewRouteApi() || !this.trialId) return null;
    try {
      this.setRouteReplay("BUILDING", "pending");
      const replay = await getJson(`/v1/trials/${this.trialId}/replay`);
      this.trialReplayPath = replay.replay_path || null;
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
    UI.btnPause.textContent = this.playing ? "Pause" : "Resume";
    this.spatialPanel?.setVoiceState(this.voiceState);
  }

  async start() {
    await this.updateVRAvailability();
    this.suitspec = await loadSuitSpec();
    await this.loadArmorMeshes();
    const replay = await loadReplay();
    await this.applyReplay(replay, { speak: false, autoplay: false });
    this.startRenderLoop();
  }

  async updateVRAvailability() {
    if (!navigator.xr?.isSessionSupported) {
      UI.micState.textContent = "WebXR is not exposed. Use Quest Browser or IWSDK Vite emulator.";
      return;
    }
    const supported = await navigator.xr.isSessionSupported(SessionMode.ImmersiveVR).catch(() => false);
    UI.btnEnterVR.disabled = !supported;
    UI.micState.textContent = supported
      ? "IWSDK immersive-vr is available. Enter VR from Quest Browser."
      : "immersive-vr is not available in this browser context.";
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
    const loadedMeshes = await Promise.all(ARMOR_PARTS.map(async (part, index) => {
      const module = modules[part] || {};
      if (module.enabled === false) return null;
      const mesh = await createArmorMesh(part, module, this.suitspec);
      return { index, mesh, part };
    }));
    for (const record of loadedMeshes) {
      if (!record) continue;
      record.mesh.userData.partIndex = record.index;
      this.rig.add(record.mesh);
      this.meshes.set(record.part, record.mesh);
    }
    const fallbackText =
      this.suitspec?.texture_fallback?.mode === "palette_material"
        ? "Palette fallback armed for missing runtime textures."
        : "No texture fallback contract.";
    setRouteContract(UI.routeContract, this.suitspec);
    UI.micState.textContent = `Loaded ${this.meshes.size} mesh assets. FIT ${formatFitContract(this.suitspec)}. TEX ${formatTextureFallback(this.suitspec)}. ${fallbackText}`;
  }

  async applyReplay(replay, { speak, autoplay = true }) {
    this.replay = replay;
    this.frames = replay?.deposition?.body_sim_path
      ? await this.loadBodySim(replay.deposition.body_sim_path)
      : [];
    UI.sessionId.textContent = replay.session_id || "SESSION";
    UI.triggerState.textContent = replay.trigger?.detected ? `VOICE: ${replay.trigger.phrase || TRIGGER_PHRASE}` : "VOICE: WAIT";
    UI.equipState.textContent = autoplay && replay.deposition?.completed ? "DEPOSITION: COMPLETE" : "DEPOSITION: READY";
    UI.voiceLine.textContent = replay.tts?.text || "";
    if (autoplay) {
      this.replayFromStart({ speak });
    } else {
      this.elapsed = 0;
      this.playing = false;
      UI.btnPause.textContent = "Resume";
      this.setVoiceState("ready", "Whisper trigger required. Say 生成 after pressing Voice.");
      this.setVoiceState("ready", `Whisper trigger required. Say ${TRIGGER_PHRASE} after pressing Voice.`);
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
    UI.btnPause.textContent = "Resume";
    UI.equipState.textContent = "DEPOSITION: READY";
    UI.meterFill.style.width = "0%";
    UI.status.textContent = "Reset. Use Archive or Voice to run the third-person deposition replay again.";
    this.setVoiceState("ready");
    this.syncRoutePanel();
    this.updateVoiceDebug("VOICE DEBUG\nresult: reset\ntrigger: 生成");
    this.updateVoiceDebug(`VOICE DEBUG\nresult: reset\ntrigger: ${TRIGGER_PHRASE}`);
  }

  replayFromStart({ speak, audio = speak }) {
    if (audio) this.audioBed.start();
    this.elapsed = 0;
    this.playing = true;
    this.completionAnnounced = false;
    UI.btnPause.textContent = "Pause";
    UI.status.textContent = `Voice command detected: ${TRIGGER_PHRASE}. Third-person armor deposition replay running.`;
    this.setVoiceState("deposition", "Archive replay is staged in front of you for review.");
    this.depositionStartPromise = this.appendTrialEvent("DEPOSITION_STARTED", {
      stateAfter: "DEPOSITION",
      payload: { source: "quest-iw-demo", trigger_phrase: TRIGGER_PHRASE },
      idempotencyKey: "deposition-started",
    });
    void this.depositionStartPromise;
    if (speak) this.speakExplanation();
  }

  async runVoiceCommand() {
    if (this.voiceState === "arming" || this.voiceState === "recording" || this.voiceState === "analyzing") return;
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
      if (data.replay) await this.applyReplay(data.replay, { speak: Boolean(data.ok), autoplay: true });
    } catch (error) {
      console.error(error);
      const message = String(error?.message || error);
      UI.status.textContent = "Voice rejected. Read the Voice debug panel for transcript and audio details.";
      UI.equipState.textContent = "DEPOSITION: CHECK";
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

  updateRigAnchor() {
    if (!this.world.session) {
      this.rig.position.lerp(NON_VR_RIG_POSITION, 0.16);
      this.rig.scale.lerp(this.nonVrScale, 0.16);
      this.rigTargetQuaternion.identity();
      this.rig.quaternion.slerp(this.rigTargetQuaternion, 0.16);
      return;
    }

    const xrCamera = this.renderer.xr.getCamera(this.camera) || this.camera;
    xrCamera.getWorldPosition(this.cameraPosition);
    xrCamera.getWorldQuaternion(this.cameraQuaternion);
    this.rigTargetEuler.setFromQuaternion(this.cameraQuaternion, "YXZ");
    this.rigTargetQuaternion.setFromEuler(new THREE.Euler(0, this.rigTargetEuler.y, 0, "YXZ"));
    this.xrForward.set(0, 0, -1).applyQuaternion(this.rigTargetQuaternion).normalize();
    this.rigTargetPosition.copy(this.cameraPosition).add(this.xrForward.multiplyScalar(VR_REPLAY_OBSERVER_DISTANCE));
    this.rigTargetPosition.y = this.cameraPosition.y + VR_REPLAY_OBSERVER_HEIGHT_OFFSET;
    this.rig.position.lerp(this.rigTargetPosition, 0.28);
    this.rig.quaternion.slerp(this.rigTargetQuaternion, 0.22);
    this.rig.scale.lerp(this.observerScale, 0.18);
  }

  updateScene(dt) {
    this.updateRigAnchor();

    if (this.playing) {
      this.elapsed = Math.min(this.elapsed + dt, this.duration);
      if (this.elapsed >= this.duration && !this.completionAnnounced) {
        UI.status.textContent = "Armor deposition complete. Replay remains available for review.";
        this.setVoiceState("complete");
        this.audioBed.pulse(1180, 0.18);
        void Promise.resolve(this.depositionStartPromise)
          .then(() =>
            this.appendTrialEvent("DEPOSITION_COMPLETED", {
              stateAfter: "ACTIVE",
              payload: { source: "quest-iw-demo", completed: true },
              idempotencyKey: "deposition-completed",
            }),
          )
          .then(() => this.generateTrialReplay());
        this.completionAnnounced = true;
      }
    }

    const progress = clamp(this.elapsed / this.duration, 0, 1);
    const reveal = easeOutCubic(progress);
    const frame = this.currentFrame(progress) || this.frames.at(-1);
    const segments = frame?.segments || {};

    UI.meterFill.style.width = `${Math.round(progress * 100)}%`;

    let order = 0;
    for (const [part, mesh] of this.meshes.entries()) {
      const segmentName = PART_TO_SEGMENT[part] || part;
      const pose = segments[segmentName];
      if (!pose) {
        mesh.visible = false;
        order += 1;
        continue;
      }
      applySegmentPose(mesh, pose, part, reveal, {
        centered: Boolean(this.world.session),
        progress,
        finalPosition: this.finalPosition,
        stagePosition: this.stagePosition,
      });
      const stagger = clamp((progress * ARMOR_PARTS.length - order) / 3.2, 0, 1);
      mesh.material.opacity = 0.08 + easeOutCubic(stagger) * 0.86;
      mesh.material.emissiveIntensity = this.world.session ? 0.35 + stagger * 0.75 : 0.18;
      mesh.visible = mesh.material.opacity > 0.09;
      order += 1;
    }

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
