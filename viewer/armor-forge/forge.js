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
const BODY_REFERENCE_COLOR = 0xe6c7a6;
const BODY_REFERENCE_EMISSIVE = 0x2a1710;
const BASE_SUIT_COLOR = 0x52777e;
const BASE_SUIT_EMISSIVE = 0x10292c;
const PREVIEW_FLOOR_Y = -0.43;
const FALLBACK_MESH_SOURCE = "seed_proxy_fallback";
const MIN_RENDERABLE_MESH_SIZE = 0.002;
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
  standStage: document.querySelector(".stand-stage"),
  previewLegend: document.querySelector(".preview-legend"),
  emptyStand: document.getElementById("emptyStand"),
  recallCode: document.getElementById("recallCode"),
  status: document.getElementById("forgeStatus"),
  questLink: document.getElementById("questLink"),
  questUrl: document.getElementById("questUrl"),
  questUrlHint: document.getElementById("questUrlHint"),
  assetPipeline: document.getElementById("assetPipeline"),
  assetPipelineTitle: document.getElementById("assetPipelineTitle"),
  assetPipelineDetail: document.getElementById("assetPipelineDetail"),
  textureJobPanel: document.getElementById("textureJobPanel"),
  textureJobButton: document.getElementById("textureJobButton"),
  textureJobTitle: document.getElementById("textureJobTitle"),
  textureJobDetail: document.getElementById("textureJobDetail"),
  textureJobMeter: document.getElementById("textureJobMeter"),
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
let latestForgeData = null;
let textureJobPollTimer = null;
let textureJobStartedAt = 0;
let armorStand = null;
let previewLayerPanel = null;
const textureLoader = new THREE.TextureLoader();

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
  updatePreviewLayerPanel(latestForgeData);
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

function syncPreviewLegendPalette() {
  const root = document.documentElement;
  root.style.setProperty("--legend-primary", UI.primaryColor?.value || "#F4F1E8");
  root.style.setProperty("--legend-secondary", UI.secondaryColor?.value || "#8C96A3");
  root.style.setProperty("--legend-emissive", UI.emissiveColor?.value || "#43D8FF");
}

function renderPreviewLegend() {
  if (!UI.previewLegend) return;
  const items = [
    ["legend-skin", "人体リファレンス"],
    ["legend-suit", "基礎スーツ層"],
    ["legend-armor", "分割装甲パーツ"],
    ["legend-glow", "表面/発光ライン"],
  ];
  UI.previewLegend.replaceChildren(
    ...items.map(([className, label]) => {
      const item = document.createElement("span");
      const swatch = document.createElement("i");
      swatch.className = className;
      item.append(swatch, document.createTextNode(label));
      return item;
    }),
  );
}

function previewRecordsFromData(data = latestForgeData) {
  const suitspec = data?.preview || data?.suitspec || data || {};
  const modules = suitspec?.modules || {};
  return Object.entries(modules).filter(([, module]) => module?.enabled);
}

function previewPipelineFromData(data = latestForgeData) {
  return data?.asset_pipeline || data?.preview?.asset_pipeline || null;
}

function layerStateForSurface(data = latestForgeData, records = previewRecordsFromData(data)) {
  const texturedCount = records.filter(([, module]) => module?.texture_path).length;
  const pipeline = previewPipelineFromData(data);
  const template = pipeline?.texture_probe_job?.payload || pipeline?.generation_job?.payload || pipeline?.job_payload_template;
  const canRun = Boolean(template?.suitspec);
  const writesFinal = textureJobWritesFinal(data);
  if (texturedCount > 0) {
    return {
      state: "ready",
      title: `${texturedCount}パーツ反映`,
      detail: "生成済みテクスチャをプレビューに重ねています。",
    };
  }
  if (UI.textureJobPanel?.classList.contains("running")) {
    return {
      state: "running",
      title: "生成中",
      detail: "表面テクスチャを作成しています。",
    };
  }
  if (UI.textureJobPanel?.classList.contains("complete")) {
    return {
      state: "ready",
      title: "生成完了",
      detail: "表面を再読み込みしてプレビューへ反映します。",
    };
  }
  if (canRun) {
    return {
      state: "queued",
      title: writesFinal ? "生成準備OK" : "Probe待機",
      detail: writesFinal
        ? "表面/テクスチャ層を追加生成できます。"
        : "部分生成またはモデルGate前のため、本番反映せず速度確認だけ行います。",
    };
  }
  return {
    state: "planned",
    title: "カラー設計",
    detail: "まだテクスチャ未生成。配色と発光ラインを表示中です。",
  };
}

