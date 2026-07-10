import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const RECALL_CODE_RE = /^[A-Z0-9]{4}$/;
const DEFAULT_URL = "http://127.0.0.1:5173/viewer/quest-iw-demo/";
const DEFAULT_API_BASE = "";
const DEFAULT_OUTPUT_ROOT = "output/playwright/replay-armor-alignment";
const DEFAULT_SAMPLES = [0.25, 0.5, 0.75, 1];
const VALID_TRIGGERS = new Set(["both", "mock-voice", "replay", "none"]);
const VALID_VIEW_MODES = new Set(["self", "mirror", "observer"]);

function usage() {
  return `
Usage:
  node tools/verify_replay_armor_alignment.mjs --code 3601

Options:
  --url <url>             Quest viewer URL. Default: ${DEFAULT_URL}
  --code <code>           4-character recall code to load, e.g. 3601.
  --api-base <url>        API/dashboard origin for /v1 calls. Default: same-origin viewer proxy
  --output-dir <path>     Artifact directory. Default: ${DEFAULT_OUTPUT_ROOT}/<code>-<timestamp>
  --trigger <mode>        both | mock-voice | replay | none. Default: both
  --view-mode <mode>      self | mirror | observer for replay sampling. Default: mirror
  --samples <list>        Comma-separated progress values, e.g. 0.25,0.5,1
  --max-settled-excess-m <number>
                          Fail if settled visible-part excess is above this. Default: 0.05
  --min-measured-parts <number>
                          Fail if fewer visible armor parts are measured. Default: 3
  --timeout-ms <number>   Browser wait timeout. Default: 90000
  --headed                Run a headed browser.
  --help                  Show this help.
`;
}

