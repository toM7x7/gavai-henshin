import * as THREE from "../body-fit/vendor/three/build/three.module.js";
import { getGLTFLoaderClass, loadVrmScene } from "../body-fit/vrm-loader.js";
import {
  VRM_BONE_ALIASES,
  clampSurfaceOffsetForPart,
  effectiveFitFor,
  effectiveVrmAnchorFor,
  normalizeBoneName,
} from "../shared/armor-canon.js";
import { applyApproximateVrmTPose } from "../shared/auto-fit-engine.js";
import {
  isRuntimeRenderPlacementRecord,
  resolveRuntimeOffset,
  resolveRuntimeRotation,
  resolveRuntimeTargetSize,
} from "../shared/runtime-placement-resolver.js";
import {
  EXHIBITION_OPERATOR_COPY,
  operatorStateColorGuide,
  operatorStateLabel,
} from "../shared/exhibition-copy.js";

const PARTS = [
  ["helmet", "ヘルメット", true],
  ["chest", "胸部装甲", true],
  ["back", "背面ユニット", true],
  ["waist", "ベルト", true],
  ["left_shoulder", "左肩", true],
  ["right_shoulder", "右肩", true],
  ["left_upperarm", "左上腕", true],
  ["right_upperarm", "右上腕", true],
  ["left_forearm", "左腕甲", true],
  ["right_forearm", "右腕甲", true],
  ["left_hand", "左手甲", true],
  ["right_hand", "右手甲", true],
  ["left_thigh", "左太腿", true],
  ["right_thigh", "右太腿", true],
  ["left_shin", "左すね", true],
  ["right_shin", "右すね", true],
  ["left_boot", "左ブーツ", true],
  ["right_boot", "右ブーツ", true],
];

const VARIANT_DISPLAY_LABELS_JA = new Map([
  ["base", "標準ヒーローフィット"],
  ["sleek", "ライン重視"],
  ["bold", "装甲強調"],
  ["Base hero fit", "標準ヒーローフィット"],
  ["Sleek line variant", "ライン重視"],
  ["Bold armored variant", "装甲強調"],
]);

const DEFAULT_HEIGHT_CM = 170;
const MIN_HEIGHT_CM = 90;
const MAX_HEIGHT_CM = 230;
const DEFAULT_VRM_PATH = "viewer/assets/vrm/default.vrm";
const DEFAULT_VARIANT_CATALOG_PATH = "viewer/assets/armor-parts/variant_catalog.json";
const AUTO_VARIANT_VALUE = "__auto__";
const DEFAULT_QUEST_DEV_PORT = 5173;
const TEXTURE_PROVIDER_PROFILE = "nano_banana";
const BODY_REFERENCE_COLOR = 0xe6c7a6;
const BODY_REFERENCE_EMISSIVE = 0x2a1710;
const BASE_SUIT_COLOR = 0x52777e;
const BASE_SUIT_EMISSIVE = 0x10292c;
const ARMOR_PREVIEW_RED = 0xd93632;
const PREVIEW_FLOOR_Y = -0.43;
const FALLBACK_MESH_SOURCE = "seed_proxy_fallback";
const MIN_RENDERABLE_MESH_SIZE = 0.002;
const ARMOR_ASSET_LOAD_CONCURRENCY = 4;
const FORGE_DISPLAY_ARM_POSE_CHAINS = Object.freeze([
  { bone: "leftUpperArm", childBone: "leftLowerArm", outward: 0.62, down: -0.78, forward: 0.06, strength: 0.96 },
  { bone: "leftLowerArm", childBone: "leftHand", outward: 0.34, down: -0.93, forward: 0.08, strength: 0.9 },
  { bone: "rightUpperArm", childBone: "rightLowerArm", outward: 0.62, down: -0.78, forward: 0.06, strength: 0.96 },
  { bone: "rightLowerArm", childBone: "rightHand", outward: 0.34, down: -0.93, forward: 0.08, strength: 0.9 },
]);
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
const EXPECTED_ARMOR_PARTS = PARTS.map(([id]) => id);
const PART_LABELS = new Map(PARTS.map(([id, label]) => [id, label]));
const PART_DISPLAY_LABELS = new Map([
  ["helmet", "ヘルメット"],
  ["chest", "胸部装甲"],
  ["back", "背面ユニット"],
  ["waist", "ベルト"],
  ["left_shoulder", "左肩"],
  ["right_shoulder", "右肩"],
  ["left_upperarm", "左上腕"],
  ["right_upperarm", "右上腕"],
  ["left_forearm", "左前腕"],
  ["right_forearm", "右前腕"],
  ["left_hand", "左手甲"],
  ["right_hand", "右手甲"],
  ["left_thigh", "左太腿"],
  ["right_thigh", "右太腿"],
  ["left_shin", "左すね"],
  ["right_shin", "右すね"],
  ["left_boot", "左ブーツ"],
  ["right_boot", "右ブーツ"],
]);
const PREVIEW_QA_GAP_WARN_M = 0.08;
const PREVIEW_QA_THIN_RATIO_WARN = 0.18;
const PREVIEW_QA_BOOT_FLOAT_WARN_M = 0.035;
const PREVIEW_QA_WAIST_GAP_WARN_M = 0.055;
const PREVIEW_QA_CONTINUITY_WARN_M = 0.09;
const PREVIEW_QA_BACK_THICKNESS_RATIO_WARN = 0.82;
const VISUAL_DENSITY_P0_PARTS = new Set([
  "helmet",
  "chest",
  "back",
  "waist",
  "left_shoulder",
  "right_shoulder",
  "left_shin",
  "right_shin",
  "left_boot",
  "right_boot",
]);
const VISUAL_DENSITY_MIN_P0_SLOTS = 2;
const VISUAL_DENSITY_MIN_P0_VARIANTS = 2;
const PREVIEW_VIEW_PRESETS = Object.freeze({
  front: { label: "正面", yaw: 0, pitch: 0, zoom: 1 },
  left: { label: "左側", yaw: -Math.PI / 2, pitch: 0.02, zoom: 1.06 },
  back: { label: "背面", yaw: Math.PI, pitch: 0.02, zoom: 1.05 },
  right: { label: "右側", yaw: Math.PI / 2, pitch: 0.02, zoom: 1.06 },
});

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
  statusHelp: document.getElementById("forgeStatusHelp"),
  questLink: document.getElementById("questLink"),
  exhibitionSummary: document.getElementById("exhibitionSummary"),
  exhibitionCode: document.getElementById("exhibitionCode"),
  exhibitionHeight: document.getElementById("exhibitionHeight"),
  exhibitionVariant: document.getElementById("exhibitionVariant"),
  exhibitionQuestLink: document.getElementById("exhibitionQuestLink"),
  replaySaveLink: document.getElementById("replaySaveLink"),
  exhibitionHint: document.getElementById("exhibitionHint"),
  questUrl: document.getElementById("questUrl"),
  questUrlHint: document.getElementById("questUrlHint"),
  assetPipeline: document.getElementById("assetPipeline"),
  assetPipelineTitle: document.getElementById("assetPipelineTitle"),
  assetPipelineDetail: document.getElementById("assetPipelineDetail"),
  proxyWarning: document.getElementById("proxyWarning"),
  modelerHandoff: document.getElementById("modelerHandoff"),
  modelerHandoffTitle: document.getElementById("modelerHandoffTitle"),
  modelerHandoffDetail: document.getElementById("modelerHandoffDetail"),
  modelerBlueprintUrl: document.getElementById("modelerBlueprintUrl"),
  textureJobPanel: document.getElementById("textureJobPanel"),
  textureQuickAction: document.getElementById("textureQuickAction"),
  textureQuickButton: document.getElementById("textureQuickButton"),
  textureQuickDetail: document.getElementById("textureQuickDetail"),
  textureJobButton: document.getElementById("textureJobButton"),
  textureJobTitle: document.getElementById("textureJobTitle"),
  textureJobDetail: document.getElementById("textureJobDetail"),
  textureJobMeter: document.getElementById("textureJobMeter"),
  serviceConfigPanel: document.getElementById("serviceConfigPanel"),
  serviceConfigTitle: document.getElementById("serviceConfigTitle"),
  serviceConfigDetail: document.getElementById("serviceConfigDetail"),
  resultDetails: document.querySelector(".result-details"),
  supportDetails: Array.from(document.querySelectorAll(".support-details")),
  standControls: document.getElementById("standControls"),
  resetViewButton: document.getElementById("resetViewButton"),
  zoomOutButton: document.getElementById("zoomOutButton"),
  zoomInButton: document.getElementById("zoomInButton"),
  spinToggle: document.getElementById("spinToggle"),
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
let localVariantCatalog = null;
let localVariantCatalogStatus = "pending";
let textureJobPollTimer = null;
let textureJobStartedAt = 0;
let armorStand = null;
let previewLayerPanel = null;
const manualVariantOverrides = new Set();
const textureLoader = new THREE.TextureLoader();

function localConfigValue(key) {
  try {
    return window.localStorage?.getItem(key) || "";
  } catch {
    return "";
  }
}

function cleanBaseUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw, window.location.origin);
    if (url.protocol !== "http:" && url.protocol !== "https:") return "";
    if (raw.startsWith("/") && !raw.startsWith("//")) return url.pathname.replace(/\/+$/, "");
    return url.toString().replace(/\/+$/, "");
  } catch {
    return "";
  }
}

function serviceConfigValue(queryName, metaName, storageKey) {
  const query = new URLSearchParams(window.location.search).get(queryName) || "";
  const meta = document.querySelector(`meta[name="${metaName}"]`)?.content || "";
  return cleanBaseUrl(query || meta || localConfigValue(storageKey));
}

const SERVICE_CONFIG = Object.freeze({
  apiBase: serviceConfigValue("apiBase", "gavai-api-base", "gavai.apiBase"),
  assetBase: serviceConfigValue("assetBase", "gavai-asset-base", "gavai.assetBase"),
});

function useExhibitionMode() {
  const params = new URLSearchParams(window.location.search);
  return params.get("mode") === "exhibition" || params.get("exhibition") === "1";
}

const EXHIBITION_MODE = useExhibitionMode();

function resolveServicePath(path, base) {
  const raw = String(path || "").replace(/\\/g, "/");
  if (!base || /^(https?:|data:|blob:)/i.test(raw)) return raw;
  const suffix = raw.startsWith("/") ? raw : `/${raw}`;
  return `${base}${suffix}`;
}

function normalizePath(path) {
  const raw = String(path || "").replace(/\\/g, "/");
  if (/^(https?:|data:|blob:)/i.test(raw)) return raw;
  return resolveServicePath(raw.startsWith("/") ? raw : `/${raw}`, SERVICE_CONFIG.assetBase);
}

async function fetchJson(path, options = {}) {
  const response = await fetch(resolveServicePath(path, SERVICE_CONFIG.apiBase), options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.ok === false) {
    throw new Error(data.error || `${path} failed with ${response.status}`);
  }
  return data;
}

function renderServiceConfig() {
  if (!UI.serviceConfigTitle || !UI.serviceConfigDetail) return;
  const api = SERVICE_CONFIG.apiBase || "同一オリジン";
  const assets = SERVICE_CONFIG.assetBase || "同一オリジン";
  UI.serviceConfigTitle.textContent = SERVICE_CONFIG.apiBase || SERVICE_CONFIG.assetBase
    ? "外部接続設定を使用中"
    : "ローカル同一オリジン";
  UI.serviceConfigDetail.textContent = `API: ${api} / アセット: ${assets}`;
}

function isLocalHost(hostname) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

