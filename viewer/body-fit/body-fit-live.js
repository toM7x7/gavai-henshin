export const POSE_IDX = {
  NOSE: 0,
  LEFT_SHOULDER: 11,
  RIGHT_SHOULDER: 12,
  LEFT_ELBOW: 13,
  RIGHT_ELBOW: 14,
  LEFT_WRIST: 15,
  RIGHT_WRIST: 16,
  LEFT_HIP: 23,
  RIGHT_HIP: 24,
  LEFT_KNEE: 25,
  RIGHT_KNEE: 26,
  LEFT_ANKLE: 27,
  RIGHT_ANKLE: 28,
};

export const LIVE_POSE_OPTIONS = Object.freeze({
  minVisibility: 0.52,
  minPresence: 0.35,
  minJointCount: 7,
  minUpperBodyJointCount: 5,
  smoothGain: 14.0,
  maxJointJump: 0.38,
  holdFramesOnMissing: 5,
  bodyScaleEmaGain: 1.1,
  bodyScaleCompRange: [0.82, 1.22],
  syntheticTorsoDropRatio: 1.35,
  syntheticHipWidthRatio: 0.72,
  minPoseDetectionConfidence: 0.6,
  minPosePresenceConfidence: 0.6,
  minTrackingConfidence: 0.6,
});

const LIVE_POSE_MODEL_CANDIDATES = [
  {
    name: "full",
    path: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task",
  },
  {
    name: "lite",
    path: "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
  },
];

function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

