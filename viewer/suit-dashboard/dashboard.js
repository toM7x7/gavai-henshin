import * as THREE from "../body-fit/vendor/three/build/three.module.js";
import { OrbitControls } from "../body-fit/vendor/three/examples/jsm/controls/OrbitControls.js";
import {
  FIT_CONTACT_PAIRS,
  VRM_BONE_ALIASES,
  VRM_HUMANOID_BONES,
  baseFitFor,
  baseVrmAnchorFor,
  effectiveFitFor,
  effectiveVrmAnchorFor,
  normalizeAttachmentSlot,
  normalizeBoneName,
  normalizeFit,
  normalizeVec3 as vec3Or,
  normalizeVrmAnchor,
  partColor,
} from "../shared/armor-canon.js";
import {
  applyAutoFitResultToSuitSpec,
  fitArmorToVrm,
  formatAutoFitSummary,
} from "../shared/auto-fit-engine.js?v=20260307b";

const UI = {
  suitPath: document.getElementById("suitPath"),
  emotionDrive: document.getElementById("emotionDrive"),
  emotionScene: document.getElementById("emotionScene"),
  emotionProtectTarget: document.getElementById("emotionProtectTarget"),
  emotionVow: document.getElementById("emotionVow"),
  operatorProtectArchetype: document.getElementById("operatorProtectArchetype"),
  operatorTemperamentBias: document.getElementById("operatorTemperamentBias"),
  operatorColorMood: document.getElementById("operatorColorMood"),
  operatorProfileNote: document.getElementById("operatorProfileNote"),
  generationBrief: document.getElementById("generationBrief"),
  selectedPartsSummary: document.getElementById("selectedPartsSummary"),
  fallbackDir: document.getElementById("fallbackDir"),
  textureMode: document.getElementById("textureMode"),
  providerProfile: document.getElementById("providerProfile"),
  trackingSource: document.getElementById("trackingSource"),
  uvRefine: document.getElementById("uvRefine"),
  simPath: document.getElementById("simPath"),
  useCache: document.getElementById("useCache"),
  preferFallback: document.getElementById("preferFallback"),
  updateSuitspec: document.getElementById("updateSuitspec"),
  heroRender: document.getElementById("heroRender"),
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
  stageSummary: document.getElementById("stageSummary"),
  stageScanline: document.getElementById("stageScanline"),
  stageMeta: document.getElementById("stageMeta"),
  routeContractStatus: document.getElementById("routeContractStatus"),
  questPreflightStatus: document.getElementById("questPreflightStatus"),
  questPreflightGeneration: document.getElementById("questPreflightGeneration"),
  questPreflightDiff: document.getElementById("questPreflightDiff"),
  questPreflightFit: document.getElementById("questPreflightFit"),
  questPreflightReplay: document.getElementById("questPreflightReplay"),
  stageParts: document.getElementById("stageParts"),
  eventLog: document.getElementById("eventLog"),
  latestTrialUpdated: document.getElementById("latestTrialUpdated"),
  latestTrialStatus: document.getElementById("latestTrialStatus"),
  latestTrialSession: document.getElementById("latestTrialSession"),
  latestTrialState: document.getElementById("latestTrialState"),
  latestTrialEvents: document.getElementById("latestTrialEvents"),
  latestTrialReplayState: document.getElementById("latestTrialReplayState"),
  latestTrialReplay: document.getElementById("latestTrialReplay"),
  suitRegistryName: document.getElementById("suitRegistryName"),
  suitRegistryStorage: document.getElementById("suitRegistryStorage"),
  suitRegistryStatus: document.getElementById("suitRegistryStatus"),
  suitRegistryRecallCode: document.getElementById("suitRegistryRecallCode"),
  suitRegistryIssueId: document.getElementById("suitRegistryIssueId"),
  suitRegistryState: document.getElementById("suitRegistryState"),
  btnIssueSuitId: document.getElementById("btnIssueSuitId"),
  btnSaveSuitRegistry: document.getElementById("btnSaveSuitRegistry"),
  btnFetchSuitRegistry: document.getElementById("btnFetchSuitRegistry"),
  status: document.getElementById("status"),
  cards: document.getElementById("cards"),
  btnRefreshSuits: document.getElementById("btnRefreshSuits"),
  btnLoadSuit: document.getElementById("btnLoadSuit"),
  btnRefreshLatestTrial: document.getElementById("btnRefreshLatestTrial"),
  btnGenerate: document.getElementById("btnGenerate"),
  btnCancelGenerate: document.getElementById("btnCancelGenerate"),
  btnAutoFitSave: document.getElementById("btnAutoFitSave"),
  btnOpenBodyFit: document.getElementById("btnOpenBodyFit"),
  advancedSettings: document.getElementById("advancedSettings"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  panelParts: document.getElementById("panelParts"),
  panelBody: document.getElementById("panelBody"),
  bodyFrontCanvas: document.getElementById("bodyFrontCanvas"),
  bodyStageOverlay: document.getElementById("bodyStageOverlay"),
  bodyStageOverlayText: document.getElementById("bodyStageOverlayText"),
  heroPosterPanel: document.getElementById("heroPosterPanel"),
  heroPosterMeta: document.getElementById("heroPosterMeta"),
  heroPosterImage: document.getElementById("heroPosterImage"),
  bodyFrontMeta: document.getElementById("bodyFrontMeta"),
  bodyTuneStatus: document.getElementById("bodyTuneStatus"),
  bodyTunePart: document.getElementById("bodyTunePart"),
  bodyTuneScaleX: document.getElementById("bodyTuneScaleX"),
  bodyTuneScaleY: document.getElementById("bodyTuneScaleY"),
  bodyTuneScaleZ: document.getElementById("bodyTuneScaleZ"),
  bodyTuneOffsetY: document.getElementById("bodyTuneOffsetY"),
  bodyTuneZOffset: document.getElementById("bodyTuneZOffset"),
  btnBodyTunePrevPart: document.getElementById("btnBodyTunePrevPart"),
  btnBodyTuneNextPart: document.getElementById("btnBodyTuneNextPart"),
  btnBodyTuneSave: document.getElementById("btnBodyTuneSave"),
  btnBodyTuneSaveNext: document.getElementById("btnBodyTuneSaveNext"),
  btnBodyTuneReset: document.getElementById("btnBodyTuneReset"),
  btnBodyTuneToFit: document.getElementById("btnBodyTuneToFit"),
  bodyTuneStepButtons: Array.from(document.querySelectorAll("[data-body-step-target]")),
};

const textureLoader = new THREE.TextureLoader();
const meshGeometryCache = new Map();

const previewCards = [];
const previewCardMap = new Map();
let currentSuitPath = "";
let currentSuit = null;
let lastSummary = null;
let isSyncingTuneControls = false;
let generationRun = null;
let hasUnsavedSuitChanges = false;
let latestTrialSnapshot = { state: "missing", replayPath: "", eventCount: 0, replayReady: false };
let lastGenerationSnapshot = null;
let suitRegistrySnapshot = { suitId: "", recallCode: "", status: "missing", manifestId: "", storagePath: "" };

const OPERATOR_PROFILE_DEFAULTS = {
  protect_archetype: "citizens",
  temperament_bias: "calm",
  color_mood: "industrial_gray",
  note: "",
};

const OPERATOR_PROFILE_LABELS = {
  protect_archetype: {
    one_person: "たった一人",
    companions: "仲間",
    citizens: "人々",
    truth: "真実",
    future: "未来",
    legacy: "継承",
  },
  temperament_bias: {
    calm: "静かに守る",
    straight: "まっすぐ進む",
    fierce: "激しく押し切る",
    gentle: "やさしく支える",
    stoic: "黙って耐える",
    noble: "高潔に立つ",
  },
  color_mood: {
    clear_white: "澄んだ白",
    midnight_blue: "深い青",
    industrial_gray: "機械グレー",
    abyssal_teal: "深海ティール",
    burnt_red: "焼けた赤",
    signal_amber: "信号アンバー",
  },
};

function apiPath(path) {
  return path;
}

async function fetchJson(path, options = undefined) {
  const res = await fetch(apiPath(path), options);
  const data = await res.json();
  return { res, data };
}

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

const DEFAULT_VRM_CANDIDATES = [
  "viewer/assets/vrm/default.vrm",
  "viewer/assets/vrm/default.glb",
  "viewer/assets/vrm/default.gltf",
];

let gltfLoaderModulePromise = null;

function setStatus(text, isError = false) {
  UI.status.textContent = text;
  UI.status.style.color = isError ? "#9c1b2f" : "#17335f";
}

function setLatestTrialStatus(text, state = "") {
  if (!UI.latestTrialStatus) return;
  UI.latestTrialStatus.classList.remove("complete", "pending", "error");
  if (state) UI.latestTrialStatus.classList.add(state);
  UI.latestTrialStatus.textContent = text;
}

function formatTrialTimestamp(value) {
  if (!value) return "未取得";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ja-JP", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function compactLabel(value, maxLength = 32) {
  const text = String(value || "-");
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(4, maxLength - 4))}...`;
}

function renderLatestTrialEmpty(message = "HENSHIN TRIAL未記録") {
  latestTrialSnapshot = { state: "missing", replayPath: "", eventCount: 0, replayReady: false };
  setLatestTrialStatus(message, "pending");
  if (UI.latestTrialUpdated) UI.latestTrialUpdated.textContent = "未取得";
  if (UI.latestTrialSession) UI.latestTrialSession.textContent = "-";
  if (UI.latestTrialState) UI.latestTrialState.textContent = "-";
  if (UI.latestTrialEvents) UI.latestTrialEvents.textContent = "-";
  if (UI.latestTrialReplayState) UI.latestTrialReplayState.textContent = "-";
  if (UI.latestTrialReplay) UI.latestTrialReplay.textContent = "Replay Archive: -";
  updateQuestPreflight();
}

function renderLatestTrial(data) {
  const summary = data?.summary || {};
  const sessionId = summary.session_id || data?.trial_id || data?.trial?.session_id || "-";
  const state = summary.state || data?.trial?.state || "-";
  const eventCount = summary.event_count ?? data?.trial?.events?.length ?? "-";
  const replayPath = summary.replay_script_path || data?.trial?.artifacts?.replay_script_path || "";
  const isComplete = state === "ACTIVE" && Boolean(replayPath);
  latestTrialSnapshot = { state, replayPath, eventCount, replayReady: isComplete };

  setLatestTrialStatus(isComplete ? "変身試験完了 / Replay Archive保存済み" : `HENSHIN TRIAL進行: ${state}`, isComplete ? "complete" : "pending");
  if (UI.latestTrialUpdated) UI.latestTrialUpdated.textContent = `更新: ${formatTrialTimestamp(summary.updated_at)}`;
  if (UI.latestTrialSession) {
    UI.latestTrialSession.textContent = compactLabel(sessionId, 28);
    UI.latestTrialSession.title = sessionId;
  }
  if (UI.latestTrialState) UI.latestTrialState.textContent = state;
  if (UI.latestTrialEvents) UI.latestTrialEvents.textContent = String(eventCount);
  if (UI.latestTrialReplayState) UI.latestTrialReplayState.textContent = replayPath ? "保存済み" : "未生成";
  if (UI.latestTrialReplay) {
    UI.latestTrialReplay.textContent = `Replay Archive: ${replayPath || "-"}`;
    UI.latestTrialReplay.title = replayPath || "";
  }
  updateQuestPreflight();
}

async function refreshLatestTrial({ silent = false } = {}) {
  if (!UI.latestTrialStatus) return;
  if (UI.btnRefreshLatestTrial) UI.btnRefreshLatestTrial.disabled = true;
  if (!silent) setLatestTrialStatus("HENSHIN TRIALを取得中...", "pending");
  try {
    const { res, data } = await fetchJson("/v1/trials/latest");
    if (res.status === 404) {
      renderLatestTrialEmpty("HENSHIN TRIAL未記録");
      return;
    }
    if (!res.ok || data.ok === false) {
      throw new Error(data.error || `Latest trial fetch failed: ${res.status}`);
    }
    renderLatestTrial(data);
  } catch (err) {
    setLatestTrialStatus("HENSHIN TRIAL取得エラー", "error");
    if (UI.latestTrialUpdated) UI.latestTrialUpdated.textContent = "取得失敗";
    if (UI.latestTrialReplay) UI.latestTrialReplay.textContent = `error: ${String(err?.message || err)}`;
  } finally {
    if (UI.btnRefreshLatestTrial) UI.btnRefreshLatestTrial.disabled = false;
  }
}

function setSuitRegistryStatus(text, state = "pending") {
  if (!UI.suitRegistryStatus) return;
  UI.suitRegistryStatus.classList.remove("complete", "pending", "error");
  UI.suitRegistryStatus.classList.add(state);
  UI.suitRegistryStatus.textContent = text;
}

function renderSuitRegistryPending(message = "登録待機中") {
  suitRegistrySnapshot = {
    suitId: currentSuit?.suit_id || "",
    recallCode: "",
    status: "missing",
    manifestId: "",
    storagePath: "",
  };
  if (UI.suitRegistryRecallCode) UI.suitRegistryRecallCode.textContent = "----";
  if (UI.suitRegistryIssueId) UI.suitRegistryIssueId.textContent = currentSuit?.suit_id || "-";
  if (UI.suitRegistryState) UI.suitRegistryState.textContent = "未登録";
  if (UI.suitRegistryStorage) UI.suitRegistryStorage.textContent = "未保存";
  setSuitRegistryStatus(message, "pending");
}

function renderSuitRegistry(data) {
  const suit = data?.suit || {};
  const metadata = suit.metadata || {};
  const suitId = suit.suit_id || currentSuit?.suit_id || "";
  const recallCode = data?.recall_code || suit.recall_code || metadata.issue?.recall_code || "";
  const manifestId = suit.manifest_id || "";
  const hasSuitspec = Boolean(data?.suitspec);
  const status = manifestId ? "manifest_ready" : hasSuitspec ? "suitspec_saved" : "issued";
  suitRegistrySnapshot = {
    suitId,
    recallCode,
    status,
    manifestId,
    storagePath: data?.storage?.path || suit.artifacts?.suitspec_path || "",
  };
  if (UI.suitRegistryRecallCode) {
    UI.suitRegistryRecallCode.textContent = recallCode || "----";
    UI.suitRegistryRecallCode.title = recallCode ? "Questで入力する4桁コード" : "";
  }
  if (UI.suitRegistryIssueId) {
    UI.suitRegistryIssueId.textContent = compactLabel(suitId || "-", 22);
    UI.suitRegistryIssueId.title = suitId || "";
  }
  if (UI.suitRegistryName && metadata.display_name && !UI.suitRegistryName.value.trim()) {
    UI.suitRegistryName.value = metadata.display_name;
  }
  if (UI.suitRegistryStorage) {
    UI.suitRegistryStorage.textContent = suitRegistrySnapshot.storagePath
      ? compactLabel(suitRegistrySnapshot.storagePath, 44)
      : "registry予約";
    UI.suitRegistryStorage.title = suitRegistrySnapshot.storagePath || "";
  }
  if (UI.suitRegistryState) {
    UI.suitRegistryState.textContent = manifestId
      ? `Manifest ${compactLabel(manifestId, 18)}`
      : hasSuitspec
        ? "SuitSpec保存済み"
        : "番号発行済み";
  }
  setSuitRegistryStatus(
    manifestId ? "Quest呼び出し準備OK" : hasSuitspec ? "SuitSpec保存済み / Manifest未発行" : "番号発行済み / SuitSpec未保存",
    manifestId ? "complete" : "pending"
  );
}

async function refreshSuitRegistry({ silent = false } = {}) {
  if (!UI.suitRegistryStatus) return null;
  const suitId = currentSuit?.suit_id || "";
  if (!suitId) {
    renderSuitRegistryPending("SuitSpecに番号がありません");
    return null;
  }
  if (!silent) setSuitRegistryStatus("呼び出し確認中...", "pending");
  const { res, data } = await fetchJson(`/v1/suits/${encodeURIComponent(suitId)}`);
  if (res.status === 404) {
    renderSuitRegistryPending("未登録 / 成立済み保存待ち");
    return null;
  }
  if (!data.ok) {
    throw new Error(data.error || `Suit registry fetch failed: ${res.status}`);
  }
  renderSuitRegistry(data);
  return data;
}

async function issueSuitRegistryId() {
  const displayName = UI.suitRegistryName?.value?.trim() || "";
  const { res, data } = await fetchJson("/v1/suits/issue-id", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ series: "AXIS", role: "OP", rev: 0, display_name: displayName }),
  });
  if (!data.ok) {
    throw new Error(data.error || `番号発行に失敗しました: ${res.status}`);
  }
  if (currentSuit) {
    currentSuit.suit_id = data.suit_id;
    markSuitDirty("Quest入力コードを発行しました。SuitSpec保存で内部IDを固定します。");
  }
  renderSuitRegistry({ suit: data.suit, suitspec: null, storage: data.storage });
  return data;
}

async function saveSuitRegistry() {
  if (!currentSuit) {
    throw new Error("登録する SuitSpec がありません。");
  }
  syncOperatorProfileToSuit();
  if (hasUnsavedSuitChanges) {
    await saveCurrentSuit();
    markSuitSaved("SuitSpecを保存しました。");
  }
  const displayName = UI.suitRegistryName?.value?.trim() || "";
  const { res, data } = await fetchJson("/v1/suits", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ suitspec: currentSuit, display_name: displayName, overwrite: true }),
  });
  if (!data.ok) {
    throw new Error(data.error || `Suit registry save failed: ${res.status}`);
  }
  const manifestResponse = await fetchJson(`/v1/suits/${encodeURIComponent(data.suit_id)}/manifest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "READY" }),
  });
  if (!manifestResponse.data.ok) {
    renderSuitRegistry({ suit: data.suit, suitspec: data.suitspec, storage: data.storage });
    throw new Error(manifestResponse.data.error || `Manifest発行に失敗しました: ${manifestResponse.res.status}`);
  }
  renderSuitRegistry({
    suit: manifestResponse.data.suit,
    suitspec: data.suitspec,
    storage: manifestResponse.data.storage,
  });
  return manifestResponse.data;
}