function ensurePreviewLayerPanel() {
  if (previewLayerPanel?.isConnected) return previewLayerPanel;
  if (!UI.standStage) return null;

  previewLayerPanel = document.createElement("div");
  previewLayerPanel.className = "preview-layer-panel";
  previewLayerPanel.setAttribute("aria-live", "polite");
  UI.standStage.classList.add("has-layer-panel");
  UI.standStage.append(previewLayerPanel);
  return previewLayerPanel;
}

function setPreviewLayerRow(panel, key, label, title, detail, state) {
  let row = panel.querySelector(`[data-layer="${key}"]`);
  if (!row) {
    row = document.createElement("div");
    row.className = "preview-layer-row";
    row.dataset.layer = key;

    const dot = document.createElement("i");
    dot.className = "preview-layer-dot";
    dot.setAttribute("aria-hidden", "true");

    const copy = document.createElement("div");
    const labelNode = document.createElement("span");
    labelNode.className = "preview-layer-label";
    const titleNode = document.createElement("strong");
    titleNode.className = "preview-layer-title";
    const detailNode = document.createElement("small");
    detailNode.className = "preview-layer-detail";
    copy.append(labelNode, titleNode, detailNode);
    row.append(dot, copy);
    panel.append(row);
  }
  row.dataset.state = state;
  row.querySelector(".preview-layer-label").textContent = label;
  row.querySelector(".preview-layer-title").textContent = title;
  row.querySelector(".preview-layer-detail").textContent = detail;
}

function modelGateStateForPipeline(pipeline) {
  const gate = pipeline?.model_quality_gate || null;
  if (!gate) {
    return {
      state: "planned",
      title: "検査待ち",
      detail: "helmet/chest/back/shoulder のモデル品質Gateを待っています。",
    };
  }
  const summary = gate.summary || {};
  const requiredCount = Number(summary.required_count || gate.required_parts?.length || gate.p0_parts?.length || 0);
  const passCount = Number(summary.required_pass_count || summary.pass_count || 0);
  const status = String(gate.status || "unknown");
  const firstReason = Array.isArray(gate.reasons) && gate.reasons.length
    ? String(gate.reasons[0])
    : "";
  if (gate.selection_complete_for_final_texture === false) {
    const missing = Array.isArray(gate.missing_required_overlay_parts)
      ? gate.missing_required_overlay_parts.join(", ")
      : "";
    return {
      state: "planned",
      title: "部分生成",
      detail: missing
        ? `本番スーツ化には ${missing} が必要です。現在は部分プレビューです。`
        : "本番スーツ化に必要な外装パーツ数が足りません。現在は部分プレビューです。",
    };
  }
  if (status === "pass") {
    return {
      state: "ready",
      title: `通過 ${passCount}/${requiredCount || passCount}`,
      detail: "P0モデルは最終テクスチャ対象として扱えます。",
    };
  }
  if (status === "warn") {
    return {
      state: "planned",
      title: `要確認 ${passCount}/${requiredCount || "?"}`,
      detail: firstReason || "P0モデルに警告があります。",
    };
  }
  return {
    state: "error",
    title: `未通過 ${passCount}/${requiredCount || "?"}`,
    detail: firstReason || "P0モデルのbounds/UV/法線/三角形を再構築してください。",
  };
}

function updatePreviewLayerPanel(data = latestForgeData, stand = armorStand) {
  const panel = ensurePreviewLayerPanel();
  if (!panel) return;

  const records = previewRecordsFromData(data);
  const pipeline = previewPipelineFromData(data);
  const selectedCount = selectedParts().length;
  const armorParts = stand?.previewStats?.armorParts || records.length || selectedCount;
  const fallbackParts = stand?.previewStats?.fallbackParts || 0;
  const height = Math.round(stand?.heightCm || declaredHeightCm());
  const heightScale = height / DEFAULT_HEIGHT_CM;
  const surface = layerStateForSurface(data, records);
  const modelGate = modelGateStateForPipeline(pipeline);
  const baseState = stand?.previewStats?.baseSuitVisible === false ? "planned" : "ready";
  const armorState = armorParts > 0 ? "ready" : "planned";
  const armorDetail = fallbackParts > 0
    ? `${fallbackParts}パーツは仮形状。分割位置を先に確認できます。`
    : "人体基準に合わせて、パーツを分けて重ねています。";

  setPreviewLayerRow(
    panel,
    "height",
    "身長反映",
    `${height}cm`,
    `鎧立て全体を ${heightScale.toFixed(2)}x で表示しています。`,
    "ready",
  );
  setPreviewLayerRow(panel, "base", "基礎スーツ層", baseState === "ready" ? "表示中" : "待機中", "人体との差が読める半透明スーツです。", baseState);
  setPreviewLayerRow(panel, "armor", "装甲パーツ層", armorParts > 0 ? `${armorParts}パーツ配置` : `${selectedCount}パーツ選択中`, armorDetail, armorState);
  setPreviewLayerRow(panel, "modelGate", "モデル品質Gate", modelGate.title, modelGate.detail, modelGate.state);
  setPreviewLayerRow(panel, "surface", "表面/テクスチャ層", surface.title, surface.detail, surface.state);
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
    throw new Error("Quest向けの呼び出し準備がまだ完了していません。");
  }
}