function parseArgs(argv) {
  const options = {
    url: DEFAULT_URL,
    code: "",
    apiBase: DEFAULT_API_BASE,
    outputDir: "",
    trigger: "both",
    viewMode: "mirror",
    samples: DEFAULT_SAMPLES,
    maxSettledExcessM: 0.05,
    minMeasuredParts: 3,
    timeoutMs: 90000,
    headed: false,
  };

  for (let index = 2; index < argv.length; index += 1) {
    const token = argv[index];
    const next = argv[index + 1];
    if (token === "--help" || token === "-h") {
      options.help = true;
    } else if (token === "--headed") {
      options.headed = true;
    } else if (token === "--url" && next) {
      options.url = next;
      index += 1;
    } else if (token === "--code" && next) {
      options.code = String(next).toUpperCase();
      index += 1;
    } else if (token === "--api-base" && next) {
      options.apiBase = next;
      index += 1;
    } else if (token === "--output-dir" && next) {
      options.outputDir = next;
      index += 1;
    } else if (token === "--trigger" && next) {
      options.trigger = next;
      index += 1;
    } else if (token === "--view-mode" && next) {
      options.viewMode = next;
      index += 1;
    } else if (token === "--samples" && next) {
      options.samples = parseSamples(next);
      index += 1;
    } else if (token === "--max-settled-excess-m" && next) {
      options.maxSettledExcessM = Number(next);
      index += 1;
    } else if (token === "--min-measured-parts" && next) {
      options.minMeasuredParts = Number(next);
      index += 1;
    } else if (token === "--timeout-ms" && next) {
      options.timeoutMs = Number(next);
      index += 1;
    } else {
      throw new Error(`Unknown or incomplete option: ${token}`);
    }
  }

  if (options.help) return options;
  if (options.code && !RECALL_CODE_RE.test(options.code)) {
    throw new Error(`--code must be exactly 4 uppercase alphanumeric characters: ${options.code}`);
  }
  if (!VALID_TRIGGERS.has(options.trigger)) {
    throw new Error(`--trigger must be one of: ${Array.from(VALID_TRIGGERS).join(", ")}`);
  }
  if (!VALID_VIEW_MODES.has(options.viewMode)) {
    throw new Error(`--view-mode must be one of: ${Array.from(VALID_VIEW_MODES).join(", ")}`);
  }
  if (!Number.isFinite(options.timeoutMs) || options.timeoutMs <= 0) {
    throw new Error("--timeout-ms must be a positive number.");
  }
  if (!options.samples.length) {
    throw new Error("--samples must contain at least one progress value.");
  }
  if (!Number.isFinite(options.maxSettledExcessM) || options.maxSettledExcessM < 0) {
    throw new Error("--max-settled-excess-m must be a non-negative number.");
  }
  if (!Number.isInteger(options.minMeasuredParts) || options.minMeasuredParts < 1) {
    throw new Error("--min-measured-parts must be a positive integer.");
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const suffix = `${options.code || "local"}-${timestamp}`;
  options.outputDir = path.resolve(options.outputDir || path.join(DEFAULT_OUTPUT_ROOT, suffix));
  return options;
}

function parseSamples(value) {
  return String(value)
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((number) => Number.isFinite(number))
    .map((number) => Math.max(0, Math.min(1, number)));
}

function sampleLabel(progress) {
  return `p${String(Math.round(progress * 100)).padStart(3, "0")}`;
}

function buildQuestUrl(options) {
  const url = new URL(options.url);
  url.searchParams.set("newRoute", "1");
  url.searchParams.set("qa", "1");
  url.searchParams.set("debug", "1");
  url.searchParams.set("mockTrigger", "1");
  url.searchParams.set("mic", "0");
  url.searchParams.set("replayView", options.viewMode);
  if (options.apiBase) url.searchParams.set("apiBase", options.apiBase);
  if (options.code) url.searchParams.set("code", options.code);
  url.searchParams.set("alignmentProbe", Date.now().toString());
  return url.toString();
}

async function launchBrowser(headed) {
  const attempts = [
    { channel: process.env.HENSHIN_PLAYWRIGHT_CHANNEL || "msedge", headless: !headed },
    { channel: "chrome", headless: !headed },
    { headless: !headed },
  ];
  let lastError = null;
  for (const attempt of attempts) {
    try {
      return await chromium.launch(attempt);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error("Unable to launch a Chromium-compatible browser.");
}

async function ensureDemoReady(page, timeoutMs) {
  await page.waitForFunction(
    () => typeof window.__questHenshinDemo?.loadSuitByRecallCode === "function",
    null,
    { timeout: timeoutMs },
  );
}

async function loadRecallCode(page, code, timeoutMs) {
  if (!code) return { skipped: true };
  const result = await page.evaluate(async (recallCode) => {
    const demo = window.__questHenshinDemo;
    await demo.loadSuitByRecallCode(recallCode, { reloadMeshes: true, pushUrl: true });
    return {
      recallCode: demo.recallCode,
      suitId: demo.activeSuitId,
      manifestId: demo.activeManifestId,
      meshes: demo.meshes?.size || 0,
      equipmentState: demo.equipmentDiagnostic?.state || "",
    };
  }, code);
  await page.waitForFunction(
    () => (window.__questHenshinDemo?.meshes?.size || 0) > 0,
    null,
    { timeout: timeoutMs },
  );
  return result;
}

async function triggerMockVoice(page) {
  return page.evaluate(async () => {
    const demo = window.__questHenshinDemo;
    demo.setArmorStandPreview(false);
    demo.reset();
    await demo.runVoiceCommand();
    return {
      voiceState: demo.voiceState,
      playing: demo.playing,
      playbackSource: demo.playbackSource,
      replayMotionSource: demo.replayMotionSource,
      replayMotionDiagnostic: demo.replayMotionDiagnostic,
      replayLoaded: Boolean(demo.replay),
      debug: document.getElementById("voiceDebug")?.textContent || "",
    };
  });
}

async function triggerReplay(page, viewMode) {
  return page.evaluate(async (mode) => {
    const demo = window.__questHenshinDemo;
    if (!demo.replay && !(demo.archiveMotionFrames?.length) && typeof demo.applyReplay === "function") {
      const replayPath =
        new URLSearchParams(window.location.search).get("replay")
        || "/sessions/S-IW-DEMO/artifacts/iwsdk-deposition-replay.json";
      const response = await fetch(replayPath);
      if (!response.ok) throw new Error(`Unable to load archive replay ${replayPath}: ${response.status}`);
      await demo.applyReplay(await response.json(), {
        speak: false,
        autoplay: false,
        viewMode: mode,
        source: "archive",
      });
    }
    demo.setArmorStandPreview(false);
    demo.replayFromStart({ speak: false, audio: false, viewMode: mode, source: "archive" });
    return {
      voiceState: demo.voiceState,
      playing: demo.playing,
      playbackSource: demo.playbackSource,
      replayLoaded: Boolean(demo.replay),
      archiveMotionFrames: demo.archiveMotionFrames?.length || 0,
      replayMotionSource: demo.replayMotionSource,
      replayMotionDiagnostic: demo.replayMotionDiagnostic,
    };
  }, viewMode);
}

async function collectAlignmentSample(page, progress, viewMode) {
  return page.evaluate(
    ({ progress: nextProgress, viewMode: nextViewMode }) => {
      const demo = window.__questHenshinDemo;
      const mapBasePart = (part) => {
        if (part === "helmet") return "head";
        if (part === "chest" || part === "back") return "torso";
        if (part === "waist") return "pelvis";
        if (part.endsWith("_shoulder") || part.endsWith("_upperarm")) {
          return part.startsWith("left_") ? "left_upperarm" : "right_upperarm";
        }
        if (part.endsWith("_forearm") || part.endsWith("_hand")) {
          return part.startsWith("left_") ? "left_forearm" : "right_forearm";
        }
        if (part.endsWith("_thigh")) return part.startsWith("left_") ? "left_thigh" : "right_thigh";
        if (part.endsWith("_shin") || part.endsWith("_boot")) {
          return part.startsWith("left_") ? "left_shin" : "right_shin";
        }
        return "";
      };
      const vector = (value) => [
        Number(value?.x || 0),
        Number(value?.y || 0),
        Number(value?.z || 0),
      ].map((number) => Number(number.toFixed(5)));
      const delta = (a, b) => a.map((value, index) => Number((value - b[index]).toFixed(5)));
      const distance = (values) => Number(Math.hypot(values[0], values[1], values[2]).toFixed(5));
      const alignmentAllowance = (part) => {
        if (part === "back") return 0.6;
        if (part.endsWith("_shoulder")) return 0.3;
        if (part.endsWith("_hand")) return 0.25;
        if (part.endsWith("_boot")) return 0.24;
        if (part === "waist" || part.endsWith("_thigh") || part.endsWith("_shin")) return 0.22;
        return 0.18;
      };
      const worldPosition = (object) => {
        const target = object.position.clone();
        object.getWorldPosition(target);
        return vector(target);
      };
      const geometrySize = (geometry) => {
        geometry?.computeBoundingBox?.();
        const box = geometry?.boundingBox;
        if (!box) return null;
        return vector(box.max.clone().sub(box.min));
      };
      const targetSize = (placement) => {
        if (Array.isArray(placement?.target_size_array_m)) {
          return placement.target_size_array_m.slice(0, 3).map((number) => Number(Number(number).toFixed(5)));
        }
        const record = placement?.target_size_m;
        if (record && typeof record === "object") {
          return ["x", "y", "z"].map((axis) => Number(Number(record[axis] || 0).toFixed(5)));
        }
        return null;
      };
      const nearestBase = (armorLocal, baseParts, part) => {
        const mappedPart = mapBasePart(part);
        const mapped = baseParts.find((entry) => entry.baseSuitPart === mappedPart);
        if (mapped) return mapped;
        let best = null;
        for (const entry of baseParts) {
          const diff = delta(armorLocal, entry.localPosition);
          const length = distance(diff);
          if (!best || length < best.distance) best = { ...entry, distance: length };
        }
        return best;
      };
      const objectDebugSnapshot = (object) => {
        if (!object) return null;
        object.updateMatrixWorld?.(true);
        return {
          name: object.name || "",
          visible: Boolean(object.visible),
          childCount: object.children?.length || 0,
          localPosition: vector(object.position),
          worldPosition: worldPosition(object),
          scale: vector(object.scale),
          rotation: vector(object.rotation || { x: 0, y: 0, z: 0 }),
        };
      };
      const elementText = (id) => document.getElementById(id)?.textContent?.trim() || "";
      const elementValue = (id) => document.getElementById(id)?.value || "";
      const elementClass = (id) => document.getElementById(id)?.className || "";
      const elementDisabled = (id) => Boolean(document.getElementById(id)?.disabled);
      const fallbackExperienceSnapshot = () => {
        const xrSession = Boolean(demo.world?.session);
        const currentViewMode = demo.xrViewMode || nextViewMode;
        const playing = Boolean(demo.playing);
        const armorStandPreview = Boolean(demo.armorStandPreview);
        const playbackSource = demo.playbackSource || "";
        const loadedMeshes = demo.meshes?.size || 0;
        const progress = Number(Number(demo.duration ? demo.elapsed / demo.duration : nextProgress).toFixed(3));
        let uxState = loadedMeshes ? "loaded_idle" : "no_suit_idle";
        if (!xrSession) {
          uxState = loadedMeshes ? "browser_loaded_idle" : "browser_no_suit_idle";
        } else if (armorStandPreview && !playing && currentViewMode === "observer") {
          uxState = "armor_stand_observer_idle";
        } else if (playing && playbackSource === "archive" && currentViewMode === "mirror") {
          uxState = "archive_replay_mirror_active";
        } else if (playing && playbackSource === "archive" && currentViewMode === "observer") {
          uxState = "archive_replay_observer_active";
        } else if (playing && currentViewMode === "self") {
          uxState = "transform_active_self";
        } else if (!playing && !armorStandPreview && currentViewMode === "mirror") {
          uxState = "mirror_idle";
        } else if (!playing && !armorStandPreview && currentViewMode === "self" && loadedMeshes) {
          uxState = "loaded_idle_self";
        } else if (!playing && !armorStandPreview && currentViewMode === "observer") {
          uxState = "observer_idle";
        } else if (playing) {
          uxState = "transform_active";
        }
        return {
          uxState,
          voiceState: demo.voiceState || "",
          playbackSource,
          viewMode: currentViewMode,
          xrSession,
          armorStandPreview,
          loadedMeshes,
          progress,
          shouldExpectMirror: uxState === "archive_replay_mirror_active" || uxState === "mirror_idle",
          shouldExpectArmorStand: uxState === "armor_stand_observer_idle",
          shouldExpectBaseSuitGuide: uxState === "transform_active_self" || uxState === "archive_replay_mirror_active",
          realMicrophoneExpected: false,
          ui: {
            status: elementText("status"),
            equipState: elementText("equipState"),
            micState: elementText("micState"),
            voiceLine: elementText("voiceLine"),
            voiceDebug: elementText("voiceDebug"),
            recallCodeInput: elementValue("recallCodeInput"),
            recallCodeState: elementText("recallCodeState"),
            equipmentStatus: elementText("equipmentStatus"),
            meterFillWidth: document.getElementById("meterFill")?.style?.width || "",
            routeMode: { text: elementText("routeMode"), className: elementClass("routeMode") },
            routeApi: { text: elementText("routeApi"), className: elementClass("routeApi") },
            routeTrial: { text: elementText("routeTrial"), className: elementClass("routeTrial") },
            routeReplay: { text: elementText("routeReplay"), className: elementClass("routeReplay") },
            routeContract: { text: elementText("routeContract"), className: elementClass("routeContract") },
            buttons: {
              voiceDisabled: elementDisabled("btnVoice"),
              replayDisabled: elementDisabled("btnReplay"),
              replayViewDisabled: elementDisabled("btnReplayView"),
              pauseDisabled: elementDisabled("btnPause"),
              resetDisabled: elementDisabled("btnReset"),
              loadRecallCodeDisabled: elementDisabled("btnLoadRecallCode"),
            },
            routeState: {
              apiLabel: demo.routeState?.apiLabel || "",
              apiState: demo.routeState?.apiState || "",
              trialLabel: demo.routeState?.trialLabel || "",
              trialState: demo.routeState?.trialState || "",
              replayLabel: demo.routeState?.replayLabel || "",
              replayState: demo.routeState?.replayState || "",
            },
            replayLoaded: Boolean(demo.replay),
            replayMotionSource: demo.replayMotionSource || "",
            completionAnnounced: Boolean(demo.completionAnnounced),
          },
        };
      };

      demo.xrViewMode = nextViewMode;
      demo.setArmorStandPreview(false);
      demo.playing = true;
      demo.elapsed = Math.max(0, Math.min(demo.duration || 0, (demo.duration || 0) * nextProgress));
      demo.completionAnnounced = nextProgress >= 1;
      demo.updateScene(0);
      demo.rig?.updateMatrixWorld?.(true);
      demo.baseSuitGroup?.updateMatrixWorld?.(true);

      const baseParts = Array.from(demo.baseSuitGroup?.children || []).map((child) => ({
        name: child.name,
        baseSuitPart: child.userData?.baseSuitPart || child.name,
        visible: Boolean(child.visible),
        localPosition: vector(child.position),
        worldPosition: worldPosition(child),
        scale: vector(child.scale),
      }));

      const parts = Array.from(demo.meshes?.entries?.() || []).map(([part, mesh]) => {
        mesh.updateMatrixWorld?.(true);
        const placement = mesh.userData?.runtimePlacement || mesh.userData?.module?.runtime_placement || null;
        const armorLocal = vector(mesh.position);
        const armorWorld = worldPosition(mesh);
        const base = nearestBase(armorLocal, baseParts, part);
        const localDelta = base ? delta(armorLocal, base.localPosition) : null;
        const worldDelta = base ? delta(armorWorld, base.worldPosition) : null;
        const distanceM = localDelta ? distance(localDelta) : null;
        const allowanceM = Number(alignmentAllowance(part).toFixed(5));
        const excessDistanceM = distanceM == null ? null : Number(Math.max(0, distanceM - allowanceM).toFixed(5));
        return {
          part,
          visible: Boolean(mesh.visible),
          opacity: Number(Number(mesh.material?.opacity ?? 0).toFixed(5)),
          armorLocalPosition: armorLocal,
          armorWorldPosition: armorWorld,
          basePart: base?.baseSuitPart || null,
          baseLocalPosition: base?.localPosition || null,
          baseWorldPosition: base?.worldPosition || null,
          localDeltaM: localDelta,
          worldDeltaM: worldDelta,
          distanceM,
          alignmentAllowanceM: allowanceM,
          excessDistanceM,
          meshSource: mesh.userData?.meshSource || "",
          assetRef: mesh.userData?.assetRef || "",
          loadedAssetRef: mesh.userData?.loadedAssetRef || "",
          selectedVariantKey: mesh.userData?.module?.selected_variant_key || "",
          runtimePlacement: placement
            ? {
                coordinateSpace: placement.coordinate_space || "",
                questCoordinateSpace: placement.quest_coordinate_space || "",
                offsetM: Array.isArray(placement.offset_m) ? placement.offset_m.slice(0, 3) : null,
                questRigOffsetM: Array.isArray(placement.quest_rig_offset_m)
                  ? placement.quest_rig_offset_m.slice(0, 3)
                  : null,
                rotationDeg: Array.isArray(placement.rotation_deg) ? placement.rotation_deg.slice(0, 3) : null,
                targetSizeM: targetSize(placement),
              }
            : null,
          scale: vector(mesh.scale),
          geometrySize: geometrySize(mesh.geometry),
          normalizedSize: Array.isArray(mesh.userData?.normalizedSize) ? mesh.userData.normalizedSize.slice(0, 3) : null,
          meshError: mesh.userData?.meshError || "",
        };
      });

      const measuredParts = parts.filter((part) => part.visible && Number(part.opacity || 0) > 0.01);
      const maxDistance = measuredParts.reduce((max, part) => Math.max(max, Number(part.distanceM || 0)), 0);
      const maxExcessDistance = measuredParts.reduce((max, part) => Math.max(max, Number(part.excessDistanceM || 0)), 0);
      const visibleParts = parts.filter((part) => part.visible).length;
      const progressValue = Number(
        Number(demo.duration ? demo.elapsed / demo.duration : nextProgress).toFixed(5),
      );
      const debugSnapshot = typeof demo.collectQuestDebugSnapshot === "function"
        ? demo.collectQuestDebugSnapshot("alignment-sample")
        : null;
      const liveMirrorSnapshot = debugSnapshot?.liveMirror || {};
      const liveMirrorGroup = objectDebugSnapshot(demo.liveMirror) || {};
      const fallbackExperience = fallbackExperienceSnapshot();
      const experience = debugSnapshot?.experience || fallbackExperience;
      const uxState = debugSnapshot?.uxState || experience?.uxState || fallbackExperience.uxState;
      const debug = {
        viewMode: demo.xrViewMode,
        playing: Boolean(demo.playing),
        progress: progressValue,
        uxState,
        experience,
        armorStandPreview: Boolean(demo.armorStandPreview),
        microphone: debugSnapshot?.microphone || null,
        baseShell: debugSnapshot?.baseShell || {
          visible: Boolean(demo.baseSuitGroup?.visible),
          childCount: baseParts.length,
          children: baseParts,
        },
        depositionEffects: debugSnapshot?.depositionEffects || {
          visible: Boolean(demo.depositionEffects?.group?.visible),
          pointsOpacity: Number(Number(demo.depositionEffects?.points?.material?.opacity ?? 0).toFixed(5)),
          sparksOpacity: Number(Number(demo.depositionEffects?.sparks?.material?.opacity ?? 0).toFixed(5)),
          pointsSize: Number(Number(demo.depositionEffects?.points?.material?.size ?? 0).toFixed(5)),
        },
        mirrorFrame: objectDebugSnapshot(demo.mirrorFrame),
        liveMirror: {
          ...liveMirrorSnapshot,
          ...liveMirrorGroup,
          ready: Boolean(demo.liveMirrorReady),
          meshCount: demo.liveMirrorMeshes?.size ?? liveMirrorSnapshot.meshCount ?? 0,
          visibleCount: liveMirrorSnapshot.visibleCount ?? 0,
          records: liveMirrorSnapshot.records || [],
        },
      };
      return {
        label: `p${String(Math.round(nextProgress * 100)).padStart(3, "0")}`,
        progress: Number(nextProgress.toFixed(5)),
        elapsedSec: Number(Number(demo.elapsed || 0).toFixed(5)),
        durationSec: Number(Number(demo.duration || 0).toFixed(5)),
        viewMode: demo.xrViewMode,
        playbackSource: demo.playbackSource,
        playing: Boolean(demo.playing),
        recallCode: demo.recallCode || "",
        suitId: demo.activeSuitId || "",
        manifestId: demo.activeManifestId || "",
        replayMotionSource: demo.replayMotionSource || "",
        replayMotionDiagnostic: demo.replayMotionDiagnostic || null,
        equipmentDiagnostic: demo.equipmentDiagnostic || null,
        debug,
        baseParts,
        parts,
        summary: {
          partCount: parts.length,
          visibleParts,
          measuredParts: measuredParts.length,
          maxDistanceM: Number(maxDistance.toFixed(5)),
          maxExcessDistanceM: Number(maxExcessDistance.toFixed(5)),
          averageDistanceM: Number(
            (
              measuredParts.reduce((sum, part) => sum + Number(part.distanceM || 0), 0)
              / Math.max(1, measuredParts.length)
            ).toFixed(5),
          ),
          averageExcessDistanceM: Number(
            (
              measuredParts.reduce((sum, part) => sum + Number(part.excessDistanceM || 0), 0)
              / Math.max(1, measuredParts.length)
            ).toFixed(5),
          ),
        },
      };
    },
    { progress, viewMode },
  );
}

function csvEscape(value) {
  if (value == null) return "";
  const text = Array.isArray(value) ? value.join(" ") : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function renderCsv(samples) {
  const header = [
    "sample",
    "progress",
    "part",
    "visible",
    "base_part",
    "distance_m",
    "allowance_m",
    "excess_distance_m",
    "delta_x_m",
    "delta_y_m",
    "delta_z_m",
    "armor_x_m",
    "armor_y_m",
    "armor_z_m",
    "base_x_m",
    "base_y_m",
    "base_z_m",
    "mesh_source",
    "asset_ref",
    "loaded_asset_ref",
    "selected_variant_key",
    "target_size_m",
    "scale",
  ];
  const rows = [header];
  for (const sample of samples) {
    for (const part of sample.parts) {
      rows.push([
        sample.label,
        sample.progress,
        part.part,
        part.visible,
        part.basePart,
        part.distanceM,
        part.alignmentAllowanceM,
        part.excessDistanceM,
        ...(part.localDeltaM || ["", "", ""]),
        ...(part.armorLocalPosition || ["", "", ""]),
        ...(part.baseLocalPosition || ["", "", ""]),
        part.meshSource,
        part.assetRef,
        part.loadedAssetRef,
        part.selectedVariantKey,
        part.runtimePlacement?.targetSizeM || "",
        part.scale || "",
      ]);
    }
  }
  return `${rows.map((row) => row.map(csvEscape).join(",")).join("\n")}\n`;
}

function aggregateSampleSummary(samples) {
  if (!samples.length) {
    return {
      sampleCount: 0,
      partCount: 0,
      measuredPartCount: 0,
      maxDistanceM: 0,
      maxExcessDistanceM: 0,
      averageDistanceM: 0,
      averageExcessDistanceM: 0,
    };
  }
  return {
    sampleCount: samples.length,
    partCount: samples[0]?.parts?.length || 0,
    measuredPartCount: Math.max(...samples.map((sample) => sample.summary.measuredParts), 0),
    maxDistanceM: Number(Math.max(...samples.map((sample) => sample.summary.maxDistanceM), 0).toFixed(5)),
    maxExcessDistanceM: Number(
      Math.max(...samples.map((sample) => sample.summary.maxExcessDistanceM), 0).toFixed(5),
    ),
    averageDistanceM: Number(
      (
        samples.reduce((sum, sample) => sum + sample.summary.averageDistanceM, 0) / Math.max(1, samples.length)
      ).toFixed(5),
    ),
    averageExcessDistanceM: Number(
      (
        samples.reduce((sum, sample) => sum + sample.summary.averageExcessDistanceM, 0)
        / Math.max(1, samples.length)
      ).toFixed(5),
    ),
  };
}

async function main() {
  const options = parseArgs(process.argv);
  if (options.help) {
    process.stdout.write(usage());
    return;
  }

  await fs.mkdir(options.outputDir, { recursive: true });
  const browser = await launchBrowser(options.headed);
  const consoleMessages = [];
  const pageErrors = [];
  const screenshots = [];
  const questUrl = buildQuestUrl(options);

  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1040 }, deviceScaleFactor: 1 });
    page.on("console", (message) => {
      const type = message.type();
      if (["error", "warning", "info"].includes(type)) {
        consoleMessages.push({ type, text: message.text() });
      }
    });
    page.on("pageerror", (error) => pageErrors.push(String(error?.stack || error)));

    await page.goto(questUrl, { waitUntil: "domcontentloaded", timeout: options.timeoutMs });
    await ensureDemoReady(page, options.timeoutMs);
    const recall = await loadRecallCode(page, options.code, options.timeoutMs);

    const triggerResults = [];
    if (options.trigger === "both" || options.trigger === "mock-voice") {
      try {
        triggerResults.push({ trigger: "mock-voice", result: await triggerMockVoice(page) });
      } catch (error) {
        const failure = { trigger: "mock-voice", error: String(error?.message || error) };
        triggerResults.push(failure);
        if (options.trigger === "mock-voice") throw error;
      }
    }
    if (options.trigger === "both" || options.trigger === "replay") {
      triggerResults.push({ trigger: "replay", result: await triggerReplay(page, options.viewMode) });
    }

    const samples = [];
    for (const progress of options.samples) {
      const sample = await collectAlignmentSample(page, progress, options.viewMode);
      const screenshotPath = path.join(options.outputDir, `alignment-${options.viewMode}-${sampleLabel(progress)}.png`);
      await page.waitForTimeout(120);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      screenshots.push(screenshotPath);
      sample.screenshot = screenshotPath;
      samples.push(sample);
    }

    const settledSamples = samples.filter((sample) => sample.progress >= 0.5);
    const summary = aggregateSampleSummary(samples);
    const settledSummary = aggregateSampleSummary(settledSamples.length ? settledSamples : samples);
    const triggerErrors = triggerResults.filter((entry) => entry.error);
    const consoleErrors = consoleMessages.filter((entry) => entry.type === "error");
    const alignmentErrors = [];
    if (settledSummary.maxExcessDistanceM > options.maxSettledExcessM) {
      alignmentErrors.push(
        `settled excess ${settledSummary.maxExcessDistanceM}m > ${options.maxSettledExcessM}m`,
      );
    }
    if (settledSummary.measuredPartCount < options.minMeasuredParts) {
      alignmentErrors.push(
        `measured parts ${settledSummary.measuredPartCount} < ${options.minMeasuredParts}`,
      );
    }
    const report = {
      ok: pageErrors.length === 0 && consoleErrors.length === 0 && triggerErrors.length === 0 && alignmentErrors.length === 0,
      generatedAt: new Date().toISOString(),
      questUrl,
      options: {
        code: options.code,
        apiBase: options.apiBase,
        trigger: options.trigger,
        viewMode: options.viewMode,
        samples: options.samples,
        maxSettledExcessM: options.maxSettledExcessM,
        minMeasuredParts: options.minMeasuredParts,
      },
      recall,
      triggerResults,
      consoleMessages,
      pageErrors,
      screenshots,
      consoleErrors,
      triggerErrors,
      alignmentErrors,
      debugTimeline: samples.map((sample) => ({
        label: sample.label,
        progress: sample.progress,
        viewMode: sample.debug?.viewMode || sample.viewMode,
        playing: Boolean(sample.debug?.playing),
        armorStandPreview: Boolean(sample.debug?.armorStandPreview),
        baseShellVisible: Boolean(sample.debug?.baseShell?.visible),
        baseShellChildCount: sample.debug?.baseShell?.childCount || 0,
        depositionEffectsVisible: Boolean(sample.debug?.depositionEffects?.visible),
        mirrorFrameVisible: Boolean(sample.debug?.mirrorFrame?.visible),
        liveMirrorVisible: Boolean(sample.debug?.liveMirror?.visible),
        liveMirrorReady: Boolean(sample.debug?.liveMirror?.ready),
        liveMirrorVisibleCount: sample.debug?.liveMirror?.visibleCount || 0,
        microphoneCaptureEnabled: Boolean(sample.debug?.microphone?.captureEnabled),
        uxState: sample.debug?.uxState || sample.debug?.experience?.uxState || null,
        experience: sample.debug?.experience || null,
      })),
      samples,
      summary,
      settledSummary: {
        ...settledSummary,
        minProgress: settledSamples.length ? 0.5 : samples[0]?.progress ?? 0,
      },
    };

    const reportPath = path.join(options.outputDir, "alignment-report.json");
    const csvPath = path.join(options.outputDir, "alignment-parts.csv");
    await fs.writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
    await fs.writeFile(csvPath, renderCsv(samples), "utf8");

    process.stdout.write(
      `${JSON.stringify(
        {
          ok: report.ok,
          outputDir: options.outputDir,
          reportPath,
          csvPath,
          screenshots,
          maxDistanceM: report.summary.maxDistanceM,
          maxExcessDistanceM: report.summary.maxExcessDistanceM,
          settledMaxExcessDistanceM: report.settledSummary.maxExcessDistanceM,
          alignmentErrors: report.alignmentErrors,
          triggerErrors: report.triggerErrors.length,
          consoleErrors: report.consoleErrors.length,
          pageErrors: pageErrors.length,
          consoleMessages: consoleMessages.length,
        },
        null,
        2,
      )}\n`,
    );
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