async function loadRuntimeInfo() {
  if (!latestForgeData) setStatus("ローカル実行環境を確認中...", "pending");
  try {
    runtimeInfo = await fetchJson("/api/runtime-info");
  } catch (error) {
    console.warn(`runtime-info unavailable: ${error?.message || error}`);
    runtimeInfo = null;
  }
  if (!latestForgeData) setStatus(EXHIBITION_OPERATOR_COPY.forge.statusIdle, "pending");
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
  const stateLabel = operatorStateLabel(state);
  const colorGuide = operatorStateColorGuide(state);
  UI.status.dataset.operatorStateLabel = stateLabel;
  UI.status.setAttribute("aria-label", `${stateLabel}: ${text}`);
  UI.status.title = colorGuide;
  if (UI.statusHelp) {
    UI.statusHelp.textContent = `${stateLabel} / ${colorGuide}`;
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function hashString(value) {
  let hash = 2166136261;
  const raw = String(value || "");
  for (let index = 0; index < raw.length; index += 1) {
    hash ^= raw.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function fitVector(value, fallback) {
  return [0, 1, 2].map((index) => numberOr(Array.isArray(value) ? value[index] : undefined, fallback[index]));
}

function optionalVector(value) {
  if (Array.isArray(value) && value.length >= 3) {
    return [numberOr(value[0], 0), numberOr(value[1], 0), numberOr(value[2], 0)];
  }
  if (value && typeof value === "object") {
    return [numberOr(value.x, 0), numberOr(value.y, 0), numberOr(value.z, 0)];
  }
  return null;
}

function firstVector(...values) {
  for (const value of values) {
    const vector = optionalVector(value);
    if (vector) return vector;
  }
  return null;
}

function firstNumber(...values) {
  for (const value of values) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function firstString(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

function stringArray(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (typeof item === "string") return item.trim();
      if (item && typeof item === "object") {
        return firstString(item.topping_slot, item.slot, item.name, item.proposal_id);
      }
      return "";
    })
    .filter(Boolean);
}

function sidecarMetadataForModule(part, module = {}) {
  const sidecar = module?.modeler_sidecar
    || module?.sidecar_metadata
    || module?.sidecar
    || module?.metadata?.modeler_sidecar
    || {};
  const attachment = module?.vrm_attachment || sidecar?.vrm_attachment || {};
  const anchor = module?.vrm_anchor || {};
  const auxiliarySlots = Array.isArray(sidecar?.auxiliary_part_suggestions)
    ? sidecar.auxiliary_part_suggestions
        .map((item) => firstString(item?.proposal_id, item?.slot, item?.parent_module))
        .filter(Boolean)
    : [];
  const toppingSlots = stringArray(
    module?.topping_slots
    || sidecar?.topping_slots
    || module?.toppings
    || auxiliarySlots,
  );
  const placementOffset = firstVector(
    module?.attachment_offset_m,
    attachment?.offset_m,
    sidecar?.attachment_offset_m,
    sidecar?.vrm_attachment?.offset_m,
    module?.attachment_offset_target_m,
    sidecar?.attachment_offset_target_m,
    anchor?.offset,
  );
  const offsetLimitM = firstNumber(
    module?.attachment_offset_target_m,
    sidecar?.attachment_offset_target_m,
    sidecar?.offset_limit_m,
  );
  const hasExplicitSidecarOffset = Boolean(
    placementOffset
    || module?.attachment_offset_target_m
    || module?.attachment_offset_m
    || attachment?.offset_m
    || sidecar?.attachment_offset_target_m
    || sidecar?.attachment_offset_m
    || sidecar?.vrm_attachment,
  );
  return {
    part,
    offsetTarget: placementOffset,
    placementOffset,
    offsetLimitM,
    toppingSlots,
    variantKey: firstString(module?.variant_key, module?.asset_variant_key, module?.variant?.key, sidecar?.variant_key),
    bodyFollowMode: firstString(sidecar?.body_follow_profile?.mode, module?.body_follow_profile?.mode),
    groundContactProfile: sidecar?.ground_contact_profile || module?.ground_contact_profile || null,
    source: placementOffset
      ? hasExplicitSidecarOffset || String(module?.asset_ref || "").includes("/armor-parts/")
        ? "modeler_sidecar"
        : "module_vrm_anchor"
      : "none",
  };
}

function variantCatalogCandidatesFromData(data = latestForgeData) {
  return [
    localVariantCatalog,
    data?.preview?.variant_catalog,
    data?.preview?.asset_pipeline?.variant_catalog,
    data?.asset_pipeline?.variant_catalog,
    data?.variant_catalog,
    data?.suitspec?.asset_pipeline?.variant_catalog,
  ];
}

function variantCatalogFromData(data = latestForgeData) {
  return variantCatalogCandidatesFromData(data).find((candidate) => candidate && typeof candidate === "object") || null;
}

async function loadLocalVariantCatalog() {
  localVariantCatalogStatus = "loading";
  try {
    const catalog = await fetchJson(normalizePath(DEFAULT_VARIANT_CATALOG_PATH));
    localVariantCatalog = {
      ...catalog,
      path: catalog.path || DEFAULT_VARIANT_CATALOG_PATH,
      status: catalog.status || "ready",
    };
    localVariantCatalogStatus = "ready";
  } catch (error) {
    console.warn(`variant catalog unavailable: ${error?.message || error}`);
    localVariantCatalog = null;
    localVariantCatalogStatus = "error";
  }
  renderPartGrid();
  renderAssetPipeline(latestForgeData);
  updatePreviewLayerPanel(latestForgeData);
  return localVariantCatalog;
}

function variantCatalogModulesFromData(data = latestForgeData) {
  const catalog = variantCatalogFromData(data);
  return catalog?.selected_modules || catalog?.modules || {};
}

function variantCatalogModuleForPart(part, data = latestForgeData) {
  const modules = variantCatalogModulesFromData(data);
  return modules?.[part] || null;
}

function catalogToppingSlotsForPart(part, data = latestForgeData) {
  return catalogToppingSlotEntriesForPart(part, data).map((entry) => entry.slot);
}

function catalogVariantKeysForPart(part, data = latestForgeData) {
  const variants = variantCatalogModuleForPart(part, data)?.variants;
  if (!Array.isArray(variants)) return [];
  return variants
    .map((variant) => firstString(variant?.variant_key, variant?.key))
    .filter(Boolean);
}

function catalogVariantRecordsForPart(part, data = latestForgeData) {
  const variants = variantCatalogModuleForPart(part, data)?.variants;
  return Array.isArray(variants) ? variants.filter((variant) => variant && typeof variant === "object") : [];
}

function catalogVariantRecordForPart(part, variantKey, data = latestForgeData) {
  const key = firstString(variantKey);
  if (!key) return null;
  return catalogVariantRecordsForPart(part, data)
    .find((variant) => firstString(variant?.variant_key, variant?.key) === key) || null;
}

function variantSlugForPart(part, variantKey) {
  const key = firstString(variantKey);
  if (!key) return "";
  if (key.includes(":")) {
    const [module, slug] = key.split(":", 2);
    return module === part ? firstString(slug) : "";
  }
  return key;
}

function variantAssetRefForPart(part, variantKey, data = latestForgeData) {
  const key = firstString(variantKey);
  if (!key || key === AUTO_VARIANT_VALUE) return "";
  const record = catalogVariantRecordForPart(part, key, data);
  const declaredRef = firstString(record?.asset_ref, record?.assetRef);
  if (declaredRef) return declaredRef;
  const slug = variantSlugForPart(part, key);
  if (!slug || slug === "base") return `viewer/assets/armor-parts/${part}/${part}.glb`;
  return `viewer/assets/armor-parts/${part}/variants/${slug}/${part}__${slug}.glb`;
}

function catalogToppingSlotEntriesForPart(part, data = latestForgeData) {
  const slots = variantCatalogModuleForPart(part, data)?.topping_slots;
  if (!Array.isArray(slots)) return [];
  return slots
    .map((slot) => {
      const name = typeof slot === "string"
        ? slot.trim()
        : firstString(slot?.topping_slot, slot?.slot, slot?.name, slot?.proposal_id);
      if (!name) return null;
      return {
        part,
        slot: name,
        label: `${part}:${name}`,
        conflictsWith: stringArray(slot?.conflicts_with),
      };
    })
    .filter(Boolean);
}

function catalogConflictLabel(part, conflict) {
  const value = firstString(conflict);
  if (!value) return "";
  return value.includes(":") ? value : `${part}:${value}`;
}

function shortCatalogPath(path) {
  const value = firstString(path);
  if (!value) return "catalog pending";
  const marker = "armor-parts/";
  const index = value.indexOf(marker);
  return index >= 0 ? value.slice(index) : value;
}

function variantCatalogStatsForRecords(records = previewRecordsFromData(), data = latestForgeData) {
  const catalog = variantCatalogFromData(data);
  const modules = variantCatalogModulesFromData(data);
  const slotEntries = records.flatMap(([part]) => catalogToppingSlotEntriesForPart(part, data));
  const variantKeys = records.flatMap(([part]) => catalogVariantKeysForPart(part, data));
  const conflictPairs = slotEntries.flatMap((entry) => entry.conflictsWith
    .map((conflict) => `${entry.label}->${catalogConflictLabel(entry.part, conflict)}`)
    .filter((label) => !label.endsWith("->")));
  const conflictSlots = Array.from(new Set(slotEntries
    .filter((entry) => entry.conflictsWith.length)
    .map((entry) => entry.label)));
  const path = firstString(catalog?.path, catalog?.catalog_path, catalog?.source_path, catalog ? DEFAULT_VARIANT_CATALOG_PATH : "");
  return {
    status: firstString(catalog?.status, catalog ? "ready" : "pending"),
    path,
    shortPath: shortCatalogPath(path),
    selectedPartCount: Number(catalog?.selected_part_count || records.length || 0),
    selectedModuleCount: Number(catalog?.selected_module_count || Object.keys(modules || {}).length || 0),
    selectedSlotCount: Number(catalog?.selected_slot_count || slotEntries.length || 0),
    selectedVariantCount: Number(catalog?.selected_variant_count || variantKeys.length || 0),
    conflictCount: conflictPairs.length,
    conflictPairs,
    conflictSlots,
  };
}

function catalogDetailFeatureCountForPart(part, data = latestForgeData) {
  const variants = variantCatalogModuleForPart(part, data)?.variants;
  if (!Array.isArray(variants)) return 0;
  return variants.reduce((count, variant) => {
    const features = Array.isArray(variant?.detail_features) ? variant.detail_features : [];
    return count + features.filter((feature) => typeof feature === "string" && feature.trim()).length;
  }, 0);
}

function labeledVariantKey(part, key) {
  const value = firstString(key);
  if (!value) return "";
  return value.startsWith(`${part}:`) ? value : `${part}:${value}`;
}

function offsetTargetLabel(metadata) {
  if (!metadata?.offsetTarget) return "";
  return `${metadata.part}:${metadata.offsetTarget.map((value) => value.toFixed(3)).join(",")}`;
}

function compactDataList(values, limit = 3, empty = "none") {
  const items = Array.from(new Set((values || []).filter(Boolean)));
  if (!items.length) return empty;
  if (items.length <= limit) return items.join(" / ");
  return `${items.slice(0, limit).join(" / ")} +${items.length - limit}`;
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

function segmentFrameQuaternion(start, end) {
  if (!start || !end) return null;
  const yAxis = end.clone().sub(start);
  if (!Number.isFinite(yAxis.lengthSq()) || yAxis.lengthSq() < 1e-8) return null;
  yAxis.normalize();
  const zAxis = new THREE.Vector3(0, 0, 1);
  zAxis.sub(yAxis.clone().multiplyScalar(zAxis.dot(yAxis)));
  if (zAxis.lengthSq() < 1e-8) {
    zAxis.set(0, 1, 0);
    zAxis.sub(yAxis.clone().multiplyScalar(zAxis.dot(yAxis)));
  }
  if (!Number.isFinite(zAxis.lengthSq()) || zAxis.lengthSq() < 1e-8) return null;
  zAxis.normalize();
  const xAxis = new THREE.Vector3().crossVectors(yAxis, zAxis).normalize();
  zAxis.crossVectors(xAxis, yAxis).normalize();
  const matrix = new THREE.Matrix4();
  matrix.makeBasis(xAxis, yAxis, zAxis);
  return new THREE.Quaternion().setFromRotationMatrix(matrix).normalize();
}

function addOrientedOffset(vector, offset = [0, 0, 0], quaternion = null) {
  if (!quaternion) return addOffset(vector, offset);
  const localOffset = new THREE.Vector3(
    numberOr(offset[0], 0),
    numberOr(offset[1], 0),
    numberOr(offset[2], 0),
  ).applyQuaternion(quaternion);
  return vector.clone().add(localOffset);
}

function wornPlacementOffsetForPart(part, offset) {
  const vector = optionalVector(offset);
  if (!vector) return null;
  return clampSurfaceOffsetForPart(part, vector, "vrm");
}

function wornDepthClamp(part, deltaZ, shoulderWidth) {
  const shoulder = Math.max(numberOr(shoulderWidth, 0.68), 0.3);
  if (part === "chest") return clamp(deltaZ, shoulder * 0.070, shoulder * 0.145);
  if (part === "back") return clamp(deltaZ, -shoulder * 0.205, -shoulder * 0.085);
  if (part === "waist") return clamp(deltaZ, -shoulder * 0.030, shoulder * 0.055);
  if (part.includes("boot")) return clamp(deltaZ, -shoulder * 0.025, shoulder * 0.045);
  return deltaZ;
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

function comparableVariantKeyForPart(part, value) {
  const key = firstString(value);
  if (!key || key === AUTO_VARIANT_VALUE) return "";
  return key.includes(":") ? key : `${part}:${key}`;
}

function comparableAssetRef(value) {
  const ref = firstString(value);
  if (!ref) return "";
  return ref.replace(/\\/g, "/").replace(/[?#].*$/, "").replace(/^\/+/, "");
}

function variantDisplayNameJa(part, variantKey, displayName = "") {
  const rawDisplay = firstString(displayName);
  const key = comparableVariantKeyForPart(part, variantKey || rawDisplay);
  const slug = variantSlugForPart(part, key);
  return VARIANT_DISPLAY_LABELS_JA.get(key)
    || VARIANT_DISPLAY_LABELS_JA.get(slug)
    || VARIANT_DISPLAY_LABELS_JA.get(rawDisplay)
    || rawDisplay
    || slug
    || firstString(variantKey).split(":").pop()
    || "自動選定";
}

function isRuntimePlacementRecord(value) {
  return isRuntimeRenderPlacementRecord(value);
}

function runtimePlacementMatchesPreviewVariant(part, placement, variantKey = "", assetRef = "") {
  if (!isRuntimePlacementRecord(placement)) return false;
  const placementPart = firstString(placement.part);
  if (placementPart && placementPart !== part) return false;
  const key = comparableVariantKeyForPart(part, variantKey);
  const placementKey = comparableVariantKeyForPart(
    part,
    firstString(placement.selected_variant_key, placement.variant_key, placement.modeler_sidecar_variant_key),
  );
  if (placementKey && key && placementKey !== key) return false;
  const asset = comparableAssetRef(assetRef);
  const placementAsset = comparableAssetRef(placement.asset_ref);
  if (asset && placementAsset && placementAsset !== asset) return false;
  return true;
}

function placementFromVariantPlacementTable(table, part, variantKey, assetRef = "") {
  if (!table || typeof table !== "object") return null;
  const scoped = table[part] && typeof table[part] === "object" && table[part] !== table
    ? placementFromVariantPlacementTable(table[part], part, variantKey, assetRef)
    : null;
  if (scoped) return scoped;
  if (runtimePlacementMatchesPreviewVariant(part, table, variantKey, assetRef)) return table;
  const key = comparableVariantKeyForPart(part, variantKey);
  const slug = variantSlugForPart(part, key);
  const asset = comparableAssetRef(assetRef);
  const directCandidates = [
    table[key],
    table[slug],
    table[assetRef],
    table[asset],
  ];
  for (const placement of directCandidates) {
    if (runtimePlacementMatchesPreviewVariant(part, placement, variantKey, assetRef)) return placement;
  }
  const values = Array.isArray(table) ? table : Object.values(table);
  return values.find((placement) => runtimePlacementMatchesPreviewVariant(part, placement, variantKey, assetRef)) || null;
}

function variantRuntimePlacementForPreviewPart(part, variantKey, assetRef = "", module = {}) {
  const key = comparableVariantKeyForPart(part, variantKey);
  if (!key) return null;
  const tables = [
    module?.variant_render_placements,
    module?.runtime_placements_by_variant,
    latestForgeData?.preview?.modules?.[part]?.variant_render_placements,
    latestForgeData?.preview?.variant_render_placements,
    latestForgeData?.preview?.asset_pipeline?.variant_render_placements,
    latestForgeData?.asset_pipeline?.variant_render_placements,
    latestForgeData?.preview?.visual_layers?.armor_overlay?.variant_render_placements,
    latestForgeData?.visual_layers?.armor_overlay?.variant_render_placements,
  ];
  for (const table of tables) {
    const placement = placementFromVariantPlacementTable(table, part, key, assetRef);
    if (placement) return placement;
  }
  return null;
}

function previewVariantKeyForRuntimePlacement(part, module = {}) {
  return comparableVariantKeyForPart(
    part,
    firstString(
      module?.selected_variant_key,
      module?.variant_key,
      latestForgeData?.preview?.modules?.[part]?.selected_variant_key,
      latestForgeData?.preview?.modules?.[part]?.variant_key,
      latestForgeData?.visual_layers?.armor_overlay?.selected_variant_keys?.[part],
      latestForgeData?.preview?.visual_layers?.armor_overlay?.selected_variant_keys?.[part],
      latestSelectedVariantKeyForPart(part),
    ),
  );
}

function previewAssetRefForRuntimePlacement(part, variantKey, module = {}) {
  return firstString(
    module?.asset_ref,
    latestForgeData?.preview?.modules?.[part]?.asset_ref,
    latestForgeData?.visual_layers?.armor_overlay?.asset_refs?.[part],
    latestForgeData?.preview?.visual_layers?.armor_overlay?.asset_refs?.[part],
    variantAssetRefForPart(part, variantKey, latestForgeData),
  );
}

function runtimePlacementForPreviewPart(part, module = {}) {
  const selectedKey = previewVariantKeyForRuntimePlacement(part, module);
  const selectedAssetRef = previewAssetRefForRuntimePlacement(part, selectedKey, module);
  const variantPlacement = variantRuntimePlacementForPreviewPart(part, selectedKey, selectedAssetRef, module);
  if (variantPlacement) return variantPlacement;
  const candidates = [
    module?.runtime_placement,
    module?.render_placement,
    latestForgeData?.preview?.modules?.[part]?.runtime_placement,
    latestForgeData?.preview?.render_placements?.[part],
    latestForgeData?.preview?.asset_pipeline?.render_placements?.[part],
    latestForgeData?.asset_pipeline?.render_placements?.[part],
    latestForgeData?.preview?.visual_layers?.armor_overlay?.render_placements?.[part],
    latestForgeData?.visual_layers?.armor_overlay?.render_placements?.[part],
  ];
  return candidates.find((placement) => (
    runtimePlacementMatchesPreviewVariant(part, placement, selectedKey, selectedAssetRef)
  )) || null;
}

function writeRuntimePlacementForPart(map, part, placement) {
  if (!map || typeof map !== "object") return;
  if (placement) {
    map[part] = { ...placement };
  } else {
    delete map[part];
  }
}

function setRuntimePlacementForPreviewPart(part, placement) {
  const module = latestForgeData?.preview?.modules?.[part];
  if (module && typeof module === "object") {
    if (placement) {
      module.runtime_placement = { ...placement };
    } else {
      delete module.runtime_placement;
    }
  }
  writeRuntimePlacementForPart(latestForgeData?.preview?.render_placements, part, placement);
  writeRuntimePlacementForPart(latestForgeData?.preview?.asset_pipeline?.render_placements, part, placement);
  writeRuntimePlacementForPart(latestForgeData?.asset_pipeline?.render_placements, part, placement);
  writeRuntimePlacementForPart(latestForgeData?.preview?.visual_layers?.armor_overlay?.render_placements, part, placement);
  writeRuntimePlacementForPart(latestForgeData?.visual_layers?.armor_overlay?.render_placements, part, placement);
}

function vector3FromRuntimeVector(value) {
  const vector = optionalVector(value);
  if (!vector) return null;
  return new THREE.Vector3(vector[0], vector[1], vector[2]);
}

function runtimeTargetSizeForPreviewPart(part, module = {}) {
  const placement = runtimePlacementForPreviewPart(part, module);
  const targetArray = resolveRuntimeTargetSize({
    placement,
    fallback: [0, 0, 0],
    mode: "web_preview_parity",
  });
  const target = vector3FromRuntimeVector(targetArray);
  if (!target) return null;
  return target.x > 0 && target.y > 0 && target.z > 0 ? target : null;
}

function runtimeOffsetForPreviewPart(part, module = {}) {
  const placement = runtimePlacementForPreviewPart(part, module);
  return resolveRuntimeOffset({
    part,
    placement,
    mode: "web_preview_parity",
  });
}

function runtimeRotationForPreviewPart(part, module = {}) {
  const placement = runtimePlacementForPreviewPart(part, module);
  return resolveRuntimeRotation({
    placement,
    mode: "web_preview_parity",
  });
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
  renderExhibitionSummary(latestForgeData);
  return height;
}

function selectedParts() {
  return Array.from(UI.partGrid.querySelectorAll("input[type='checkbox']:checked")).map((input) => input.value);
}

function partVariantSelect(part) {
  return UI.partGrid?.querySelector(`select[data-part-variant="${part}"]`) || null;
}

function latestSelectedVariantKeyForPart(part) {
  return firstString(
    latestForgeData?.preview?.modules?.[part]?.selected_variant_key,
    latestForgeData?.asset_pipeline?.variant_catalog?.selected_modules?.[part]?.selected_variant_key,
    latestForgeData?.visual_layers?.armor_overlay?.selected_variant_keys?.[part],
  );
}

function selectedVariantKeyForPart(part, options = {}) {
  const value = firstString(partVariantSelect(part)?.value);
  const explicit = value && value !== AUTO_VARIANT_VALUE && manualVariantOverrides.has(part);
  if (options.explicitOnly) return explicit ? value : "";
  if (value && value !== AUTO_VARIANT_VALUE) return value;
  return latestSelectedVariantKeyForPart(part) || firstString(catalogVariantKeysForPart(part)[0]) || `${part}:base`;
}

function selectedVariantMetaForPart(part, options = {}) {
  const selectedKey = selectedVariantKeyForPart(part, options);
  if (!selectedKey) return null;
  const selectedVariant = catalogVariantRecordForPart(part, selectedKey);
  return {
    part,
    selected_variant_key: selectedKey,
    display_name: firstString(selectedVariant?.display_name, selectedKey),
    display_name_ja: variantDisplayNameJa(part, selectedKey, selectedVariant?.display_name),
    selection_mode: manualVariantOverrides.has(part) ? "manual_override" : "auto",
  };
}

function selectedVariantMap(options = {}) {
  return Object.fromEntries(
    selectedParts()
      .map((part) => [part, selectedVariantKeyForPart(part, options)])
      .filter(([, key]) => key),
  );
}

function selectedVariantRecords(options = {}) {
  return selectedParts().map((part) => selectedVariantMetaForPart(part, options)).filter(Boolean);
}

function selectedVariantSummary(limit = 4) {
  const records = selectedVariantRecords();
  if (!records.length) return "none";
  return compactDataList(
    records.map((record) => `${record.part}:${record.selected_variant_key.split(":").pop()}`),
    limit,
    "none",
  );
}

function selectedVariantSummaryJa(limit = 4) {
  const records = selectedVariantRecords();
  if (!records.length) return "自動選定";
  return compactDataList(
    records.map((record) => {
      const variantName = firstString(record.display_name_ja, record.display_name, record.selected_variant_key).split(":").pop();
      return `${partLabel(record.part)}:${variantName}`;
    }),
    limit,
    "自動選定",
  );
}

function partLabel(part) {
  return PART_DISPLAY_LABELS.get(part) || PART_LABELS.get(part) || part;
}

function compactPartList(parts, limit = 4) {
  const labels = parts.map(partLabel);
  if (labels.length <= limit) return labels.join(" / ") || "なし";
  return `${labels.slice(0, limit).join(" / ")} +${labels.length - limit}`;
}

function qaSourcePartIds(data, records) {
  const recordIds = records.map(([part]) => part);
  if (recordIds.length) return recordIds;
  if (data?.preview?.modules || data?.suitspec?.modules || data?.modules) return recordIds;
  return selectedParts();
}

function coverageQaFor(data = latestForgeData, records = previewRecordsFromData(data)) {
  const sourceIds = qaSourcePartIds(data, records);
  const selected = new Set(sourceIds);
  const selectedCount = selected.size;
  const missingParts = EXPECTED_ARMOR_PARTS.filter((part) => !selected.has(part));
  const selectedUiCount = selectedParts().length;
  const unresolvedSelected = data && selectedUiCount > records.length ? selectedUiCount - records.length : 0;
  const state = unresolvedSelected > 0 ? "error" : missingParts.length ? "planned" : "ready";
  const title = missingParts.length
    ? `${selectedCount}/${EXPECTED_ARMOR_PARTS.length}パーツ`
    : `全${EXPECTED_ARMOR_PARTS.length}パーツ`;
  const detail = unresolvedSelected > 0
    ? `生成欠落候補: UI選択${selectedUiCount} / preview ${records.length}`
    : missingParts.length
    ? `不足候補: ${compactPartList(missingParts)}`
    : "上腕/太腿/手甲まで全身カバー対象です。";
  return {
    state,
    title,
    detail,
    selectedCount,
    expectedCount: EXPECTED_ARMOR_PARTS.length,
    missingParts,
    unresolvedSelected,
  };
}

function vectorFromArray(value) {
  return Array.isArray(value) && value.length >= 3
    ? new THREE.Vector3(numberOr(value[0], 0), numberOr(value[1], 0), numberOr(value[2], 0))
    : null;
}

function scaledPreviewSize(mesh) {
  const source = mesh?.userData?.sourceSize;
  const sourceSize = source?.isVector3 ? source : vectorFromArray(source);
  if (!sourceSize) return null;
  return new THREE.Vector3(
    Math.abs(sourceSize.x * mesh.scale.x),
    Math.abs(sourceSize.y * mesh.scale.y),
    Math.abs(sourceSize.z * mesh.scale.z),
  );
}

function thinRatioThresholdForPart(part) {
  if (part === "back") return 0.22;
  if (part === "chest" || part === "waist") return 0.18;
  if (part.includes("boot") || part.includes("hand")) return 0.16;
  return PREVIEW_QA_THIN_RATIO_WARN;
}

function fitQaForMesh(part, mesh, module = {}) {
  const actualSize = scaledPreviewSize(mesh);
  const targetSize = vectorFromArray(mesh?.userData?.fitTargetSize);
  const gapM = Math.max(0, numberOr(mesh?.userData?.fitGapM, 0));
  const sidecar = sidecarMetadataForModule(part, module);
  const referencePoint = vectorFromArray(mesh?.userData?.fitReferencePoint);
  const centerY = numberOr(mesh?.position?.y, 0);
  const bottomY = actualSize ? centerY - actualSize.y * 0.5 : centerY;
  const topY = actualSize ? centerY + actualSize.y * 0.5 : centerY;
  const bootContactDeltaM = part.includes("boot") && referencePoint
    ? Math.max(0, bottomY - referencePoint.y)
    : 0;
  const floorLiftM = part.includes("boot")
    ? Math.max(0, bottomY - PREVIEW_FLOOR_Y)
    : 0;
  const sideProfileRatio = actualSize
    ? actualSize.z / Math.max(actualSize.x, actualSize.y, 0.001)
    : 1;
  const thicknessRatio = actualSize && targetSize
    ? actualSize.z / Math.max(targetSize.z, 0.001)
    : 1;
  const warnings = [];
  if (gapM > PREVIEW_QA_GAP_WARN_M) warnings.push("gap");
  if (sideProfileRatio < thinRatioThresholdForPart(part)) warnings.push("thin");
  if (part.includes("boot") && Math.max(bootContactDeltaM, floorLiftM) > PREVIEW_QA_BOOT_FLOAT_WARN_M) warnings.push("boot_float");
  if (mesh?.userData?.fitPreview !== "vrm_bone_metrics") warnings.push("fallback_pose");
  return {
    part,
    label: partLabel(part),
    state: warnings.length ? "planned" : "ready",
    warnings,
    gapM,
    bootContactDeltaM,
    floorLiftM,
    bottomY,
    topY,
    centerY,
    sideProfileRatio,
    thicknessRatio,
    offsetAllowanceM: Math.max(0, numberOr(mesh?.userData?.fitOffsetAllowanceM, 0)),
    attachmentOffsetTargetM: sidecar.offsetTarget,
    variantKey: sidecar.variantKey,
    toppingSlots: sidecar.toppingSlots,
    meshSource: mesh?.userData?.meshSource || "unknown",
    fitPreview: mesh?.userData?.fitPreview || "unknown",
  };
}

function summarizePreviewFitQa(records, meshes) {
  const entries = records.map(([part, module], index) => fitQaForMesh(part, meshes[index], module)).filter(Boolean);
  const byPart = Object.fromEntries(entries.map((entry) => [entry.part, entry]));
  const gapParts = entries.filter((entry) => entry.warnings.includes("gap")).map((entry) => entry.part);
  const thinParts = entries.filter((entry) => entry.warnings.includes("thin")).map((entry) => entry.part);
  const bootFloatParts = entries.filter((entry) => entry.warnings.includes("boot_float")).map((entry) => entry.part);
  const fallbackPoseParts = entries.filter((entry) => entry.warnings.includes("fallback_pose")).map((entry) => entry.part);
  const warningParts = Array.from(new Set([...gapParts, ...thinParts, ...bootFloatParts, ...fallbackPoseParts]));
  return {
    state: warningParts.length ? "planned" : "ready",
    totalParts: entries.length,
    warningCount: warningParts.length,
    gapParts,
    thinParts,
    bootFloatParts,
    fallbackPoseParts,
    parts: byPart,
  };
}

function verticalSeamGap(upper, lower) {
  if (!upper || !lower) return null;
  return Math.max(0, upper.bottomY - lower.topY);
}

function continuityPairsForQa(parts) {
  return [
    ["chest", "waist", "chest-waist"],
    ["back", "waist", "back-waist"],
    ["waist", "left_thigh", "waist-left_thigh"],
    ["left_thigh", "left_shin", "left_thigh-left_shin"],
    ["left_shin", "left_boot", "left_shin-left_boot"],
    ["waist", "right_thigh", "waist-right_thigh"],
    ["right_thigh", "right_shin", "right_thigh-right_shin"],
    ["right_shin", "right_boot", "right_shin-right_boot"],
  ]
    .map(([upperPart, lowerPart, label]) => {
      const gapM = verticalSeamGap(parts?.[upperPart], parts?.[lowerPart]);
      return gapM === null ? null : { label, upperPart, lowerPart, gapM };
    })
    .filter(Boolean);
}

function structuralQaForFit(summary) {
  const parts = summary?.parts || {};
  const gapParts = summary?.gapParts || [];
  const bootFloatParts = summary?.bootFloatParts || [];
  const back = parts.back;
  const waist = parts.waist;
  const backThicknessRatio = numberOr(back?.thicknessRatio, 1);
  const waistGapM = Math.max(0, numberOr(waist?.gapM, 0));
  const continuityPairs = continuityPairsForQa(parts);
  const continuityBreaks = continuityPairs
    .filter((entry) => entry.gapM > PREVIEW_QA_CONTINUITY_WARN_M);
  const backThinParts = back && backThicknessRatio < PREVIEW_QA_BACK_THICKNESS_RATIO_WARN ? ["back"] : [];
  const waistGapParts = waistGapM > PREVIEW_QA_WAIST_GAP_WARN_M ? ["waist"] : [];
  const warningParts = Array.from(new Set([
    ...gapParts,
    ...bootFloatParts,
    ...backThinParts,
    ...waistGapParts,
    ...continuityBreaks.flatMap((entry) => [entry.upperPart, entry.lowerPart]),
  ]));
  return {
    state: warningParts.length ? "planned" : "ready",
    warningCount: warningParts.length,
    floatingParts: gapParts,
    bootFloatParts,
    backThinParts,
    waistGapParts,
    continuityBreaks,
    warningParts,
    backThicknessRatio,
    waistGapM,
    maxContinuityGapM: continuityPairs.reduce((max, entry) => Math.max(max, entry.gapM), 0),
  };
}

function sidecarQaFor(records = previewRecordsFromData(), data = latestForgeData) {
  const entries = records.map(([part, module]) => sidecarMetadataForModule(part, module));
  const offsetEntries = entries.filter((entry) => entry.offsetTarget);
  const focusEntries = offsetEntries.filter((entry) => entry.part === "back" || entry.part.includes("boot"));
  const detailEntries = focusEntries.length ? focusEntries : offsetEntries.slice(0, 4);
  const offsetTargets = offsetEntries.map(offsetTargetLabel).filter(Boolean);
  const sidecarToppingSlots = entries.flatMap((entry) => entry.toppingSlots.map((slot) => `${entry.part}:${slot}`));
  const catalogStats = variantCatalogStatsForRecords(records, data);
  const catalogToppingSlots = records.flatMap(([part]) => catalogToppingSlotEntriesForPart(part, data).map((entry) => entry.label));
  const toppingSlots = Array.from(new Set([...sidecarToppingSlots, ...catalogToppingSlots]));
  const sidecarVariantKeys = entries
    .map((entry) => labeledVariantKey(entry.part, entry.variantKey))
    .filter(Boolean);
  const catalogVariantKeys = records
    .flatMap(([part]) => catalogVariantKeysForPart(part, data).map((key) => labeledVariantKey(part, key)))
    .filter(Boolean);
  const variantKeys = Array.from(new Set([...sidecarVariantKeys, ...catalogVariantKeys]));
  const p0Records = records.filter(([part]) => VISUAL_DENSITY_P0_PARTS.has(part));
  const densityWarnings = p0Records
    .map(([part]) => {
      const slotCount = catalogToppingSlotsForPart(part, data).length;
      const variantCount = catalogVariantKeysForPart(part, data).length;
      const featureCount = catalogDetailFeatureCountForPart(part, data);
      if (slotCount < VISUAL_DENSITY_MIN_P0_SLOTS) return `${part}:slot`;
      if (variantCount < VISUAL_DENSITY_MIN_P0_VARIANTS) return `${part}:variant`;
      if (featureCount < variantCount * 2) return `${part}:detail`;
      return "";
    })
    .filter(Boolean);
  const offsetTitle = `位置 ${offsetEntries.length}/${records.length || 0}`;
  const toppingTitle = toppingSlots.length ? `枠 ${toppingSlots.length} / 衝突 ${catalogStats.conflictCount}` : "枠なし";
  const variantTitle = variantKeys.length ? `型 ${variantKeys.length}` : "型 既定";
  const densityTitle = densityWarnings.length
    ? `要設計 ${densityWarnings.length}`
    : `カタログ ${catalogStats.selectedModuleCount}部位`;
  return {
    state: offsetEntries.length ? "ready" : "planned",
    title: `位置基準 ${offsetEntries.length}/${records.length || 0}`,
    detail: detailEntries.length
      ? detailEntries.map(offsetTargetLabel).join(" / ")
      : "装着位置基準は未設定",
    offsetTitle,
    offsetDetail: detailEntries.length
      ? compactDataList(detailEntries.map(offsetTargetLabel), 3)
      : "背中/ブーツの位置基準は未設定",
    offsetState: offsetEntries.length ? "ready" : "planned",
    toppingTitle,
    toppingDetail: catalogStats.conflictCount
      ? `衝突 ${compactDataList(catalogStats.conflictPairs, 2)}`
      : `catalog枠 ${catalogToppingSlots.length} / sidecar ${sidecarToppingSlots.length} / 衝突なし`,
    toppingState: toppingSlots.length ? "ready" : "planned",
    variantTitle,
    variantDetail: `catalog型 ${catalogVariantKeys.length} / sidecar ${sidecarVariantKeys.length} / ${compactDataList(variantKeys, 2, "型キー未設定")}`,
    variantState: variantKeys.length ? "ready" : "planned",
    densityTitle,
    densityDetail: densityWarnings.length
      ? compactDataList(densityWarnings, 4, "細部パーツ契約は未設定")
      : `枠 ${catalogStats.selectedSlotCount} / 型 ${catalogStats.selectedVariantCount} / ${catalogStats.shortPath}`,
    densityState: densityWarnings.length ? "planned" : "ready",
    offsetParts: offsetEntries.map((entry) => entry.part),
    offsetTargets,
    toppingSlots,
    variantKeys,
    densityWarnings,
    catalogPath: catalogStats.path,
    catalogStatus: catalogStats.status,
    catalogSelectedPartCount: catalogStats.selectedPartCount,
    catalogSelectedModuleCount: catalogStats.selectedModuleCount,
    catalogSlotCount: catalogStats.selectedSlotCount,
    catalogVariantCount: catalogStats.selectedVariantCount,
    conflictCount: catalogStats.conflictCount,
    conflictPairs: catalogStats.conflictPairs,
    conflictSlots: catalogStats.conflictSlots,
  };
}

function layerReadabilityFor(stand, records, surface) {
  const armorParts = stand?.previewStats?.armorParts || records.length || selectedParts().length;
  const glbParts = stand?.previewStats?.glbParts || 0;
  const fallbackParts = stand?.previewStats?.fallbackParts || 0;
  const texturedParts = stand?.previewStats?.texturedParts || 0;
  const mockTexturedParts = stand?.previewStats?.mockTexturedParts || 0;
  const baseVisible = stand?.previewStats?.baseSuitVisible !== false;
  const lineState = texturedParts > 0 || mockTexturedParts > 0 || surface?.state === "ready" ? "ready" : "planned";
  const state = baseVisible && armorParts > 0 && lineState === "ready" ? "ready" : armorParts > 0 ? "planned" : "queued";
  const armorText = glbParts > 0
    ? `外装GLB ${glbParts}${fallbackParts > 0 ? ` + 代替形状 ${fallbackParts}` : ""}`
    : armorParts > 0
    ? `外装代替形状 ${armorParts}`
    : "外装待機";
  const lineText = texturedParts > 0
    ? `表面テクスチャ ${texturedParts}`
    : mockTexturedParts > 0
    ? `仮表面 ${mockTexturedParts}`
    : surface?.title || "表面待機";
  return {
    state,
    title: `${baseVisible ? "基礎スーツ表示中" : "基礎スーツ待機"} / ${armorText}`,
    detail: `${lineText} / パーツ ${records.length || armorParts}`,
  };
}

function fitQaSummaryFor(stand = armorStand) {
  const summary = stand?.previewStats?.fitQa || null;
  if (!summary?.totalParts) {
    return {
      state: "planned",
      title: "生成後に評価",
      detail: "背面/側面ビューでギャップ・薄さを採寸します。",
      gapParts: [],
      thinParts: [],
      bootFloatParts: [],
      fallbackPoseParts: [],
    };
  }
  if (summary.warningCount) {
    const details = [];
    if (summary.gapParts.length) details.push(`すき間: ${compactPartList(summary.gapParts, 3)}`);
    if (summary.thinParts.length) details.push(`薄すぎ: ${compactPartList(summary.thinParts, 3)}`);
    if (summary.bootFloatParts.length) details.push(`ブーツ浮き: ${compactPartList(summary.bootFloatParts, 2)}`);
    if (summary.fallbackPoseParts.length) details.push(`基準姿勢補正: ${compactPartList(summary.fallbackPoseParts, 2)}`);
    return {
      state: summary.state,
      title: `要確認 ${summary.warningCount}/${summary.totalParts}`,
      detail: details.join(" / "),
      gapParts: summary.gapParts,
      thinParts: summary.thinParts,
      bootFloatParts: summary.bootFloatParts,
      fallbackPoseParts: summary.fallbackPoseParts,
    };
  }
  return {
    state: "ready",
    title: `OK ${summary.totalParts}/${summary.totalParts}`,
    detail: "装着ギャップ・厚み比は警告なし。",
    gapParts: [],
    thinParts: [],
    bootFloatParts: [],
    fallbackPoseParts: [],
  };
}

function structureQaSummaryFor(stand = armorStand) {
  const summary = stand?.previewStats?.structureQa || null;
  if (!summary) {
    return {
      state: "planned",
      title: "生成後に評価",
      detail: "浮き・接触・背面・腰・ブーツ・連続性は生成後に採寸します。",
      floatingParts: [],
      bootFloatParts: [],
      continuityBreaks: [],
    };
  }
  if (summary.warningCount) {
    const details = [];
    if (summary.floatingParts.length) details.push(`浮き: ${compactPartList(summary.floatingParts, 3)}`);
    if (summary.bootFloatParts.length) details.push(`ブーツ: ${compactPartList(summary.bootFloatParts, 2)}`);
    if (summary.backThinParts.length) details.push(`背面厚み ${(summary.backThicknessRatio * 100).toFixed(0)}%`);
    if (summary.waistGapParts.length) details.push(`腰すき間 ${summary.waistGapM.toFixed(3)}m`);
    if (summary.continuityBreaks.length) {
      details.push(`連続性: ${summary.continuityBreaks.slice(0, 2).map((entry) => entry.label).join(" / ")}`);
    }
    return {
      state: summary.state,
      title: `要確認 ${summary.warningCount}`,
      detail: details.join(" / "),
      floatingParts: summary.floatingParts,
      bootFloatParts: summary.bootFloatParts,
      continuityBreaks: summary.continuityBreaks,
    };
  }
  return {
    state: "ready",
    title: "OK",
    detail: `背面 ${(summary.backThicknessRatio * 100).toFixed(0)}% / 腰 ${summary.waistGapM.toFixed(3)}m / 連続性OK`,
    floatingParts: [],
    bootFloatParts: [],
    continuityBreaks: [],
  };
}

function previewViewQaFor(stand = armorStand) {
  const label = stand?.previewStats?.viewLabel || PREVIEW_VIEW_PRESETS.front.label;
  const preset = stand?.previewStats?.viewPreset || "front";
  const detail = preset === "back"
    ? "背面ユニットと背骨側の浮きを確認中。"
    : preset === "left" || preset === "right"
    ? "側面厚みと体表からの距離を確認中。"
    : preset === "spin"
    ? "自動回転中。固定ビューでQAできます。"
    : "固定ビュー: 左側 / 背面 / 右側を追加済み。";
  return {
    state: preset === "spin" ? "queued" : "ready",
    title: label,
    detail,
  };
}

function publishQaDatasets(stand, coverage, fitQa, sidecarQa, structureQa) {
  const canvas = stand?.canvas;
  if (!canvas) return;
  const qaReady = coverage.state === "ready" && fitQa.state === "ready" && structureQa.state === "ready";
  canvas.dataset.previewQaState = qaReady ? "ready" : "planned";
  canvas.dataset.previewCoverageParts = String(coverage.selectedCount);
  canvas.dataset.previewExpectedParts = String(coverage.expectedCount);
  canvas.dataset.previewMissingParts = coverage.missingParts.join(",");
  canvas.dataset.previewFitGapParts = fitQa.gapParts.join(",");
  canvas.dataset.previewThinParts = fitQa.thinParts.join(",");
  canvas.dataset.previewBootFloatParts = (fitQa.bootFloatParts || []).join(",");
  canvas.dataset.previewFallbackPoseParts = fitQa.fallbackPoseParts.join(",");
  canvas.dataset.previewStructureQaState = structureQa.state;
  canvas.dataset.previewFloatingParts = (structureQa.floatingParts || []).join(",");
  canvas.dataset.previewGroundLiftParts = (structureQa.bootFloatParts || []).join(",");
  canvas.dataset.previewContinuityBreaks = (structureQa.continuityBreaks || []).map((entry) => entry.label).join(",");
  canvas.dataset.previewBackThicknessRatio = numberOr(stand?.previewStats?.structureQa?.backThicknessRatio, 1).toFixed(3);
  canvas.dataset.previewWaistGapM = numberOr(stand?.previewStats?.structureQa?.waistGapM, 0).toFixed(3);
  canvas.dataset.previewMaxContinuityGapM = numberOr(stand?.previewStats?.structureQa?.maxContinuityGapM, 0).toFixed(3);
  canvas.dataset.previewAttachmentOffsetParts = (sidecarQa?.offsetParts || []).join(",");
  canvas.dataset.previewAttachmentOffsetTargets = (sidecarQa?.offsetTargets || []).join("|");
  canvas.dataset.previewToppingSlots = (sidecarQa?.toppingSlots || []).join("|");
  canvas.dataset.previewVariantKeys = (sidecarQa?.variantKeys || []).join("|");
  canvas.dataset.previewAttachmentOffsetCount = String(sidecarQa?.offsetTargets?.length || 0);
  canvas.dataset.previewToppingSlotCount = String(sidecarQa?.toppingSlots?.length || 0);
  canvas.dataset.previewVariantKeyCount = String(sidecarQa?.variantKeys?.length || 0);
  canvas.dataset.previewConflictCount = String(sidecarQa?.conflictCount || 0);
  canvas.dataset.previewConflictSlots = (sidecarQa?.conflictSlots || []).join("|");
  canvas.dataset.previewConflictsWith = (sidecarQa?.conflictPairs || []).join("|");
  canvas.dataset.previewCatalogPath = sidecarQa?.catalogPath || "";
  canvas.dataset.previewCatalogStatus = sidecarQa?.catalogStatus || "pending";
  canvas.dataset.previewCatalogSelectedPartCount = String(sidecarQa?.catalogSelectedPartCount || 0);
  canvas.dataset.previewSelectedModuleCount = String(sidecarQa?.catalogSelectedModuleCount || 0);
  canvas.dataset.previewCatalogSlotCount = String(sidecarQa?.catalogSlotCount || 0);
  canvas.dataset.previewCatalogVariantCount = String(sidecarQa?.catalogVariantCount || 0);
  canvas.dataset.previewVisualDensityState = sidecarQa?.densityState || "planned";
  canvas.dataset.previewVisualDensityWarnings = (sidecarQa?.densityWarnings || []).join("|");
}

function setPreviewModuleVariant(part, variantKey) {
  if (!latestForgeData?.preview?.modules?.[part]) return false;
  const key = firstString(variantKey);
  if (!key || key === AUTO_VARIANT_VALUE) return false;
  const assetRef = variantAssetRefForPart(part, key, latestForgeData);
  if (!assetRef) return false;
  const module = latestForgeData.preview.modules[part];
  module.selected_variant_key = key;
  module.variant_key = key;
  module.asset_ref = assetRef;
  const catalogModule = latestForgeData.asset_pipeline?.variant_catalog?.selected_modules?.[part]
    || latestForgeData.preview?.variant_catalog?.selected_modules?.[part];
  if (catalogModule && typeof catalogModule === "object") {
    catalogModule.selected_variant_key = key;
    catalogModule.asset_ref = assetRef;
  }
  const overlay = latestForgeData.visual_layers?.armor_overlay
    || latestForgeData.preview?.visual_layers?.armor_overlay;
  if (overlay && typeof overlay === "object") {
    overlay.selected_variant_keys = { ...(overlay.selected_variant_keys || {}), [part]: key };
    overlay.asset_refs = { ...(overlay.asset_refs || {}), [part]: assetRef };
    const assets = overlay.assets && typeof overlay.assets === "object" ? overlay.assets : {};
    overlay.assets = {
      ...assets,
      [part]: {
        ...(assets[part] || {}),
        module: part,
        selected_variant_key: key,
        asset_ref: assetRef,
        asset_kind: assetRef.includes("/variants/") ? "variant_glb" : "canonical_glb",
      },
    };
  }
  const placement = variantRuntimePlacementForPreviewPart(part, key, assetRef, module);
  setRuntimePlacementForPreviewPart(part, placement);
  return true;
}

async function applyVariantOverrideToPreview(part, variantKey) {
  if (!latestForgeData?.preview?.modules?.[part]) {
    renderAssetPipeline(latestForgeData);
    updatePreviewLayerPanel(latestForgeData);
    return;
  }
  const changed = setPreviewModuleVariant(part, variantKey);
  if (changed) {
    setStatus(`${partLabel(part)}の型プレビューを読み込み中...`, "pending");
    await armorStand.renderSuit(latestForgeData.preview);
  }
  renderAssetPipeline(latestForgeData);
  updatePreviewLayerPanel(latestForgeData);
  renderExhibitionSummary(latestForgeData);
  if (changed) {
    markQuestLinkStaleForPreview(`${partLabel(part)}の見た目だけ更新しました。Questへ反映するには再生成してください。`);
  }
}

function syncVariantSelectsFromForgeData(data = latestForgeData) {
  if (!data?.preview?.modules) return;
  for (const [part, module] of Object.entries(data.preview.modules)) {
    if (manualVariantOverrides.has(part)) continue;
    const select = partVariantSelect(part);
    const key = firstString(module?.selected_variant_key);
    if (!select || !key) continue;
    select.value = Array.from(select.options).some((option) => option.value === key)
      ? key
      : AUTO_VARIANT_VALUE;
    const summary = select.parentElement?.querySelector(".part-variant-summary");
    if (summary) summary.textContent = key ? `自動: ${variantDisplayNameJa(part, key)}` : summary.textContent;
  }
  renderExhibitionSummary(data);
}

function renderPartGrid() {
  const previousSelections = Object.fromEntries(
    Array.from(UI.partGrid.querySelectorAll("select[data-part-variant]"))
      .map((select) => [select.dataset.partVariant, select.value]),
  );
  const checkedParts = new Set(selectedParts());
  UI.partGrid.innerHTML = "";
  for (const [id, rawLabel, checked] of PARTS) {
    const label = partLabel(id) || rawLabel;
    const item = document.createElement("div");
    item.className = "part-option";
    item.dataset.part = id;
    const checkLabel = document.createElement("label");
    checkLabel.className = "part-toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = id;
    input.checked = checkedParts.size ? checkedParts.has(id) : checked;
    const labelText = document.createElement("span");
    labelText.textContent = label;
    checkLabel.append(input, labelText);
    item.append(checkLabel);

    const variants = catalogVariantKeysForPart(id);
    const variantSelect = document.createElement("select");
    variantSelect.dataset.partVariant = id;
    variantSelect.name = `variant_${id}`;
    variantSelect.disabled = !input.checked || !variants.length;
    variantSelect.setAttribute("aria-label", `${label}の型選択`);
    if (!variants.length) {
      const option = document.createElement("option");
      option.value = AUTO_VARIANT_VALUE;
      option.textContent = localVariantCatalogStatus === "error" ? "カタログ未読込" : "自動選定";
      variantSelect.append(option);
    } else {
      const autoOption = document.createElement("option");
      autoOption.value = AUTO_VARIANT_VALUE;
      autoOption.textContent = "自動選定";
      variantSelect.append(autoOption);
      for (const variantKey of variants) {
        const option = document.createElement("option");
        option.value = variantKey;
        const record = catalogVariantRecordForPart(id, variantKey);
        const assetRef = variantAssetRefForPart(id, variantKey);
        option.textContent = variantDisplayNameJa(id, variantKey, record?.display_name);
        option.dataset.assetRef = assetRef;
        variantSelect.append(option);
      }
      const preferred = previousSelections[id] || latestSelectedVariantKeyForPart(id) || AUTO_VARIANT_VALUE;
      variantSelect.value = variants.includes(preferred) ? preferred : AUTO_VARIANT_VALUE;
    }
    const summary = document.createElement("small");
    summary.className = "part-variant-summary";
    summary.textContent = variants.length ? `自動 / ${variants.length}案` : localVariantCatalogStatus;
    item.append(variantSelect, summary);
    input.addEventListener("change", () => {
      variantSelect.disabled = !input.checked || !variants.length;
      renderAssetPipeline(latestForgeData);
      updatePreviewLayerPanel(latestForgeData);
      markQuestLinkStaleForPreview("外装パーツの選択を変更しました。Questへ反映するには再生成してください。");
    });
    variantSelect.addEventListener("change", () => {
      if (variantSelect.value && variantSelect.value !== AUTO_VARIANT_VALUE) {
        manualVariantOverrides.add(id);
      } else {
        manualVariantOverrides.delete(id);
      }
      applyVariantOverrideToPreview(id, variantSelect.value).catch((error) => {
        console.warn(`variant preview update failed for ${id}: ${error?.message || error}`);
      });
    });
    UI.partGrid.append(item);
  }
  renderExhibitionSummary(latestForgeData);
}

function syncPreviewLegendPalette() {
  const root = document.documentElement;
  const palette = {
    primary: UI.primaryColor?.value || "#F4F1E8",
    secondary: UI.secondaryColor?.value || "#8C96A3",
    emissive: UI.emissiveColor?.value || "#43D8FF",
  };
  root.style.setProperty("--base-suit", colorToCss(resolveBaseSuitPalette(palette).base));
  root.style.setProperty("--legend-primary", palette.primary);
  root.style.setProperty("--legend-secondary", palette.secondary);
  root.style.setProperty("--legend-emissive", palette.emissive);
}

function renderPreviewLegend() {
  if (!UI.previewLegend) return;
  // Static contract labels retained for tests: "Body reference" / "Base suit" / "Armor parts" / "Surface lines".
  const stats = armorStand?.previewStats || {};
  const armorParts = Number(stats.armorParts || 0);
  const glbParts = Number(stats.glbParts || 0);
  const fallbackParts = Number(stats.fallbackParts || 0);
  const texturedParts = Number(stats.texturedParts || 0);
  const mockTexturedParts = Number(stats.mockTexturedParts || 0);
  const readableItems = [
    ["legend-skin", "人体基準", stats.vrmVisible === false ? "代替" : "VRM"],
    ["legend-suit", "基礎スーツ", stats.baseSuitVisible === false ? "待機" : "表示中"],
    [
      "legend-armor",
      "外装",
      glbParts > 0 ? `${glbParts} GLB${fallbackParts > 0 ? ` + 補助${fallbackParts}` : ""}` : armorParts > 0 ? `補助${armorParts}` : "待機",
    ],
    [
      "legend-glow",
      "表面ライン",
      texturedParts > 0 ? `${texturedParts}実体` : mockTexturedParts > 0 ? `${mockTexturedParts}仮` : "計画",
    ],
  ];
  UI.previewLegend.replaceChildren(
    ...readableItems.map(([className, label, status]) => {
      const item = document.createElement("span");
      item.dataset.previewLegend = className.replace("legend-", "");
      const swatch = document.createElement("i");
      swatch.className = className;
      const labelNode = document.createElement("b");
      labelNode.textContent = label;
      const statusNode = document.createElement("small");
      statusNode.textContent = status;
      item.append(swatch, labelNode, statusNode);
      return item;
    }),
  );
  const publicLegendItems = [
    ["legend-skin", "身体基準", stats.vrmVisible === false ? "代替" : "VRM"],
    ["legend-suit", "基礎スーツ", stats.baseSuitVisible === false ? "待機" : "表示中"],
    [
      "legend-armor",
      "外装パーツ",
      glbParts > 0 ? `${glbParts} GLB${fallbackParts > 0 ? ` + 補助${fallbackParts}` : ""}` : armorParts > 0 ? `補助${armorParts}` : "待機",
    ],
    [
      "legend-glow",
      "表面ライン",
      texturedParts > 0 ? `${texturedParts}読込` : mockTexturedParts > 0 ? `${mockTexturedParts}仮表示` : "計画中",
    ],
  ];
  UI.previewLegend.replaceChildren(
    ...publicLegendItems.map(([className, label, status]) => {
      const item = document.createElement("span");
      item.dataset.previewLegend = className.replace("legend-", "");
      const swatch = document.createElement("i");
      swatch.className = className;
      const labelNode = document.createElement("b");
      labelNode.textContent = label;
      const statusNode = document.createElement("small");
      statusNode.textContent = status;
      item.append(swatch, labelNode, statusNode);
      return item;
    }),
  );
  return;
  const items = [
    ["legend-skin", "VRM骨格"],
    ["legend-suit", "VRM表面ボディスーツ"],
    ["legend-armor", "外装GLB/実体"],
    ["legend-glow", "表面/補助ライン"],
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

function surfacePlanFromData(data = latestForgeData) {
  return data?.asset_pipeline?.surface_plan
    || data?.preview?.asset_pipeline?.surface_plan
    || data?.preview?.generation?.surface_plan
    || data?.suitspec?.asset_pipeline?.surface_plan
    || data?.suitspec?.generation?.surface_plan
    || data?.generation?.surface_plan
    || null;
}

function layerStateForSurface(data = latestForgeData, records = previewRecordsFromData(data)) {
  const declaredTextureCount = records.filter(([, module]) => module?.texture_path).length;
  const texturedCount = armorStand?.previewStats?.texturedParts || 0;
  const textureFailedCount = armorStand?.previewStats?.textureFailedParts || 0;
  const mockTexturedCount = armorStand?.previewStats?.mockTexturedParts || 0;
  const pipeline = previewPipelineFromData(data);
  const template = pipeline?.texture_probe_job?.payload || pipeline?.generation_job?.payload || pipeline?.job_payload_template;
  const canRun = Boolean(template?.suitspec);
  const writesFinal = textureJobWritesFinal(data);
  if (texturedCount > 0) {
    return {
      state: "ready",
      title: `${texturedCount}パーツ反映`,
      detail: "生成済み表面を表示中。",
    };
  }
  if (textureFailedCount > 0) {
    return {
      state: "planned",
      title: `${textureFailedCount}/${declaredTextureCount} 表面読込要確認`,
      detail: "SuitSpecにtexture_pathがありますが、Webプレビューで読み込めません。ここでは仮マップへ差し替えていません。",
    };
  }
  if (mockTexturedCount > 0) {
    return {
      state: "ready",
      title: `プレビュー表面 ${mockTexturedCount}パーツ`,
      detail: "仮表面を表示中。SuitSpec texture_pathは未変更。",
    };
  }
  if (UI.textureJobPanel?.classList.contains("running")) {
    return {
      state: "running",
      title: "生成中",
      detail: "表面テクスチャ作成中。",
    };
  }
  if (UI.textureJobPanel?.classList.contains("complete")) {
    return {
      state: "ready",
      title: "生成完了",
      detail: "表面を再読み込みします。",
    };
  }
  if (canRun) {
    return {
      state: "queued",
      title: writesFinal ? "生成準備OK" : "表面確認待機",
      detail: writesFinal
        ? "表面を追加生成できます。"
        : "速度確認用の仮生成です。",
    };
  }
  return {
    state: "planned",
    title: "カラー設計",
    detail: "配色と発光線を表示中。",
  };
}

function ensurePreviewLayerPanel() {
  if (previewLayerPanel?.isConnected) return previewLayerPanel;
  if (!UI.standStage) return null;

  previewLayerPanel = document.createElement("details");
  previewLayerPanel.className = "preview-layer-panel";
  previewLayerPanel.dataset.supportDiagnostics = "preview";
  previewLayerPanel.setAttribute("aria-live", "polite");
  const summary = document.createElement("summary");
  summary.textContent = "プレビュー診断";
  previewLayerPanel.append(summary);
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
      detail: "主要パーツの品質Gate待ち。",
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
        ? `不足: ${missing}`
        : "本番化に必要な外装が不足。",
    };
  }
  if (status === "pass") {
    return {
      state: "ready",
      title: `通過 ${passCount}/${requiredCount || passCount}`,
      detail: "最終表面の対象です。",
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
  const glbParts = stand?.previewStats?.glbParts || 0;
  const height = Math.round(stand?.heightCm || declaredHeightCm());
  const heightScale = height / DEFAULT_HEIGHT_CM;
  const surface = layerStateForSurface(data, records);
  const modelGate = modelGateStateForPipeline(pipeline);
  const viewQa = previewViewQaFor(stand);
  const coverage = coverageQaFor(data, records);
  const fitQa = fitQaSummaryFor(stand);
  const structureQa = structureQaSummaryFor(stand);
  const sidecarQa = sidecarQaFor(records, data);
  const layerReadability = layerReadabilityFor(stand, records, surface);
  const baseState = stand?.previewStats?.baseSuitVisible === false ? "planned" : "ready";
  const armorState = armorParts > 0 ? "ready" : "planned";
  const armorDetail = glbParts > 0
    ? `納品GLB ${glbParts}パーツを主表示。`
    : fallbackParts > 0
    ? `仮形状 ${fallbackParts}パーツを表示。`
    : "人体基準で分割表示中。";
  renderPreviewLegend();
  publishQaDatasets(stand, coverage, fitQa, sidecarQa, structureQa);
  if (stand?.canvas) {
    stand.canvas.dataset.previewLayerReadability = layerReadability.state;
  }
  setPreviewLayerRow(panel, "readability", "表示層", layerReadability.title, layerReadability.detail, layerReadability.state);
  setPreviewLayerRow(panel, "sidecar", "設計メタ", sidecarQa.title, sidecarQa.detail, sidecarQa.state);
  setPreviewLayerRow(panel, "offset", "装着位置", sidecarQa.offsetTitle, sidecarQa.offsetDetail, sidecarQa.offsetState);
  setPreviewLayerRow(panel, "topping", "追加意匠", sidecarQa.toppingTitle, sidecarQa.toppingDetail, sidecarQa.toppingState);
  setPreviewLayerRow(panel, "variant", "型選択", sidecarQa.variantTitle, sidecarQa.variantDetail, sidecarQa.variantState);
  setPreviewLayerRow(panel, "density", "意匠QA", sidecarQa.densityTitle, sidecarQa.densityDetail, sidecarQa.densityState);

  setPreviewLayerRow(panel, "view", "ビュー", viewQa.title, viewQa.detail, viewQa.state);
  setPreviewLayerRow(panel, "coverage", "構成QA", coverage.title, coverage.detail, coverage.state);
  setPreviewLayerRow(panel, "fit", "装着QA", fitQa.title, fitQa.detail, fitQa.state);
  setPreviewLayerRow(panel, "structure", "構造QA", structureQa.title, structureQa.detail, structureQa.state);
  setPreviewLayerRow(
    panel,
    "height",
    "身長",
    `${height}cm`,
    `${heightScale.toFixed(2)}x 表示`,
    "ready",
  );
  setPreviewLayerRow(
    panel,
    "base",
    "素体",
    baseState === "ready" ? "VRM表示中" : "待機中",
    "VRMの体表テクスチャを特撮ボディスーツとして扱います。",
    baseState,
  );
  setPreviewLayerRow(
    panel,
    "armor",
    glbParts > 0 ? "納品GLB" : "装甲",
    glbParts > 0 ? `主表示 ${glbParts}パーツ` : armorParts > 0 ? `${armorParts}パーツ` : `${selectedCount}パーツ選択`,
    armorDetail,
    armorState,
  );
  setPreviewLayerRow(panel, "modelGate", "品質", modelGate.title, modelGate.detail, modelGate.state);
  setPreviewLayerRow(panel, "surface", "表面", surface.title, surface.detail, surface.state);
}

function formPayload() {
  const heightCm = declaredHeightCm();
  const selected_variant_keys = selectedVariantMap({ explicitOnly: true });
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
    variant_selection_mode: "auto",
    variant_selection_provider: "sakura_ai",
    selected_variant_keys,
    selected_variants: selectedVariantRecords({ explicitOnly: true }),
    variant_catalog_path: DEFAULT_VARIANT_CATALOG_PATH,
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
      hint: "Quest BrowserでこのURLを開くとcode付きで起動します。表示されない場合は、VR内で同じ4桁コードを入力してください。",
    };
  }
  if (isLocalHost(currentHost)) {
    return {
      url: localhostUrl,
      hint: "Questで開くにはADB reverseが必要です。VR内のコード入力でも同じ4桁コードを呼び出せます。",
    };
  }
  return {
    url: questViewerUrl(currentHost, code),
    hint: "同じネットワークのQuest Browserで開けます。URLにも4桁コードを付けています。",
  };
}

function replaySaveUrlFromQuestUrl(rawUrl) {
  try {
    const url = new URL(rawUrl, window.location.href);
    url.searchParams.set("replayView", "mirror");
    return url.toString();
  } catch {
    return rawUrl || "#";
  }
}

function setExhibitionLinkState(link, { href = "#", text, enabled = false, ariaLabel = "" } = {}) {
  if (!link) return;
  link.href = enabled ? href : "#";
  link.textContent = text;
  link.classList.toggle("disabled", !enabled);
  link.setAttribute("aria-disabled", enabled ? "false" : "true");
  if (enabled && ariaLabel) {
    link.setAttribute("aria-label", ariaLabel);
  } else {
    link.removeAttribute("aria-label");
  }
}

function renderExhibitionSummary(data = latestForgeData) {
  if (!EXHIBITION_MODE || !UI.exhibitionSummary) return;
  const code = data?.recall_code || "";
  const stale = UI.questLink?.dataset.stalePreview === "true";
  const enabled = Boolean(code) && !stale;
  const quest = enabled ? questLinkOptions(code) : { url: "#", hint: "" };
  UI.exhibitionSummary.hidden = false;
  if (UI.exhibitionCode) UI.exhibitionCode.textContent = code || "----";
  if (UI.exhibitionHeight) UI.exhibitionHeight.textContent = `${declaredHeightCm()}cm`;
  if (UI.exhibitionVariant) UI.exhibitionVariant.textContent = selectedVariantSummaryJa();
  setExhibitionLinkState(UI.exhibitionQuestLink, {
    href: quest.url,
    text: enabled ? "Questで開く/試す" : "生成後にQuestで試す",
    enabled,
    ariaLabel: enabled ? `Questで開く/試す。コード ${code}` : "",
  });
  setExhibitionLinkState(UI.replaySaveLink, {
    href: replaySaveUrlFromQuestUrl(quest.url),
    text: enabled ? "Questで試してReplay保存" : "生成後にReplay保存へ",
    enabled,
    ariaLabel: enabled ? `Questで試してReplay保存へ進む。コード ${code}` : "",
  });
  if (UI.exhibitionHint) {
    UI.exhibitionHint.textContent = enabled
      ? `${quest.hint} 体験後はQuest側の記録再生でReplayを保存・確認します。`
      : "生成すると4桁コード、Questで開く/試す導線、Replay保存導線をここにまとめます。";
  }
}

function applyExhibitionModePreference() {
  document.body.dataset.exhibitionMode = EXHIBITION_MODE ? "true" : "false";
  document.documentElement.dataset.exhibitionMode = EXHIBITION_MODE ? "true" : "false";
  if (UI.exhibitionSummary) UI.exhibitionSummary.hidden = !EXHIBITION_MODE;
  if (!EXHIBITION_MODE) return;
  UI.resultDetails?.removeAttribute("open");
  UI.supportDetails.forEach((details) => {
    details.dataset.exhibitionPriority = "low";
    details.removeAttribute("open");
  });
  renderExhibitionSummary();
}

function markQuestLinkStaleForPreview(message = "入力内容を変更しました。Questへ反映するには再生成してください。") {
  if (!latestForgeData?.recall_code) return;
  UI.questLink.href = "#";
  UI.questLink.textContent = "再生成してQuestへ";
  UI.questLink.classList.add("disabled");
  UI.questLink.dataset.stalePreview = "true";
  UI.questLink.setAttribute("aria-disabled", "true");
  UI.questLink.removeAttribute("aria-label");
  if (UI.questUrl) UI.questUrl.value = "再生成後に表示";
  if (UI.questUrlHint) {
    UI.questUrlHint.textContent = "表示中の4桁コードは変更前の結果です。Questで同じスーツを見るには、もう一度「生成してコード発行」を押してください。";
  }
  renderExhibitionSummary(latestForgeData);
  setStatus(message, "pending");
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
  const glbParts = armorStand?.previewStats?.glbParts || 0;
  const surface = layerStateForSurface(data, records);
  const baseReady = armorStand?.previewStats?.baseSuitVisible !== false;
  const hasGeneratedPreview = Boolean(data);
  const pipeline = previewPipelineFromData(data);
  const modelPlan = pipeline?.model_plan || {};
  const texturePlan = pipeline?.texture_plan || {};
  const modelJob = pipeline?.model_rebuild_job || {};
  const modelGate = modelGateStateForPipeline(pipeline);
  const textureProbe = pipeline?.texture_probe_job || {};
  const provider = TEXTURE_PROVIDER_PROFILE;
  const mode = texturePlan.texture_mode || "mesh_uv";
  const variantSummary = selectedVariantSummary();
  const status = texturePlan.status || pipeline?.surface_generation_status || "planned_not_generated";
  const fitStatus = pipeline?.fit_status || modelPlan.fit_solver || "preview_vrm_bone_metrics";
  const meshStatus = modelPlan.mesh_source_status || "seed/proxy";
  const modelStatus = modelJob.status || modelPlan.status || "requires_rebuild";
  const probeStatus = textureProbe.status || "probe_only";
  const coverage = coverageQaFor(data, records);
  const fitQa = fitQaSummaryFor(armorStand);
  UI.assetPipeline.dataset.pipelineContract = `model ${modelStatus} / ${fitStatus} / ${provider} / ${mode} / ${status} / ${meshStatus} / ${probeStatus}`;
  if (UI.proxyWarning) {
    UI.proxyWarning.dataset.previewRole = "proxy_envelope_only";
    UI.proxyWarning.classList.toggle("is-auxiliary", hasGeneratedPreview && glbParts > 0);
    const title = UI.proxyWarning.querySelector("strong");
    const detail = UI.proxyWarning.querySelector("span");
    if (hasGeneratedPreview && glbParts > 0) {
      if (title) title.textContent = "納品GLB主表示";
      if (detail) detail.textContent = fallbackParts > 0
        ? `GLB ${glbParts}パーツを実体表示。仮プロキシ${fallbackParts}パーツは補助です。`
        : "寸法ガイドは補助扱いです。形状修正はモデラー向けWave 1仕様に反映します。";
    } else {
      if (title) title.textContent = "仮プロキシ";
      if (detail) detail.textContent = "半透明の箱/筒は発注対象外。現在の生成結果内の設計図寸法を正本にします。";
    }
  }

  if (UI.proxyWarning) {
    const supportTitle = UI.proxyWarning.querySelector("strong");
    const supportDetail = UI.proxyWarning.querySelector("span");
    if (supportTitle) supportTitle.textContent = hasGeneratedPreview && glbParts > 0 ? "納品GLBを主表示" : "プレビュー補足";
    if (supportDetail) {
      supportDetail.textContent = hasGeneratedPreview && glbParts > 0
        ? `納品GLB ${glbParts}パーツを表示中${fallbackParts > 0 ? `。補助仮形状 ${fallbackParts}パーツあり` : ""}。`
        : "納品GLBが読み込まれるまで仮形状が出る場合があります。設営時はサポート診断を確認してください。";
    }
  }

  UI.assetPipeline.classList.remove("pending", "planned", "complete", "error");
  if (!hasGeneratedPreview) {
    UI.assetPipeline.classList.add("pending");
    UI.assetPipelineTitle.textContent = "レイヤー待機中";
    UI.assetPipelineDetail.textContent = `基礎スーツ層: ${baseReady ? "表示中" : "待機中"} / 装甲パーツ層: ${selectedCount}パーツ選択中 / 構成QA: ${coverage.title} / 仮プロキシ / 表面: ${provider}`;
    UI.assetPipelineDetail.textContent += ` / Variant: ${variantSummary}`;
    updatePreviewLayerPanel(data);
    return;
  }
  UI.assetPipeline.classList.add(surface.state === "ready" ? "complete" : "planned");
  UI.assetPipelineTitle.textContent = glbParts > 0 ? `納品GLB + 外装${armorParts}パーツ` : `基礎スーツ + 装甲${armorParts}パーツ`;
  UI.assetPipelineDetail.textContent = [
    `基礎スーツ層: ${baseReady ? "表示中" : "待機中"}`,
    `外装GLB/実体層: ${glbParts > 0 ? `納品GLB主表示 ${glbParts}パーツ${fallbackParts > 0 ? ` / 補助プロキシ${fallbackParts}` : ""}` : fallbackParts > 0 ? `仮プロキシ${fallbackParts}パーツ` : "分割配置済み"}`,
    `モデルGate: ${modelGate.title}`,
    `プレビュー表面: ${surface.title} / ${provider}`,
    `構成QA: ${coverage.title}`,
    `装着QA: ${fitQa.title}`,
  ].join(" / ");
  UI.assetPipelineDetail.textContent += ` / Variant: ${variantSummary}`;
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

function textureJobButtons() {
  return [UI.textureJobButton, UI.textureQuickButton].filter(Boolean);
}

function setTextureJobButtonsDisabled(disabled) {
  for (const button of textureJobButtons()) {
    button.disabled = disabled;
  }
}

function setTextureJobButtonsText(text) {
  for (const button of textureJobButtons()) {
    button.textContent = text;
  }
}

function setTextureQuickState(state, title, detail) {
  if (!UI.textureQuickAction) return;
  UI.textureQuickAction.classList.remove("pending", "running", "complete", "error");
  UI.textureQuickAction.classList.add(state);
  UI.textureQuickAction.dataset.textureState = state;
  if (UI.textureQuickDetail) {
    UI.textureQuickDetail.textContent = title ? `${title} / ${detail}` : detail;
  }
}

function setTextureJobState(state, title, detail, progress = 0) {
  if (!UI.textureJobPanel || !UI.textureJobTitle || !UI.textureJobDetail || !UI.textureJobMeter) return;
  UI.textureJobPanel.classList.remove("pending", "running", "complete", "error");
  UI.textureJobPanel.classList.add(state);
  UI.textureJobTitle.textContent = title;
  UI.textureJobDetail.textContent = detail;
  UI.textureJobMeter.style.width = `${clamp(progress, 0, 1) * 100}%`;
  setTextureQuickState(state, title, detail);
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
  if (!textureJobButtons().length) return;
  const pipeline = data?.asset_pipeline || data?.preview?.asset_pipeline || null;
  const job = textureJobContract(data);
  const template = job?.payload || pipeline?.job_payload_template;
  const canRun = Boolean(template?.suitspec);
  const writesFinal = textureJobWritesFinal(data);
  setTextureJobButtonsDisabled(!canRun);
  if (!canRun) {
    setTextureJobState("pending", "未開始", "鎧を生成すると、表面/テクスチャ層を追加できます。", 0);
  } else if (!UI.textureJobPanel?.classList.contains("running") && !UI.textureJobPanel?.classList.contains("complete")) {
    setTextureJobButtonsText(writesFinal ? "本番表面生成" : "表面確認を試す");
    setTextureJobState(
      "pending",
      writesFinal ? "本番表面生成待機" : "表面確認待機",
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
    provider_profile: TEXTURE_PROVIDER_PROFILE,
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

function textureGenerationSummaryFromSnapshot(snapshot) {
  return snapshot?.result?.texture_generation_summary || snapshot?.texture_generation_summary || null;
}

function textureGenerationSummaryText(summary) {
  if (!summary || typeof summary !== "object") return "";
  const counts = summary.status_counts || {};
  const generated = Number(counts.generated_by_provider_profile || 0);
  const cache = Number(counts.cache_reused || 0);
  const fallback = Number(counts.fallback_asset_reused || 0);
  const generatedNow = Number(summary.generated_now_count || 0);
  const writeable = Number(summary.final_texture_writeable_count || 0);
  return `Nanobanana内訳: 新規${generated} / cache${cache} / fallback${fallback} / 今回生成${generatedNow} / 最終反映可${writeable}`;
}

async function snapshotWithTextureGenerationSummary(snapshot) {
  if (textureGenerationSummaryFromSnapshot(snapshot)) return snapshot;
  const summaryPath = snapshot?.result?.summary_path || snapshot?.summary_path;
  if (!summaryPath) return snapshot;
  try {
    const summary = await fetchJson(summaryPath);
    if (!summary?.texture_generation_summary) return snapshot;
    return {
      ...snapshot,
      result: {
        ...(snapshot.result || {}),
        texture_generation_summary: summary.texture_generation_summary,
      },
    };
  } catch (error) {
    console.warn(`texture generation summary fetch failed: ${error?.message || error}`);
    return snapshot;
  }
}

function updateModelerHandoff(data = latestForgeData) {
  if (!UI.modelerBlueprintUrl) return;
  const code = String(data?.recall_code || "").trim();
  const selectedBlueprints = data?.asset_pipeline?.modeler_blueprints || data?.preview?.asset_pipeline?.modeler_blueprints;
  const partCount = Number(selectedBlueprints?.part_count || 0);
  const blueprintRef = partCount > 0
    ? `asset_pipeline.modeler_blueprints / ${partCount} selected parts`
    : "GET /v1/catalog/part-blueprints / full seed catalog";
  UI.modelerBlueprintUrl.value = blueprintRef;
  if (UI.modelerHandoffTitle) {
    UI.modelerHandoffTitle.textContent = code ? `現在の生成結果 / 呼び出し ${code}` : "簡易メモ / 設計図API";
  }
  if (UI.modelerHandoffDetail) {
    UI.modelerHandoffDetail.textContent = "docs/modeler-armor-brief.md / viewer/assets/armor-parts/<module>/<module>.glb";
  }
  if (UI.modelerHandoff) {
    UI.modelerHandoff.dataset.blueprintApi = "/v1/catalog/part-blueprints";
    UI.modelerHandoff.dataset.blueprintSource = partCount > 0 ? "current_forge_response" : "seed_catalog";
    UI.modelerHandoff.dataset.intakePath = "viewer/assets/armor-parts/<module>/<module>.glb";
  }
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
  const textureSummaryText = textureGenerationSummaryText(textureGenerationSummaryFromSnapshot(snapshot));
  if (snapshot.status === "completed") {
    setTextureJobButtonsDisabled(false);
    setTextureJobButtonsText(textureJobWritesFinal() ? "本番表面再生成" : "表面確認を再試行");
    setTextureJobState(
      "complete",
      `表面生成完了 ${result.generated_count ?? done}/${total || result.generated_count || done}`,
      `所要 ${formatSeconds(result.total_elapsed_sec || elapsed)}${speedText}${timingText}。プレビューへ反映します。`,
      1,
    );
    if (textureSummaryText && UI.textureJobDetail) {
      UI.textureJobDetail.textContent = `${UI.textureJobDetail.textContent} / ${textureSummaryText}`;
      if (UI.textureQuickDetail) UI.textureQuickDetail.textContent = UI.textureJobDetail.textContent;
    }
    return;
  }
  if (snapshot.status === "failed" || snapshot.status === "cancelled") {
    setTextureJobButtonsDisabled(false);
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
  const displaySnapshot = snapshot.status === "completed" ? await snapshotWithTextureGenerationSummary(snapshot) : snapshot;
  updateTextureJobFromSnapshot(displaySnapshot);
  if (displaySnapshot.status === "completed") {
    await refreshPreviewFromGeneratedSuit(payload).catch((error) => {
      console.warn(`texture preview refresh failed: ${error?.message || error}`);
    });
    return;
  }
  if (displaySnapshot.status === "failed" || displaySnapshot.status === "cancelled") return;
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
  setTextureJobButtonsDisabled(true);
  setTextureJobButtonsText("生成中...");
  textureJobStartedAt = performance.now();
  setTextureJobState(
    "running",
    textureJobWritesFinal() ? "本番表面生成を開始" : "表面確認を開始",
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
    const textures = new Set([item.map, item.emissiveMap, item.normalMap, item.roughnessMap, item.metalnessMap]);
    textures.forEach((texture) => texture?.dispose?.());
    item.dispose?.();
  }
}

function disposeObjectTree(root) {
  if (!root) return;
  const geometries = new Set();
  const materials = new Set();
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry);
    const objectMaterials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of objectMaterials) {
      if (material) materials.add(material);
    }
  });
  geometries.forEach((geometry) => geometry.dispose?.());
  materials.forEach((material) => disposeMaterial(material));
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

function colorFrom(value, fallback) {
  try {
    return new THREE.Color(value || fallback);
  } catch {
    return new THREE.Color(fallback);
  }
}

function colorToCss(color, alpha = 1) {
  const display = color.clone();
  if (THREE.ColorManagement?.enabled) display.convertLinearToSRGB?.();
  const r = Math.round(clamp(display.r, 0, 1) * 255);
  const g = Math.round(clamp(display.g, 0, 1) * 255);
  const b = Math.round(clamp(display.b, 0, 1) * 255);
  return alpha >= 1 ? `rgb(${r}, ${g}, ${b})` : `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function resolveBaseSuitPalette(palette = {}) {
  const primary = colorFrom(palette.primary, "#F4F1E8");
  const secondary = colorFrom(palette.secondary, "#52777E");
  const emissive = colorFrom(palette.emissive, "#43D8FF");
  const ink = new THREE.Color(0x071214);
  const coolShadow = new THREE.Color(0x10292c);
  return {
    base: secondary.clone().lerp(primary, 0.18).lerp(ink, 0.34),
    panel: secondary.clone().lerp(primary, 0.4).lerp(coolShadow, 0.2),
    shadow: secondary.clone().lerp(ink, 0.58),
    seam: secondary.clone().lerp(ink, 0.72),
    armorEcho: primary.clone().lerp(secondary, 0.44).lerp(ink, 0.08),
    glow: emissive.clone().lerp(new THREE.Color(0xffffff), 0.1),
  };
}

function createBaseSuitTexture(palette = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const suit = resolveBaseSuitPalette(palette);
  ctx.fillStyle = colorToCss(suit.base);
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const fillPanel = (points, color, alpha) => {
    ctx.beginPath();
    points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.fillStyle = colorToCss(color, alpha);
    ctx.fill();
  };

  const strokePanel = (points, color, width, alpha) => {
    ctx.beginPath();
    points.forEach(([x, y], index) => {
      if (index === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = colorToCss(color, alpha);
    ctx.lineWidth = width;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.stroke();
  };

  const mirrorX = (points) => points.map(([x, y]) => [512 - x, y]);

  fillPanel([[0, 0], [122, 0], [190, 512], [0, 512]], suit.shadow, 0.42);
  fillPanel(mirrorX([[0, 0], [122, 0], [190, 512], [0, 512]]), suit.shadow, 0.42);
  fillPanel([[214, 0], [298, 0], [282, 512], [230, 512]], suit.panel, 0.28);
  fillPanel([[156, 48], [224, 160], [206, 354], [126, 464], [98, 426], [168, 326], [184, 178], [126, 84]], suit.armorEcho, 0.16);
  fillPanel(mirrorX([[156, 48], [224, 160], [206, 354], [126, 464], [98, 426], [168, 326], [184, 178], [126, 84]]), suit.armorEcho, 0.16);

  ctx.save();
  ctx.globalAlpha = 0.08;
  ctx.strokeStyle = colorToCss(suit.armorEcho);
  ctx.lineWidth = 1;
  for (let x = -96; x < 640; x += 24) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x + 180, 512);
    ctx.stroke();
  }
  ctx.globalAlpha = 0.11;
  ctx.strokeStyle = colorToCss(suit.seam);
  for (let y = 16; y < 512; y += 32) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(512, y + ((y / 32) % 2 ? 4 : -4));
    ctx.stroke();
  }
  ctx.restore();

  strokePanel([[256, 0], [256, 512]], suit.seam, 3, 0.5);
  strokePanel([[144, 0], [210, 140], [190, 326], [126, 512]], suit.seam, 3, 0.46);
  strokePanel(mirrorX([[144, 0], [210, 140], [190, 326], [126, 512]]), suit.seam, 3, 0.46);
  strokePanel([[88, 114], [178, 210], [166, 300], [74, 398]], suit.seam, 2, 0.4);
  strokePanel(mirrorX([[88, 114], [178, 210], [166, 300], [74, 398]]), suit.seam, 2, 0.4);

  strokePanel([[258, 52], [286, 150], [278, 272], [304, 436]], suit.glow, 2.4, 0.78);
  strokePanel(mirrorX([[258, 52], [286, 150], [278, 272], [304, 436]]), suit.glow, 2.4, 0.78);
  strokePanel([[102, 172], [170, 236], [160, 326]], suit.glow, 1.8, 0.5);
  strokePanel(mirrorX([[102, 172], [170, 236], [160, 326]]), suit.glow, 1.8, 0.5);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(1.15, 2.05);
  texture.anisotropy = 4;
  texture.name = "vrm-body-suit-surface-texture";
  return texture;
}

function createBaseSuitMaterial(palette = {}, options = {}) {
  const opacity = clamp(numberOr(options.opacity, 1), 0.5, 1);
  const suit = resolveBaseSuitPalette(palette);
  return new THREE.MeshStandardMaterial({
    name: "vrm-body-suit-surface-material",
    color: suit.base,
    map: createBaseSuitTexture(palette),
    emissive: suit.glow.clone().lerp(new THREE.Color(BASE_SUIT_EMISSIVE), 0.55),
    emissiveIntensity: numberOr(options.emissiveIntensity, 0.22),
    metalness: 0.14,
    roughness: 0.48,
    transparent: opacity < 0.995,
    opacity,
    depthWrite: opacity >= 0.98,
    side: THREE.DoubleSide,
  });
}

function baseSuitMaterialKey(palette = {}, options = {}) {
  return JSON.stringify({
    primary: palette.primary || BASE_SUIT_COLOR,
    secondary: palette.secondary || "#52777E",
    emissive: palette.emissive || BASE_SUIT_EMISSIVE,
    opacity: numberOr(options.opacity, 1),
    emissiveIntensity: numberOr(options.emissiveIntensity, 0.22),
  });
}

function createArmorMockSurfaceTexture(part, palette = {}, surfacePlan = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const primary = palette.primary || "#F4F1E8";
  const secondary = palette.secondary || "#8C96A3";
  const emissive = palette.emissive || "#43D8FF";
  const seed = hashString(`${part}:${surfacePlan.contract_version || "surface-plan.v1"}`);
  ctx.fillStyle = secondary;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = primary;
  const stripeWidth = 42 + (seed % 26);
  for (let x = -512; x < 1024; x += stripeWidth) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x + 22, 0);
    ctx.lineTo(x + 534, 512);
    ctx.lineTo(x + 512, 512);
    ctx.closePath();
    ctx.fill();
  }
  ctx.globalAlpha = 0.26;
  ctx.strokeStyle = emissive;
  ctx.lineWidth = 2;
  for (let x = 64 + (seed % 32); x < 512; x += 128) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x + ((seed % 2) ? 70 : -70), 512);
    ctx.stroke();
  }
  ctx.lineWidth = 1.5;
  ctx.globalAlpha = 0.2;
  ctx.strokeStyle = "#132d32";
  for (let y = 96; y < 512; y += 112) {
    ctx.beginPath();
    ctx.moveTo(0, y + (seed % 17));
    ctx.lineTo(512, y - (seed % 23));
    ctx.stroke();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(0.9, 1.25);
  texture.anisotropy = 4;
  texture.name = `texture_mock_preview:${part}`;
  texture.userData.textureMockPreview = true;
  texture.userData.surfacePlanContract = surfacePlan.contract_version || "surface-plan.v1";
  return texture;
}

function armorPreviewColorForPart(part, palette) {
  const primary = new THREE.Color(palette?.primary || "#F4F1E8");
  const secondary = new THREE.Color(palette?.secondary || "#8C96A3");
  const heroRed = new THREE.Color(ARMOR_PREVIEW_RED);
  const redWeight = part === "helmet" || part === "chest" || part === "back" ? 0.14 : 0.08;
  return secondary.clone().lerp(primary, 0.18).lerp(heroRed, redWeight);
}

function finishArmorPreviewMaterial(material, part, palette, options = {}) {
  const emissive = new THREE.Color(palette?.emissive || "#43D8FF");
  if (options.surfaceTexture) {
    material.color?.setHex?.(0xffffff);
  } else {
    material.color?.copy?.(armorPreviewColorForPart(part, palette));
  }
  material.emissive?.copy?.(emissive);
  material.emissiveIntensity = Math.max(
    numberOr(material.emissiveIntensity, 0),
    part === "chest" || part === "helmet" ? 0.2 : 0.12,
  );
  if ("metalness" in material) material.metalness = Math.max(numberOr(material.metalness, 0), 0.42);
  if ("roughness" in material) material.roughness = clamp(numberOr(material.roughness, 0.34), 0.22, 0.42);
  material.transparent = false;
  material.opacity = 1;
  material.depthWrite = true;
  material.depthTest = true;
  material.side = THREE.DoubleSide;
  material.needsUpdate = true;
  return material;
}

function materialForPart(part, palette) {
  return finishArmorPreviewMaterial(
    new THREE.MeshStandardMaterial({
      name: `armor-preview-material:${part}`,
      metalness: 0.36,
      roughness: 0.34,
      side: THREE.DoubleSide,
    }),
    part,
    palette,
  );
}

function addArmorEdges(mesh, palette, options = {}) {
  const color = new THREE.Color(palette?.emissive || "#43D8FF");
  const seam = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({
      color: 0x1d2a28,
      transparent: true,
      opacity: numberOr(options.seamOpacity, 0.16),
      depthTest: options.seamDepthTest ?? true,
    }),
  );
  seam.name = `${mesh.name}-part-seams`;
  seam.renderOrder = numberOr(options.seamRenderOrder, 7.1);
  seam.userData.previewLayer = "surface_lines";
  const glow = new THREE.LineSegments(
    new THREE.EdgesGeometry(mesh.geometry, 28),
    new THREE.LineBasicMaterial({
      color,
      transparent: true,
      opacity: numberOr(options.glowOpacity, 0.28),
      depthTest: options.glowDepthTest ?? true,
    }),
  );
  glow.name = `${mesh.name}-surface-lines`;
  glow.renderOrder = numberOr(options.glowRenderOrder, 7.2);
  glow.userData.previewLayer = "surface_lines";
  mesh.add(seam, glow);
}

function addArmorEdgesToObject(object, palette) {
  const meshes = [];
  object.traverse((child) => {
    if (child.isMesh && child.geometry) meshes.push(child);
  });
  for (const mesh of meshes) {
    addArmorEdges(mesh, palette);
  }
}

function isGltfAsset(path) {
  return /\.(glb|gltf)$/i.test(String(path || "").split(/[?#]/)[0]);
}

function adjacentPreviewMeshAsset(asset) {
  const clean = String(asset || "").replace(/[?#].*$/, "");
  const match = clean.match(/^(.*)\/([^/]+)\.(?:glb|gltf)$/i);
  return match ? `${match[1]}/preview/${match[2]}.mesh.json` : null;
}

function uniquePaths(paths) {
  const seen = new Set();
  return paths.filter((path) => {
    if (!path || seen.has(path)) return false;
    seen.add(path);
    return true;
  });
}

function meshJsonAssetCandidates(part, asset) {
  const defaultAsset = normalizePath(`viewer/assets/meshes/${part}.mesh.json`);
  const candidates = [];
  if (isGltfAsset(asset)) {
    candidates.push(adjacentPreviewMeshAsset(asset));
  } else {
    candidates.push(asset);
  }
  candidates.push(defaultAsset);
  return uniquePaths(candidates);
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

async function loadMeshJsonGeometry(part, asset) {
  const errors = [];
  for (const candidate of meshJsonAssetCandidates(part, asset)) {
    try {
      const payload = await fetchJson(candidate);
      return {
        geometry: meshGeometryFromPayload(payload),
        loadedAssetRef: candidate,
      };
    } catch (error) {
      errors.push(`${candidate}: ${String(error?.message || error)}`);
    }
  }
  throw new Error(errors.join(" | ") || "Mesh JSON asset failed.");
}

async function loadGltf(asset) {
  const GLTFLoader = await getGLTFLoaderClass();
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.load(asset, resolve, undefined, reject);
  });
}

async function loadGlbArmorObject(asset, part) {
  const gltf = await loadGltf(asset);
  const model = gltf?.scene || gltf?.scenes?.[0] || null;
  if (!model) {
    throw new Error("GLB asset has no renderable scene.");
  }

  let root = null;
  try {
    root = new THREE.Group();
    root.name = `${part}-glb-root`;
    root.add(model);
    root.updateMatrixWorld(true);

    const meshes = [];
    root.traverse((child) => {
      if (!child.isMesh || !child.geometry) return;
      meshes.push(child);
      child.renderOrder = 4;
      if (!child.geometry.getAttribute("normal")) {
        child.geometry.computeVertexNormals();
      }
    });
    if (!meshes.length) {
      throw new Error("GLB asset has no renderable meshes.");
    }

    const box = new THREE.Box3().setFromObject(root);
    if (box.isEmpty()) {
      throw new Error("GLB asset bounds are empty.");
    }
    const size = box.getSize(new THREE.Vector3());
    if (Math.max(size.x, size.y, size.z) < MIN_RENDERABLE_MESH_SIZE) {
      throw new Error("GLB asset bounds are empty.");
    }

    const center = box.getCenter(new THREE.Vector3());
    model.position.sub(center);
    root.updateMatrixWorld(true);

    const centeredBox = new THREE.Box3().setFromObject(root);
    const sourceSize = centeredBox.getSize(new THREE.Vector3());
    return { object: root, sourceSize };
  } catch (error) {
    disposeObjectTree(root || model);
    throw error;
  }
}

function applySurfaceTextureToMaterial(material, texture, mockSurfaceTexture) {
  const next = material?.clone?.() || new THREE.MeshStandardMaterial();
  const surfaceTexture = texture || mockSurfaceTexture;
  if (!surfaceTexture) return next;
  next.map = surfaceTexture;
  next.color?.setHex?.(0xffffff);
  if (typeof next.emissiveIntensity === "number") {
    next.emissiveIntensity *= texture ? 0.6 : 0.22;
  }
  next.transparent = false;
  next.opacity = 1;
  next.depthWrite = true;
  next.depthTest = true;
  next.needsUpdate = true;
  return next;
}

function applyArmorSurfaceToObject(object, part, palette, texture, mockSurfaceTexture) {
  object.traverse((child) => {
    if (!child.isMesh) return;
    child.renderOrder = 7;
    if (!child.material) {
      child.material = materialForPart(part, palette);
    }
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    const nextMaterials = materials.map((material) => {
      const previewMaterial = finishArmorPreviewMaterial(
        material?.clone?.() || new THREE.MeshStandardMaterial(),
        part,
        palette,
        { surfaceTexture: Boolean(texture || mockSurfaceTexture || material?.map) },
      );
      return applySurfaceTextureToMaterial(previewMaterial, texture, mockSurfaceTexture);
    });
    child.material = Array.isArray(child.material) ? nextMaterials : nextMaterials[0];
  });
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
      geometry = new THREE.BoxGeometry(0.7, 0.74, 0.24, 2, 3, 2);
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

function createArmorShellMaterial(part, palette) {
  const secondary = new THREE.Color(palette?.secondary || "#8C96A3").lerp(new THREE.Color(0xffffff), 0.32);
  const emissive = new THREE.Color(palette?.emissive || "#43D8FF");
  return new THREE.MeshStandardMaterial({
    name: "armor-attachment-preview-shell-material",
    color: secondary,
    emissive,
    emissiveIntensity: part === "helmet" || part === "chest" ? 0.14 : 0.08,
    metalness: 0.04,
    roughness: 0.68,
    transparent: true,
    opacity: 0.08,
    depthWrite: false,
    depthTest: true,
    side: THREE.DoubleSide,
  });
}

function createArmorAttachmentShellMesh(part, module, palette) {
  const geometry = createFallbackArmorGeometry(part);
  const sourceSize = new THREE.Vector3();
  geometry.computeBoundingBox();
  geometry.boundingBox.getSize(sourceSize);
  const mesh = new THREE.Mesh(geometry, createArmorShellMaterial(part, palette));
  mesh.name = `${part}-attachment-preview-shell`;
  mesh.renderOrder = 5;
  mesh.userData.sourceSize = sourceSize;
  mesh.userData.armorPart = true;
  mesh.userData.attachmentPreviewShell = true;
  mesh.userData.texturePath = null;
  mesh.userData.meshSource = "attachment_preview_shell";
  mesh.userData.previewRole = "proxy_envelope_only";
  mesh.userData.previewPriority = "auxiliary_proxy";
  addArmorEdges(mesh, palette, {
    seamOpacity: 0.08,
    glowOpacity: 0.16,
    glowDepthTest: true,
    seamRenderOrder: 4.6,
    glowRenderOrder: 4.7,
  });
  return mesh;
}

function demoteAttachmentPreviewShell(shell) {
  shell.userData.previewPriority = "post_load_hidden_guide";
  shell.visible = false;
  shell.renderOrder = 4.4;
  shell.traverse((object) => {
    if (object.isMesh && object.material) {
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      for (const material of materials) {
        material.transparent = true;
        material.opacity = 0.018;
        material.depthWrite = false;
        material.depthTest = true;
        material.wireframe = true;
        material.needsUpdate = true;
      }
      object.renderOrder = 4.4;
      return;
    }
    if (object.isLineSegments && object.material) {
      object.material.opacity = Math.min(numberOr(object.material.opacity, 0.08), 0.08);
      object.material.depthTest = true;
      object.material.needsUpdate = true;
      object.renderOrder = 4.5;
    }
  });
}

async function createArmorMesh(part, module, palette, surfacePlan = null) {
  const asset = normalizePath(module?.asset_ref || `viewer/assets/meshes/${part}.mesh.json`);
  const isGlbAsset = isGltfAsset(asset);
  let geometry;
  let object = null;
  let sourceSize = null;
  let meshSource = "mesh_asset";
  let meshError = "";
  let loadedAssetRef = asset;
  if (isGlbAsset) {
    try {
      const result = await loadGlbArmorObject(asset, part);
      object = result.object;
      sourceSize = result.sourceSize;
      meshSource = "glb_asset";
    } catch (error) {
      meshError = `GLB: ${String(error?.message || error)}`;
      console.warn(`armor GLB fallback for ${part}: ${meshError}`);
    }
  }

  try {
    if (!object) {
      const result = await loadMeshJsonGeometry(part, asset);
      geometry = result.geometry;
      loadedAssetRef = result.loadedAssetRef;
      meshSource = "mesh_asset";
    }
  } catch (jsonError) {
    if (!object) {
      meshSource = FALLBACK_MESH_SOURCE;
      meshError = [meshError, `Mesh JSON: ${String(jsonError?.message || jsonError)}`].filter(Boolean).join("; ");
      console.warn(`armor mesh fallback for ${part}: ${meshError}`);
      geometry = createFallbackArmorGeometry(part);
      loadedAssetRef = null;
    }
  }
  if (!sourceSize) {
    sourceSize = new THREE.Vector3();
    geometry.computeBoundingBox();
    geometry.boundingBox.getSize(sourceSize);
  }
  const material = object ? null : materialForPart(part, palette);
  const texture = await loadTextureMap(module?.texture_path);
  let mockSurfaceTexture = null;
  if (texture && !object) {
    material.map = texture;
    finishArmorPreviewMaterial(material, part, palette, { surfaceTexture: true });
    material.emissiveIntensity *= 0.72;
    material.needsUpdate = true;
  } else if (!module?.texture_path && surfacePlan?.contract_version) {
    mockSurfaceTexture = createArmorMockSurfaceTexture(part, palette, surfacePlan);
    if (!object) {
      material.map = mockSurfaceTexture;
      finishArmorPreviewMaterial(material, part, palette, { surfaceTexture: true });
      material.emissiveIntensity *= 0.22;
      material.needsUpdate = true;
    }
  }
  const mesh = object || new THREE.Mesh(geometry, material);
  if (object) {
    applyArmorSurfaceToObject(object, part, palette, texture, mockSurfaceTexture);
  }
  mesh.name = part;
  mesh.renderOrder = 7;
  mesh.userData.sourceSize = sourceSize;
  mesh.userData.texturePath = module?.texture_path || null;
  mesh.userData.textureLoaded = Boolean(texture);
  mesh.userData.textureMockPreview = Boolean(mockSurfaceTexture);
  mesh.userData.textureLoadFailed = Boolean(module?.texture_path && !texture);
  mesh.userData.surfacePlanContract = mockSurfaceTexture?.userData?.surfacePlanContract || null;
  mesh.userData.meshSource = meshSource;
  mesh.userData.previewLayer = "armor_model";
  mesh.userData.previewRole = meshSource === "glb_asset" ? "delivered_glb_primary" : "fallback_preview_mesh";
  mesh.userData.assetRef = asset;
  mesh.userData.loadedAssetRef = loadedAssetRef;
  mesh.userData.meshError = meshError;
  if (object) addArmorEdgesToObject(mesh, palette);
  else addArmorEdges(mesh, palette);
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
    this.currentPalette = {};
    this.baseSuitMaterial = null;
    this.baseSuitMaterialKey = "";
    this.viewYaw = 0;
    this.viewPitch = 0;
    this.viewZoom = 1;
    this.autoSpin = true;
    this.dragState = null;
    this.previewStats = {
      armorParts: 0,
      glbParts: 0,
      fallbackParts: 0,
      texturedParts: 0,
      textureFailedParts: 0,
      mockTexturedParts: 0,
      baseSuitVisible: true,
      vrmVisible: false,
      heightCm: DEFAULT_HEIGHT_CM,
      displayPoseChains: 0,
      displayPoseMode: "pending",
      viewPreset: "front",
      viewLabel: PREVIEW_VIEW_PRESETS.front.label,
      fitQa: null,
      structureQa: null,
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
    this.installPreviewControls();
    this.installViewPresetControls();
    this.publishPreviewStats();
    this.animate();
    window.addEventListener("resize", () => this.resize());
  }

  publishPreviewStats() {
    if (!this.canvas) return;
    this.previewStats.baseSuitVisible = Boolean(this.vrmModel || this.ghostGroup?.visible);
    this.canvas.dataset.previewArmorParts = String(this.previewStats.armorParts);
    this.canvas.dataset.previewGlbParts = String(this.previewStats.glbParts || 0);
    this.canvas.dataset.previewFallbackParts = String(this.previewStats.fallbackParts);
    this.canvas.dataset.previewTexturedParts = String(this.previewStats.texturedParts);
    this.canvas.dataset.previewTextureFailedParts = String(this.previewStats.textureFailedParts || 0);
    this.canvas.dataset.previewMockTexturedParts = String(this.previewStats.mockTexturedParts || 0);
    this.canvas.dataset.previewBaseSuit = this.previewStats.baseSuitVisible ? "visible" : "hidden";
    this.canvas.dataset.previewVrm = this.previewStats.vrmVisible ? "visible" : "fallback";
    this.canvas.dataset.previewHeightCm = String(Math.round(this.heightCm));
    this.canvas.dataset.previewHeightScale = (this.heightCm / DEFAULT_HEIGHT_CM).toFixed(3);
    this.canvas.dataset.previewDisplayPoseChains = String(this.previewStats.displayPoseChains || 0);
    this.canvas.dataset.previewDisplayPoseMode = this.previewStats.displayPoseMode || "pending";
    this.canvas.dataset.previewView = this.previewStats.viewPreset || "front";
    this.canvas.dataset.previewViewLabel = this.previewStats.viewLabel || PREVIEW_VIEW_PRESETS.front.label;
    updatePreviewLayerPanel(latestForgeData, this);
  }

  buildBaseSuit() {
    const ghost = createBaseSuitMaterial({}, { opacity: 0.5, emissiveIntensity: 0.24 });
    this.ghostGroup.name = "base-suit-vrm-surface-fallback";
    const standMat = new THREE.MeshBasicMaterial({ color: 0x9a7b2c, transparent: true, opacity: 0.14, depthTest: true });
    const seamMat = new THREE.MeshBasicMaterial({ color: 0x154e55, transparent: true, opacity: 0.2 });
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
          opacity: 0.3,
          depthTest: true,
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
      material.opacity = 0.14;
    }
    this.standGroup.add(floor);
    const spine = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 2.1, 12), standMat);
    spine.position.set(0, 0.62, -0.28);
    this.standGroup.add(spine);
    for (const [width, y, z] of [
      [0.56, 1.18, -0.48],
      [0.48, 0.74, -0.48],
    ]) {
      const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, width, 12), standMat);
      bar.rotation.z = Math.PI / 2;
      bar.position.set(0, y, z);
      this.standGroup.add(bar);
    }
    const guideMat = new THREE.LineBasicMaterial({
      color: 0x1c6f78,
      transparent: true,
      opacity: 0.18,
      depthTest: true,
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
    heightGuide.renderOrder = 2.6;
    heightGuide.userData.previewLayer = "dimension_guide";
    this.standGroup.add(heightGuide);
    this.group.add(this.ghostGroup);
    this.group.add(this.standGroup);
  }

  installPreviewControls() {
    const canvas = this.canvas;
    if (!canvas) return;
    canvas.addEventListener("pointerdown", (event) => {
      canvas.setPointerCapture?.(event.pointerId);
      canvas.classList.add("dragging");
      this.autoSpin = false;
      this.previewStats.viewPreset = "manual";
      this.previewStats.viewLabel = "手動";
      this.updateSpinToggle();
      this.updateViewPresetButtons();
      this.publishPreviewStats();
      this.dragState = {
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
      };
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!this.dragState || this.dragState.pointerId !== event.pointerId) return;
      const dx = event.clientX - this.dragState.x;
      const dy = event.clientY - this.dragState.y;
      this.dragState.x = event.clientX;
      this.dragState.y = event.clientY;
      this.viewYaw += dx * 0.008;
      this.viewPitch = clamp(this.viewPitch + dy * 0.004, -0.34, 0.22);
    });
    const stopDrag = (event) => {
      if (this.dragState?.pointerId === event.pointerId) this.dragState = null;
      canvas.classList.remove("dragging");
    };
    canvas.addEventListener("pointerup", stopDrag);
    canvas.addEventListener("pointercancel", stopDrag);
    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      this.zoomBy(event.deltaY > 0 ? 1.08 : 0.92);
    }, { passive: false });
  }

  installViewPresetControls() {
    const controls = UI.standControls;
    if (!controls || controls.dataset.viewPresetsInstalled === "true") return;
    controls.dataset.viewPresetsInstalled = "true";
    UI.resetViewButton?.classList.add("view-preset-button");
    if (UI.resetViewButton) UI.resetViewButton.dataset.viewPreset = "front";
    const buttons = [
      ["left", "左側"],
      ["back", "背面"],
      ["right", "右側"],
    ].map(([preset, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "view-preset-button";
      button.dataset.viewPreset = preset;
      button.title = `${label}を固定表示`;
      button.setAttribute("aria-label", `${label}を固定表示`);
      button.textContent = label;
      button.addEventListener("click", () => this.setViewPreset(preset));
      return button;
    });
    UI.resetViewButton?.after(...buttons);
    this.updateViewPresetButtons();
  }

  updateSpinToggle() {
    if (UI.spinToggle) UI.spinToggle.setAttribute("aria-pressed", this.autoSpin ? "true" : "false");
  }

  updateViewPresetButtons() {
    UI.standControls?.querySelectorAll("[data-view-preset]").forEach((button) => {
      const active = button.dataset.viewPreset === this.previewStats.viewPreset;
      button.dataset.viewActive = active ? "true" : "false";
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  setViewPreset(name, options = {}) {
    const preset = PREVIEW_VIEW_PRESETS[name] || PREVIEW_VIEW_PRESETS.front;
    this.viewYaw = preset.yaw;
    this.viewPitch = preset.pitch;
    this.viewZoom = numberOr(options.zoom, preset.zoom);
    this.autoSpin = false;
    this.previewStats.viewPreset = PREVIEW_VIEW_PRESETS[name] ? name : "front";
    this.previewStats.viewLabel = preset.label;
    this.updateSpinToggle();
    this.updateViewPresetButtons();
    this.updateCameraDistance();
    this.publishPreviewStats();
  }

  resetView() {
    this.setViewPreset("front", { zoom: 1 });
  }

  zoomBy(factor) {
    this.viewZoom = clamp(this.viewZoom * factor, 0.72, 1.45);
    this.updateCameraDistance();
  }

  toggleSpin() {
    this.autoSpin = !this.autoSpin;
    this.previewStats.viewPreset = this.autoSpin ? "spin" : "manual";
    this.previewStats.viewLabel = this.autoSpin ? "自動回転" : "手動";
    this.updateSpinToggle();
    this.updateViewPresetButtons();
    this.publishPreviewStats();
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
      this.applyForgeDisplayPose();
      this.ghostGroup.visible = false;
      this.refreshBaseSuitSurface(this.currentPalette);
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

  worldPositionForBone(boneName) {
    const bone = this.resolveBone(boneName);
    if (!bone) return null;
    bone.updateMatrixWorld(true);
    return bone.getWorldPosition(new THREE.Vector3());
  }

  displayPoseCenterWorldX() {
    const pairedCandidates = [
      ["leftShoulder", "rightShoulder"],
      ["leftUpperArm", "rightUpperArm"],
      ["leftLowerArm", "rightLowerArm"],
      ["leftHand", "rightHand"],
    ];
    for (const [left, right] of pairedCandidates) {
      const leftPos = this.worldPositionForBone(left);
      const rightPos = this.worldPositionForBone(right);
      if (leftPos && rightPos && Number.isFinite(leftPos.x) && Number.isFinite(rightPos.x)) {
        return (leftPos.x + rightPos.x) * 0.5;
      }
    }
    const centerCandidates = ["upperChest", "chest", "spine", "hips"]
      .map((boneName) => this.worldPositionForBone(boneName))
      .filter((pos) => pos && Number.isFinite(pos.x));
    if (centerCandidates.length) {
      return centerCandidates.reduce((sum, pos) => sum + pos.x, 0) / centerCandidates.length;
    }
    return 0;
  }

  displayArmTargetForChain(chain, bonePos) {
    const outwardMagnitude = Math.max(0, numberOr(chain.outward, 0));
    const fallbackSign = chain.bone?.startsWith("right") ? 1 : -1;
    const sideDelta = Number.isFinite(bonePos?.x) ? bonePos.x - this.displayPoseCenterWorldX() : fallbackSign;
    const outwardSign = Math.sign(sideDelta) || fallbackSign;
    return new THREE.Vector3(
      outwardSign * outwardMagnitude,
      numberOr(chain.down, -1),
      numberOr(chain.forward, 0),
    );
  }

  rotateBoneChainTowardWorldDir(boneName, childBoneName, target, strength = 1) {
    const bone = this.resolveBone(boneName);
    const childBone = this.resolveBone(childBoneName);
    if (!bone || !childBone) return false;
    bone.updateMatrixWorld(true);
    childBone.updateMatrixWorld(true);
    const bonePos = bone.getWorldPosition(new THREE.Vector3());
    const childPos = childBone.getWorldPosition(new THREE.Vector3());
    const currentDir = childPos.sub(bonePos);
    if (!Number.isFinite(currentDir.lengthSq()) || currentDir.lengthSq() < 1e-8) return false;
    currentDir.normalize();
    const targetDir = target?.isVector3
      ? target.clone()
      : new THREE.Vector3(
        numberOr(target?.[0], 0),
        numberOr(target?.[1], 0),
        numberOr(target?.[2], 0),
      );
    if (!Number.isFinite(targetDir.lengthSq()) || targetDir.lengthSq() < 1e-8) return false;
    targetDir.normalize();
    const deltaWorld = new THREE.Quaternion().setFromUnitVectors(currentDir, targetDir);
    const parentWorldQuat = bone.parent ? bone.parent.getWorldQuaternion(new THREE.Quaternion()) : new THREE.Quaternion();
    const boneWorldQuat = bone.getWorldQuaternion(new THREE.Quaternion());
    const desiredWorldQuat = deltaWorld.multiply(boneWorldQuat);
    const desiredLocalQuat = parentWorldQuat.clone().invert().multiply(desiredWorldQuat).normalize();
    bone.quaternion.slerp(desiredLocalQuat, clamp(strength, 0, 1));
    bone.updateMatrixWorld(true);
    return true;
  }

  applyForgeDisplayPose() {
    let applied = 0;
    for (const chain of FORGE_DISPLAY_ARM_POSE_CHAINS) {
      const bonePos = this.worldPositionForBone(chain.bone);
      const target = this.displayArmTargetForChain(chain, bonePos);
      if (this.rotateBoneChainTowardWorldDir(chain.bone, chain.childBone, target, chain.strength)) applied += 1;
    }
    this.metricsCache = null;
    this.previewStats.displayPoseChains = applied;
    this.previewStats.displayPoseMode = "center_outward_a_pose";
    this.vrmModel?.updateMatrixWorld(true);
    return applied;
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
    metrics.shoulderWidth = Math.max(distanceOr(metrics.leftShoulder, metrics.rightShoulder, 0.68), 0.58);
    metrics.torsoHeight = Math.max(distanceOr(metrics.upperChest, metrics.hips, 0.78), 0.68);
    metrics.headHeight = Math.max(distanceOr(metrics.head, metrics.neck, 0.2), 0.18);
    metrics.upperArmLength = Math.max(distanceOr(metrics.leftUpperArm, metrics.leftLowerArm, 0.34), 0.3);
    metrics.forearmLength = Math.max(distanceOr(metrics.leftLowerArm, metrics.leftHand, 0.34), 0.3);
    metrics.thighLength = Math.max(distanceOr(metrics.leftUpperLeg, metrics.leftLowerLeg, 0.46), 0.4);
    metrics.shinLength = Math.max(distanceOr(metrics.leftLowerLeg, metrics.leftFoot, 0.46), 0.4);
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
    if (part.endsWith("hand")) return [metrics[sideKey("LowerArm")], metrics[sideKey("Hand")]];
    if (part.endsWith("thigh")) return [metrics[sideKey("UpperLeg")], metrics[sideKey("LowerLeg")]];
    if (part.endsWith("shin")) return [metrics[sideKey("LowerLeg")], metrics[sideKey("Foot")]];
    return [null, null];
  }

  fitReferenceCenterForPart(part, metrics) {
    switch (part) {
      case "helmet":
        return metrics.head;
      case "chest":
      case "back":
        return midpoint(metrics.shouldersCenter, metrics.torsoCenter);
      case "waist":
        return metrics.hips;
      case "left_shoulder":
        return metrics.leftShoulder;
      case "right_shoulder":
        return metrics.rightShoulder;
      case "left_hand":
        return metrics.leftHand;
      case "right_hand":
        return metrics.rightHand;
      case "left_boot":
        return metrics.leftFoot;
      case "right_boot":
        return metrics.rightFoot;
      default: {
        const [start, end] = this.segmentForPart(part, metrics);
        return midpoint(start, end);
      }
    }
  }

  fitOffsetAllowanceForPart(part, module, segmentQuat = null) {
    const sidecar = sidecarMetadataForModule(part, module);
    if (Number.isFinite(sidecar.offsetLimitM)) {
      return clamp(Math.abs(sidecar.offsetLimitM), 0, 0.18);
    }
    const offsetTarget = runtimeOffsetForPreviewPart(part, module)
      || wornPlacementOffsetForPart(part, sidecar.offsetTarget);
    if (!offsetTarget) return 0;
    const offset = new THREE.Vector3(offsetTarget[0], offsetTarget[1], offsetTarget[2]);
    if (segmentQuat) offset.applyQuaternion(segmentQuat);
    return clamp(Math.abs(offset.z), 0, 0.18);
  }

  fitClearanceForPart(part, center, targetSize, metrics, module = null, segmentQuat = null) {
    const reference = this.fitReferenceCenterForPart(part, metrics);
    if (!reference || !center || !targetSize) return 0;
    const expectedDepth = Math.max(targetSize.z * 0.5, 0.001);
    const depthDistance = Math.abs(center.z - reference.z);
    const offsetAllowance = this.fitOffsetAllowanceForPart(part, module, segmentQuat);
    const exposedGap = Math.max(0, depthDistance - expectedDepth - offsetAllowance);
    if (part === "chest" || part === "back" || part === "waist") return exposedGap;
    return exposedGap > 0.04 ? exposedGap : 0;
  }

  targetSizeForPart(part, module, metrics) {
    const runtimeTarget = runtimeTargetSizeForPreviewPart(part, module);
    if (runtimeTarget) return runtimeTarget;
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
        size = new THREE.Vector3(shoulder * 0.9, torso * 0.68, shoulder * 0.28);
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
        size = new THREE.Vector3(shoulder * 0.21, shoulder * 0.26, shoulder * 0.39);
        break;
      default:
        size = new THREE.Vector3(0.24, 0.24, 0.24);
    }
    return softFitSize(part, module, size);
  }

  targetCenterForPart(part, module, metrics) {
    const fit = effectiveFitFor(part, module);
    const anchor = effectiveVrmAnchorFor(part, module);
    const sidecar = sidecarMetadataForModule(part, module);
    const front = part === "back" ? -1 : 1;
    const [segmentStart, segmentEnd] = this.segmentForPart(part, metrics);
    const segmentQuat = segmentFrameQuaternion(segmentStart, segmentEnd);
    let center = null;
    switch (part) {
      case "helmet":
        center = metrics.head?.clone().add(new THREE.Vector3(0, 0.04, metrics.shoulderWidth * 0.04));
        break;
      case "chest":
        center = midpoint(metrics.shouldersCenter, metrics.torsoCenter)?.add(new THREE.Vector3(0, -metrics.torsoHeight * 0.08, metrics.shoulderWidth * 0.10));
        break;
      case "back":
        center = midpoint(metrics.shouldersCenter, metrics.torsoCenter)?.add(new THREE.Vector3(0, -metrics.torsoHeight * 0.07, -metrics.shoulderWidth * 0.115));
        break;
      case "waist":
        center = metrics.hips?.clone().add(new THREE.Vector3(0, metrics.torsoHeight * 0.045, metrics.shoulderWidth * 0.018));
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
        center = metrics.leftFoot?.clone().add(new THREE.Vector3(0, 0.0, metrics.shoulderWidth * 0.018));
        break;
      case "right_boot":
        center = metrics.rightFoot?.clone().add(new THREE.Vector3(0, 0.0, metrics.shoulderWidth * 0.018));
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
    const placementOffset = runtimeOffsetForPreviewPart(part, module)
      || wornPlacementOffsetForPart(part, sidecar.placementOffset || sidecar.offsetTarget || anchor.offset);
    center = addOrientedOffset(center, placementOffset || [0, 0, 0], segmentQuat);
    center.y += clamp(numberOr(fit.offsetY, 0), -0.42, 0.42) * 0.12;
    center.z += clamp(numberOr(fit.zOffset, 0), -0.25, 0.25) * 0.55 * front;
    return center;
  }

  enforceWornCenterForPart(part, center, targetSize, metrics) {
    if (!center || !targetSize) return center;
    const next = center.clone();
    const reference = this.fitReferenceCenterForPart(part, metrics);
    if (reference && (part === "chest" || part === "back" || part === "waist")) {
      next.z = reference.z + wornDepthClamp(part, next.z - reference.z, metrics.shoulderWidth);
    }
    if (part.includes("boot")) {
      const foot = part.startsWith("left_") ? metrics.leftFoot : metrics.rightFoot;
      const floorCenterY = PREVIEW_FLOOR_Y + targetSize.y * 0.5 + 0.004;
      next.y = floorCenterY;
      if (foot) {
        next.x = foot.x;
        next.z = foot.z + wornDepthClamp(part, next.z - foot.z, metrics.shoulderWidth);
      }
    }
    return next;
  }

  vrmPoseFor(part, module, mesh) {
    if (!this.vrmModel || !this.boneMap.size) return null;
    const metrics = this.measureVrmMetrics();
    const rawCenter = this.targetCenterForPart(part, module, metrics);
    const targetSize = this.targetSizeForPart(part, module, metrics);
    const center = this.enforceWornCenterForPart(part, rawCenter, targetSize, metrics);
    if (!center) return null;
    const sourceSize = mesh.userData?.sourceSize || new THREE.Vector3(1, 1, 1);
    const [segmentStart, segmentEnd] = this.segmentForPart(part, metrics);
    const segmentQuat = segmentFrameQuaternion(segmentStart, segmentEnd);
    const referenceCenter = this.fitReferenceCenterForPart(part, metrics);
    const anchor = effectiveVrmAnchorFor(part, module);
    const runtimeRotation = runtimeRotationForPreviewPart(part, module);
    const rotation = runtimeRotation
      || fitVector(anchor.rotation, [0, 0, 0]).map((degrees) => THREE.MathUtils.degToRad(degrees));
    const anchorQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(rotation[0], rotation[1], rotation[2], "XYZ"));
    const quaternion = segmentQuat ? segmentQuat.clone().multiply(anchorQuat).normalize() : null;
    const anchorScale = fitVector(anchor.scale, [1, 1, 1]);
    const scale = scaleForTarget(sourceSize, targetSize);
    scale.set(
      clamp(scale.x * Math.max(anchorScale[0], 0.01), 0.04, 2.4),
      clamp(scale.y * Math.max(anchorScale[1], 0.01), 0.04, 2.4),
      clamp(scale.z * Math.max(anchorScale[2], 0.01), 0.04, 2.4),
    );
    return {
      p: center.toArray(),
      s: scale.toArray(),
      r: rotation,
      q: quaternion ? quaternion.toArray() : null,
      source: "vrm_bone_metrics",
      targetSize: targetSize.toArray(),
      fitGapM: this.fitClearanceForPart(part, center, targetSize, metrics, module, segmentQuat),
      fitOffsetAllowanceM: this.fitOffsetAllowanceForPart(part, module, segmentQuat),
      fitReferencePoint: referenceCenter?.toArray() || null,
      attachmentOffsetTargetM: sidecarMetadataForModule(part, module).offsetTarget,
      runtimePlacementSource: runtimePlacementForPreviewPart(part, module)?.target_size_source || null,
    };
  }

  applyPreviewPose(mesh, part, module) {
    const fallbackPose = armorStandPoseFor(part, module);
    const pose = this.vrmPoseFor(part, module, mesh) || {
      p: fallbackPose.p,
      s: fallbackPose.s,
      r: [0, 0, 0],
      source: "fallback_pose",
      targetSize: fallbackPose.s,
      fitGapM: 0,
      fitOffsetAllowanceM: 0,
      fitReferencePoint: null,
      attachmentOffsetTargetM: sidecarMetadataForModule(part, module).offsetTarget,
      runtimePlacementSource: null,
    };
    mesh.position.set(...pose.p);
    if (pose.q) mesh.quaternion.set(...pose.q);
    else mesh.rotation.set(...pose.r);
    mesh.scale.set(...pose.s);
    mesh.userData.fitPreview = pose.source;
    mesh.userData.fitTargetSize = pose.targetSize || fallbackPose.s;
    mesh.userData.fitGapM = numberOr(pose.fitGapM, 0);
    mesh.userData.fitOffsetAllowanceM = numberOr(pose.fitOffsetAllowanceM, 0);
    mesh.userData.fitReferencePoint = pose.fitReferencePoint || null;
    mesh.userData.attachmentOffsetTargetM = pose.attachmentOffsetTargetM || null;
    mesh.userData.runtimePlacementSource = pose.runtimePlacementSource || null;
  }

  getBaseSuitMaterial(palette = this.currentPalette, options = {}) {
    const key = baseSuitMaterialKey(palette, options);
    if (!this.baseSuitMaterial || this.baseSuitMaterialKey !== key) {
      disposeMaterial(this.baseSuitMaterial);
      this.baseSuitMaterial = createBaseSuitMaterial(palette, options);
      this.baseSuitMaterialKey = key;
    }
    return this.baseSuitMaterial;
  }

  refreshBaseSuitSurface(palette = this.currentPalette) {
    this.currentPalette = palette || {};
    if (!this.vrmModel) return;
    const material = this.getBaseSuitMaterial(this.currentPalette, { opacity: 1, emissiveIntensity: 0.22 });
    this.vrmModel.traverse((obj) => {
      if (!obj.isMesh) return;
      if (obj.material !== material && obj.userData.baseSuitSurface !== "vrm_surface_texture") {
        disposeMaterial(obj.material);
      }
      obj.material = material;
      obj.renderOrder = 2;
      obj.userData.baseSuitSurface = "vrm_surface_texture";
    });
  }

  prepareVrmMannequin(model) {
    const material = this.getBaseSuitMaterial(this.currentPalette, { opacity: 1, emissiveIntensity: 0.22 });
    const originalMaterials = new Set();
    model.traverse((obj) => {
      if (!obj.isMesh) return;
      obj.renderOrder = 2;
      originalMaterials.add(obj.material);
      obj.material = material;
      obj.userData.baseSuitSurface = "vrm_surface_texture";
    });
    originalMaterials.forEach((originalMaterial) => {
      if (originalMaterial !== material) disposeMaterial(originalMaterial);
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
    this.camera.position.set(0, 0.96 * Math.min(heightScale, 1.18), 4.15 * heightScale * narrowCompensation * this.viewZoom);
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
    this.previewStats.fitQa = null;
    this.previewStats.structureQa = null;
  }

  async renderSuit(suitspec) {
    await this.vrmReady;
    this.clearArmor();
    this.setHeightCm(suitspec?.body_profile?.height_cm || DEFAULT_HEIGHT_CM);
    this.metricsCache = null;
    const modules = suitspec?.modules || {};
    const palette = suitspec?.palette || {};
    const surfacePlan = surfacePlanFromData(suitspec) || surfacePlanFromData(latestForgeData);
    this.refreshBaseSuitSurface(palette);
    const records = Object.entries(modules).filter(([, module]) => module?.enabled);
    const shells = records.map(([part, module]) => createArmorAttachmentShellMesh(part, module, palette));
    for (let index = 0; index < shells.length; index += 1) {
      const [part, module] = records[index];
      const shell = shells[index];
      this.applyPreviewPose(shell, part, module);
      this.group.add(shell);
    }
    let meshes = [];
    try {
      meshes = await mapWithConcurrency(
        records,
        ARMOR_ASSET_LOAD_CONCURRENCY,
        ([part, module]) => createArmorMesh(part, module, palette, surfacePlan),
        ({ done, total }) => {
          this.previewStats.assetLoadDone = done;
          this.previewStats.assetLoadTotal = total;
          setStatus(`装甲アセット読込中... ${done}/${total}`, "pending");
          this.publishPreviewStats();
          updatePreviewLayerPanel(suitspec);
        },
      );
      for (let index = 0; index < meshes.length; index += 1) {
        const [part, module] = records[index];
        const mesh = meshes[index];
        this.applyPreviewPose(mesh, part, module);
        mesh.userData.armorPart = true;
        mesh.renderOrder = 7;
        this.group.add(mesh);
      }
    } finally {
      shells.forEach((shell) => demoteAttachmentPreviewShell(shell));
    }
    this.previewStats.armorParts = meshes.length;
    this.previewStats.glbParts = meshes.filter((mesh) => mesh.userData.meshSource === "glb_asset").length;
    this.previewStats.fallbackParts = meshes.filter((mesh) => mesh.userData.meshSource === FALLBACK_MESH_SOURCE).length;
    this.previewStats.texturedParts = meshes.filter((mesh) => mesh.userData.textureLoaded).length;
    this.previewStats.textureFailedParts = meshes.filter((mesh) => mesh.userData.textureLoadFailed).length;
    this.previewStats.mockTexturedParts = meshes.filter((mesh) => mesh.userData.textureMockPreview).length;
    this.previewStats.fitQa = summarizePreviewFitQa(records, meshes);
    this.previewStats.structureQa = structuralQaForFit(this.previewStats.fitQa);
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
    const autoYaw = this.autoSpin ? Math.sin(performance.now() * 0.00028) * 0.08 : 0;
    this.group.rotation.set(this.viewPitch, this.viewYaw + autoYaw, 0);
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(() => this.animate());
  }
}

armorStand = new ArmorStand(UI.canvas);

if (UI.heightCm) {
  UI.heightCm.addEventListener("input", () => {
    syncHeightControls(UI.heightCm.value);
    markQuestLinkStaleForPreview("身長を変更しました。Questへ反映するには再生成してください。");
  });
  UI.heightCm.addEventListener("change", () => {
    syncHeightControls(UI.heightCm.value);
    markQuestLinkStaleForPreview("身長を変更しました。Questへ反映するには再生成してください。");
  });
}
if (UI.heightRange) {
  UI.heightRange.addEventListener("input", () => {
    syncHeightControls(UI.heightRange.value);
    markQuestLinkStaleForPreview("身長を変更しました。Questへ反映するには再生成してください。");
  });
}
UI.resetViewButton?.addEventListener("click", () => armorStand?.resetView());
UI.zoomOutButton?.addEventListener("click", () => armorStand?.zoomBy(1.1));
UI.zoomInButton?.addEventListener("click", () => armorStand?.zoomBy(0.9));
UI.spinToggle?.addEventListener("click", () => armorStand?.toggleSpin());
syncHeightControls(UI.heightCm?.value || DEFAULT_HEIGHT_CM);

function applyResult(data) {
  latestForgeData = data;
  syncVariantSelectsFromForgeData(data);
  const quest = questLinkOptions(data.recall_code || "");
  const recallCode = data.recall_code || "----";
  UI.recallCode.textContent = recallCode;
  UI.recallCode.setAttribute("aria-label", `Quest入力コード ${recallCode}`);
  UI.questLink.href = quest.url;
  UI.questLink.textContent = "Quest入力ページを開く";
  UI.questLink.classList.remove("disabled");
  delete UI.questLink.dataset.stalePreview;
  UI.questLink.setAttribute("aria-disabled", "false");
  UI.questLink.setAttribute("aria-label", `Quest入力ページを開く。コード ${recallCode}`);
  if (UI.questUrl) UI.questUrl.value = quest.url;
  if (UI.questUrlHint) UI.questUrlHint.textContent = quest.hint;
  renderAssetPipeline(data);
  updateModelerHandoff(data);
  updateTextureJobAvailability(data);
  renderExhibitionSummary(data);
  UI.emptyStand.classList.add("hidden");
}

async function submitForge(event) {
  event.preventDefault();
  latestForgeData = null;
  setTextureJobButtonsText("表面生成を試す");
  updateTextureJobAvailability(null);
  UI.button.disabled = true;
  syncHeightControls(UI.heightCm?.value);
  setStatus(EXHIBITION_OPERATOR_COPY.forge.submitting, "pending");
  try {
    const data = await fetchJson("/v1/suits/forge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formPayload()),
    });
    setStatus(EXHIBITION_OPERATOR_COPY.forge.assembling, "pending");
    await armorStand.renderSuit(data.preview);
    setStatus(EXHIBITION_OPERATOR_COPY.forge.questPreparing, "pending");
    await ensureRuntimeInfo();
    assertForgeReadiness(data);
    applyResult(data);
    setStatus(EXHIBITION_OPERATOR_COPY.forge.complete, "complete");
  } catch (error) {
    setStatus(String(error?.message || error), "error");
  } finally {
    UI.button.disabled = false;
  }
}

applyExhibitionModePreference();
renderPartGrid();
loadLocalVariantCatalog();
renderPreviewLegend();
renderAssetPipeline();
syncPreviewLegendPalette();
renderServiceConfig();
updateTextureJobAvailability();
updateModelerHandoff();
updatePreviewLayerPanel(latestForgeData);
runtimeInfoPromise = loadRuntimeInfo();
UI.form.addEventListener("submit", submitForge);
for (const input of [UI.displayName, UI.archetype, UI.temperament, UI.brief]) {
  input?.addEventListener("input", () => markQuestLinkStaleForPreview("入力内容を変更しました。Questへ反映するには再生成してください。"));
  input?.addEventListener("change", () => markQuestLinkStaleForPreview("入力内容を変更しました。Questへ反映するには再生成してください。"));
}
for (const colorInput of [UI.primaryColor, UI.secondaryColor, UI.emissiveColor]) {
  colorInput?.addEventListener("input", () => {
    syncPreviewLegendPalette();
    markQuestLinkStaleForPreview("配色を変更しました。Questへ反映するには再生成してください。");
  });
}
function runTextureGenerationFromUi() {
  startTextureGeneration().catch((error) => {
    setTextureJobState("error", "表面生成エラー", String(error?.message || error), 0);
    updateTextureJobAvailability(latestForgeData);
  });
}

UI.textureJobButton?.addEventListener("click", runTextureGenerationFromUi);
UI.textureQuickButton?.addEventListener("click", runTextureGenerationFromUi);