function renderAssetPipeline(data = null) {
  if (!UI.assetPipeline || !UI.assetPipelineTitle || !UI.assetPipelineDetail) return;
  const records = previewRecordsFromData(data);
  const selectedCount = selectedParts().length;
  const armorParts = armorStand?.previewStats?.armorParts || records.length || selectedCount;
  const fallbackParts = armorStand?.previewStats?.fallbackParts || 0;
  const surface = layerStateForSurface(data, records);
  const baseReady = armorStand?.previewStats?.baseSuitVisible !== false;
  const hasGeneratedPreview = Boolean(data);
  const pipeline = previewPipelineFromData(data);
  const modelPlan = pipeline?.model_plan || {};
  const texturePlan = pipeline?.texture_plan || {};
  const modelJob = pipeline?.model_rebuild_job || {};
  const modelGate = modelGateStateForPipeline(pipeline);
  const textureProbe = pipeline?.texture_probe_job || {};
  const provider = texturePlan.provider_profile || "nano_banana";
  const mode = texturePlan.texture_mode || "mesh_uv";
  const status = texturePlan.status || pipeline?.surface_generation_status || "planned_not_generated";
  const fitStatus = pipeline?.fit_status || modelPlan.fit_solver || "preview_vrm_bone_metrics";
  const meshStatus = modelPlan.mesh_source_status || "seed/proxy";
  const modelStatus = modelJob.status || modelPlan.status || "requires_rebuild";
  const probeStatus = textureProbe.status || "probe_only";
  UI.assetPipeline.dataset.pipelineContract = `model ${modelStatus} / ${fitStatus} / ${provider} / ${mode} / ${status} / ${meshStatus} / ${probeStatus}`;

  UI.assetPipeline.classList.remove("pending", "planned", "complete", "error");
  if (!hasGeneratedPreview) {
    UI.assetPipeline.classList.add("pending");
    UI.assetPipelineTitle.textContent = "レイヤー待機中";
    UI.assetPipelineDetail.textContent = `基礎スーツ層: ${baseReady ? "表示中" : "待機中"} / 装甲パーツ層: ${selectedCount}パーツ選択中 / 表面: カラー設計`;
    updatePreviewLayerPanel(data);
    return;
  }
  UI.assetPipeline.classList.add(surface.state === "ready" ? "complete" : "planned");
  UI.assetPipelineTitle.textContent = `基礎スーツ + 装甲${armorParts}パーツ`;
  UI.assetPipelineDetail.textContent = [
    `基礎スーツ層: ${baseReady ? "表示中" : "待機中"}`,
    `装甲パーツ層: ${fallbackParts > 0 ? `仮形状${fallbackParts}パーツ含む` : "分割配置済み"}`,
    `モデルGate: ${modelGate.title}`,
    `表面: ${surface.title}`,
  ].join(" / ");
  updatePreviewLayerPanel(data);
}

function formatSeconds(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds)) return "--";
  return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
}

function friendlyTextureStage(stage) {
  const value = String(stage || "").toLowerCase();
  if (value.includes("queue") || value.includes("wait")) return "待機中";
  if (value.includes("load") || value.includes("scan")) return "装甲確認中";
  if (value.includes("texture") || value.includes("generate") || value.includes("inference")) return "表面生成中";
  if (value.includes("write") || value.includes("save")) return "反映準備中";
  return "生成中";
}

function setTextureJobState(state, title, detail, progress = 0) {
  if (!UI.textureJobPanel || !UI.textureJobTitle || !UI.textureJobDetail || !UI.textureJobMeter) return;
  UI.textureJobPanel.classList.remove("pending", "running", "complete", "error");
  UI.textureJobPanel.classList.add(state);
  UI.textureJobTitle.textContent = title;
  UI.textureJobDetail.textContent = detail;
  UI.textureJobMeter.style.width = `${clamp(progress, 0, 1) * 100}%`;
  updatePreviewLayerPanel(latestForgeData);
}

