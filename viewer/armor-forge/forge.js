import * as THREE from "../body-fit/vendor/three/build/three.module.js";
import { loadVrmScene } from "../body-fit/vrm-loader.js";
import {
  VRM_BONE_ALIASES,
  effectiveFitFor,
  effectiveVrmAnchorFor,
  normalizeBoneName,
} from "../shared/armor-canon.js";
import { applyApproximateVrmTPose } from "../shared/auto-fit-engine.js";

const PARTS = [
  ["helmet", "ヘルメット", true],
  ["chest", "胸部装甲", true],
  ["back", "背面ユニット", true],
  ["waist", "ベルト", true],
  ["left_shoulder", "左肩", true],
  ["right_shoulder", "右肩", true],
  ["left_forearm", "左腕甲", true],
  ["right_forearm", "右腕甲", true],
  ["left_shin", "左すね", true],
  ["right_shin", "右すね", true],
  ["left_boot", "左ブーツ", true],
  ["right_boot", "右ブーツ", true],
  ["left_upperarm", "左上腕", false],
  ["right_upperarm", "右上腕", false],
  ["left_thigh", "左太腿", false],
  ["right_thigh", "右太腿", false],
  ["left_hand", "左手甲", false],
  ["right_hand", "右手甲", false],
];

const DEFAULT_HEIGHT_CM = 170;
const MIN_HEIGHT_CM = 90;
const MAX_HEIGHT_CM = 230;
const DEFAULT_VRM_PATH = "viewer/assets/vrm/default.vrm";
const DEFAULT_QUEST_DEV_PORT = 5173;
const VRM_BONE_ALIAS_INDEX = new Map();
for (const [canonical, aliases] of Object.entries(VRM_BONE_ALIASES)) {
  VRM_BONE_ALIAS_INDEX.set(normalizeBoneName(canonical), canonical);
  for (const alias of aliases) {
    VRM_BONE_ALIAS_INDEX.set(normalizeBoneName(alias), canonical);
  }
}

const PART_POSES = {
  helmet: { p: [0, 1.68, 0.02], s: [0.22, 0.22, 0.22] },
  chest: { p: [0, 1.22, 0.02], s: [0.42, 0.42, 0.42] },
  back: { p: [0, 1.18, -0.16], s: [0.36, 0.36, 0.36] },
  waist: { p: [0, 0.78, 0.02], s: [0.3, 0.3, 0.3] },
  left_shoulder: { p: [-0.43, 1.28, 0], s: [0.26, 0.26, 0.26] },
  right_shoulder: { p: [0.43, 1.28, 0], s: [0.26, 0.26, 0.26] },
  left_upperarm: { p: [-0.66, 1.02, 0], s: [0.24, 0.3, 0.24] },
  right_upperarm: { p: [0.66, 1.02, 0], s: [0.24, 0.3, 0.24] },
  left_forearm: { p: [-0.82, 0.68, 0], s: [0.24, 0.32, 0.24] },
  right_forearm: { p: [0.82, 0.68, 0], s: [0.24, 0.32, 0.24] },
  left_hand: { p: [-0.9, 0.38, 0.02], s: [0.18, 0.18, 0.18] },
  right_hand: { p: [0.9, 0.38, 0.02], s: [0.18, 0.18, 0.18] },
  left_thigh: { p: [-0.18, 0.42, 0], s: [0.25, 0.34, 0.25] },
  right_thigh: { p: [0.18, 0.42, 0], s: [0.25, 0.34, 0.25] },
  left_shin: { p: [-0.18, 0.04, 0], s: [0.25, 0.34, 0.25] },
  right_shin: { p: [0.18, 0.04, 0], s: [0.25, 0.34, 0.25] },
  left_boot: { p: [-0.18, -0.26, 0.06], s: [0.22, 0.22, 0.22] },
  right_boot: { p: [0.18, -0.26, 0.06], s: [0.22, 0.22, 0.22] },
};

const FIT_SHAPE_BASELINES = {
  sphere: [0.24, 0.24, 0.24],
  box: [0.52, 0.5, 0.46],
  cylinder: [0.9, 1.0, 0.9],
};

