import {
  createBoneInferenceSnapshot,
  inferCanonicalJointsFromNamedBones,
  inferCanonicalJointsFromPoseLandmarks,
} from "./bone-inference.js";

const BODY_TRACKING_FRAME_SCHEMA_VERSION = 1;

let frameSequence = 0;

function nowMs() {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

function clonePlain(value) {
  if (value == null) return value;
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch {
      // Fall through to JSON clone for plain tracking payloads.
    }
  }
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return value;
  }
}

function nextFrameId(source, timestampMs) {
  frameSequence += 1;
  return `${String(source || "unknown")}:${Math.round(timestampMs)}:${frameSequence}`;
}

export function createBodyTrackingFrame({
  source = "unknown",
  canonicalJoints = null,
  boneInferenceSnapshot = null,
  timestampMs = nowMs(),
  frameIndex = null,
  raw = null,
  surfaceSamples = null,
  metadata = {},
} = {}) {
  const inference =
    boneInferenceSnapshot ||
    createBoneInferenceSnapshot({
      joints: canonicalJoints || {},
      source,
      options: metadata?.inferenceOptions || {},
    });
  return {
    schemaVersion: BODY_TRACKING_FRAME_SCHEMA_VERSION,
    id: nextFrameId(source, timestampMs),
    source: String(source || inference?.source || "unknown"),
    timestampMs,
    frameIndex: Number.isFinite(frameIndex) ? frameIndex : null,
    canonicalJoints: clonePlain(inference?.joints || canonicalJoints || {}),
    rawJoints: clonePlain(inference?.rawJoints || canonicalJoints || {}),
    boneInference: clonePlain(inference),
    surfaceSamples: Array.isArray(surfaceSamples) ? surfaceSamples : null,
    metadata: clonePlain(metadata || {}),
    raw: raw == null ? null : clonePlain(raw),
  };
}

export function createBodyTrackingFrameFromInference(boneInferenceSnapshot, options = {}) {
  return createBodyTrackingFrame({
    source: options.source || boneInferenceSnapshot?.source || "unknown",
    boneInferenceSnapshot,
    timestampMs: options.timestampMs,
    frameIndex: options.frameIndex,
    surfaceSamples: options.surfaceSamples,
    metadata: options.metadata,
    raw: options.raw,
  });
}

export function createBodyTrackingFrameFromPoseLandmarks(landmarks, options = {}) {
  const joints = inferCanonicalJointsFromPoseLandmarks(landmarks, {
    minVisibility: options.minVisibility,
    minPresence: options.minPresence,
    mirror: options.mirror,
  });
  const inference = createBoneInferenceSnapshot({
    joints,
    source: options.source || "webcam",
    options: options.inferenceOptions || {},
  });
  return createBodyTrackingFrame({
    source: options.source || "webcam",
    canonicalJoints: joints,
    boneInferenceSnapshot: inference,
    timestampMs: options.timestampMs,
    frameIndex: options.frameIndex,
    raw: { landmarks },
    surfaceSamples: options.surfaceSamples,
    metadata: {
      model: options.model || "mediapipe-pose",
      ...options.metadata,
    },
  });
}

export function createBodyTrackingFrameFromNamedBones(namedBones, options = {}) {
  const joints = inferCanonicalJointsFromNamedBones(namedBones, options);
  const inference = createBoneInferenceSnapshot({
    joints,
    source: options.source || "named-bones",
    options: options.inferenceOptions || {},
  });
  return createBodyTrackingFrame({
    source: options.source || "named-bones",
    canonicalJoints: joints,
    boneInferenceSnapshot: inference,
    timestampMs: options.timestampMs,
    frameIndex: options.frameIndex,
    raw: { namedBones },
    surfaceSamples: options.surfaceSamples,
    metadata: {
      bridge: options.bridge || null,
      ...options.metadata,
    },
  });
}