function textureJobContract(data = latestForgeData) {
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  return pipeline?.texture_probe_job || pipeline?.generation_job || null;
}

function textureJobWritesFinal(data = latestForgeData) {
  const job = textureJobContract(data);
  return Boolean(job?.writes_final_texture || job?.final_texture_lock_allowed || job?.payload?.writes_final_texture);
}

function updateTextureJobAvailability(data = latestForgeData) {
  if (!UI.textureJobButton) return;
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  const job = textureJobContract(data);
  const template = job?.payload || pipeline?.job_payload_template;
  const canRun = Boolean(template?.suitspec);
  const writesFinal = textureJobWritesFinal(data);
  UI.textureJobButton.disabled = !canRun;
  if (!canRun) {
    setTextureJobState("pending", "未開始", "鎧を生成すると、表面/テクスチャ層を追加できます。", 0);
  } else if (!UI.textureJobPanel?.classList.contains("running") && !UI.textureJobPanel?.classList.contains("complete")) {
    UI.textureJobButton.textContent = writesFinal ? "本番表面生成" : "表面Probeを試す";
    setTextureJobState(
      "pending",
      writesFinal ? "本番表面生成待機" : "表面Probe待機",
      writesFinal
        ? "モデル品質Gate通過。生成結果をSuitSpecへ反映します。"
        : "モデル品質Gate前は速度確認と仮貼り用途です。",
      0,
    );
  }
}

function textureJobPayload(data) {
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  const job = textureJobContract(data);
  const template = job?.payload || pipeline?.job_payload_template || null;
  if (!template?.suitspec) {
    throw new Error("texture job payload is not ready.");
  }
  return {
    ...template,
    root: template.root || "sessions",
    session_id: template.session_id || `S-FORGE-${data.recall_code || Date.now()}`,
    writes_final_texture: textureJobWritesFinal(data),
    dry_run: false,
  };
}

function textureJobLinks(data) {
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  return pipeline?.texture_probe_job?.links || pipeline?.generation_job?.links || pipeline?.links || {};
}

function updateTextureJobFromSnapshot(snapshot) {
  const total = Number(snapshot.requested_count || 0);
  const done = Number(snapshot.completed_count || 0);
  const localElapsed = textureJobStartedAt ? (performance.now() - textureJobStartedAt) / 1000 : 0;
  const elapsed = Number.isFinite(Number(snapshot.elapsed_sec)) ? Number(snapshot.elapsed_sec) : localElapsed;
  const speed = Number(snapshot.parts_per_min || 0);
  const timingMs = snapshot.last_timing_ms && typeof snapshot.last_timing_ms === "object"
    ? Number(snapshot.last_timing_ms.total_ms || snapshot.last_timing_ms.inference_ms || 0)
    : 0;
  const speedText = Number.isFinite(speed) && speed > 0 ? ` / ${speed.toFixed(1)}パーツ/分` : "";
  const timingText = Number.isFinite(timingMs) && timingMs > 0 ? ` / 直近 ${(timingMs / 1000).toFixed(1)}s` : "";
  const progress = total > 0 ? done / total : snapshot.status === "completed" ? 1 : 0.08;
  const result = snapshot.result || {};
  if (snapshot.status === "completed") {
    if (UI.textureJobButton) {
      UI.textureJobButton.disabled = false;
      UI.textureJobButton.textContent = textureJobWritesFinal() ? "本番表面再生成" : "表面Probe再試行";
    }
    setTextureJobState(
      "complete",
      `表面生成完了 ${result.generated_count ?? done}/${total || result.generated_count || done}`,
      `所要 ${formatSeconds(result.total_elapsed_sec || elapsed)}${speedText}${timingText}。プレビューへ反映します。`,
      1,
    );
    return;
  }
  if (snapshot.status === "failed" || snapshot.status === "cancelled") {
    if (UI.textureJobButton) UI.textureJobButton.disabled = false;
    setTextureJobState("error", "表面生成に失敗", snapshot.error || "表面テクスチャを生成できませんでした。", progress);
    return;
  }
  setTextureJobState(
    "running",
    `生成中 ${done}/${total || "?"}`,
    `${friendlyTextureStage(snapshot.stage)} / 経過 ${formatSeconds(elapsed)}${speedText}${timingText}`,
    Math.max(progress, 0.08),
  );
}