function bodyTunePartNames() {
  return Array.from(UI.bodyTunePart?.options || []).map((option) => option.value);
}

function bodyTunePartIndex(partName = UI.bodyTunePart?.value) {
  return bodyTunePartNames().indexOf(partName);
}

function updateBodyTuneNavigation() {
  const names = bodyTunePartNames();
  const index = bodyTunePartIndex();
  if (UI.btnBodyTunePrevPart) UI.btnBodyTunePrevPart.disabled = index <= 0;
  if (UI.btnBodyTuneNextPart) UI.btnBodyTuneNextPart.disabled = index < 0 || index >= names.length - 1;
  const disabled = !names.length;
  if (UI.btnBodyTuneSave) UI.btnBodyTuneSave.disabled = disabled;
  if (UI.btnBodyTuneSaveNext) UI.btnBodyTuneSaveNext.disabled = disabled;
  if (UI.btnBodyTuneReset) UI.btnBodyTuneReset.disabled = disabled;
}

function updateBodyTuneStatus(message = "") {
  if (!UI.bodyTuneStatus) return;
  const partName = UI.bodyTunePart?.value || "";
  const state = hasUnsavedSuitChanges ? "SuitSpec未保存" : "保存済み";
  const lead = partName ? `調整中: ${partName} | ${state}` : "調整対象なし";
  const detail =
    message ||
    (partName
      ? hasUnsavedSuitChanges
        ? "見た目には反映済みです。保存で確定します。"
        : "数値を動かすと即時にプレビューへ反映されます。"
      : "SuitSpecを読み込むと調整できます。");
  UI.bodyTuneStatus.textContent = `${lead}\n${detail}`;
  updateBodyTuneNavigation();
}