const UI = {
  form: document.getElementById("forgeForm"),
  button: document.getElementById("forgeButton"),
  partGrid: document.getElementById("partGrid"),
  canvas: document.getElementById("armorCanvas"),
  emptyStand: document.getElementById("emptyStand"),
  recallCode: document.getElementById("recallCode"),
  status: document.getElementById("forgeStatus"),
  questLink: document.getElementById("questLink"),
  questUrl: document.getElementById("questUrl"),
  questUrlHint: document.getElementById("questUrlHint"),
  assetPipeline: document.getElementById("assetPipeline"),
  assetPipelineTitle: document.getElementById("assetPipelineTitle"),
  assetPipelineDetail: document.getElementById("assetPipelineDetail"),
  displayName: document.getElementById("displayName"),
  archetype: document.getElementById("archetype"),
  temperament: document.getElementById("temperament"),
  heightCm: document.getElementById("heightCm"),
  heightRange: document.getElementById("heightRange"),
  heightValue: document.getElementById("heightValue"),
  primaryColor: document.getElementById("primaryColor"),
  secondaryColor: document.getElementById("secondaryColor"),
  emissiveColor: document.getElementById("emissiveColor"),
  brief: document.getElementById("brief"),
};

let runtimeInfo = null;
let runtimeInfoPromise = null;

function normalizePath(path) {
  const raw = String(path || "").replace(/\\/g, "/");
  if (/^(https?:|data:|blob:)/i.test(raw) || raw.startsWith("/")) return raw;
  return `/${raw}`;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `${path} failed with ${response.status}`);
  }
  return data;
}