async function refreshPreviewFromGeneratedSuit(payload) {
  if (!payload?.suitspec) return;
  const data = await fetchJson(`/api/suitspec?path=${encodeURIComponent(payload.suitspec)}`);
  if (data?.suitspec) {
    await armorStand.renderSuit(data.suitspec);
    latestForgeData = { ...(latestForgeData || {}), preview: data.suitspec };
    renderAssetPipeline(latestForgeData);
    updatePreviewLayerPanel(latestForgeData);
  }
}

async function pollTextureJob(jobId, payload) {
  if (textureJobPollTimer) window.clearTimeout(textureJobPollTimer);
  const snapshot = await fetchJson(`/api/generation-jobs/${encodeURIComponent(jobId)}`);
  updateTextureJobFromSnapshot(snapshot);
  if (snapshot.status === "completed") {
    await refreshPreviewFromGeneratedSuit(payload).catch((error) => {
      console.warn(`texture preview refresh failed: ${error?.message || error}`);
    });
    return;
  }
  if (snapshot.status === "failed" || snapshot.status === "cancelled") return;
  textureJobPollTimer = window.setTimeout(() => {
    pollTextureJob(jobId, payload).catch((error) => {
      setTextureJobState("error", "表面生成エラー", String(error?.message || error), 0);
    });
  }, 1000);
}

async function startTextureGeneration() {
  if (!latestForgeData) return;
  const payload = textureJobPayload(latestForgeData);
  const links = textureJobLinks(latestForgeData);
  const createUrl = links.create_generation_job || "/api/generation-jobs";
  UI.textureJobButton.disabled = true;
  UI.textureJobButton.textContent = "生成中...";
  textureJobStartedAt = performance.now();
  setTextureJobState(
    "running",
    textureJobWritesFinal() ? "本番表面生成を開始" : "表面Probeを開始",
    textureJobWritesFinal()
      ? "装甲パーツの表面テクスチャを生成し、SuitSpecへ反映します。"
      : "装甲パーツの表面テクスチャを速度確認用に準備しています。",
    0.05,
  );
  const job = await fetchJson(createUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  await pollTextureJob(job.job_id, payload);
}

async function loadTextureMap(path) {
  if (!path) return null;
  return new Promise((resolve) => {
    textureLoader.load(
      normalizePath(path),
      (texture) => {
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.anisotropy = 4;
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        resolve(texture);
      },
      undefined,
      (error) => {
        console.warn(`texture load failed: ${path}`, error);
        resolve(null);
      },
    );
  });
}

function disposeMaterial(material) {
  const materials = Array.isArray(material) ? material : [material];
  for (const item of materials) {
    if (!item) continue;
    item.map?.dispose?.();
    item.emissiveMap?.dispose?.();
    item.normalMap?.dispose?.();
    item.roughnessMap?.dispose?.();
    item.metalnessMap?.dispose?.();
    item.dispose?.();
  }
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
    emissiveIntensity: part === "chest" || part === "helmet" ? 0.38 : 0.22,
    metalness: 0.2,
    roughness: 0.42,
    side: THREE.DoubleSide,
  });
}

function addArmorEdges(mesh, palette) {
  const color = new THREE.Color(palette?.emissive || "#43D8FF");
  const seam = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({ color: 0x1d2a28, transparent: true, opacity: 0.44 }),
  );
  seam.name = `${mesh.name}-part-seams`;
  seam.renderOrder = 6;
  const glow = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.86, depthTest: false }),
  );
  glow.name = `${mesh.name}-surface-lines`;
  glow.renderOrder = 10;
  mesh.add(seam, glow);
}

function meshGeometryFromPayload(payload) {
  if (!payload || payload.format !== "mesh.v1") {
    throw new Error("Unsupported mesh asset format.");
  }
  const positions = (payload.positions || []).flat();
  if (positions.length < 9 || positions.length % 3 !== 0) {
    throw new Error("Mesh asset has no renderable triangles.");
  }
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
  const indices = Array.isArray(payload.indices) ? payload.indices.flat() : [];
  if (indices.length >= 3) {
    geometry.setIndex(indices);
  }
  geometry.computeBoundingBox();
  const size = new THREE.Vector3();
  geometry.boundingBox.getSize(size);
  if (Math.max(size.x, size.y, size.z) < MIN_RENDERABLE_MESH_SIZE) {
    throw new Error("Mesh asset bounds are empty.");
  }
  geometry.center();
  return geometry;
}