function markSuitDirty(message = "") {
  hasUnsavedSuitChanges = true;
  updateBodyTuneStatus(message);
  if (suitRegistrySnapshot.status !== "missing") {
    setSuitRegistryStatus("SuitSpec未保存 / 再登録待ち", "pending");
    if (UI.suitRegistryState) UI.suitRegistryState.textContent = "未保存変更あり";
  }
  updateQuestPreflight();
}

function markSuitSaved(message = "") {
  hasUnsavedSuitChanges = false;
  updateBodyTuneStatus(message);
  updateQuestPreflight();
}

function setBodyTunePart(partName, { announce = false } = {}) {
  if (!partName || !currentSuit?.modules?.[partName]) return false;
  UI.bodyTunePart.value = partName;
  UI.fitPart.value = partName;
  UI.vrmPart.value = partName;
  loadFitEditor(partName);
  if (announce) {
    setStatus(`フィッティング対象を切り替えました: ${partName}`);
  }
  return true;
}

function moveBodyTunePart(direction) {
  const names = bodyTunePartNames();
  const index = bodyTunePartIndex();
  if (index < 0) return false;
  const nextIndex = clamp(index + direction, 0, names.length - 1);
  if (nextIndex === index) return false;
  return setBodyTunePart(names[nextIndex], { announce: true });
}

function decimalPlaces(stepValue) {
  const step = String(stepValue || "");
  if (!step.includes(".")) return 0;
  return step.split(".")[1].length;
}