function isLocalHost(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

async function loadRuntimeInfo() {
  try {
    runtimeInfo = await fetchJson("/api/runtime-info");
  } catch (error) {
    console.warn(`runtime-info unavailable: ${error?.message || error}`);
    runtimeInfo = null;
  }
  return runtimeInfo;
}

async function ensureRuntimeInfo() {
  if (runtimeInfo) return runtimeInfo;
  runtimeInfoPromise ||= loadRuntimeInfo();
  return runtimeInfoPromise;
}

function setStatus(text, state = "pending") {
  UI.status.classList.remove("pending", "complete", "error");
  UI.status.classList.add(state);
  UI.status.textContent = text;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function fitVector(value, fallback) {
  return [0, 1, 2].map((index) => numberOr(Array.isArray(value) ? value[index] : undefined, fallback[index]));
}

function softFitFactor(value, baseline) {
  return clamp(1 + (numberOr(value, baseline) - baseline) * 0.22, 0.82, 1.28);
}

function softFitSize(part, module, size) {
  const fit = effectiveFitFor(part, module);
  const baseline = FIT_SHAPE_BASELINES[String(fit.shape || "box").toLowerCase()] || FIT_SHAPE_BASELINES.box;
  const fitScale = fitVector(fit.scale, baseline);
  return new THREE.Vector3(
    size.x * softFitFactor(fitScale[0], baseline[0]),
    size.y * softFitFactor(fitScale[1], baseline[1]),
    size.z * softFitFactor(fitScale[2], baseline[2]),
  );
}

function midpoint(a, b) {
  if (!a && !b) return null;
  if (!a) return b.clone();
  if (!b) return a.clone();
  return a.clone().add(b).multiplyScalar(0.5);
}

function distanceOr(a, b, fallback) {
  return a && b ? Math.max(a.distanceTo(b), 0.001) : fallback;
}

function addOffset(vector, offset = [0, 0, 0]) {
  const next = vector.clone();
  next.x += numberOr(offset[0], 0);
  next.y += numberOr(offset[1], 0);
  next.z += numberOr(offset[2], 0);
  return next;
}

function rotationZFromSegment(start, end, fallback = 0) {
  if (!start || !end) return fallback;
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  if (Math.hypot(dx, dy) < 0.001) return fallback;
  return Math.atan2(-dx, dy);
}

function scaleForTarget(sourceSize, targetSize) {
  return new THREE.Vector3(
    clamp(targetSize.x / Math.max(sourceSize.x, 0.001), 0.04, 2.4),
    clamp(targetSize.y / Math.max(sourceSize.y, 0.001), 0.04, 2.4),
    clamp(targetSize.z / Math.max(sourceSize.z, 0.001), 0.04, 2.4),
  );
}

function armorStandPoseFor(part, module) {
  const pose = PART_POSES[part] || { p: [0, 0.8, 0], s: [0.24, 0.24, 0.24] };
  const fit = module?.fit && typeof module.fit === "object" ? module.fit : null;
  if (!fit) return { p: [...pose.p], s: [...pose.s] };

  const shape = String(fit.shape || "box").toLowerCase();
  const baseline = FIT_SHAPE_BASELINES[shape] || FIT_SHAPE_BASELINES.box;
  const fitScale = fitVector(fit.scale, baseline);
  const p = [...pose.p];
  const s = pose.s.map((value, index) => value * softFitFactor(fitScale[index], baseline[index]));
  p[1] += clamp(numberOr(fit.offsetY, 0), -0.42, 0.42) * 0.35;
  p[2] += clamp(numberOr(fit.zOffset, 0), -0.25, 0.25) * 0.85;
  if (fit.attach === "end") p[1] -= 0.035;
  return { p, s };
}

function declaredHeightCm() {
  const parsed = Number.parseFloat(UI.heightCm?.value || DEFAULT_HEIGHT_CM);
  if (!Number.isFinite(parsed)) return DEFAULT_HEIGHT_CM;
  return clamp(Math.round(parsed), MIN_HEIGHT_CM, MAX_HEIGHT_CM);
}

function syncHeightControls(sourceValue) {
  const height = clamp(Math.round(Number.parseFloat(sourceValue || DEFAULT_HEIGHT_CM)), MIN_HEIGHT_CM, MAX_HEIGHT_CM);
  if (UI.heightCm) UI.heightCm.value = String(height);
  if (UI.heightRange) UI.heightRange.value = String(height);
  if (UI.heightValue) UI.heightValue.textContent = `${height}cm`;
  armorStand?.setHeightCm(height);
  return height;
}

function selectedParts() {
  return Array.from(UI.partGrid.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value);
}

function renderPartGrid() {
  UI.partGrid.innerHTML = "";
  for (const [id, label, checked] of PARTS) {
    const item = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = id;
    input.checked = checked;
    item.append(input, document.createTextNode(label));
    UI.partGrid.append(item);
  }
}

function formPayload() {
  const heightCm = declaredHeightCm();
  return {
    display_name: UI.displayName.value.trim(),
    archetype: UI.archetype.value,
    temperament: UI.temperament.value,
    height_cm: heightCm,
    body_profile: {
      height_cm: heightCm,
      source: "web_forge_declared",
      vrm_baseline_ref: DEFAULT_VRM_PATH,
    },
    palette: {
      primary: UI.primaryColor.value,
      secondary: UI.secondaryColor.value,
      emissive: UI.emissiveColor.value,
    },
    brief: UI.brief.value.trim(),
    parts: selectedParts(),
  };
}

function questViewerUrl(hostname, code) {
  const questPort = Number(runtimeInfo?.quest_dev_port || DEFAULT_QUEST_DEV_PORT);
  const scheme = runtimeInfo?.quest_runtime_scheme || (window.location.protocol === "https:" ? "https" : "http");
  const url = new URL(`${scheme}://${hostname}:${questPort}/viewer/quest-iw-demo/`);
  url.searchParams.set("newRoute", "1");
  if (code) url.searchParams.set("code", code);
  return url.toString();
}

function questLinkOptions(code) {
  const currentHost = window.location.hostname || "localhost";
  const lanHost = runtimeInfo?.preferred_lan_host || "";
  const localhostUrl = questViewerUrl("localhost", code);
  const lanUrl = lanHost ? questViewerUrl(lanHost, code) : "";
  if (isLocalHost(currentHost) && lanUrl) {
    return {
      url: lanUrl,
      hint: "Questでlocalhostが404になる場合はこのLAN URLを使うか、ADB reverse後にlocalhost:5173を開いてください。VR内では4桁コード入力でも呼び出せます。",
    };
  }
  if (isLocalHost(currentHost)) {
    return {
      url: localhostUrl,
      hint: "Questでlocalhostを使うにはADB reverseが必要です。VR内では左手メニューから4桁コードを入力できます。",
    };
  }
  return {
    url: questViewerUrl(currentHost, code),
    hint: "同じネットワークのQuest Browserで開き、VR内の4桁コード入力から呼び出せます。",
  };
}

function assertForgeReadiness(data) {
  if (!data?.readiness?.suitspec_ready) {
    throw new Error("Quest呼び出し準備が未完了です。");
  }
  if (!data?.readiness?.manifest_ready) {
    throw new Error("Quest Manifestが未発行です。");
  }
}

function renderAssetPipeline(data = null) {
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  if (!UI.assetPipeline || !UI.assetPipelineTitle || !UI.assetPipelineDetail) return;
  UI.assetPipeline.classList.remove("pending", "planned", "complete", "error");
  if (!pipeline) {
    UI.assetPipeline.classList.add("pending");
    UI.assetPipelineTitle.textContent = "待機中";
    UI.assetPipelineDetail.textContent = "planned only / surface not generated";
    return;
  }
  const modelPlan = pipeline.model_plan || {};
  const texturePlan = pipeline.texture_plan || {};
  const parts = Array.isArray(modelPlan.overlay_parts) ? modelPlan.overlay_parts : selectedParts();
  const provider = texturePlan.provider_profile || "nano_banana";
  const mode = texturePlan.texture_mode || "mesh_uv";
  const status = texturePlan.status || pipeline.surface_generation_status || "planned_not_generated";
  const fitStatus = pipeline.fit_status || modelPlan.fit_solver || "preview_vrm_bone_metrics";
  const refine = texturePlan.uv_refine ? "UV再構成" : "UVガイド";
  UI.assetPipeline.classList.add("planned");
  UI.assetPipelineTitle.textContent = `${parts.length}部位 / ${provider} / planned`;
  UI.assetPipelineDetail.textContent = `${fitStatus} / ${status}: ${mode} + ${refine} / ${modelPlan.asset_contract || "vrm-base-suit+mesh-v1-overlay"}`;
}

function materialForPart(part, palette) {
  const primary = new THREE.Color(palette?.primary || "#F4F1E8");
  const secondary = new THREE.Color(palette?.secondary || "#8C96A3");
  const emissive = new THREE.Color(palette?.emissive || "#43D8FF");
  const color = part.includes("shin") || part.includes("boot") || part.includes("forearm") || part.includes("shoulder")
    ? secondary
    : primary;
  return new THREE.MeshStandardMaterial({
    color,
    emissive,
    emissiveIntensity: part === "chest" || part === "helmet" ? 0.22 : 0.12,
    metalness: 0.45,
    roughness: 0.38,
  });
}

function addArmorEdges(mesh, palette) {
  const color = new THREE.Color(palette?.emissive || "#43D8FF");
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.34 }),
  );
  edges.name = `${mesh.name}-surface-lines`;
  edges.renderOrder = 3;
  mesh.add(edges);
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh asset format.");
  }
  const positions = (payload.positions || []).flat();
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  const normals = Array.isArray(payload.normals) ? payload.normals.flat() : [];
  if (normals.length === positions.length) {
    geometry.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
  } else {
    geometry.computeVertexNormals();
  }
  const uvs = Array.isArray(payload.uv) ? payload.uv.flat() : [];
  if (uvs.length === (positions.length / 3) * 2) {
    geometry.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  }
  if (Array.isArray(payload.indices)) {
    geometry.setIndex(payload.indices.flat());
  }
  geometry.computeBoundingBox();
  geometry.center();
  return geometry;
}