function createFallbackArmorGeometry(part) {
  let geometry;
  switch (part) {
    case "helmet":
      geometry = new THREE.SphereGeometry(0.28, 32, 20);
      break;
    case "chest":
      geometry = new THREE.BoxGeometry(0.72, 0.76, 0.2, 2, 3, 1);
      break;
    case "back":
      geometry = new THREE.BoxGeometry(0.68, 0.72, 0.16, 2, 3, 1);
      break;
    case "waist":
      geometry = new THREE.BoxGeometry(0.58, 0.22, 0.24, 2, 1, 1);
      break;
    case "left_shoulder":
    case "right_shoulder":
      geometry = new THREE.SphereGeometry(0.2, 24, 14, 0, Math.PI * 2, 0, Math.PI * 0.72);
      break;
    case "left_upperarm":
    case "right_upperarm":
    case "left_forearm":
    case "right_forearm":
    case "left_thigh":
    case "right_thigh":
    case "left_shin":
    case "right_shin":
      geometry = new THREE.CylinderGeometry(0.12, 0.1, 0.64, 20, 2);
      break;
    case "left_boot":
    case "right_boot":
      geometry = new THREE.BoxGeometry(0.24, 0.18, 0.42, 1, 1, 2);
      break;
    case "left_hand":
    case "right_hand":
      geometry = new THREE.BoxGeometry(0.2, 0.16, 0.2, 1, 1, 1);
      break;
    default:
      geometry = new THREE.BoxGeometry(0.28, 0.28, 0.2, 1, 1, 1);
      break;
  }
  geometry.computeVertexNormals();
  geometry.center();
  geometry.computeBoundingBox();
  return geometry;
}

async function createArmorMesh(part, module, palette) {
  const asset = normalizePath(module?.asset_ref || `viewer/assets/meshes/${part}.mesh.json`);
  let geometry;
  let meshSource = "mesh_asset";
  let meshError = "";
  try {
    const payload = await fetchJson(asset);
    geometry = meshGeometryFromPayload(payload);
  } catch (error) {
    meshSource = FALLBACK_MESH_SOURCE;
    meshError = String(error?.message || error);
    console.warn(`armor mesh fallback for ${part}: ${meshError}`);
    geometry = createFallbackArmorGeometry(part);
  }
  const sourceSize = new THREE.Vector3();
  geometry.computeBoundingBox();
  geometry.boundingBox.getSize(sourceSize);
  const material = materialForPart(part, palette);
  const texture = await loadTextureMap(module?.texture_path);
  if (texture) {
    material.map = texture;
    material.color.setHex(0xffffff);
    material.emissiveIntensity *= 0.72;
    material.needsUpdate = true;
  }
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = part;
  mesh.renderOrder = 4;
  mesh.userData.sourceSize = sourceSize;
  mesh.userData.texturePath = module?.texture_path || null;
  mesh.userData.meshSource = meshSource;
  mesh.userData.assetRef = asset;
  mesh.userData.meshError = meshError;
  addArmorEdges(mesh, palette);
  return mesh;
}