function nudgeNumberInput(input, delta) {
  if (!input) return;
  const current = Number(input.value || "0");
  if (!Number.isFinite(current)) return;
  let value = current + delta;
  const min = Number(input.min);
  const max = Number(input.max);
  if (Number.isFinite(min)) value = Math.max(min, value);
  if (Number.isFinite(max)) value = Math.min(max, value);
  input.value = value.toFixed(decimalPlaces(input.step));
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function appendEventLog(text) {
  if (!UI.eventLog) return;
  const lines = String(UI.eventLog.textContent || "")
    .split("\n")
    .filter(Boolean)
    .slice(-10);
  lines.push(text);
  UI.eventLog.textContent = lines.join("\n");
  UI.eventLog.scrollTop = UI.eventLog.scrollHeight;
}

function eventLabel(type) {
  const map = {
    job_started: "ジョブ開始",
    wave_started: "Wave開始",
    part_started: "部位生成開始",
    part_completed: "部位生成完了",
    part_failed: "部位生成失敗",
    hero_started: "ポスター生成開始",
    hero_completed: "ポスター生成完了",
    hero_failed: "ポスター生成失敗",
    provider_progress: "生成進行",
    job_completed: "ジョブ完了",
    job_failed: "ジョブ失敗",
    job_cancelled: "ジョブ停止",
  };
  return map[type] || type || "ログ";
}

function setStageSummary(summary, meta = "") {
  if (UI.stageSummary) UI.stageSummary.textContent = summary;
  if (UI.stageMeta) UI.stageMeta.textContent = meta;
}

function isRuntimeTexturePath(path) {
  return /^sessions[\\/]/.test(String(path || ""));
}

function formatFitContract(suitspec) {
  const contract = suitspec?.fit_contract || {};
  const stage = contract.module_fit_stage || "missing";
  const space = contract.module_fit_space || "missing";
  return `${stage} / ${space}`;
}

function formatTextureFallback(suitspec) {
  const fallback = suitspec?.texture_fallback || {};
  const mode = fallback.mode || "missing";
  const source = fallback.source || "missing";
  return `${mode} / ${source}`;
}

function textureFallbackAllowsPalette(suitspec) {
  return suitspec?.texture_fallback?.mode === "palette_material";
}

function textureStatusLabel(suitspec, module) {
  if (!module?.texture_path) return "Texture: none";
  if (isRuntimeTexturePath(module.texture_path) && textureFallbackAllowsPalette(suitspec)) {
    return "Texture: runtime + palette fallback";
  }
  return "Texture: linked";
}

function renderRouteContractStatus(suitspec) {
  if (!UI.routeContractStatus) return;
  UI.routeContractStatus.textContent = [
    `FIT CONTRACT: ${formatFitContract(suitspec)}`,
    `TEXTURE FALLBACK: ${formatTextureFallback(suitspec)}`,
  ].join("\n");
  UI.routeContractStatus.classList.toggle(
    "is-warning",
    !suitspec?.fit_contract || !suitspec?.texture_fallback
  );
}

function setQuestPreflightStatus(text, state = "pending") {
  if (!UI.questPreflightStatus) return;
  UI.questPreflightStatus.classList.remove("complete", "pending", "error");
  UI.questPreflightStatus.classList.add(state);
  UI.questPreflightStatus.textContent = text;
}

function setQuestPreflightLine(node, text, state = "pending") {
  if (!node) return;
  node.classList.remove("complete", "pending", "error");
  node.classList.add(state);
  node.textContent = text;
}

function moduleTextureReady(module) {
  return Boolean(module?.texture_path);
}

function suitHasFitContract(suitspec) {
  const contract = suitspec?.fit_contract || {};
  return Boolean(contract.module_fit_stage && contract.module_fit_space);
}

function suitHasTextureFallback(suitspec) {
  const fallback = suitspec?.texture_fallback || {};
  return Boolean(fallback.mode && fallback.source);
}

function updateQuestPreflight() {
  if (!UI.questPreflightStatus) return;

  const enabled = currentSuit ? readEnabledModules(currentSuit) : [];
  const totalParts = enabled.length;
  const textureReadyCount = enabled.filter(([, module]) => moduleTextureReady(module)).length;
  const allTexturesReady = totalParts > 0 && textureReadyCount === totalParts;
  const fitReady = suitHasFitContract(currentSuit);
  const fallbackReady = suitHasTextureFallback(currentSuit);
  const replayReady = Boolean(latestTrialSnapshot?.replayReady);
  const generationSnapshot = lastGenerationSnapshot || {};

  let generationText = currentSuit ? `既存 ${textureReadyCount}/${totalParts}` : "未読込";
  let generationState = allTexturesReady ? "complete" : "pending";
  if (generationRun) {
    generationText = `生成中 ${generationRun.completed.size}/${generationRun.requestedParts.length}`;
    generationState = "pending";
  } else if (generationSnapshot.status === "completed") {
    const completed = generationSnapshot.generatedCount ?? generationSnapshot.completedCount ?? textureReadyCount;
    const requested = generationSnapshot.requestedCount || totalParts || completed;
    generationText = generationSnapshot.suitspecApplied === false ? `完了 ${completed}/${requested} / 未反映` : `完了 ${completed}/${requested}`;
    generationState = generationSnapshot.suitspecApplied === false ? "pending" : "complete";
  } else if (generationSnapshot.status === "failed" || generationSnapshot.status === "cancelled") {
    generationText = generationSnapshot.status === "cancelled" ? "停止済み" : `失敗 ${generationSnapshot.errorCount || 1}部位`;
    generationState = "error";
  }

  let diffText = currentSuit ? (UI.useCache?.checked ? "Cache ON" : "Cache OFF") : "未確認";
  let diffState = "pending";
  if (generationRun) {
    diffText = "実行中";
  } else if (generationSnapshot.status === "completed" || generationSnapshot.status === "failed") {
    const generatedCount = Number(generationSnapshot.generatedCount || 0);
    const cacheHitCount = Number(generationSnapshot.cacheHitCount || 0);
    const fallbackUsedCount = Number(generationSnapshot.fallbackUsedCount || 0);
    const updatedCount = Math.max(0, generatedCount - cacheHitCount - fallbackUsedCount);
    diffText = `更新 ${updatedCount} / Cache ${cacheHitCount} / 予備 ${fallbackUsedCount}`;
    diffState = generationSnapshot.status === "failed" ? "error" : "complete";
  }

  const fitText = !currentSuit
    ? "未読込"
    : hasUnsavedSuitChanges
      ? "未保存"
      : fitReady && fallbackReady
        ? "OK"
        : `要確認 ${fitReady ? "Fit" : "Fitなし"} / ${fallbackReady ? "Fallback" : "Fallbackなし"}`;
  const fitState = !currentSuit ? "pending" : hasUnsavedSuitChanges ? "pending" : fitReady && fallbackReady ? "complete" : "error";
  const replayText = replayReady ? `保存済み ${latestTrialSnapshot.eventCount ?? "-"}ev` : "未生成 / 試験後保存";
  const replayState = replayReady ? "complete" : "pending";

  setQuestPreflightLine(UI.questPreflightGeneration, generationText, generationState);
  setQuestPreflightLine(UI.questPreflightDiff, diffText, diffState);
  setQuestPreflightLine(UI.questPreflightFit, fitText, fitState);
  setQuestPreflightLine(UI.questPreflightReplay, replayText, replayState);

  const suitSpecNotApplied = generationSnapshot.status === "completed" && generationSnapshot.suitspecApplied === false;
  const blocked =
    !currentSuit ||
    generationSnapshot.status === "failed" ||
    generationSnapshot.status === "cancelled" ||
    suitSpecNotApplied ||
    !allTexturesReady ||
    !fitReady ||
    !fallbackReady;
  const needsReview = hasUnsavedSuitChanges;
  if (generationRun) {
    setQuestPreflightStatus("Quest送信前チェック: 生成中", "pending");
  } else if (suitSpecNotApplied) {
    setQuestPreflightStatus("Quest送信前チェック: 保存未反映", "pending");
  } else if (blocked) {
    setQuestPreflightStatus("Quest送信前チェック: Quest確認 不可", "error");
  } else if (needsReview) {
    setQuestPreflightStatus("Quest送信前チェック: 要確認", "pending");
  } else {
    setQuestPreflightStatus(replayReady ? "Quest送信前チェック: Quest確認 完了" : "Quest送信前チェック: Quest確認 可", "complete");
  }
}

function setBodyStageOverlay(visible, text = "") {
  if (!UI.bodyStageOverlay) return;
  UI.bodyStageOverlay.classList.toggle("hidden", !visible);
  if (UI.bodyStageOverlayText) {
    UI.bodyStageOverlayText.textContent = text || "装甲プロトコル起動中";
  }
}

function clearHeroPoster() {
  if (UI.heroPosterPanel) UI.heroPosterPanel.classList.add("hidden");
  if (UI.heroPosterImage) UI.heroPosterImage.removeAttribute("src");
  if (UI.heroPosterMeta) UI.heroPosterMeta.textContent = "未生成";
}

function showHeroPoster(url, meta = "") {
  if (!url || !UI.heroPosterPanel || !UI.heroPosterImage) return;
  UI.heroPosterPanel.classList.remove("hidden");
  UI.heroPosterImage.src = normPath(url);
  if (UI.heroPosterMeta) UI.heroPosterMeta.textContent = meta || "生成完了";
}

function updateCardState(partName, state) {
  const card = previewCardMap.get(partName)?.card;
  if (!card) return;
  card.classList.remove("is-hidden", "is-running", "is-completed", "is-failed");
  if (state) {
    card.classList.add(`is-${state}`);
  }
}

function renderStageParts(requestedParts) {
  if (!UI.stageParts) return;
  UI.stageParts.innerHTML = "";
  for (const part of requestedParts || []) {
    const chip = document.createElement("div");
    chip.className = "stage-chip pending";
    chip.dataset.part = part;
    chip.textContent = part;
    UI.stageParts.appendChild(chip);
  }
}

function setStagePartStatus(partName, state) {
  const chip = UI.stageParts?.querySelector(`[data-part="${partName}"]`);
  if (!chip) return;
  chip.classList.remove("pending", "running", "completed", "failed");
  chip.classList.add(state || "pending");
}

function stopGenerationRun() {
  if (generationRun?.eventSource) {
    generationRun.eventSource.close();
  }
  if (generationRun?.fallbackTimer) {
    clearTimeout(generationRun.fallbackTimer);
  }
  generationRun = null;
  UI.stageScanline?.classList.remove("running");
  if (UI.btnGenerate) UI.btnGenerate.disabled = false;
  if (UI.btnCancelGenerate) UI.btnCancelGenerate.disabled = true;
}

function normPath(path) {
  let p = String(path || "").replace(/\\/g, "/").trim();
  if (!p) return p;
  if (/^https?:\/\//i.test(p)) return p;
  if (p.startsWith("/")) return p;
  if (p.startsWith("./")) p = p.slice(2);
  return `/${p}`;
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
    gltfLoaderModulePromise = import("https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/loaders/GLTFLoader.js");
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
    this.geometry = null;
    this.texture = null;
    this.textureImage = null;
    this.reliefAmplitude = Number(UI.reliefSlider.value || "0.05");
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.mesh = null;
    this.wire = null;
    this.disposed = false;

    this.tick = this.tick.bind(this);
    this.loadAssetGeometry().then(() => this.updateUvDebug());
    this.loadTextureAndRelief(this.reliefAmplitude);
  }

  ensureRenderer() {
    if (this.disposed || this.renderer) return;

    this.renderer = new THREE.WebGLRenderer({ canvas: this.meshCanvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xffffff);

    this.camera = new THREE.PerspectiveCamera(44, 1, 0.01, 50);
    this.camera.position.set(0, 0.2, 2.2);

    this.controls = new OrbitControls(this.camera, this.meshCanvas);
    this.controls.enablePan = false;
    this.controls.enableDamping = true;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 1.5;
    this.controls.target.set(0, 0, 0);

    this.scene.add(new THREE.AmbientLight(0xffffff, 0.78));
    const dir = new THREE.DirectionalLight(0xffffff, 0.86);
    dir.position.set(1.2, 1.8, 1.4);
    this.scene.add(dir);

    const geometry = this.geometry ? this.geometry.clone() : new THREE.SphereGeometry(0.5, 24, 16).toNonIndexed();
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

    fitCameraToObject(this.camera, this.controls, this.mesh, 2.15);
    this.applyCurrentTextureToMesh();
    requestAnimationFrame(this.tick);
  }

  applyGeometryToMesh(geometry) {
    if (!this.mesh || !this.wire) return;
    this.mesh.geometry.dispose();
    this.mesh.geometry = geometry.clone();
    this.mesh.userData.basePositions = new Float32Array(this.mesh.geometry.attributes.position.array);
    this.wire.geometry.dispose();
    this.wire.geometry = new THREE.EdgesGeometry(this.mesh.geometry, 18);
    fitCameraToObject(this.camera, this.controls, this.mesh, 2.15);
    this.applyCurrentTextureToMesh();
  }

  async loadAssetGeometry() {
    try {
      const geometry = await loadMeshGeometryFromAsset(this.assetPath);
      if (this.disposed) {
        geometry.dispose();
        return;
      }
      this.geometry?.dispose?.();
      this.geometry = geometry;
      this.applyGeometryToMesh(geometry);
    } catch (error) {
      console.warn(`asset mesh fallback for ${this.partName}`, error);
    }
  }

  applyCurrentTextureToMesh() {
    if (!this.mesh) return;
    if (this.texture) {
      this.mesh.material.map = this.texture;
      this.mesh.material.color.setHex(0xe7f0ff);
      this.mesh.material.needsUpdate = true;
      applyRelief(this.mesh, this.texture, this.reliefAmplitude);
      return;
    }
    restoreBase(this.mesh);
    this.mesh.material.map = null;
    this.mesh.material.color.setHex(0xdfe8f8);
    this.mesh.material.needsUpdate = true;
  }

  async loadTextureAndRelief(amplitude) {
    this.reliefAmplitude = amplitude;
    if (!this.texturePath) {
      this.texture?.dispose?.();
      this.texture = null;
      this.textureImage = null;
      this.applyCurrentTextureToMesh();
      this.updateUvDebug();
      return;
    }

    const tex = await loadTexture(this.texturePath);
    if (this.disposed) {
      tex?.dispose?.();
      return;
    }
    this.texture?.dispose?.();
    this.texture = tex;
    this.textureImage = tex?.image || null;
    this.applyCurrentTextureToMesh();
    this.updateUvDebug();
  }

  async updateTexturePath(path) {
    this.texturePath = path || null;
    await this.loadTextureAndRelief(this.reliefAmplitude);
  }

  updateRelief(amplitude) {
    this.reliefAmplitude = amplitude;
    if (this.mesh) {
      applyRelief(this.mesh, this.texture, amplitude);
    }
  }

  updateUvDebug() {
    const { w, h } = prepareCanvas(this.uvCanvas);
    const ctx = this.uvCanvas.getContext("2d");
    const geometry = this.geometry || this.mesh?.geometry || null;
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

    if (geometry) {
      drawUvWire(ctx, geometry, w, h);
    }

    const uvAreaRatio = geometry ? computeUvAreaRatio(geometry) : 0;
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
    if (this.disposed || !this.renderer || !this.camera || !this.controls || !this.scene) return;
    const w = this.meshCanvas.clientWidth || 320;
    const h = this.meshCanvas.clientHeight || 210;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    requestAnimationFrame(this.tick);
  }

  dispose() {
    this.disposed = true;
    this.texture?.dispose?.();
    this.texture = null;
    this.textureImage = null;
    if (this.mesh) {
      this.mesh.geometry?.dispose?.();
      this.mesh.material?.dispose?.();
    }
    if (this.wire) {
      this.wire.geometry?.dispose?.();
      this.wire.material?.dispose?.();
    }
    this.geometry?.dispose?.();
    this.geometry = null;
    this.controls?.dispose?.();
    if (this.renderer) {
      this.renderer.dispose?.();
      this.renderer.forceContextLoss?.();
    }
    this.renderer = null;
    this.scene = null;
    this.camera = null;
    this.controls = null;
    this.mesh = null;
    this.wire = null;
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
    if (!rec || !module || !rec.group.visible) {
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

  setPartVisible(partName, visible) {
    const rec = this.findRecord(partName);
    if (!rec) return;
    rec.group.visible = Boolean(visible);
    this.updateAnchorForPart(partName, currentSuit?.modules?.[partName]);
    this.updateMeta();
  }

  async updatePartTexture(partName, module) {
    const rec = this.findRecord(partName);
    if (!rec) return;
    rec.texture?.dispose?.();
    rec.texture = await loadTexture(module?.texture_path || null);
    if (rec.texture) {
      rec.mesh.material.map = rec.texture;
      rec.mesh.material.color.setHex(0xe8f1ff);
      rec.mesh.material.needsUpdate = true;
      applyRelief(rec.mesh, rec.texture, Number(UI.reliefSlider.value || "0.05"));
    } else {
      rec.mesh.material.map = null;
      rec.mesh.material.needsUpdate = true;
      restoreBase(rec.mesh);
    }
    this.refreshPart(partName, module);
  }

  calculateFitStats() {
    this.root.updateMatrixWorld(true);
    const byPart = new Map();
    for (const rec of this.records) {
      if (!rec.group.visible) continue;
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
      `Fit契約: ${formatFitContract(currentSuit)}`,
      `Texture fallback: ${formatTextureFallback(currentSuit)}`,
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
    checked.addEventListener("change", () => {
      updateSelectedPartsSummary();
    });
    label.appendChild(checked);
    label.append(` ${name}`);
    UI.partChecks.appendChild(label);
  }
  updateSelectedPartsSummary();
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
  if (!parts.length) {
    updateBodyTuneStatus();
    return;
  }
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
  updateBodyTuneStatus();
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
  markSuitDirty(`${partName} の見た目に反映中です。保存で確定します。`);
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
  markSuitDirty(`${partName} の詳細fitを更新しました。保存で確定します。`);
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
  markSuitDirty(`${partName} のfitを解除しました。保存で確定します。`);
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
  markSuitDirty(`${partName} のアンカーを更新しました。保存で確定します。`);
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
  markSuitDirty(`${partName} のアンカーを解除しました。保存で確定します。`);
  setStatus(`vrm_anchorを解除しました: ${partName}`);
}

async function saveCurrentSuit() {
  if (!currentSuitPath || !currentSuit) {
    throw new Error("保存対象の SuitSpec がありません。");
  }
  syncOperatorProfileToSuit();
  const { data } = await fetchJson("/api/suitspec-save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      path: currentSuitPath,
      suitspec: currentSuit,
    }),
  });
  if (!data.ok) {
    throw new Error(data.error || "SuitSpec保存に失敗しました。");
  }
  return data;
}

async function saveBodyTunePart({ moveNext = false } = {}) {
  const partName = UI.bodyTunePart.value;
  if (!partName || !currentSuit?.modules?.[partName]) {
    throw new Error("保存対象の部位がありません。");
  }
  const names = bodyTunePartNames();
  const currentIndex = bodyTunePartIndex(partName);
  const nextPart = moveNext && currentIndex >= 0 ? names[Math.min(currentIndex + 1, names.length - 1)] : partName;
  applyBodyTuneToSuit({ syncFitEditor: true, silent: true });
  await saveCurrentSuit();
  await loadSuit(currentSuitPath);
  setBodyTunePart(nextPart || partName);
  markSuitSaved(
    nextPart && nextPart !== partName
      ? `${partName} を保存しました。次は ${nextPart} を調整できます。`
      : `${partName} を保存しました。`
  );
  setStatus(
    nextPart && nextPart !== partName
      ? `${partName} を保存し、次の部位 ${nextPart} を開きました。`
      : `${partName} のフィットを保存しました。`
  );
}

function buildBodyFrontMeshMap() {
  return new Map(
    (bodyFrontPreview.records || [])
      .map((rec) => [rec.partName, rec.mesh])
      .filter(([, mesh]) => mesh && typeof mesh.updateMatrixWorld === "function")
  );
}

function applyAutoFitResultToCurrentSuit(result) {
  if (!currentSuit || !result) return false;
  applyAutoFitResultToSuitSpec(currentSuit, result);
  const enabled = readEnabledModules(currentSuit);
  renderFitPartSelector(enabled);
  renderVrmPartSelector(enabled);
  bodyFrontPreview.updateAnchors(currentSuit);
  bodyFrontPreview.updateMeta();
  if (UI.fitPart.value) {
    loadFitEditor(UI.fitPart.value);
  }
  if (UI.vrmPart.value) {
    loadVrmEditor(UI.vrmPart.value);
  }
  if (UI.bodyTunePart.value && currentSuit.modules?.[UI.bodyTunePart.value]) {
    loadBodyTuneEditor(UI.bodyTunePart.value);
  }
  return true;
}

async function autoFitCurrentSuitToVrm() {
  if (!currentSuit || !currentSuitPath) {
    throw new Error("SuitSpec を先に読込してください。");
  }
  if (!bodyFrontPreview.vrmModel) {
    await loadVrmModelFromInput({ silent: true });
  }
  if (!bodyFrontPreview.vrmModel) {
    throw new Error("VRM モデルを先に読込してください。");
  }

  const result = fitArmorToVrm({
    vrmModel: bodyFrontPreview.vrmModel,
    meshes: buildBodyFrontMeshMap(),
    suitspec: currentSuit,
    options: {
      forceTPose: true,
      resolveBone: (boneName) => bodyFrontPreview.findVrmBone(boneName),
      refinePasses: 2,
    },
  });
  applyAutoFitResultToCurrentSuit(result);
  if (!result.summary?.canSave) {
    setStatus(formatAutoFitSummary(result.summary), true);
    return result;
  }
  await saveCurrentSuit();
  await loadSuit(currentSuitPath);
  setStatus(`自動フィット保存が完了しました: ${formatAutoFitSummary(result.summary)}`);
  return result;
}

function selectedParts() {
  return Array.from(UI.partChecks.querySelectorAll("input[type='checkbox']:checked")).map((el) => el.value);
}

function updateSelectedPartsSummary() {
  if (!UI.selectedPartsSummary) return;
  const all = Array.from(UI.partChecks.querySelectorAll("input[type='checkbox']")).map((el) => el.value);
  const selected = selectedParts();
  if (all.length === 0) {
    UI.selectedPartsSummary.textContent = "対象パーツを準備中";
    return;
  }
  if (selected.length === 0) {
    UI.selectedPartsSummary.textContent = "対象パーツが未選択です";
    return;
  }
  if (selected.length === all.length) {
    UI.selectedPartsSummary.textContent = `全身 ${all.length} 部位を生成`;
    return;
  }
  const preview = selected.slice(0, 3).join(" / ");
  const suffix = selected.length > 3 ? " / ..." : "";
  UI.selectedPartsSummary.textContent = `${selected.length} / ${all.length} 部位: ${preview}${suffix}`;
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

function currentEmotionProfile({ forRequest = false } = {}) {
  const protectTarget = (UI.emotionProtectTarget?.value || "").trim();
  const vow = (UI.emotionVow?.value || "").trim();
  const scene = UI.emotionScene?.value || "urban_night";
  const profile = {
    drive: UI.emotionDrive?.value || "protect",
  };
  if (protectTarget) profile.protect_target = protectTarget;
  if (!forRequest || scene !== "urban_night") profile.scene = scene;
  if (vow) profile.vow = vow;
  return profile;
}

function currentOperatorProfile({ forRequest = false } = {}) {
  const note = (UI.operatorProfileNote?.value || "").trim();
  const profile = {
    protect_archetype: UI.operatorProtectArchetype?.value || OPERATOR_PROFILE_DEFAULTS.protect_archetype,
    temperament_bias: UI.operatorTemperamentBias?.value || OPERATOR_PROFILE_DEFAULTS.temperament_bias,
    color_mood: UI.operatorColorMood?.value || OPERATOR_PROFILE_DEFAULTS.color_mood,
  };
  if (!forRequest || note) {
    profile.note = note;
  }
  return profile;
}

function applyOperatorProfileToUi(profile = null) {
  const resolved = {
    ...OPERATOR_PROFILE_DEFAULTS,
    ...(profile || {}),
  };
  if (UI.operatorProtectArchetype) UI.operatorProtectArchetype.value = resolved.protect_archetype;
  if (UI.operatorTemperamentBias) UI.operatorTemperamentBias.value = resolved.temperament_bias;
  if (UI.operatorColorMood) UI.operatorColorMood.value = resolved.color_mood;
  if (UI.operatorProfileNote) UI.operatorProfileNote.value = resolved.note || "";
}

function syncOperatorProfileToSuit() {
  if (!currentSuit) return null;
  const profile = currentOperatorProfile({ forRequest: true });
  currentSuit.operator_profile = profile;
  return profile;
}

function formatEmotionPreview(profile) {
  if (!profile) return "";
  const lines = [];
  if (profile.drive_label) lines.push(`胸の感情: ${profile.drive_label}`);
  else if (profile.drive) lines.push(`胸の感情: ${profile.drive}`);
  if (profile.scene_label) lines.push(`立つ場所: ${profile.scene_label}`);
  else if (profile.scene) lines.push(`立つ場所: ${profile.scene}`);
  if (profile.protect_target) lines.push(`守りたいもの: ${profile.protect_target}`);
  if (profile.vow) lines.push(`誓い: ${profile.vow}`);
  if (profile.note) lines.push(`補足: ${profile.note}`);
  return lines.join("\n");
}

function formatOperatorProfilePreview(profile) {
  if (!profile) return "";
  const protect = profile.protect_archetype_label || OPERATOR_PROFILE_LABELS.protect_archetype[profile.protect_archetype] || profile.protect_archetype;
  const temperament =
    profile.temperament_bias_label || OPERATOR_PROFILE_LABELS.temperament_bias[profile.temperament_bias] || profile.temperament_bias;
  const colorMood = profile.color_mood_label || OPERATOR_PROFILE_LABELS.color_mood[profile.color_mood] || profile.color_mood;
  const lines = [
    `守る対象: ${protect}`,
    `性格: ${temperament}`,
    `色気分: ${colorMood}`,
  ];
  if (profile.note) lines.push(`補足: ${profile.note}`);
  if (profile.identity_seed) lines.push(`identity_seed: ${profile.identity_seed}`);
  return lines.join("\n");
}

function formatPreviewBlock(value) {
  if (!value || typeof value !== "object") return String(value ?? "");
  return Object.entries(value)
    .map(([key, item]) => {
      if (Array.isArray(item)) {
        const rendered = item
          .map((entry) => (entry && typeof entry === "object" ? JSON.stringify(entry) : String(entry)))
          .join(", ");
        return `${key}: ${rendered}`;
      }
      if (item && typeof item === "object") {
        return `${key}: ${JSON.stringify(item)}`;
      }
      return `${key}: ${item}`;
    })
    .join("\n");
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
  const designDna = lastSummary?.design_dna || null;
  const uvContract = lastSummary?.uv_contracts?.[part] || null;
  const runtimeOperatorProfile = lastSummary?.operator_profile_resolved || null;
  const runtimeUserArmorProfile = lastSummary?.user_armor_profile || null;
  const runtimeOperatorDefaults = lastSummary?.operator_resolved_defaults || null;
  const runtimeEmotionProfile = lastSummary?.emotion_profile_resolved || lastSummary?.emotion_profile || null;
  const runtimeEmotionDirectives = lastSummary?.emotion_directives || null;
  const runtimeStyleVariation = lastSummary?.style_variation || null;
  const runtimeResolvedDefaults = lastSummary?.resolved_defaults || null;
  const runtimeUvGuide = lastSummary?.uv_guides?.[part] || null;
  const runtimeReferenceStack = lastSummary?.generated?.[part]?.reference_stack || null;
  const generationBrief = (UI.generationBrief?.value || "").trim();
  const liveEmotionProfile = currentEmotionProfile();
  const liveOperatorProfile = currentOperatorProfile();

  const lines = [
    `[部位] ${part}`,
    "",
    "[現在の感情入力]",
    formatEmotionPreview(liveEmotionProfile),
    "",
    "[現在のユーザー固有プロフィール]",
    formatOperatorProfilePreview(liveOperatorProfile),
    "",
    "[SuitSpec の既定プロンプト]",
    specPrompt,
  ];
  if (generationBrief) {
    lines.push("", "[今回の生成指示]", generationBrief);
  }
  if (designDna) {
    lines.push("", "[スーツ設計DNA]", formatPreviewBlock(designDna));
  }
  if (runtimeOperatorProfile) {
    lines.push("", "[直近のユーザー固有プロフィール]", formatOperatorProfilePreview(runtimeOperatorProfile));
  }
  if (runtimeUserArmorProfile) {
    lines.push("", "[直近のユーザー固有武装DNA]", formatPreviewBlock(runtimeUserArmorProfile));
  }
  if (runtimeOperatorDefaults && Object.keys(runtimeOperatorDefaults).length > 0) {
    lines.push("", "[補完された武装核の既定値]", formatPreviewBlock(runtimeOperatorDefaults));
  }
  if (uvContract) {
    lines.push("", "[UV契約]", formatPreviewBlock(uvContract));
  }
  if (runtimeEmotionProfile) {
    lines.push("", "[直近の感情入力]", formatEmotionPreview(runtimeEmotionProfile));
  }
  if (runtimeEmotionDirectives) {
    lines.push("", "[感情から変換された設計指示]", formatPreviewBlock(runtimeEmotionDirectives));
  }
  if (runtimeStyleVariation) {
    lines.push("", "[感情から導いた今回差分]", formatPreviewBlock(runtimeStyleVariation));
  }
  if (runtimeResolvedDefaults && Object.keys(runtimeResolvedDefaults).length > 0) {
    lines.push("", "[補完された既定値]", formatPreviewBlock(runtimeResolvedDefaults));
  }
  if (runtimeUvGuide) {
    lines.push("", "[UVガイド参照]", formatPreviewBlock(runtimeUvGuide));
  }
  if (runtimeReferenceStack?.length) {
    lines.push("", "[参照スタック]", formatPreviewBlock(runtimeReferenceStack));
  }
  if (runtimePrompt) {
    lines.push("", "[直近の実行プロンプト]", runtimePrompt);
  }
  if (refinePrompt) {
    lines.push("", "[直近の仕上げプロンプト]", refinePrompt);
  }
  UI.promptPreview.textContent = lines.join("\n");
}

function clearPreviews() {
  for (const preview of previewCards) {
    preview.dispose();
  }
  previewCards.splice(0, previewCards.length);
  previewCardMap.clear();
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
        <small>${textureStatusLabel(suitspec, mod)}</small>
      </div>
      <div class="view-tabs">
        <button class="view-btn" data-view="mesh">3D</button>
        <button class="view-btn active" data-view="uv">UV</button>
      </div>
      <canvas class="part-canvas view-pane" data-view="mesh"></canvas>
      <canvas class="uv-canvas view-pane active" data-view="uv"></canvas>
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
    previewCardMap.set(name, { preview, card });

    for (const btn of card.querySelectorAll(".view-btn")) {
      btn.onclick = () => {
        if (btn.dataset.view === "mesh") {
          preview.ensureRenderer();
        }
        switchCardView(card, btn.dataset.view);
        if (btn.dataset.view === "uv") {
          preview.updateUvDebug();
        }
      };
    }
  }
}

async function applyGeneratedPart(partName, previewUrl) {
  if (!currentSuit?.modules?.[partName]) return;
  currentSuit.modules[partName].texture_path = previewUrl.replace(/^\//, "");
  const previewInfo = previewCardMap.get(partName);
  if (previewInfo?.preview) {
    await previewInfo.preview.updateTexturePath(currentSuit.modules[partName].texture_path);
  }
  await bodyFrontPreview.updatePartTexture(partName, currentSuit.modules[partName]);
  bodyFrontPreview.setPartVisible(partName, true);
  updateCardState(partName, "completed");
  setStagePartStatus(partName, "completed");
}

function hideRequestedParts(parts) {
  for (const part of parts || []) {
    bodyFrontPreview.setPartVisible(part, false);
    updateCardState(part, "hidden");
    setStagePartStatus(part, "pending");
  }
}

function revealFallbackShell(parts) {
  for (const part of parts || []) {
    bodyFrontPreview.setPartVisible(part, true);
    updateCardState(part, "running");
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
  const { data } = await fetchJson("/api/suitspecs");
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
  const { data } = await fetchJson(`/api/suitspec?path=${encodeURIComponent(path)}`);
  if (!data.ok) throw new Error(data.error || "SuitSpec読込に失敗しました。");

  const previousSuitPath = currentSuitPath;
  currentSuitPath = path;
  if (previousSuitPath && previousSuitPath !== currentSuitPath) {
    lastGenerationSnapshot = null;
  }
  currentSuit = data.suitspec;
  if (UI.suitRegistryName) UI.suitRegistryName.value = "";
  renderRouteContractStatus(currentSuit);
  updateQuestPreflight();
  await refreshSuitRegistry({ silent: true });
  applyOperatorProfileToUi(currentSuit?.operator_profile || null);

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

  markSuitSaved("部位を選んで数値を動かすと、プレビューへ即時反映されます。");
  updateQuestPreflight();
  setStatus(
    [
      `読込完了: ${path}`,
      `有効パーツ: ${enabled.length}`,
      `FIT CONTRACT: ${formatFitContract(currentSuit)}`,
      `TEXTURE FALLBACK: ${formatTextureFallback(currentSuit)}`,
    ].join("\n")
  );
}

function stageLabel(stage) {
  const map = {
    scan: "生成準備",
    core_materialization: "主要パーツ生成",
    full_assembly: "全身生成",
    hero_finish: "仕上げ",
    complete: "完了",
    error: "エラー",
  };
  return map[stage] || stage || "待機中";
}

function refreshGenerationMeta(event = null) {
  if (!generationRun) return;
  const nextPart =
    generationRun.requestedParts.find((part) => !generationRun.completed.has(part) && !generationRun.failed.has(part)) || "-";
  const wave = event?.wave_index || "-";
  const queuePosition = event?.queue_position ?? "-";
  const meta = [
    `ジョブ: ${generationRun.jobId || "-"}`,
    `進行: ${stageLabel(generationRun.stage)}`,
    `Wave: ${wave}`,
    `完了: ${generationRun.completed.size}/${generationRun.requestedParts.length}`,
    `次の部位: ${nextPart}`,
    `待機列: ${queuePosition}`,
  ].join("\n");
  setStageSummary(stageLabel(generationRun.stage), meta);
}

function beginGenerationState(requestedParts) {
  stopGenerationRun();
  generationRun = {
    jobId: "",
    requestedParts: requestedParts.slice(),
    completed: new Set(),
    failed: new Set(),
    stage: "scan",
    eventSource: null,
    fallbackRevealed: false,
    fallbackTimer: null,
  };
  lastGenerationSnapshot = {
    status: "running",
    requestedCount: requestedParts.length,
    completedCount: 0,
    errorCount: 0,
    cacheHitCount: 0,
    fallbackUsedCount: 0,
    suitspecApplied: false,
  };
  renderStageParts(requestedParts);
  clearHeroPoster();
  UI.stageScanline?.classList.add("running");
  if (UI.btnGenerate) UI.btnGenerate.disabled = true;
  if (UI.btnCancelGenerate) UI.btnCancelGenerate.disabled = false;
  setBodyStageOverlay(true, "装甲プロトコル起動中");
  setStageSummary("生成準備", `完了: 0/${requestedParts.length}\n次の部位: ${requestedParts[0] || "-"}`);
  UI.eventLog.textContent = "生成準備を開始しました";
  updateQuestPreflight();
  hideRequestedParts(requestedParts);
  const coreParts = ["helmet", "chest", "left_shoulder", "right_shoulder"].filter((part) => requestedParts.includes(part));
  generationRun.fallbackTimer = window.setTimeout(() => {
    if (!generationRun || generationRun.completed.size > 0 || generationRun.fallbackRevealed) return;
    generationRun.fallbackRevealed = true;
    revealFallbackShell(coreParts);
    appendEventLog("8秒経過: ベースシェルを先行表示");
    setBodyStageOverlay(true, "ベースシェルを先行表示");
  }, 8000);
}

function failGenerationStart(requestedParts, message) {
  lastGenerationSnapshot = {
    status: "failed",
    requestedCount: requestedParts.length,
    completedCount: generationRun?.completed?.size || 0,
    generatedCount: generationRun?.completed?.size || 0,
    errorCount: 1,
    cacheHitCount: 0,
    fallbackUsedCount: 0,
    suitspecApplied: false,
  };
  revealFallbackShell(requestedParts);
  stopGenerationRun();
  setBodyStageOverlay(false, "");
  updateQuestPreflight();
  setStatus(`生成開始失敗\n${message || "不明なエラー"}`, true);
}

async function completeGenerationRun(finalEvent, failed = false) {
  if (!generationRun) return;
  UI.stageScanline?.classList.remove("running");
  if (generationRun.fallbackTimer) {
    clearTimeout(generationRun.fallbackTimer);
  }
  lastSummary = null;
  if (finalEvent?.summary_path) {
    try {
      const summaryRes = await fetch(normPath(finalEvent.summary_path));
      if (summaryRes.ok) {
        lastSummary = await summaryRes.json();
      }
    } catch {
      // best effort
    }
  }
  if (lastSummary?.hero_result?.preview_url) {
    showHeroPoster(lastSummary.hero_result.preview_url, lastSummary.hero_result.provider || "hero");
  }
  if (failed) {
    revealFallbackShell(generationRun.requestedParts);
  }
  if (!failed && UI.updateSuitspec.checked) {
    await loadSuit(currentSuitPath);
  } else {
    updatePromptPreview(UI.promptPart.value, currentSuit);
    bodyFrontPreview.updateMeta();
  }
  if (!failed) {
    setStatus(
      [
        "生成完了",
        `ジョブID: ${finalEvent?.job_id || generationRun.jobId || "-"}`,
        `生成済み: ${finalEvent?.generated_count || generationRun.completed.size}`,
        `エラー: ${finalEvent?.error_count || generationRun.failed.size}`,
        `Fallback: ${finalEvent?.fallback_used_count || 0}`,
        `Cache: ${finalEvent?.cache_hit_count || 0}`,
      ].join("\n")
    );
  }
  lastGenerationSnapshot = {
    status: failed ? (finalEvent?.type === "job_cancelled" ? "cancelled" : "failed") : "completed",
    requestedCount: generationRun.requestedParts.length,
    completedCount: generationRun.completed.size,
    generatedCount: finalEvent?.generated_count ?? generationRun.completed.size,
    errorCount: finalEvent?.error_count ?? generationRun.failed.size,
    cacheHitCount: finalEvent?.cache_hit_count ?? 0,
    fallbackUsedCount: finalEvent?.fallback_used_count ?? 0,
    suitspecApplied: !failed && Boolean(UI.updateSuitspec?.checked),
  };
  stopGenerationRun();
  updateQuestPreflight();
}

async function handleGenerationEvent(event) {
  if (!generationRun) return;
  generationRun.stage = event.stage || generationRun.stage;
  refreshGenerationMeta(event);
  if (event.log) {
    appendEventLog(`${eventLabel(event.type)}: ${event.log}`);
  }

  switch (event.type) {
    case "job_started":
      generationRun.jobId = event.job_id;
      appendEventLog(`ジョブ開始: ${event.job_id}`);
      break;
    case "wave_started":
      setBodyStageOverlay(true, event.wave_index === 1 ? "主役パーツを形成中" : "装甲を全身へ展開中");
      break;
    case "part_started":
      setStagePartStatus(event.part, "running");
      updateCardState(event.part, "running");
      break;
    case "part_completed":
      generationRun.completed.add(event.part);
      if (event.preview_url) {
        await applyGeneratedPart(event.part, event.preview_url);
      } else {
        bodyFrontPreview.setPartVisible(event.part, true);
      }
      setBodyStageOverlay(generationRun.completed.size === 0, "装甲素材を形成中");
      break;
    case "part_failed":
      generationRun.failed.add(event.part);
      setStagePartStatus(event.part, "failed");
      updateCardState(event.part, "failed");
      break;
    case "hero_started":
      setBodyStageOverlay(true, "ヒーローポスターを生成中");
      break;
    case "hero_completed":
      showHeroPoster(event.preview_url, "生成完了");
      setBodyStageOverlay(false, "");
      appendEventLog("ヒーローポスターを生成しました");
      break;
    case "job_completed":
      setBodyStageOverlay(false, "");
      await completeGenerationRun(event, false);
      break;
    case "job_failed":
      setBodyStageOverlay(false, "");
      setStatus(`生成失敗\n${event.log || "不明なエラー"}`, true);
      await completeGenerationRun(event, true);
      break;
    case "job_cancelled":
      setBodyStageOverlay(false, "");
      setStatus("生成をキャンセルしました。", true);
      await completeGenerationRun(event, true);
      break;
    default:
      break;
  }
  if (lastGenerationSnapshot && generationRun) {
    lastGenerationSnapshot.completedCount = generationRun.completed.size;
    lastGenerationSnapshot.errorCount = generationRun.failed.size;
  }
  updateQuestPreflight();
}

async function openGenerationStream(jobId) {
  if (!generationRun) return;
  const source = new EventSource(apiPath(`/api/generation-jobs/${jobId}/events`));
  generationRun.eventSource = source;
  source.onmessage = (msg) => {
    const event = JSON.parse(msg.data);
    handleGenerationEvent(event).catch((err) => {
      appendEventLog(`イベント処理エラー: ${String(err)}`);
    });
  };
  source.onerror = () => {
    appendEventLog("イベント接続を再試行しています");
  };
}

async function cancelGenerate() {
  if (!generationRun?.jobId) {
    setStatus("停止対象の生成ジョブがありません。", true);
    return;
  }
  const { data } = await fetchJson(`/api/generation-jobs/${generationRun.jobId}/cancel`, {
    method: "POST",
  });
  if (!data.ok) {
    setStatus(`停止要求に失敗\n${data.error || "不明なエラー"}`, true);
    return;
  }
  appendEventLog(`停止要求を送信: ${generationRun.jobId}`);
  setStatus(`停止要求を送信しました\nジョブID: ${generationRun.jobId}`);
}

async function runGenerate() {
  if (!currentSuitPath) {
    setStatus("先に SuitSpec を読み込んでください。", true);
    return;
  }

  const requestedParts = selectedParts();
  if (requestedParts.length === 0) {
    setStatus("対象パーツを選択してください。", true);
    return;
  }
  const body = {
    suitspec: currentSuitPath,
    parts: requestedParts,
    texture_mode: UI.textureMode.value,
    uv_refine: UI.uvRefine.checked,
    fallback_dir: UI.fallbackDir.value.trim() || null,
    prefer_fallback: UI.preferFallback.checked,
    update_suitspec: UI.updateSuitspec.checked,
    provider_profile: UI.providerProfile.value,
    priority_mode: "web_service",
    use_cache: UI.useCache.checked,
    hero_render: UI.heroRender.checked,
    tracking_source: UI.trackingSource.value,
    generation_brief: UI.generationBrief.value.trim() || null,
    emotion_profile: currentEmotionProfile({ forRequest: true }),
    operator_profile_override: currentOperatorProfile({ forRequest: true }),
    max_parallel: 4,
    retry_count: 1,
  };

  beginGenerationState(requestedParts);
  setStatus("生成ジョブを作成中...");

  let data = null;
  try {
    const response = await fetchJson("/api/generation-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    data = response.data;
  } catch (err) {
    failGenerationStart(requestedParts, String(err?.message || err || "不明なエラー"));
    return;
  }

  if (!data.ok) {
    failGenerationStart(requestedParts, data.error || "不明なエラー");
    return;
  }

  generationRun.jobId = data.job_id;
  appendEventLog(`ジョブ受付: ${data.job_id}`);
  refreshGenerationMeta();
  await openGenerationStream(data.job_id);
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

  if (UI.btnRefreshLatestTrial) {
    UI.btnRefreshLatestTrial.onclick = async () => {
      await refreshLatestTrial();
    };
  }

  if (UI.btnIssueSuitId) {
    UI.btnIssueSuitId.onclick = async () => {
      try {
        const data = await issueSuitRegistryId();
        setStatus(`Quest入力コードを発行しました: ${data.recall_code} / ${data.suit_id}`);
      } catch (err) {
        setStatus(String(err?.message || err || "番号発行に失敗しました"), true);
      }
    };
  }

  if (UI.btnSaveSuitRegistry) {
    UI.btnSaveSuitRegistry.onclick = async () => {
      try {
        const data = await saveSuitRegistry();
        setStatus(`成立済みスーツを保存しました: ${suitRegistrySnapshot.recallCode || data.recall_code || "----"} / ${data.suit_id} / ${data.manifest_id}`);
      } catch (err) {
        setStatus(String(err?.message || err || "スーツ登録に失敗しました"), true);
      }
    };
  }

  if (UI.btnFetchSuitRegistry) {
    UI.btnFetchSuitRegistry.onclick = async () => {
      try {
        await refreshSuitRegistry();
        setStatus(`呼び出し確認を更新しました: ${suitRegistrySnapshot.recallCode || "----"} / ${currentSuit?.suit_id || "-"}`);
      } catch (err) {
        setStatus(String(err?.message || err || "呼び出し確認に失敗しました"), true);
      }
    };
  }

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

  UI.btnCancelGenerate.onclick = async () => {
    try {
      await cancelGenerate();
    } catch (err) {
      setStatus(String(err), true);
    }
  };

  if (UI.btnAutoFitSave) {
    UI.btnAutoFitSave.onclick = async () => {
      try {
        await autoFitCurrentSuitToVrm();
      } catch (err) {
        setStatus(String(err?.message || err || "自動フィットに失敗しました"), true);
      }
    };
  }

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
    setBodyTunePart(part);
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

  if (UI.btnBodyTunePrevPart) {
    UI.btnBodyTunePrevPart.onclick = () => {
      moveBodyTunePart(-1);
    };
  }

  if (UI.btnBodyTuneNextPart) {
    UI.btnBodyTuneNextPart.onclick = () => {
      moveBodyTunePart(1);
    };
  }

  if (UI.btnBodyTuneSave) {
    UI.btnBodyTuneSave.onclick = async () => {
      try {
        await saveBodyTunePart({ moveNext: false });
      } catch (err) {
        setStatus(String(err?.message || err || "フィット保存に失敗しました"), true);
      }
    };
  }

  if (UI.btnBodyTuneSaveNext) {
    UI.btnBodyTuneSaveNext.onclick = async () => {
      try {
        await saveBodyTunePart({ moveNext: true });
      } catch (err) {
        setStatus(String(err?.message || err || "フィット保存に失敗しました"), true);
      }
    };
  }

  if (UI.btnBodyTuneReset) {
    UI.btnBodyTuneReset.onclick = () => {
      const part = UI.bodyTunePart.value;
      if (!part) return;
      UI.fitPart.value = part;
      resetFitForPart();
      loadBodyTuneEditor(part);
    };
  }

  UI.btnBodyTuneToFit.onclick = () => {
    const part = UI.bodyTunePart.value;
    if (!part) return;
    UI.fitPart.value = part;
    loadFitEditor(part);
    if (UI.advancedSettings) UI.advancedSettings.open = true;
    UI.advancedSettings?.scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus(`詳細調整を開きました: ${part}`);
  };

  for (const button of UI.bodyTuneStepButtons || []) {
    button.onclick = () => {
      const target = button.dataset.bodyStepTarget;
      const delta = Number(button.dataset.bodyStepDelta || "0");
      const input = document.getElementById(target);
      nudgeNumberInput(input, delta);
    };
  }

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

  if (UI.generationBrief) {
    UI.generationBrief.oninput = () => {
      updatePromptPreview(UI.promptPart.value, currentSuit);
    };
  }
  for (const key of [
    "operatorProtectArchetype",
    "operatorTemperamentBias",
    "operatorColorMood",
    "operatorProfileNote",
  ]) {
    if (UI[key]) {
      const handler = () => {
        syncOperatorProfileToSuit();
        markSuitDirty("武装核を更新しました。保存すると恒常プロフィールとして固定されます。");
        updatePromptPreview(UI.promptPart.value, currentSuit);
      };
      UI[key].oninput = handler;
      UI[key].onchange = handler;
    }
  }
  for (const key of ["emotionDrive", "emotionScene", "emotionProtectTarget", "emotionVow"]) {
    if (UI[key]) {
      UI[key].oninput = () => {
        updatePromptPreview(UI.promptPart.value, currentSuit);
      };
      UI[key].onchange = () => {
        updatePromptPreview(UI.promptPart.value, currentSuit);
      };
    }
  }

  for (const btn of UI.tabButtons) {
    btn.onclick = () => activateTab(btn.dataset.tab || "parts");
  }
}

async function init() {
  populateVrmBoneOptions();
  bindEvents();
  activateTab("parts");
  clearHeroPoster();
  if (UI.btnCancelGenerate) UI.btnCancelGenerate.disabled = true;
  if (UI.eventLog) UI.eventLog.textContent = "進行ログを待機中...";
  renderLatestTrialEmpty();
  void refreshLatestTrial({ silent: true });

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