function toNumberOr(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normToWorld(x01, y01, mirror = true) {
  const xNorm = mirror ? 1 - x01 : x01;
  const x = xNorm * 2 - 1;
  const y = -(y01 * 2 - 1);
  return { x, y };
}

function normToWorld3(x01, y01, zRaw = 0, mirror = true) {
  const p2 = normToWorld(x01, y01, mirror);
  const z = clamp(toNumberOr(zRaw, 0), -1.2, 1.2) * 0.45 + 0.22;
  return { x: p2.x, y: p2.y, z };
}

function midpoint3(a, b) {
  if (!a || !b) return null;
  return {
    x: (a.x + b.x) * 0.5,
    y: (a.y + b.y) * 0.5,
    z: (toNumberOr(a.z, 0.22) + toNumberOr(b.z, 0.22)) * 0.5,
  };
}

function distance3(a, b) {
  if (!a || !b) return 0;
  const dz = toNumberOr(a.z, 0.22) - toNumberOr(b.z, 0.22);
  return Math.hypot(a.x - b.x, a.y - b.y, dz);
}

export function estimateLiveBodyScale(joints) {
  const shoulderWidth = distance3(joints.left_shoulder, joints.right_shoulder);
  const hipWidth = distance3(joints.left_hip, joints.right_hip);
  const torsoHeight = distance3(joints.shoulders_center, joints.hips_center);
  const measures = [shoulderWidth, hipWidth, torsoHeight].filter((v) => Number.isFinite(v) && v > 0.05);
  if (!measures.length) return 0;
  return measures.reduce((sum, v) => sum + v, 0) / measures.length;
}

function isReliableLandmark(landmark, minVisibility, minPresence) {
  if (!landmark) return false;
  if (!Number.isFinite(landmark.x) || !Number.isFinite(landmark.y)) return false;
  if (Number.isFinite(landmark.visibility) && landmark.visibility < minVisibility) return false;
  if (Number.isFinite(landmark.presence) && landmark.presence < minPresence) return false;
  return true;
}

export function extractPoseJointsWorld(landmarks, options = {}) {
  const minVisibility = toNumberOr(options.minVisibility, LIVE_POSE_OPTIONS.minVisibility);
  const minPresence = toNumberOr(options.minPresence, LIVE_POSE_OPTIONS.minPresence);
  const pick = (index) => landmarks?.[index] || null;
  const joints = {};

  const nose = pick(POSE_IDX.NOSE);
  const lShoulder = pick(POSE_IDX.LEFT_SHOULDER);
  const rShoulder = pick(POSE_IDX.RIGHT_SHOULDER);
  const lElbow = pick(POSE_IDX.LEFT_ELBOW);
  const rElbow = pick(POSE_IDX.RIGHT_ELBOW);
  const lWrist = pick(POSE_IDX.LEFT_WRIST);
  const rWrist = pick(POSE_IDX.RIGHT_WRIST);
  const lHip = pick(POSE_IDX.LEFT_HIP);
  const rHip = pick(POSE_IDX.RIGHT_HIP);
  const lKnee = pick(POSE_IDX.LEFT_KNEE);
  const rKnee = pick(POSE_IDX.RIGHT_KNEE);
  const lAnkle = pick(POSE_IDX.LEFT_ANKLE);
  const rAnkle = pick(POSE_IDX.RIGHT_ANKLE);

  if (isReliableLandmark(nose, minVisibility, minPresence)) {
    joints.nose = normToWorld3(nose.x, nose.y, nose.z, true);
  }
  if (isReliableLandmark(lShoulder, minVisibility, minPresence)) {
    joints.left_shoulder = normToWorld3(lShoulder.x, lShoulder.y, lShoulder.z, true);
  }
  if (isReliableLandmark(rShoulder, minVisibility, minPresence)) {
    joints.right_shoulder = normToWorld3(rShoulder.x, rShoulder.y, rShoulder.z, true);
  }
  if (isReliableLandmark(lElbow, minVisibility, minPresence)) {
    joints.left_elbow = normToWorld3(lElbow.x, lElbow.y, lElbow.z, true);
  }
  if (isReliableLandmark(rElbow, minVisibility, minPresence)) {
    joints.right_elbow = normToWorld3(rElbow.x, rElbow.y, rElbow.z, true);
  }
  if (isReliableLandmark(lWrist, minVisibility, minPresence)) {
    joints.left_wrist = normToWorld3(lWrist.x, lWrist.y, lWrist.z, true);
  }
  if (isReliableLandmark(rWrist, minVisibility, minPresence)) {
    joints.right_wrist = normToWorld3(rWrist.x, rWrist.y, rWrist.z, true);
  }
  if (isReliableLandmark(lHip, minVisibility, minPresence)) {
    joints.left_hip = normToWorld3(lHip.x, lHip.y, lHip.z, true);
  }
  if (isReliableLandmark(rHip, minVisibility, minPresence)) {
    joints.right_hip = normToWorld3(rHip.x, rHip.y, rHip.z, true);
  }
  if (isReliableLandmark(lKnee, minVisibility, minPresence)) {
    joints.left_knee = normToWorld3(lKnee.x, lKnee.y, lKnee.z, true);
  }
  if (isReliableLandmark(rKnee, minVisibility, minPresence)) {
    joints.right_knee = normToWorld3(rKnee.x, rKnee.y, rKnee.z, true);
  }
  if (isReliableLandmark(lAnkle, minVisibility, minPresence)) {
    joints.left_ankle = normToWorld3(lAnkle.x, lAnkle.y, lAnkle.z, true);
  }
  if (isReliableLandmark(rAnkle, minVisibility, minPresence)) {
    joints.right_ankle = normToWorld3(rAnkle.x, rAnkle.y, rAnkle.z, true);
  }

  const shouldersCenter = midpoint3(joints.left_shoulder, joints.right_shoulder);
  if (shouldersCenter) {
    joints.shoulders_center = shouldersCenter;
  }
  const hipsCenter = midpoint3(joints.left_hip, joints.right_hip);
  if (hipsCenter) {
    joints.hips_center = hipsCenter;
  }
  if (!joints.nose && joints.shoulders_center) {
    joints.nose = {
      x: joints.shoulders_center.x,
      y: joints.shoulders_center.y + 0.28,
      z: joints.shoulders_center.z + 0.02,
    };
  }
  return joints;
}

export function createDefaultLiveState() {
  return {
    active: false,
    video: null,
    stream: null,
    landmarker: null,
    lastVideoTime: -1,
    lastNowMs: performance.now(),
    fps: 0,
    bodyScaleRef: null,
    poseModel: null,
    poseQuality: "idle",
    poseReliableJoints: 0,
  };
}

export class LiveCameraPipeline {
  constructor(modules = []) {
    this.modules = [];
    this.setModules(modules);
  }

  setModules(modules) {
    this.modules = [];
    const seen = new Set();
    for (const raw of modules || []) {
      if (!raw || typeof raw !== "object") continue;
      const name = String(raw.name || "").trim();
      if (!name || seen.has(name)) continue;
      seen.add(name);
      this.modules.push(raw);
    }
  }

  listModuleNames() {
    return this.modules.map((mod) => mod.name);
  }

  async runStart(ctx) {
    for (const mod of this.modules) {
      if (typeof mod.onStart !== "function") continue;
      try {
        await mod.onStart(ctx);
      } catch (error) {
        throw new Error(`[${mod.name}] ${String(error?.message || error || "onStart failed")}`);
      }
    }
  }

  runUpdate(ctx) {
    for (const mod of this.modules) {
      if (typeof mod.onUpdate !== "function") continue;
      try {
        mod.onUpdate(ctx);
      } catch (error) {
        throw new Error(`[${mod.name}] ${String(error?.message || error || "onUpdate failed")}`);
      }
    }
  }

  runStop(ctx) {
    for (let i = this.modules.length - 1; i >= 0; i -= 1) {
      const mod = this.modules[i];
      if (typeof mod.onStop !== "function") continue;
      try {
        mod.onStop(ctx);
      } catch (error) {
        throw new Error(`[${mod.name}] ${String(error?.message || error || "onStop failed")}`);
      }
    }
  }
}

export function createPoseLandmarkerPipelineModule(viewer) {
  const wasmBase = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";

  return {
    name: "pose-landmarker",
    async onStart(ctx) {
      const visionTasks = await import("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14");
      const vision = await visionTasks.FilesetResolver.forVisionTasks(wasmBase);
      let landmarker = null;
      let selectedModel = null;
      let lastError = null;
      for (const candidate of LIVE_POSE_MODEL_CANDIDATES) {
        try {
          landmarker = await visionTasks.PoseLandmarker.createFromOptions(vision, {
            baseOptions: { modelAssetPath: candidate.path },
            runningMode: "VIDEO",
            numPoses: 1,
            minPoseDetectionConfidence: LIVE_POSE_OPTIONS.minPoseDetectionConfidence,
            minPosePresenceConfidence: LIVE_POSE_OPTIONS.minPosePresenceConfidence,
            minTrackingConfidence: LIVE_POSE_OPTIONS.minTrackingConfidence,
          });
          selectedModel = candidate.name;
          break;
        } catch (error) {
          lastError = error;
        }
      }
      if (!landmarker) {
        throw lastError || new Error("pose landmarker model initialization failed");
      }
      ctx.live.landmarker = landmarker;
      ctx.live.poseModel = selectedModel;
      ctx.live.poseQuality = "warming";
      ctx.live.poseReliableJoints = 0;
      viewer?.refreshLiveTrackingStatus?.();
    },
    onUpdate(ctx) {
      if (!ctx.live.landmarker || !ctx.video) return;
      const result = ctx.live.landmarker.detectForVideo(ctx.video, ctx.nowMs);
      const landmarks = result?.landmarks?.[0] || null;
      ctx.poseLandmarks = landmarks;
      if (!Array.isArray(landmarks) || landmarks.length === 0) {
        ctx.live.poseQuality = "missing";
        ctx.live.poseReliableJoints = 0;
        viewer?.refreshLiveTrackingStatus?.();
      }
    },
    onStop(ctx) {
      try {
        ctx.live.landmarker?.close?.();
      } catch {
        // ignore close errors during teardown
      }
      ctx.live.landmarker = null;
    },
  };
}

export function createPoseSegmentsPipelineModule(viewer) {
  return {
    name: "pose-segments",
    onUpdate(ctx) {
      const landmarks = ctx.poseLandmarks;
      if (!Array.isArray(landmarks) || landmarks.length === 0) return;
      const liveSegments = viewer.buildLiveSegmentsFromLandmarks(landmarks, ctx.dtSec);
      if (!liveSegments || Object.keys(liveSegments).length === 0) return;
      ctx.liveSegments = liveSegments;
      viewer.applySegments(liveSegments, null);
    },
  };
}