async function createArmorMesh(part, module, palette) {
  const asset = normalizePath(module?.asset_ref || `viewer/assets/meshes/${part}.mesh.json`);
  const payload = await fetchJson(asset);
  const geometry = meshGeometryFromPayload(payload);
  const sourceSize = new THREE.Vector3();
  geometry.computeBoundingBox();
  geometry.boundingBox.getSize(sourceSize);
  const mesh = new THREE.Mesh(geometry, materialForPart(part, palette));
  mesh.name = part;
  mesh.userData.sourceSize = sourceSize;
  addArmorEdges(mesh, palette);
  return mesh;
}

class ArmorStand {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x080b0b);
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.05, 40);
    this.camera.position.set(0, 0.95, 4.1);
    this.group = new THREE.Group();
    this.ghostGroup = new THREE.Group();
    this.standGroup = new THREE.Group();
    this.avatarGroup = new THREE.Group();
    this.heightCm = DEFAULT_HEIGHT_CM;
    this.vrmModel = null;
    this.boneMap = new Map();
    this.metricsCache = null;
    this.scene.add(this.group);
    this.scene.add(new THREE.HemisphereLight(0xeef9ff, 0x222018, 2.1));
    const key = new THREE.DirectionalLight(0xfff2cc, 2.6);
    key.position.set(2.4, 3.4, 3);
    this.scene.add(key);
    this.buildBaseSuit();
    this.group.add(this.avatarGroup);
    this.vrmReady = this.loadBaselineVrm(DEFAULT_VRM_PATH);
    this.animate();
    window.addEventListener("resize", () => this.resize());
  }

  buildBaseSuit() {
    const ghost = new THREE.MeshBasicMaterial({
      color: 0x5ad8ff,
      transparent: true,
      opacity: 0.16,
      depthWrite: false,
    });
    const standMat = new THREE.MeshBasicMaterial({ color: 0xf4c766, transparent: true, opacity: 0.45 });
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.24, 0.82, 32), ghost);
    torso.position.y = 0.98;
    this.ghostGroup.add(torso);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.19, 32, 20), ghost);
    head.position.y = 1.58;
    this.ghostGroup.add(head);
    for (const [x, y, h, r] of [
      [-0.58, 0.86, 0.82, -0.2],
      [0.58, 0.86, 0.82, 0.2],
      [-0.17, 0.18, 0.78, 0],
      [0.17, 0.18, 0.78, 0],
    ]) {
      const limb = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.07, h, 20), ghost);
      limb.position.set(x, y, -0.03);
      limb.rotation.z = r;
      this.ghostGroup.add(limb);
    }
    const base = new THREE.Mesh(new THREE.TorusGeometry(0.72, 0.01, 8, 96), standMat);
    base.rotation.x = Math.PI / 2;
    base.position.y = -0.43;
    this.standGroup.add(base);
    const spine = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 2.1, 12), standMat);
    spine.position.set(0, 0.62, -0.28);
    this.standGroup.add(spine);
    this.group.add(this.ghostGroup);
    this.group.add(this.standGroup);
  }

  async loadBaselineVrm(path) {
    try {
      const { model } = await loadVrmScene(normalizePath(path));
      if (!model) throw new Error("VRM model is empty.");
      this.prepareVrmMannequin(model);
      applyApproximateVrmTPose({ vrmModel: model });
      this.avatarGroup.clear();
      this.avatarGroup.add(model);
      this.vrmModel = model;
      this.indexVrmBones(model);
      this.ghostGroup.visible = false;
      this.fitVrmToStand(model);
      this.setHeightCm(this.heightCm);
    } catch (error) {
      this.vrmModel = null;
      this.boneMap = new Map();
      this.metricsCache = null;
      this.ghostGroup.visible = true;
      console.warn(`VRM baseline fallback: ${error?.message || error}`);
    }
  }

  indexVrmBones(model) {
    this.boneMap = new Map();
    model?.traverse?.((obj) => {
      if (!obj?.isBone || !obj.name) return;
      this.boneMap.set(normalizeBoneName(obj.name), obj);
    });
    this.metricsCache = null;
  }

  resolveBone(boneName) {
    const canonical = VRM_BONE_ALIAS_INDEX.get(normalizeBoneName(boneName)) || boneName;
    const candidates = [boneName, canonical, ...(VRM_BONE_ALIASES[canonical] || [])];
    const seen = new Set();
    for (const candidate of candidates) {
      const key = normalizeBoneName(candidate);
      if (seen.has(key)) continue;
      seen.add(key);
      const bone = this.boneMap.get(key);
      if (bone) return bone;
    }
    return null;
  }

  boneLocalPosition(boneName) {
    const bone = this.resolveBone(boneName);
    if (!bone) return null;
    const world = new THREE.Vector3();
    bone.updateMatrixWorld(true);
    bone.getWorldPosition(world);
    return this.group.worldToLocal(world.clone());
  }

  measureVrmMetrics() {
    if (this.metricsCache) return this.metricsCache;
    const p = (boneName) => this.boneLocalPosition(boneName);
    const metrics = {
      head: p("head"),
      neck: p("neck"),
      upperChest: p("upperChest") || p("chest"),
      chest: p("chest") || p("upperChest"),
      spine: p("spine"),
      hips: p("hips"),
      leftShoulder: p("leftShoulder"),
      rightShoulder: p("rightShoulder"),
      leftUpperArm: p("leftUpperArm"),
      rightUpperArm: p("rightUpperArm"),
      leftLowerArm: p("leftLowerArm"),
      rightLowerArm: p("rightLowerArm"),
      leftHand: p("leftHand"),
      rightHand: p("rightHand"),
      leftUpperLeg: p("leftUpperLeg"),
      rightUpperLeg: p("rightUpperLeg"),
      leftLowerLeg: p("leftLowerLeg"),
      rightLowerLeg: p("rightLowerLeg"),
      leftFoot: p("leftFoot"),
      rightFoot: p("rightFoot"),
    };
    metrics.shoulderWidth = distanceOr(metrics.leftShoulder, metrics.rightShoulder, 0.68);
    metrics.torsoHeight = distanceOr(metrics.upperChest, metrics.hips, 0.78);
    metrics.headHeight = distanceOr(metrics.head, metrics.neck, 0.2);
    metrics.upperArmLength = distanceOr(metrics.leftUpperArm, metrics.leftLowerArm, 0.34);
    metrics.forearmLength = distanceOr(metrics.leftLowerArm, metrics.leftHand, 0.34);
    metrics.thighLength = distanceOr(metrics.leftUpperLeg, metrics.leftLowerLeg, 0.46);
    metrics.shinLength = distanceOr(metrics.leftLowerLeg, metrics.leftFoot, 0.46);
    metrics.torsoCenter = midpoint(metrics.upperChest, metrics.hips) || new THREE.Vector3(0, 0.96, 0);
    metrics.shouldersCenter = midpoint(metrics.leftShoulder, metrics.rightShoulder) || metrics.upperChest || new THREE.Vector3(0, 1.3, 0);
    this.metricsCache = metrics;
    return metrics;
  }

  segmentForPart(part, metrics) {
    const side = part.startsWith("left_") ? "left" : part.startsWith("right_") ? "right" : "";
    const sideKey = (name) => (side ? `${side}${name}` : name);
    if (part.endsWith("upperarm")) return [metrics[sideKey("UpperArm")], metrics[sideKey("LowerArm")]];
    if (part.endsWith("forearm")) return [metrics[sideKey("LowerArm")], metrics[sideKey("Hand")]];
    if (part.endsWith("thigh")) return [metrics[sideKey("UpperLeg")], metrics[sideKey("LowerLeg")]];
    if (part.endsWith("shin")) return [metrics[sideKey("LowerLeg")], metrics[sideKey("Foot")]];
    return [null, null];
  }

  targetSizeForPart(part, module, metrics) {
    const shoulder = metrics.shoulderWidth;
    const torso = metrics.torsoHeight;
    const arm = Math.max(metrics.upperArmLength, 0.24);
    const forearm = Math.max(metrics.forearmLength, 0.24);
    const thigh = Math.max(metrics.thighLength, 0.36);
    const shin = Math.max(metrics.shinLength, 0.36);
    let size;
    switch (part) {
      case "helmet":
        size = new THREE.Vector3(shoulder * 0.42, Math.max(metrics.headHeight * 1.7, 0.28), shoulder * 0.38);
        break;
      case "chest":
        size = new THREE.Vector3(shoulder * 0.94, torso * 0.64, shoulder * 0.24);
        break;
      case "back":
        size = new THREE.Vector3(shoulder * 0.88, torso * 0.66, shoulder * 0.2);
        break;
      case "waist":
        size = new THREE.Vector3(shoulder * 0.72, torso * 0.22, shoulder * 0.28);
        break;
      case "left_shoulder":
      case "right_shoulder":
        size = new THREE.Vector3(shoulder * 0.28, shoulder * 0.18, shoulder * 0.24);
        break;
      case "left_upperarm":
      case "right_upperarm":
        size = new THREE.Vector3(shoulder * 0.16, arm * 0.86, shoulder * 0.16);
        break;
      case "left_forearm":
      case "right_forearm":
        size = new THREE.Vector3(shoulder * 0.15, forearm * 0.82, shoulder * 0.15);
        break;
      case "left_hand":
      case "right_hand":
        size = new THREE.Vector3(shoulder * 0.17, shoulder * 0.12, shoulder * 0.2);
        break;
      case "left_thigh":
      case "right_thigh":
        size = new THREE.Vector3(shoulder * 0.2, thigh * 0.86, shoulder * 0.19);
        break;
      case "left_shin":
      case "right_shin":
        size = new THREE.Vector3(shoulder * 0.17, shin * 0.86, shoulder * 0.17);
        break;
      case "left_boot":
      case "right_boot":
        size = new THREE.Vector3(shoulder * 0.18, shoulder * 0.13, shoulder * 0.42);
        break;
      default:
        size = new THREE.Vector3(0.24, 0.24, 0.24);
    }
    return softFitSize(part, module, size);
  }

  targetCenterForPart(part, module, metrics) {
    const fit = effectiveFitFor(part, module);
    const anchor = effectiveVrmAnchorFor(part, module);
    const front = part === "back" ? -1 : 1;
    let center = null;
    switch (part) {
      case "helmet":
        center = metrics.head?.clone().add(new THREE.Vector3(0, 0.04, metrics.shoulderWidth * 0.04));
        break;
      case "chest":
        center = midpoint(metrics.shouldersCenter, metrics.torsoCenter)?.add(new THREE.Vector3(0, -metrics.torsoHeight * 0.08, metrics.shoulderWidth * 0.13));
        break;
      case "back":
        center = midpoint(metrics.shouldersCenter, metrics.torsoCenter)?.add(new THREE.Vector3(0, -metrics.torsoHeight * 0.08, -metrics.shoulderWidth * 0.13));
        break;
      case "waist":
        center = metrics.hips?.clone().add(new THREE.Vector3(0, metrics.torsoHeight * 0.05, metrics.shoulderWidth * 0.08));
        break;
      case "left_shoulder":
        center = metrics.leftShoulder?.clone().add(new THREE.Vector3(-metrics.shoulderWidth * 0.08, 0, metrics.shoulderWidth * 0.04));
        break;
      case "right_shoulder":
        center = metrics.rightShoulder?.clone().add(new THREE.Vector3(metrics.shoulderWidth * 0.08, 0, metrics.shoulderWidth * 0.04));
        break;
      case "left_hand":
        center = metrics.leftHand?.clone().add(new THREE.Vector3(0, 0, metrics.shoulderWidth * 0.05));
        break;
      case "right_hand":
        center = metrics.rightHand?.clone().add(new THREE.Vector3(0, 0, metrics.shoulderWidth * 0.05));
        break;
      case "left_boot":
        center = metrics.leftFoot?.clone().add(new THREE.Vector3(0, 0.02, metrics.shoulderWidth * 0.1));
        break;
      case "right_boot":
        center = metrics.rightFoot?.clone().add(new THREE.Vector3(0, 0.02, metrics.shoulderWidth * 0.1));
        break;
      default: {
        const [start, end] = this.segmentForPart(part, metrics);
        center = midpoint(start, end);
      }
    }
    if (!center) {
      const anchorBone = this.boneLocalPosition(anchor.bone);
      if (anchorBone) center = anchorBone;
    }
    if (!center) return null;
    center = addOffset(center, anchor.offset);
    center.y += clamp(numberOr(fit.offsetY, 0), -0.42, 0.42) * 0.12;
    center.z += clamp(numberOr(fit.zOffset, 0), -0.25, 0.25) * 0.55 * front;
    return center;
  }

  vrmPoseFor(part, module, mesh) {
    if (!this.vrmModel || !this.boneMap.size) return null;
    const metrics = this.measureVrmMetrics();
    const center = this.targetCenterForPart(part, module, metrics);
    if (!center) return null;
    const targetSize = this.targetSizeForPart(part, module, metrics);
    const sourceSize = mesh.userData?.sourceSize || new THREE.Vector3(1, 1, 1);
    const [segmentStart, segmentEnd] = this.segmentForPart(part, metrics);
    const anchor = effectiveVrmAnchorFor(part, module);
    const rotation = fitVector(anchor.rotation, [0, 0, 0]).map((degrees) => THREE.MathUtils.degToRad(degrees));
    const anchorScale = fitVector(anchor.scale, [1, 1, 1]);
    const scale = scaleForTarget(sourceSize, targetSize);
    scale.set(
      clamp(scale.x * Math.max(anchorScale[0], 0.01), 0.04, 2.4),
      clamp(scale.y * Math.max(anchorScale[1], 0.01), 0.04, 2.4),
      clamp(scale.z * Math.max(anchorScale[2], 0.01), 0.04, 2.4),
    );
    rotation[2] += rotationZFromSegment(segmentStart, segmentEnd, 0);
    return {
      p: center.toArray(),
      s: scale.toArray(),
      r: rotation,
      source: "vrm_bone_metrics",
    };
  }

  applyPreviewPose(mesh, part, module) {
    const fallbackPose = armorStandPoseFor(part, module);
    const pose = this.vrmPoseFor(part, module, mesh) || {
      p: fallbackPose.p,
      s: fallbackPose.s,
      r: [0, 0, 0],
      source: "fallback_pose",
    };
    mesh.position.set(...pose.p);
    mesh.rotation.set(...pose.r);
    mesh.scale.set(...pose.s);
    mesh.userData.fitPreview = pose.source;
  }

  prepareVrmMannequin(model) {
    model.traverse((obj) => {
      if (!obj.isMesh) return;
      obj.renderOrder = 1;
      const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
      obj.material = materials.map((material) => {
        const clone = material?.clone ? material.clone() : new THREE.MeshStandardMaterial({ color: 0x87dceb });
        clone.transparent = true;
        clone.opacity = 0.26;
        clone.depthWrite = false;
        return clone;
      });
      if (obj.material.length === 1) obj.material = obj.material[0];
    });
  }

  fitVrmToStand(model) {
    model.position.set(0, 0, 0);
    model.rotation.set(0, 0, 0);
    model.scale.setScalar(1);
    model.updateMatrixWorld(true);
    const box = new THREE.Box3().setFromObject(model);
    if (box.isEmpty()) return;
    const sourceHeight = Math.max(box.max.y - box.min.y, 0.001);
    const targetHeight = 1.96;
    model.scale.setScalar(targetHeight / sourceHeight);
    model.updateMatrixWorld(true);
    const scaledBox = new THREE.Box3().setFromObject(model);
    const center = scaledBox.getCenter(new THREE.Vector3());
    model.position.add(new THREE.Vector3(-center.x, -0.36 - scaledBox.min.y, -center.z - 0.02));
    model.updateMatrixWorld(true);
  }

  setHeightCm(heightCm) {
    this.heightCm = clamp(Number(heightCm) || DEFAULT_HEIGHT_CM, MIN_HEIGHT_CM, MAX_HEIGHT_CM);
    const scale = this.heightCm / DEFAULT_HEIGHT_CM;
    this.group.scale.setScalar(scale);
    this.updateCameraDistance();
  }

  updateCameraDistance() {
    const aspect = this.camera.aspect || 1;
    const heightScale = Math.max(this.heightCm / DEFAULT_HEIGHT_CM, 1);
    const narrowCompensation = aspect < 1.05 ? 1.05 / Math.max(aspect, 0.2) : 1;
    this.camera.position.set(0, 0.96 * Math.min(heightScale, 1.18), 4.15 * heightScale * narrowCompensation);
  }

  clearArmor() {
    const removable = this.group.children.filter((child) => child.userData?.armorPart);
    for (const child of removable) {
      child.traverse((object) => {
        if (object === child) return;
        object.geometry?.dispose?.();
        object.material?.dispose?.();
      });
      child.removeFromParent();
      child.geometry?.dispose?.();
      child.material?.dispose?.();
    }
  }

  async renderSuit(suitspec) {
    await this.vrmReady;
    this.clearArmor();
    this.setHeightCm(suitspec?.body_profile?.height_cm || DEFAULT_HEIGHT_CM);
    this.metricsCache = null;
    const modules = suitspec?.modules || {};
    const palette = suitspec?.palette || {};
    const records = Object.entries(modules).filter(([, module]) => module?.enabled);
    const meshes = await Promise.all(records.map(([part, module]) => createArmorMesh(part, module, palette)));
    for (let index = 0; index < meshes.length; index += 1) {
      const [part, module] = records[index];
      const mesh = meshes[index];
      this.applyPreviewPose(mesh, part, module);
      mesh.userData.armorPart = true;
      this.group.add(mesh);
    }
  }

  resize() {
    const width = this.canvas.clientWidth || 640;
    const height = this.canvas.clientHeight || 640;
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.updateCameraDistance();
    this.camera.updateProjectionMatrix();
  }

  animate() {
    this.resize();
    this.group.rotation.y = Math.sin(performance.now() * 0.00028) * 0.08;
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(() => this.animate());
  }
}