class ArmorStand {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.28;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.setClearColor(0xf7fbf4, 1);
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xf7fbf4);
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
    this.lastCanvasSize = { width: 0, height: 0 };
    this.previewStats = {
      armorParts: 0,
      fallbackParts: 0,
      texturedParts: 0,
      baseSuitVisible: true,
      vrmVisible: false,
      heightCm: DEFAULT_HEIGHT_CM,
    };
    this.scene.add(this.group);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x8ca5a1, 1.55));
    this.scene.add(new THREE.AmbientLight(0xd9f3ee, 0.42));
    const key = new THREE.DirectionalLight(0xffffff, 3.1);
    key.position.set(2.2, 3.6, 3.4);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0x9feaff, 1.45);
    fill.position.set(-3.2, 1.8, 2.4);
    this.scene.add(fill);
    const rim = new THREE.DirectionalLight(0xffd48a, 1.2);
    rim.position.set(0.2, 2.4, -3.4);
    this.scene.add(rim);
    this.buildBaseSuit();
    this.group.add(this.avatarGroup);
    this.vrmReady = this.loadBaselineVrm(DEFAULT_VRM_PATH);
    this.publishPreviewStats();
    this.animate();
    window.addEventListener("resize", () => this.resize());
  }

  publishPreviewStats() {
    if (!this.canvas) return;
    this.previewStats.baseSuitVisible = Boolean(this.ghostGroup?.visible);
    this.canvas.dataset.previewArmorParts = String(this.previewStats.armorParts);
    this.canvas.dataset.previewFallbackParts = String(this.previewStats.fallbackParts);
    this.canvas.dataset.previewTexturedParts = String(this.previewStats.texturedParts);
    this.canvas.dataset.previewBaseSuit = this.previewStats.baseSuitVisible ? "visible" : "hidden";
    this.canvas.dataset.previewVrm = this.previewStats.vrmVisible ? "visible" : "fallback";
    this.canvas.dataset.previewHeightCm = String(Math.round(this.heightCm));
    this.canvas.dataset.previewHeightScale = (this.heightCm / DEFAULT_HEIGHT_CM).toFixed(3);
    updatePreviewLayerPanel(latestForgeData, this);
  }

  buildBaseSuit() {
    const ghost = new THREE.MeshStandardMaterial({
      color: BASE_SUIT_COLOR,
      emissive: BASE_SUIT_EMISSIVE,
      emissiveIntensity: 0.26,
      metalness: 0.08,
      roughness: 0.58,
      transparent: true,
      opacity: 0.62,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    this.ghostGroup.name = "base-suit-reference";
    const standMat = new THREE.MeshBasicMaterial({ color: 0x9a7b2c, transparent: true, opacity: 0.68 });
    const seamMat = new THREE.MeshBasicMaterial({ color: 0x154e55, transparent: true, opacity: 0.58 });
    const torso = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.24, 0.82, 32), ghost);
    torso.name = "base-suit-surface-torso";
    torso.renderOrder = 3;
    torso.position.y = 0.98;
    this.ghostGroup.add(torso);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.19, 32, 20), ghost);
    head.name = "base-suit-surface-head";
    head.renderOrder = 3;
    head.position.y = 1.58;
    this.ghostGroup.add(head);
    for (const [x, y, h, r] of [
      [-0.58, 0.86, 0.82, -0.2],
      [0.58, 0.86, 0.82, 0.2],
      [-0.17, 0.18, 0.78, 0],
      [0.17, 0.18, 0.78, 0],
    ]) {
      const limb = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.07, h, 20), ghost);
      limb.name = "base-suit-surface-limb";
      limb.renderOrder = 3;
      limb.position.set(x, y, -0.03);
      limb.rotation.z = r;
      this.ghostGroup.add(limb);
    }
    this.ghostGroup.traverse((obj) => {
      if (!obj.isMesh || obj.userData.baseSuitEdges) return;
      const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(obj.geometry, 32),
        new THREE.LineBasicMaterial({
          color: 0x0f5f68,
          transparent: true,
          opacity: 0.68,
          depthTest: false,
        }),
      );
      edges.name = `${obj.name || "base-suit"}-surface-lines`;
      edges.renderOrder = 3.5;
      edges.userData.baseSuitEdges = true;
      obj.add(edges);
    });
    const base = new THREE.Mesh(new THREE.TorusGeometry(0.72, 0.01, 8, 96), standMat);
    base.rotation.x = Math.PI / 2;
    base.position.y = PREVIEW_FLOOR_Y;
    this.standGroup.add(base);
    for (const y of [0.78, 1.16]) {
      const seam = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.004, 8, 80), seamMat);
      seam.rotation.x = Math.PI / 2;
      seam.position.set(0, y, 0);
      seam.renderOrder = 3.4;
      this.ghostGroup.add(seam);
    }
    const floor = new THREE.GridHelper(2.5, 12, 0x6f9291, 0xb7c8c5);
    floor.position.y = PREVIEW_FLOOR_Y;
    const floorMaterials = Array.isArray(floor.material) ? floor.material : [floor.material];
    for (const material of floorMaterials) {
      material.transparent = true;
      material.opacity = 0.34;
    }
    this.standGroup.add(floor);
    const spine = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 2.1, 12), standMat);
    spine.position.set(0, 0.62, -0.28);
    this.standGroup.add(spine);
    for (const [width, y, z] of [
      [1.18, 1.25, -0.28],
      [0.78, 0.76, -0.28],
    ]) {
      const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, width, 12), standMat);
      bar.rotation.z = Math.PI / 2;
      bar.position.set(0, y, z);
      this.standGroup.add(bar);
    }
    const guideMat = new THREE.LineBasicMaterial({
      color: 0x1c6f78,
      transparent: true,
      opacity: 0.78,
      depthTest: false,
    });
    const guideX = -1.02;
    const guideZ = 0.08;
    const guideTop = PREVIEW_FLOOR_Y + 1.96;
    const tick = 0.08;
    const guidePoints = [
      new THREE.Vector3(guideX, PREVIEW_FLOOR_Y, guideZ),
      new THREE.Vector3(guideX, guideTop, guideZ),
      new THREE.Vector3(guideX - tick, PREVIEW_FLOOR_Y, guideZ),
      new THREE.Vector3(guideX + tick, PREVIEW_FLOOR_Y, guideZ),
      new THREE.Vector3(guideX - tick, guideTop, guideZ),
      new THREE.Vector3(guideX + tick, guideTop, guideZ),
      new THREE.Vector3(guideX - tick * 0.6, (PREVIEW_FLOOR_Y + guideTop) / 2, guideZ),
      new THREE.Vector3(guideX + tick * 0.6, (PREVIEW_FLOOR_Y + guideTop) / 2, guideZ),
    ];
    const heightGuide = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(guidePoints), guideMat);
    heightGuide.name = "declared-height-guide";
    heightGuide.renderOrder = 8;
    this.standGroup.add(heightGuide);
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
      this.ghostGroup.visible = true;
      this.fitVrmToStand(model);
      this.setHeightCm(this.heightCm);
      this.previewStats.vrmVisible = true;
      this.publishPreviewStats();
    } catch (error) {
      this.vrmModel = null;
      this.boneMap = new Map();
      this.metricsCache = null;
      this.ghostGroup.visible = true;
      this.previewStats.vrmVisible = false;
      this.publishPreviewStats();
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
      obj.renderOrder = 2;
      const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
      obj.material = materials.map(
        () =>
          new THREE.MeshStandardMaterial({
            color: BODY_REFERENCE_COLOR,
            emissive: BODY_REFERENCE_EMISSIVE,
            emissiveIntensity: 0.08,
            metalness: 0.02,
            roughness: 0.82,
            transparent: true,
            opacity: 0.22,
            depthWrite: false,
            side: THREE.DoubleSide,
          }),
      );
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
    this.previewStats.heightCm = this.heightCm;
    this.updateCameraDistance();
    this.publishPreviewStats();
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
        disposeMaterial(object.material);
      });
      child.removeFromParent();
      child.geometry?.dispose?.();
      disposeMaterial(child.material);
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
    this.previewStats.armorParts = meshes.length;
    this.previewStats.fallbackParts = meshes.filter((mesh) => mesh.userData.meshSource === FALLBACK_MESH_SOURCE).length;
    this.previewStats.texturedParts = meshes.filter((mesh) => mesh.userData.texturePath).length;
    this.publishPreviewStats();
  }

  resize() {
    const width = this.canvas.clientWidth || 640;
    const height = this.canvas.clientHeight || 640;
    if (this.lastCanvasSize.width === width && this.lastCanvasSize.height === height) return;
    this.lastCanvasSize = { width, height };
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

armorStand = new ArmorStand(UI.canvas);

if (UI.heightCm) {
  UI.heightCm.addEventListener("input", () => syncHeightControls(UI.heightCm.value));
  UI.heightCm.addEventListener("change", () => syncHeightControls(UI.heightCm.value));
}
if (UI.heightRange) {
  UI.heightRange.addEventListener("input", () => syncHeightControls(UI.heightRange.value));
}
syncHeightControls(UI.heightCm?.value || DEFAULT_HEIGHT_CM);

function applyResult(data) {
  latestForgeData = data;
  const quest = questLinkOptions(data.recall_code || "");
  UI.recallCode.textContent = data.recall_code || "----";
  UI.questLink.href = quest.url;
  UI.questLink.classList.remove("disabled");
  UI.questLink.setAttribute("aria-disabled", "false");
  if (UI.questUrl) UI.questUrl.value = quest.url;
  if (UI.questUrlHint) UI.questUrlHint.textContent = quest.hint;
  renderAssetPipeline(data);
  updateTextureJobAvailability(data);
  UI.emptyStand.classList.add("hidden");
}

async function submitForge(event) {
  event.preventDefault();
  latestForgeData = null;
  if (UI.textureJobButton) UI.textureJobButton.textContent = "表面生成を試す";
  updateTextureJobAvailability(null);
  UI.button.disabled = true;
  syncHeightControls(UI.heightCm?.value);
  setStatus("生成条件を送信中...", "pending");
  try {
    const data = await fetchJson("/v1/suits/forge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    setStatus("人体基準の鎧立てを構築中...", "pending");
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
renderPreviewLegend();
renderAssetPipeline();
syncPreviewLegendPalette();
updateTextureJobAvailability();
updatePreviewLayerPanel(latestForgeData);
runtimeInfoPromise = loadRuntimeInfo();
UI.form.addEventListener("submit", submitForge);
for (const colorInput of [UI.primaryColor, UI.secondaryColor, UI.emissiveColor]) {
  colorInput?.addEventListener("input", syncPreviewLegendPalette);
}
UI.textureJobButton?.addEventListener("click", () => {
  startTextureGeneration().catch((error) => {
    setTextureJobState("error", "表面生成エラー", String(error?.message || error), 0);
    updateTextureJobAvailability(latestForgeData);
  });
});