const armorStand = new ArmorStand(UI.canvas);

if (UI.heightCm) {
  UI.heightCm.addEventListener("input", () => syncHeightControls(UI.heightCm.value));
  UI.heightCm.addEventListener("change", () => syncHeightControls(UI.heightCm.value));
}
if (UI.heightRange) {
  UI.heightRange.addEventListener("input", () => syncHeightControls(UI.heightRange.value));
}
syncHeightControls(UI.heightCm?.value || DEFAULT_HEIGHT_CM);

function applyResult(data) {
  const quest = questLinkOptions(data.recall_code || "");
  UI.recallCode.textContent = data.recall_code || "----";
  UI.questLink.href = quest.url;
  UI.questLink.classList.remove("disabled");
  UI.questLink.setAttribute("aria-disabled", "false");
  if (UI.questUrl) UI.questUrl.value = quest.url;
  if (UI.questUrlHint) UI.questUrlHint.textContent = quest.hint;
  renderAssetPipeline(data);
  UI.emptyStand.classList.add("hidden");
}

async function submitForge(event) {
  event.preventDefault();
  UI.button.disabled = true;
  syncHeightControls(UI.heightCm?.value);
  setStatus("生成条件を送信中...", "pending");
  try {
    const data = await fetchJson("/v1/suits/forge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    setStatus("VRM基準の鎧立てを構築中...", "pending");
    await armorStand.renderSuit(data.preview);
    setStatus("Quest接続情報を確認中...", "pending");
    await ensureRuntimeInfo();
    assertForgeReadiness(data);
    applyResult(data);
    setStatus("生成完了 / Quest入力準備OK", "complete");
  } catch (error) {
    setStatus(String(error?.message || error), "error");
  } finally {
    UI.button.disabled = false;
  }
}

renderPartGrid();
renderAssetPipeline();
runtimeInfoPromise = loadRuntimeInfo();
UI.form.addEventListener("submit", submitForge);
